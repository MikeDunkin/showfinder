import httpx
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("")
async def get_location(ip: str = Query(..., description="Client public IP")):
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get(f"http://ip-api.com/json/{ip}?fields=status,lat,lon")
            data = res.json()
            if data.get("status") == "success":
                return {"lat": data["lat"], "lng": data["lon"]}
    except Exception:
        pass

    return {"lat": None, "lng": None}
