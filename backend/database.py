from motor.motor_asyncio import AsyncIOMotorClient

from .config import settings


class Database:
    client: AsyncIOMotorClient | None = None


db = Database()


async def connect_to_mongo():
    db.client = AsyncIOMotorClient(
        settings.mongodb_uri,
        maxPoolSize=100,
        minPoolSize=10,
        maxIdleTimeMS=60000,
        serverSelectionTimeoutMS=5000,
        socketTimeoutMS=30000,
        connectTimeoutMS=10000
    )


async def close_mongo_connection():
    if db.client:
        db.client.close()
        db.client = None


def get_database():
    if not db.client:
        raise RuntimeError("Database not initialized. Call connect_to_mongo() first.")
    # print(f"DEBUG_DB: Accessing DB {settings.mongodb_db}")
    return db.client[settings.mongodb_db]



