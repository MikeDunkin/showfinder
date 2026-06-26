from fastapi import APIRouter, Query, HTTPException
from app.services import events, geo

router = APIRouter()


@router.get("/")
async def get_shows_by_coords(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius: int = Query(25, description="Search radius in miles"),
):
    return await events.find_car_shows(lat, lng, radius)


@router.get("/by-zip")
async def get_shows_by_zip(
    zip_code: str = Query(..., description="US ZIP code"),
    radius: int = Query(25, description="Search radius in miles"),
):
    coords = await geo.zip_to_coords(zip_code)
    if not coords:
        raise HTTPException(status_code=404, detail=f"Could not resolve ZIP code: {zip_code}")
    return await events.find_car_shows(coords["lat"], coords["lng"], radius)
