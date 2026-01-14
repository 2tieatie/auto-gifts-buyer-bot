import asyncio
from datetime import datetime, timedelta, timezone, UTC
from typing import Any, Optional, Union
from bson import ObjectId
from aiocache import cached
from pymongo import DESCENDING, ASCENDING, ReturnDocument

from base.enums import AccountSource
from config import db

accounts = db.accounts


def _kb_user_accounts(func, *args, **kwargs):
    user_id = args[0] if args else kwargs.get("user_id")
    page = kwargs[1] if len(args) > 1 else kwargs.get("page", 1)
    per_page = kwargs[2] if len(args) > 2 else kwargs.get("per_page", 20)
    return f"user_accounts:{user_id}:p{page}:pp{per_page}"


def _ensure_oid(v: Union[str, ObjectId]) -> ObjectId:
    return v if isinstance(v, ObjectId) else ObjectId(str(v))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def get_account_by_phone(phone: str) -> Optional[dict]:
    return await accounts.find_one({"phone": phone})


async def get_available_accounts() -> Optional[dict]:
    return await accounts.count_documents({"owner": None})


async def save_account(me, phone: str, owner: int, password: str = None):
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
        "owner": owner,
        "type": AccountSource.MANUAL,
        "stars_limit": 0,
        "autobuy_enabled": True,
        "gifts_receiver": me.username,
    }
    await accounts.update_one({"phone": phone}, {"$set": doc}, upsert=True)


@cached(ttl=15, key_builder=_kb_user_accounts)
async def get_user_accounts(
    user_id: int,
    page: int = 1,
    per_page: int = 8,
) -> dict:
    page = max(int(page), 1)
    per_page = max(min(int(per_page), 200), 1)

    search_filter = {"owner": user_id}
    skip = (page - 1) * per_page

    pipeline = [
        {"$match": search_filter},
        {"$sort": {"created_at": -1}},
        {
            "$facet": {
                "items": [{"$skip": skip}, {"$limit": per_page}],
                "total": [{"$count": "count"}],
            }
        },
    ]

    res = await accounts.aggregate(pipeline, allowDiskUse=False).to_list(length=1)
    block = res[0] if res else {"items": [], "total": []}
    items = block.get("items", [])
    total = (block.get("total") or [{"count": 0}])[0]["count"]
    pages = (total + per_page - 1) // per_page if per_page else 0

    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
        "has_prev": page > 1,
        "has_next": skip + per_page < total,
    }


async def update_autobuy_stars_limit(phone: str, stars: int):
    await accounts.update_one({"phone": phone}, {"$set": {"stars_limit": stars}})


async def transfer_account_ownership(user_id: int):
    free_account = await accounts.find_one_and_update(
        {"owner": None},
        {"$set": {"owner": user_id}},
        sort=[("created_at", ASCENDING)],
        return_document=ReturnDocument.AFTER,
    )
    return free_account


async def change_gifts_receiver(phone: str, receiver: str):
    return await accounts.update_one(
        {"phone": phone},
        {"$set": {"gifts_receiver": receiver}},
    )


async def delete_account(phone: str):
    return await accounts.delete_one({"phone": phone})
