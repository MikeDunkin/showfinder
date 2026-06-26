import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db import get_db
from app.services.geo import geocode_city

router = APIRouter()


class ShowCreate(BaseModel):
    name: str
    date: str | None = None
    venue: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    lat: float | None = None
    lng: float | None = None
    url: str | None = None
    description: str | None = None


@router.post("/shows")
async def add_show(show: ShowCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    data = show.model_dump()
    lat = data.pop("lat")
    lng = data.pop("lng")

    if (lat is None or lng is None) and show.city and show.state:
        try:
            coords = await geocode_city(show.city, show.state)
            if coords:
                lat, lng = coords
        except Exception:
            pass

    if lat is not None and lng is not None:
        data["location"] = {"type": "Point", "coordinates": [lng, lat]}

    existing = await db.car_shows.find_one({"name": show.name, "date": show.date})
    if existing:
        return {"id": str(existing["_id"]), "duplicate": True}

    result = await db.car_shows.insert_one(data)
    return {"id": str(result.inserted_id), **data}


@router.post("/geocode-pending")
async def geocode_pending(background_tasks: BackgroundTasks, db: AsyncIOMotorDatabase = Depends(get_db)):
    pending = await db.car_shows.count_documents({"location": {"$exists": False}, "city": {"$exists": True}})
    background_tasks.add_task(_run_geocoding, db)
    return {"queued": pending}


async def _run_geocoding(db: AsyncIOMotorDatabase):
    cache: dict[tuple, tuple] = {}
    cursor = db.car_shows.find({"location": {"$exists": False}, "city": {"$exists": True}})
    updated = 0
    async for show in cursor:
        city = show.get("city")
        state = show.get("state")
        if not city or not state:
            continue
        key = (city.lower(), state.lower())
        if key not in cache:
            coords = await geocode_city(city, state)
            cache[key] = coords
            await asyncio.sleep(1.1)  # Nominatim rate limit: 1 req/sec
        coords = cache[key]
        if coords:
            lat, lng = coords
            await db.car_shows.update_one(
                {"_id": show["_id"]},
                {"$set": {"location": {"type": "Point", "coordinates": [lng, lat]}}}
            )
            updated += 1
    print(f"[geocode] done — {updated} shows geocoded", flush=True)


@router.delete("/shows/{show_id}")
async def delete_show(show_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        result = await db.car_shows.delete_one({"_id": ObjectId(show_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid show ID")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Show not found")
    return {"deleted": show_id}
