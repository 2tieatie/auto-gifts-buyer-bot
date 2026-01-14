import math
from datetime import datetime, UTC

import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from config import MONGO_URI, DB_NAME, PAGE_SIZE


async def get_db():
    cli = AsyncIOMotorClient(
        MONGO_URI,
        uuidRepresentation="standard",
        tls=True,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=30000,
    )
    db = cli[DB_NAME]
    await db.accounts.create_index("phone", unique=True)
    return db


async def fetch_page(accs: AsyncIOMotorCollection, page: int):
    total = await accs.count_documents({})
    pages_total = max(1, math.ceil(total / PAGE_SIZE))
    page = max(0, min(page, pages_total - 1))
    docs = (
        await accs.find({})
        .sort("updated_at", -1)
        .skip(page * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .to_list(length=None)
    )
    return docs, total, page, pages_total


async def save_account(me, phone: str, password: str = None):

    db = await get_db()
    doc = {
        "user_id": me.id,
        "username": me.username,
        "first_name": me.first_name,
        "last_name": me.last_name,
        "phone": phone,
        "is_premium": bool(getattr(me, "is_premium", False)),
        "updated_at": datetime.now(UTC),
        "session_string": me.session_string,
        "stars_balance": me.stars_balance,
        "created_at": datetime.now(UTC),
        "password": password,
        "stars_limit": 0,
        "owner": None,
        "type": "shop",
        "autobuy_enabled": True,
        "gifts_receiver": me.username,
    }
    await db.accounts.update_one({"phone": phone}, {"$set": doc}, upsert=True)


async def update_account(me, phone: str):
    db = await get_db()
    doc = {
        "username": me.username,
        "first_name": me.first_name,
        "last_name": me.last_name,
        "is_premium": bool(getattr(me, "is_premium", False)),
        "updated_at": datetime.now(UTC),
        "session_string": me.session_string,
        "stars_balance": me.stars_balance,
    }
    await db.accounts.update_one({"phone": phone}, {"$set": doc}, upsert=True)
