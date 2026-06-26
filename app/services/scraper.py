import math
import asyncio
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup

STATE_SLUGS = {
    "AL": "alabama", "AK": "alaska", "AZ": "arizona", "AR": "arkansas",
    "CA": "california", "CO": "colorado", "CT": "connecticut", "DE": "delaware",
    "FL": "florida", "GA": "georgia", "HI": "hawaii", "ID": "idaho",
    "IL": "illinois", "IN": "indiana", "IA": "iowa", "KS": "kansas",
    "KY": "kentucky", "LA": "louisiana", "ME": "maine", "MD": "maryland",
    "MA": "massachusetts", "MI": "michigan", "MN": "minnesota", "MS": "mississippi",
    "MO": "missouri", "MT": "montana", "NE": "nebraska", "NV": "nevada",
    "NH": "new-hampshire", "NJ": "new-jersey", "NM": "new-mexico", "NY": "new-york",
    "NC": "north-carolina", "ND": "north-dakota", "OH": "ohio", "OK": "oklahoma",
    "OR": "oregon", "PA": "pennsylvania", "RI": "rhode-island", "SC": "south-carolina",
    "SD": "south-dakota", "TN": "tennessee", "TX": "texas", "UT": "utah",
    "VT": "vermont", "VA": "virginia", "WA": "washington", "WV": "west-virginia",
    "WI": "wisconsin", "WY": "wyoming",
}

_shows_cache: dict = {}
_geo_cache: dict = {}
_geo_lock = asyncio.Semaphore(1)
CACHE_TTL = timedelta(hours=6)


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 3956
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


async def _geocode_city(city: str, state: str) -> tuple[float, float] | None:
    key = f"{city},{state}"
    if key in _geo_cache:
        return _geo_cache[key]

    async with _geo_lock:
        if key in _geo_cache:
            return _geo_cache[key]
        await asyncio.sleep(1)  # respect Nominatim rate limit
        async with httpx.AsyncClient(timeout=8) as client:
            res = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"city": city, "state": state, "country": "US", "format": "json", "limit": 1},
                headers={"User-Agent": "carshow-finder/1.0"},
            )
            results = res.json()
            if results:
                coords = (float(results[0]["lat"]), float(results[0]["lon"]))
                _geo_cache[key] = coords
                return coords
    return None


async def _scrape_state(state_slug: str) -> list[dict]:
    if state_slug in _shows_cache:
        ts, shows = _shows_cache[state_slug]
        if datetime.now() - ts < CACHE_TTL:
            return shows

    url = f"https://carcruisefinder.com/car-shows/category/{state_slug}/"
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        res = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        print(f"[scraper] GET {url} -> {res.status_code}", flush=True)
        if res.status_code != 200:
            return []

    soup = BeautifulSoup(res.text, "lxml")

    # Try multiple selectors to handle different page structures
    candidates = (
        soup.select("article") or
        soup.select(".tribe-events-calendar li") or
        soup.select(".entry-content li") or
        soup.select("li")
    )
    print(f"[scraper] selector matched {len(candidates)} elements", flush=True)

    shows = []
    for el in candidates:
        h = el.find(["h2", "h3", "h4"])
        if not h:
            continue
        link = h.find("a")
        if not link:
            continue

        # Gather all text nodes in <p> or <span> tags as metadata
        paragraphs = el.find_all(["p", "span", "div"], recursive=False)
        if not paragraphs:
            paragraphs = el.find_all(["p"])

        texts = [t.get_text(strip=True) for t in paragraphs if t.get_text(strip=True)]

        venue = texts[0] if len(texts) > 0 else None
        city_state_raw = texts[1] if len(texts) > 1 else ""
        date_raw = texts[2] if len(texts) > 2 else None

        city, state_abbr = None, None
        parts = [p.strip() for p in city_state_raw.split(",")]
        if len(parts) >= 2:
            city = parts[0]
            state_abbr = parts[1]

        shows.append({
            "name": link.get_text(strip=True),
            "date": date_raw,
            "venue": venue,
            "city": city,
            "state": state_abbr,
            "url": link.get("href", ""),
            "lat": None,
            "lng": None,
        })

    print(f"[scraper] parsed {len(shows)} shows for {state_slug}", flush=True)
    _shows_cache[state_slug] = (datetime.now(), shows)
    return shows


async def find_car_shows(lat: float, lng: float, radius: int, state_abbr: str) -> list[dict]:
    state_slug = STATE_SLUGS.get(state_abbr.upper())
    if not state_slug:
        return []

    shows = await _scrape_state(state_slug)
    results = []

    for show in shows:
        if not show["city"] or not show["state"]:
            continue
        coords = await _geocode_city(show["city"], show["state"])
        if not coords:
            continue
        dist = _haversine(lat, lng, coords[0], coords[1])
        if dist <= radius:
            results.append({**show, "lat": coords[0], "lng": coords[1], "distance_miles": round(dist, 1)})

    results.sort(key=lambda s: s["distance_miles"])
    return results
