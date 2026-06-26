import os
import httpx
from fastapi import HTTPException

EVENTBRITE_TOKEN = os.getenv("EVENTBRITE_TOKEN")
BASE_URL = "https://www.eventbriteapi.com/v3"


async def find_car_shows(lat: float, lng: float, radius: int) -> list[dict]:
    if not EVENTBRITE_TOKEN:
        raise HTTPException(status_code=500, detail="EVENTBRITE_TOKEN is not configured")

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{BASE_URL}/events/search/",
            params={
                "q": "car show",
                "location.latitude": lat,
                "location.longitude": lng,
                "location.within": f"{radius}mi",
                "expand": "venue",
            },
            headers={"Authorization": f"Bearer {EVENTBRITE_TOKEN}"},
        )

        if response.status_code == 401:
            raise HTTPException(status_code=500, detail="Invalid Eventbrite token")
        response.raise_for_status()

        data = response.json()
        results = []
        for event in data.get("events", []):
            venue = event.get("venue") or {}
            address = venue.get("address") or {}
            lat = venue.get("latitude")
            lng = venue.get("longitude")
            results.append({
                "name": event["name"]["text"],
                "date": event["start"]["local"],
                "url": event["url"],
                "venue": address.get("localized_address_display"),
                "lat": float(lat) if lat else None,
                "lng": float(lng) if lng else None,
            })
        return results
