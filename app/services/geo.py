import httpx


async def zip_to_coords(zip_code: str) -> dict | None:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"postalcode": zip_code, "country": "US", "format": "json", "limit": 1, "addressdetails": 1},
            headers={"User-Agent": "carshow-finder/1.0"},
        )
        results = response.json()
        if not results:
            return None
        result = results[0]
        state = result.get("address", {}).get("ISO3166-2-lvl4", "").replace("US-", "")
        return {"lat": float(result["lat"]), "lng": float(result["lon"]), "state": state}


async def coords_to_state(lat: float, lng: float) -> str | None:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lng, "format": "json", "addressdetails": 1},
            headers={"User-Agent": "carshow-finder/1.0"},
        )
        data = response.json()
        state = data.get("address", {}).get("ISO3166-2-lvl4", "").replace("US-", "")
        return state or None
