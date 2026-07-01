#!/usr/bin/env python3
"""
Fetches car shows from carcruisefinder.com via The Events Calendar REST API
and posts them to the carshowfinder admin API.

Usage:
    python scripts/scrape.py --states NJ NY PA --api http://34.138.72.24
"""

import argparse
import os
import time
import httpx

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

BASE_URL = "https://carcruisefinder.com/wp-json/tribe/events/v1/events"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch_state(state: str) -> list[dict]:
    slug = STATE_SLUGS.get(state.upper())
    if not slug:
        print(f"Unknown state: {state}")
        return []

    shows = []
    page = 1
    while True:
        try:
            res = httpx.get(BASE_URL, headers=HEADERS, timeout=30, params={
                "per_page": 100,
                "page": page,
                "categories": slug,
                "start_date": time.strftime("%Y-%m-%d"),
            })
        except Exception as e:
            print(f"  Error fetching {state} page {page}: {e}")
            break

        if res.status_code == 404:
            # No events for this state/page
            break
        if res.status_code != 200:
            print(f"  {state} page {page}: HTTP {res.status_code} — skipping")
            break

        data = res.json()
        events = data.get("events", [])
        if not events:
            break

        for event in events:
            venue = event.get("venue", {})
            shows.append({
                "name": event.get("title", ""),
                "date": event.get("start_date"),
                "url": event.get("url"),
                "venue": venue.get("venue"),
                "city": venue.get("city"),
                "state": venue.get("stateprovince") or state,
                "lat": venue.get("geo_lat"),
                "lng": venue.get("geo_lng"),
            })

        total_pages = data.get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.5)

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
                        help="State abbreviations to fetch")
    parser.add_argument("--api", default="http://35.229.88.234",
                        help="Carshowfinder API base URL")
    args = parser.parse_args()

    total_added = 0
    for state in args.states:
        print(f"\nFetching {state}...")
        shows = fetch_state(state)
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
