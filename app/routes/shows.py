from fastapi import APIRouter, Query, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db import get_db
from app.services import geo

router = APIRouter()


def _fmt(show: dict) -> dict:
    show["id"] = str(show.pop("_id"))
    coords = show.pop("location", {}).get("coordinates", [None, None])
    show["lng"], show["lat"] = coords[0], coords[1]
    return show


async def _search(lat: float, lng: float, radius: int, db: AsyncIOMotorDatabase) -> list[dict]:
    cursor = db.car_shows.find({
        "location": {
            "$nearSphere": {
                "$geometry": {"type": "Point", "coordinates": [lng, lat]},
                "$maxDistance": radius * 1609.34,
            }
        }
    }).limit(50)
    return [_fmt(s) async for s in cursor]


@router.get("")
async def get_shows_by_coords(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius: int = Query(25, description="Search radius in miles"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await _search(lat, lng, radius, db)


@router.get("/by-zip")
async def get_shows_by_zip(
    zip_code: str = Query(..., description="US ZIP code"),
    radius: int = Query(25, description="Search radius in miles"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    coords = await geo.zip_to_coords(zip_code)
    if not coords:
        raise HTTPException(status_code=404, detail=f"Could not resolve ZIP code: {zip_code}")
    return await _search(coords["lat"], coords["lng"], radius, db)
