from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from app.db import get_db
from app.models import CarShow
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
async def add_show(show: ShowCreate, db: AsyncSession = Depends(get_db)):
    if (show.lat is None or show.lng is None) and show.city and show.state:
        coords = await geocode_city(show.city, show.state)
        if coords:
            show.lat, show.lng = coords

    db_show = CarShow(**show.model_dump())
    db.add(db_show)
    await db.commit()
    await db.refresh(db_show)
    return db_show


@router.delete("/shows/{show_id}")
async def delete_show(show_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(delete(CarShow).where(CarShow.id == show_id))
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Show not found")
    return {"deleted": show_id}
