import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes import shows, admin, dunkin, location
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Car Show Finder", version="1.0.0", lifespan=lifespan)

app.include_router(shows.router, prefix="/shows", tags=["shows"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(dunkin.router, prefix="/dunkin", tags=["dunkin"])
app.include_router(location.router, prefix="/location", tags=["location"])


@app.get("/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="frontend")
