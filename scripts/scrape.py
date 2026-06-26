#!/usr/bin/env python3
"""
Scrapes carcruisefinder.com and posts car shows to the carshowfinder admin API.
Run from a non-cloud machine (local or GitHub Actions) to avoid IP blocks.

Usage:
    python scripts/scrape.py --states NJ NY PA --api http://34.138.72.24
"""

import argparse
import os
import time
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

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def build_url(target_url: str, scraperapi_key: str | None) -> str:
    if scraperapi_key:
        return f"https://api.scraperapi.com?api_key={scraperapi_key}&render=true&url={target_url}"
    return target_url


def scrape_state(state: str, scraperapi_key: str | None = None) -> list[dict]:
    slug = STATE_SLUGS.get(state.upper())
    if not slug:
        print(f"Unknown state: {state}")
        return []

    target = f"https://carcruisefinder.com/car-shows/category/{slug}/"
    url = build_url(target, scraperapi_key)
    try:
        res = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=30)
    except Exception as e:
        print(f"  Error fetching {state}: {e}")
        return []

    if res.status_code != 200:
        print(f"  {state} returned HTTP {res.status_code} — skipping")
        return []

    soup = BeautifulSoup(res.text, "lxml")

    # Debug: print snippet on first parse failure
    if not soup.select("div.event-item"):
        print(f"  DEBUG: no div.event-item found. Page snippet:")
        print(res.text[:1500])

    shows: list[dict] = []

    for item in soup.select("div.event-item"):
        link = item.select_one("h3 a")
        if not link:
            continue

        date_el = item.select_one("div.event-date span.time")
        venue_el = item.select_one("p.venue")
        location_el = item.select_one("p.location")

        date_raw = date_el.get_text(strip=True) if date_el else None
        venue = venue_el.get_text(strip=True) if venue_el else None

        city, state_abbr = None, None
        if location_el:
            parts = [p.strip() for p in location_el.get_text(strip=True).split(",")]
            if len(parts) >= 2:
                city = parts[0]
                state_abbr = parts[1].strip()

        shows.append({
            "name": link.get_text(strip=True),
            "date": date_raw,
            "venue": venue,
            "city": city,
            "state": state_abbr,
            "url": link.get("href", ""),
        })

    return shows


def post_show(api_base: str, show: dict) -> str:
    try:
        res = httpx.post(f"{api_base}/admin/shows", json=show, timeout=10)
        if res.status_code == 200:
            body = res.json()
            return "duplicate" if body.get("duplicate") else "added"
        return f"error {res.status_code}"
    except Exception as e:
        return f"error: {e}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--states", nargs="+", default=["NJ", "NY", "PA", "CT"],
                        help="State abbreviations to scrape")
    parser.add_argument("--api", default="http://34.138.72.24",
                        help="Carshowfinder API base URL")
    parser.add_argument("--scraperapi-key", default=None,
                        help="ScraperAPI key for bypassing IP blocks")
    args = parser.parse_args()

    scraperapi_key = args.scraperapi_key or os.getenv("SCRAPERAPI_KEY")
    if scraperapi_key:
        print(f"Using ScraperAPI proxy (key length: {len(scraperapi_key)})")
    else:
        print("WARNING: No ScraperAPI key — requests may be blocked")

    total_added = 0
    for state in args.states:
        print(f"\nScraping {state}...")
        shows = scrape_state(state, scraperapi_key)
        print(f"  Found {len(shows)} shows")
        for show in shows:
            status = post_show(args.api, show)
            if status == "added":
                total_added += 1
                print(f"  + {show['name']}")
            elif status == "duplicate":
                print(f"  ~ {show['name']} (already exists)")
            else:
                print(f"  ! {show['name']} ({status})")
            time.sleep(0.2)

    print(f"\nDone. {total_added} new show(s) added.")


if __name__ == "__main__":
    main()
