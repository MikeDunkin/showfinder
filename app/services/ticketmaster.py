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
                "apikey": TICKETMASTER_API_KEY,
                "keyword": "car show",
                "latlong": f"{lat},{lng}",
                "radius": radius,
                "unit": "miles",
                "countryCode": "US",
                "size": 50,
            },
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for event in data.get("_embedded", {}).get("events", []):
            venues = event.get("_embedded", {}).get("venues", [{}])
            venue = venues[0] if venues else {}
            loc = venue.get("location", {})
            vlat = loc.get("latitude")
            vlng = loc.get("longitude")
            addr = venue.get("address", {}).get("line1", "")
            city = venue.get("city", {}).get("name", "")
            state = venue.get("state", {}).get("stateCode", "")
            venue_name = ", ".join(filter(None, [venue.get("name"), city, state]))
            start = event.get("dates", {}).get("start", {})
            date = f"{start.get('localDate', '')}T{start.get('localTime', '00:00:00')}"
            results.append({
                "eventbrite_id": event["id"],
                "name": event["name"],
                "date": date,
                "url": event.get("url"),
                "venue": venue_name or None,
                "lat": float(vlat) if vlat else None,
                "lng": float(vlng) if vlng else None,
            })
        return results
