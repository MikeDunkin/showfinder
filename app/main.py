import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes import shows

app = FastAPI(title="Car Show Finder", version="1.0.0")

app.include_router(shows.router, prefix="/shows", tags=["shows"])


@app.get("/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="frontend")
