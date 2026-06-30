import httpx

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
US_BBOX = "18.91,-171.79,71.38,-66.96"  # south,west,north,east — covers contiguous US + AK + HI


async def fetch_all_dunkin_us() -> list[dict]:
    query = f"""[out:json][timeout:120];
(
  node["brand:wikidata"="Q1141226"]({US_BBOX});
  way["brand:wikidata"="Q1141226"]({US_BBOX});
);
out center;"""
    async with httpx.AsyncClient(timeout=130) as client:
        res = await client.get(
            OVERPASS_URL,
            params={"data": query},
            headers={"User-Agent": "carshow-finder/1.0"},
        )
        res.raise_for_status()
        data = res.json()

    locations = []
    seen: set[str] = set()
    for el in data.get("elements", []):
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
    return locations
