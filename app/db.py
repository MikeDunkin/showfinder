import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
_client: AsyncIOMotorClient | None = None


def get_db() -> AsyncIOMotorDatabase:
    return _client.carshowdb


async def init_db():
    global _client
    for attempt in range(10):
        try:
            _client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
            await _client.server_info()
            await _client.carshowdb.car_shows.create_index([("location", "2dsphere")])
            print("[db] MongoDB connected and 2dsphere index ready", flush=True)
            return
        except Exception as e:
            wait = 2 ** attempt
            print(f"[db] attempt {attempt + 1}/10 failed: {e} — retrying in {wait}s", flush=True)
            await asyncio.sleep(wait)
    raise RuntimeError("Could not connect to MongoDB after 10 attempts")
