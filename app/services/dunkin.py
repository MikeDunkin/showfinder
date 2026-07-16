import httpx

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# Split US into a 4×3 grid of the contiguous states plus AK and HI separately.
# Each cell is small enough for Overpass to handle within its timeout.
US_BBOXES = [
    # Contiguous US — 4 columns × 3 rows (south, west, north, east)
    "24.5,-125.0,32.5,-110.0", "24.5,-110.0,32.5,-95.0",
    "24.5,-95.0,32.5,-80.0",  "24.5,-80.0,32.5,-65.0",
    "32.5,-125.0,40.5,-110.0", "32.5,-110.0,40.5,-95.0",
    "32.5,-95.0,40.5,-80.0",  "32.5,-80.0,40.5,-65.0",
    "40.5,-125.0,49.0,-110.0", "40.5,-110.0,49.0,-95.0",
    "40.5,-95.0,49.0,-80.0",  "40.5,-80.0,49.0,-65.0",
    # Alaska and Hawaii
    "51.0,-179.0,72.0,-129.0",
    "18.0,-161.0,23.0,-154.0",
]


def _make_query(bbox: str) -> str:
    return (
        f"[out:json][timeout:60];"
        f"(node[\"name\"~\"Dunkin\",i]({bbox});"
        f"way[\"name\"~\"Dunkin\",i]({bbox}););"
        f"out center;"
    )


def _parse_elements(elements: list, seen: set, locations: list) -> None:
    for el in elements:
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if not lat or not lon:
            continue
        key = f"{lat:.5f},{lon:.5f}"
        if key in seen:
            continue
        seen.add(key)
        tags = el.get("tags", {})
        locations.append({
            "osm_id": el["id"],
            "osm_type": el["type"],
            "name": tags.get("name", "Dunkin'"),
            "address": " ".join(filter(None, [
                tags.get("addr:housenumber"),
                tags.get("addr:street"),
                tags.get("addr:city"),
                tags.get("addr:state"),
            ])),
            "location": {"type": "Point", "coordinates": [lon, lat]},
        })


async def fetch_all_dunkin_us() -> list[dict]:
    locations: list[dict] = []
    seen: set[str] = set()

    async with httpx.AsyncClient(timeout=75) as client:
        for bbox in US_BBOXES:
            query = _make_query(bbox)
            fetched = False
            for url in OVERPASS_ENDPOINTS:
                try:
                    res = await client.get(url, params={"data": query}, headers={"User-Agent": "carshow-finder/1.0"})
                    res.raise_for_status()
                    data = res.json()
                    if data.get("elements") is not None:
                        _parse_elements(data["elements"], seen, locations)
                        fetched = True
                        break
                except Exception:
                    continue
            if not fetched:
                raise RuntimeError(f"All Overpass endpoints failed for bbox {bbox}")

    return locations
