import httpx


async def zip_to_coords(zip_code: str) -> dict | None:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"postalcode": zip_code, "country": "US", "format": "json", "limit": 1},
            headers={"User-Agent": "carshow-finder/1.0"},
        )
        results = response.json()
        if not results:
            return None
        return {"lat": float(results[0]["lat"]), "lng": float(results[0]["lon"])}
