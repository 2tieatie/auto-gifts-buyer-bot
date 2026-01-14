import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

from aiocache import cached
from bson import ObjectId
from pydantic import BaseModel
from pymongo import ReturnDocument, ASCENDING, DESCENDING

from base.enums import InvoiceType, InvoiceStatus
from base.invoice_results import BaseInvoiceResult
from config import db, INVOICE_TTL_SECONDS

invoices = db.invoices


async def setup_invoices_indexes() -> None:
    await invoices.create_index([("user_id", ASCENDING), ("status", ASCENDING)])
    await invoices.create_index([("status", ASCENDING), ("expires_at", ASCENDING)])
    await invoices.create_index([("created_at", ASCENDING)])
    await invoices.create_index([("type", ASCENDING)])
    await invoices.create_index([("tx_hash", ASCENDING)])


def _ensure_oid(v: Union[str, ObjectId]) -> Optional[ObjectId]:
    try:
        return v if isinstance(v, ObjectId) else ObjectId(str(v))
    except Exception:
        return None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def create_invoice(
    user_id: int,
    invoice_type: InvoiceType,
    amount_ton: float,
    amount_usdt: float,
    result: BaseInvoiceResult,
    ttl_seconds: Optional[int] = INVOICE_TTL_SECONDS,
) -> dict:
    _id = ObjectId()
    now = _utcnow()
    expires_at = now + timedelta(seconds=ttl_seconds)

    doc = {
        "_id": _id,
        "id": str(_id),
        "user_id": user_id,
        "type": invoice_type,
        "status": InvoiceStatus.PENDING,
        "amount_ton": float(amount_ton),
        "amount_usdt": float(amount_usdt),
        "tx_hash": "",
        "status_reason": "",
        "result": (
            result.model_dump(mode="python")
            if isinstance(result, BaseModel)
            else dict(result)
        ),
        "created_at_unix": int(now.timestamp()),
        "created_at": now,
        "ttl_seconds": ttl_seconds,
        "expires_at_unix": int(expires_at.timestamp()),
        "expires_at": expires_at,
        "updated_at": now,
    }
    await invoices.insert_one(doc)
    return doc


async def get_invoice_by_id(
    invoice_id: Union[str, ObjectId], filters: Optional[dict] = None
) -> Optional[dict]:
    oid = _ensure_oid(invoice_id)

    if oid is None:
        return None

    search_filter = {"_id": oid}
    if filters:
        search_filter.update(filters)
    return await invoices.find_one(search_filter)


async def _update_status(
    invoice_id: Union[str, ObjectId],
    new_status: InvoiceStatus,
    *,
    reason: Optional[str] = None,
    tx_hash: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> Optional[dict]:
    oid = _ensure_oid(invoice_id)
    if not oid:
        return None
    if new_status in (InvoiceStatus.CANCELED, InvoiceStatus.EXPIRED):
        if not reason:
            raise ValueError(f"`reason` is required for status {new_status}")
    if new_status is InvoiceStatus.PAID:
        if not reason:
            raise ValueError("`reason` is required for status paid")
        if not tx_hash:
            raise ValueError("`tx_hash` is required for status paid")

    now = _utcnow()
    set_fields: dict[str, Any] = {
        "status": str(new_status),
        "updated_at": now,
    }

    if reason is not None:
        set_fields["status_reason"] = reason

    if new_status is InvoiceStatus.PAID:
        set_fields["tx_hash"] = tx_hash
        set_fields["paid_at"] = now
    elif new_status is InvoiceStatus.CANCELED:
        set_fields["canceled_at"] = now
    elif new_status is InvoiceStatus.EXPIRED:
        set_fields["expired_at"] = now

    if extra:
        set_fields.update(extra)

    return await invoices.find_one_and_update(
        {"_id": oid},
        {"$set": set_fields},
        return_document=ReturnDocument.AFTER,
    )


async def mark_paid(
    invoice_id: Union[str, ObjectId],
    *,
    reason: str,
    tx_hash: str,
    extra: Optional[dict[str, Any]] = None,
) -> Optional[dict]:
    if not tx_hash:
        raise ValueError("`tx_hash` must be non-empty for mark_paid")
    if not reason:
        raise ValueError("`reason` must be non-empty for mark_paid")
    return await _update_status(
        invoice_id,
        InvoiceStatus.PAID,
        reason=reason,
        tx_hash=tx_hash,
        extra=extra,
    )


async def mark_canceled(
    invoice_id: Union[str, ObjectId],
    *,
    reason: str,
    extra: Optional[dict[str, Any]] = None,
) -> Optional[dict]:
    if not reason:
        raise ValueError("`reason` must be non-empty for mark_canceled")
    return await _update_status(
        invoice_id,
        InvoiceStatus.CANCELED,
        reason=reason,
        extra=extra,
    )


async def mark_expired(
    invoice_id: Union[str, ObjectId],
    *,
    reason: str,
    extra: Optional[dict[str, Any]] = None,
) -> Optional[dict]:
    if not reason:
        raise ValueError("`reason` must be non-empty for mark_expired")
    return await _update_status(
        invoice_id,
        InvoiceStatus.EXPIRED,
        reason=reason,
        extra=extra,
    )


async def expire_invoices_loop(
    stop_event: Optional[asyncio.Event] = None,
    interval_seconds: int = 60,
    *,
    reason_for_expire: str = "expired by scheduler",
) -> None:
    while True:
        try:
            now = _utcnow()
            res = await invoices.update_many(
                {
                    "status": str(InvoiceStatus.PENDING),
                    "expires_at": {"$lte": now},
                },
                {
                    "$set": {
                        "status": str(InvoiceStatus.EXPIRED),
                        "status_reason": reason_for_expire,
                        "expired_at": now,
                        "updated_at": now,
                    }
                },
            )
        except Exception:
            pass

        if stop_event:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
                break
            except asyncio.TimeoutError:
                continue
        else:
            await asyncio.sleep(interval_seconds)


def _kb_user_invoices(func, *args, **kwargs):
    user_id = args[0] if args else kwargs.get("user_id")
    page = kwargs[1] if len(args) > 1 else kwargs.get("page", 1)
    per_page = kwargs[2] if len(args) > 2 else kwargs.get("per_page", 20)
    show_expired = kwargs[3] if len(args) > 3 else kwargs.get("show_expired", True)
    return f"user_invoices:{user_id}:p{page}:pp{per_page}:{show_expired}"


@cached(ttl=15, key_builder=_kb_user_invoices)
async def get_user_invoices(
    user_id: int,
    page: int = 1,
    per_page: int = 8,
    filters: Optional[dict[str, Any]] = None,
    show_expired: bool = True,
) -> dict:
    page = max(int(page), 1)
    per_page = max(min(int(per_page), 200), 1)

    base = {"user_id": user_id}
    parts = [base]
    if filters:
        parts.append(filters)
    if not show_expired and not (filters and "status" in filters):
        parts.append(
            {"status": {"$nin": [InvoiceStatus.EXPIRED, InvoiceStatus.CANCELED]}}
        )
    search_filter = parts[0] if len(parts) == 1 else {"$and": parts}

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
    res = await invoices.aggregate(pipeline, allowDiskUse=False).to_list(length=1)
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
