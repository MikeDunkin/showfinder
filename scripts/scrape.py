#!/usr/bin/env python3
"""
Fetches car shows from carcruisefinder.com by scraping HTML listings
and posts them to the carshowfinder admin API.

Usage:
    python scripts/scrape.py --states NJ NY PA --api http://35.229.88.234

Requires: pip install playwright httpx && python -m playwright install chromium
"""

import argparse
import re
import time
import httpx
from playwright.sync_api import sync_playwright, Page

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


def parse_city_state(address: str) -> tuple[str | None, str | None]:
    """Extract city and state from 'City, ST, United States' format."""
    parts = [p.strip() for p in address.split(",")]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None, None


def scrape_page(page: Page, url: str, state_abbr: str) -> list[dict]:
    shows = []
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        time.sleep(2)
    except Exception as e:
        print(f"  Error loading {url}: {e}")
        return shows

    articles = page.locator("article").all()
    for article in articles:
        try:
            time_el = article.locator("time").first
            date = time_el.get_attribute("datetime") if time_el else None

            title_el = article.locator("h3 a").first
            name = title_el.inner_text().strip() if title_el else None
            event_url = title_el.get_attribute("href") if title_el else None

            venue_el = article.locator(".tribe-events-calendar-list__event-venue-title").first
            venue = venue_el.inner_text().strip() if venue_el else None

            addr_el = article.locator(".tribe-events-calendar-list__event-venue-address").first
            addr_text = addr_el.inner_text().strip() if addr_el else ""
            # Remove "SAVE EVENT" and similar trailing text
            addr_text = re.split(r"\s{2,}|\n", addr_text)[0].strip()
            city, state = parse_city_state(addr_text)

            if name and date:
                shows.append({
                    "name": name,
                    "date": date,
                    "url": event_url,
                    "venue": venue,
                    "city": city,
                    "state": state or state_abbr,
                })
        except Exception:
            continue

    return shows


def fetch_state(state: str, page: Page) -> list[dict]:
    slug = STATE_SLUGS.get(state.upper())
    if not slug:
        print(f"Unknown state: {state}")
        return []

    base_url = f"https://carcruisefinder.com/car-shows/category/{slug}/"
    all_shows = []
    page_num = 1

    while True:
        url = base_url if page_num == 1 else f"{base_url}page/{page_num}/"
        shows = scrape_page(page, url, state)
        if not shows:
            break
        all_shows.extend(shows)

        next_el = page.locator(".tribe-events-c-nav__next").all()
        if not next_el:
            break
        page_num += 1
        time.sleep(0.5)

    return all_shows


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
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        for state in args.states:
            print(f"\nFetching {state}...")
            shows = fetch_state(state, page)
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

        browser.close()

    print(f"\nDone. {total_added} new show(s) added.")


if __name__ == "__main__":
    main()
