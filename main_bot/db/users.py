from datetime import datetime, timezone
from typing import Optional

from aiocache import cached, caches
from aiogram.types import User
from pymongo import ReturnDocument
from config import (
    db,
    BASE_COMMISSION_RATE,
    BASE_STARS_COMMISSION_RATE,
    BASE_ACCOUNT_PRICE,
    BASE_REF_BONUS,
)

TTL = 3600
GET_TTL = 300

caches.set_config(
    {
        "default": {"cache": "aiocache.SimpleMemoryCache"},
        "users": {"cache": "aiocache.SimpleMemoryCache"},
    }
)


def _kb(func, *args, **kwargs):
    return f"user:{args[0]}"


async def _upsert_user_impl(
    user_id: int,
    first_name: str,
    last_name: str,
    username: str,
    lang: str,
    is_premium: bool,
    update_lang: bool = False,
):
    now = datetime.now(timezone.utc)
    to_set = {
        "first_name": first_name or "",
        "last_name": last_name or "",
        "username": username or "",
        "is_premium": is_premium,
        "updated_at": now,
    }

    if update_lang:
        to_set["language"] = lang

    return await db.users.find_one_and_update(
        {"user_id": user_id},
        {
            "$set": to_set,
            "$setOnInsert": {
                "user_id": user_id,
                "created_at": now,
                "referrer": None,
                "subscription": None,
                "ref_balance": 0,
                "ref_bonus": BASE_REF_BONUS,
            },
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )


@cached(ttl=TTL, alias="users", key_builder=_kb)
async def _upsert_user_cached(
    user_id: int,
    first_name: str,
    last_name: str,
    username: str,
    lang: str,
    is_premium: bool,
):
    return await _upsert_user_impl(
        user_id, first_name, last_name, username, lang, is_premium
    )


async def update_user(user: User, update: bool = False):
    lang_code = (getattr(user, "language_code", None) or "").lower()
    lang = "ru" if lang_code.startswith(("ru", "uk")) else "en"
    uid = user.id
    fn = user.first_name or ""
    ln = user.last_name or ""
    un = user.username or ""
    prem = user.is_premium
    if not update:
        return await _upsert_user_cached(uid, fn, ln, un, lang, prem)
    doc = await _upsert_user_impl(uid, fn, ln, un, lang, prem)
    key = f"user:{uid}"
    cache = caches.get("users")
    await cache.set(key, doc, ttl=TTL)
    return doc


async def update_user_language(user: User, lang: str):
    lang = "ru" if lang in ("ru", "uk") else "en"
    doc = await _upsert_user_impl(
        user.id,
        user.first_name or "",
        user.last_name or "",
        user.username or "",
        lang,
        user.is_premium,
        update_lang=True,
    )
    await caches.get("users").set(f"user:{user.id}", doc, ttl=TTL)
    return doc


async def set_referrer(user_id: int, referrer: int):
    return await db.users.find_one_and_update(
        {"user_id": user_id},
        {"$set": {"referrer": referrer}},
    )


async def get_user(user_id: int, from_cache: Optional[bool] = True) -> Optional[dict]:
    key = f"user:{user_id}"
    cache = caches.get("users")
    if not from_cache:
        doc = await db.users.find_one({"user_id": user_id})
        if doc is None:
            return None

        await cache.set(key, doc, ttl=GET_TTL)
        return doc

    cached_user = await cache.get(key)
    if cached_user is not None:
        return cached_user

    doc = await db.users.find_one({"user_id": user_id})
    if doc is None:
        return None

    await cache.set(key, doc, ttl=GET_TTL)
    return doc


async def update_subscription(user_id: int, subscription_type: str):
    key = f"user:{user_id}"
    cache = caches.get("users")

    doc = await db.users.find_one_and_update(
        {"user_id": user_id},
        {
            "$set": {
                "subscription": subscription_type,
                "subscription_updated_at": datetime.now(timezone.utc),
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    await cache.set(key, doc, ttl=GET_TTL)
    return doc


@cached(ttl=300)
async def get_referrals_count(user_id: int) -> int:
    return await db.users.count_documents({"referrer": user_id})


async def increase_ref_balance(user_id: int, amount: int | float):
    return await db.users.update_one(
        {"user_id": user_id}, {"$inc": {"ref_balance": amount}}
    )
