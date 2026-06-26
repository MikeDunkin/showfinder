from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db import get_db
from app.services import geo

router = APIRouter()

_SEARCH_SQL = """
    WITH distances AS (
        SELECT id, name, date, venue, city, state, zip_code, lat, lng, url, description,
            ROUND(CAST(
                3956 * 2 * asin(sqrt(
                    power(sin(radians(lat - :lat) / 2), 2) +
                    cos(radians(:lat)) * cos(radians(lat)) *
                    power(sin(radians(lng - :lng) / 2), 2)
                ))
            AS NUMERIC), 1) AS distance_miles
        FROM car_shows
        WHERE lat IS NOT NULL AND lng IS NOT NULL
    )
    SELECT * FROM distances WHERE distance_miles <= :radius ORDER BY distance_miles
"""


async def _search(lat: float, lng: float, radius: int, db: AsyncSession) -> list[dict]:
    result = await db.execute(text(_SEARCH_SQL), {"lat": lat, "lng": lng, "radius": radius})
    return [dict(row._mapping) for row in result]


@router.get("/")
async def get_shows_by_coords(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius: int = Query(25, description="Search radius in miles"),
    db: AsyncSession = Depends(get_db),
):
    return await _search(lat, lng, radius, db)


@router.get("/by-zip")
async def get_shows_by_zip(
    zip_code: str = Query(..., description="US ZIP code"),
    radius: int = Query(25, description="Search radius in miles"),
    db: AsyncSession = Depends(get_db),
):
    coords = await geo.zip_to_coords(zip_code)
    if not coords:
        raise HTTPException(status_code=404, detail=f"Could not resolve ZIP code: {zip_code}")
    return await _search(coords["lat"], coords["lng"], radius, db)
