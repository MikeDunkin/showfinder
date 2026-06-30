from fastapi import APIRouter, Query, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import UpdateOne
from app.db import get_db
from app.services.dunkin import fetch_all_dunkin_us

router = APIRouter()


def _fmt(loc: dict) -> dict:
    loc["id"] = str(loc.pop("_id"))
    coords = loc.pop("location", {}).get("coordinates", [None, None])
    loc["lng"], loc["lat"] = coords[0], coords[1]
    return loc


@router.get("")
async def get_dunkin(
    lat: float = Query(...),
    lng: float = Query(...),
    radius: int = Query(25),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    cursor = db.dunkin_locations.find({
        "location": {
            "$nearSphere": {
                "$geometry": {"type": "Point", "coordinates": [lng, lat]},
                "$maxDistance": radius * 1609.34,
            }
        }
    }).limit(100)
    return [_fmt(loc) async for loc in cursor]


@router.post("/refresh")
async def refresh_dunkin(db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        locations = await fetch_all_dunkin_us()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Overpass error: {e}")

    if not locations:
        raise HTTPException(status_code=502, detail="No locations returned from Overpass")

    ops = [
        UpdateOne({"osm_id": loc["osm_id"]}, {"$set": loc}, upsert=True)
        for loc in locations
    ]
    result = await db.dunkin_locations.bulk_write(ops)
    return {
        "total": len(locations),
        "upserted": result.upserted_count,
        "modified": result.modified_count,
    }
