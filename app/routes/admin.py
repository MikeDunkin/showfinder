from fastapi import APIRouter, Depends, HTTPException
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


@router.delete("/shows/{show_id}")
async def delete_show(show_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        result = await db.car_shows.delete_one({"_id": ObjectId(show_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid show ID")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Show not found")
    return {"deleted": show_id}
