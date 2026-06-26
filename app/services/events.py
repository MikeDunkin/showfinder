import os
import httpx
from fastapi import HTTPException

TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY")
BASE_URL = "https://app.ticketmaster.com/discovery/v2"


async def find_car_shows(lat: float, lng: float, radius: int) -> list[dict]:
    if not TICKETMASTER_API_KEY:
        raise HTTPException(status_code=500, detail="TICKETMASTER_API_KEY is not configured")

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{BASE_URL}/events.json",
            params={
                "keyword": "car show",
                "latlong": f"{lat},{lng}",
                "radius": radius,
                "unit": "miles",
                "apikey": TICKETMASTER_API_KEY,
            },
        )

        if response.status_code == 401:
            raise HTTPException(status_code=500, detail="Invalid Ticketmaster API key")
        response.raise_for_status()

        data = response.json()
        events = data.get("_embedded", {}).get("events", [])

        results = []
        for event in events:
            venues = event.get("_embedded", {}).get("venues", [])
            venue = venues[0] if venues else {}
            location = venue.get("location", {})
            address_parts = [
                venue.get("address", {}).get("line1"),
                venue.get("city", {}).get("name"),
                venue.get("state", {}).get("stateCode"),
            ]
            address = ", ".join(p for p in address_parts if p) or None
            results.append({
                "name": event["name"],
                "date": event.get("dates", {}).get("start", {}).get("localDate"),
                "url": event.get("url"),
                "venue": address,
                "lat": float(location["latitude"]) if location.get("latitude") else None,
                "lng": float(location["longitude"]) if location.get("longitude") else None,
            })
        return results
