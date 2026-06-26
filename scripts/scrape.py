#!/usr/bin/env python3
"""
Scrapes carcruisefinder.com and posts car shows to the carshowfinder admin API.
Run from a non-cloud machine (local or GitHub Actions) to avoid IP blocks.

Usage:
    python scripts/scrape.py --states NJ NY PA --api http://34.138.72.24
"""

import argparse
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


def scrape_state(state: str) -> list[dict]:
    slug = STATE_SLUGS.get(state.upper())
    if not slug:
        print(f"Unknown state: {state}")
        return []

    url = f"https://carcruisefinder.com/car-shows/category/{slug}/"
    try:
        res = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
    except Exception as e:
        print(f"  Error fetching {state}: {e}")
        return []

    if res.status_code != 200:
        print(f"  {state} returned HTTP {res.status_code} — skipping")
        return []

    soup = BeautifulSoup(res.text, "lxml")
    shows = []

    for li in soup.select("li"):
        h3 = li.find("h3")
        if not h3:
            continue
        link = h3.find("a")
        if not link:
            continue

        paragraphs = li.find_all("p")
        venue = paragraphs[0].get_text(strip=True) if len(paragraphs) > 0 else None
        city_state_raw = paragraphs[1].get_text(strip=True) if len(paragraphs) > 1 else ""
        date_raw = paragraphs[2].get_text(strip=True) if len(paragraphs) > 2 else None

        city, state_abbr = None, None
        parts = [p.strip() for p in city_state_raw.split(",")]
        if len(parts) >= 2:
            city, state_abbr = parts[0], parts[1].strip()

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
    args = parser.parse_args()

    total_added = 0
    for state in args.states:
        print(f"\nScraping {state}...")
        shows = scrape_state(state)
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
