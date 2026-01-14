import asyncio, os, time, random, base64, datetime
import re
import traceback
from typing import Any, Dict, Optional
import httpx
from motor.motor_asyncio import AsyncIOMotorClient

DEBUG = True

if DEBUG:
    ADDRESS = "*********"
    WEBHOOK_URL = os.getenv(
        "WEBHOOK_URL", " http://0.0.0.0:8001/payment"
    ).strip()
    DB_NAME = "gifts-test"

else:
    ADDRESS = "*********"
    WEBHOOK_URL = os.getenv(
        "WEBHOOK_URL", "*********"
    ).strip()
    DB_NAME = "gifts"

MONGO_URI = os.getenv(
    "MONGO_URI",
    "*********"
)

COL_TXS = "txs"
COL_CURSORS = "cursors"
API_KEY = os.getenv(
    "*********",
    "*********",
)

WEBHOOK_HEADERS = {
    "Authorization": "Bearer *********",
}
BASE_URL = "https://toncenter.com/api/v3"
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL_SEC", "5"))


def decode_ton_memo(b64: str) -> str | None:
    if not b64:
        return None
    try:
        pad = "=" * (-len(b64) % 4)
        data = base64.b64decode(b64 + pad)

        ms = list(re.finditer(rb"[ -~]{2,}", data))
        if not ms:
            return None
        run = max(ms, key=lambda m: len(m.group(0))).group(0).decode("utf-8", "ignore")
        t = run.strip()
        if not t:
            return None

        ups = sum(1 for c in t if (c.isupper() or c.isdigit() or c == " "))
        if " " in t and ups / len(t) >= 0.7:
            while t and (t[-1].islower()):
                t = t[:-1]

        allowed_tail = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 )]}!?.,:;%-+_/'\""
        )
        while t and t[-1] not in allowed_tail:
            t = t[:-1]
        return t
    except Exception as e:
        print("Failed to decode TON memo:", e)
        print(traceback.format_exc())
        return None


def to_ton(nano: str) -> str:
    try:
        v = int(nano)
        return f"{v/1_000_000_000:.9f}".rstrip("0").rstrip(".")
    except:
        return nano


def to_usdt(amount_str: str) -> str:
    try:
        v = int(amount_str)
        return f"{v/1_000_000:.6f}".rstrip("0").rstrip(".")
    except:
        try:
            v = float(amount_str)
            return f"{v:.6f}".rstrip("0").rstrip(".")
        except:
            return amount_str


def utc_iso(ts: int) -> str:
    return (
        datetime.datetime.fromtimestamp(ts, datetime.UTC)
        .replace(tzinfo=datetime.timezone.utc)
        .isoformat()
    )


def jitter_delay(base: float, attempt: int) -> float:
    return min(30.0, base * (2 ** min(attempt, 5)) + random.uniform(0, base))


def build_headers() -> Dict[str, str]:
    h = {"Accept": "application/json"}
    if API_KEY:
        h["Authorization"] = f"Bearer {API_KEY}"
    return h


def safe_get(d: Dict, *path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


async def ensure_indexes(db):
    await db[COL_TXS].create_index("uid", unique=True, background=True)
    await db[COL_TXS].create_index([("ts", 1)], background=True)
    await db[COL_CURSORS].create_index("key", unique=True, background=True)


async def load_cursor(db, key: str) -> Optional[str]:
    doc = await db[COL_CURSORS].find_one({"key": key})
    return doc.get("value") if doc else None


async def save_cursor(db, key: str, value: str):
    await db[COL_CURSORS].update_one(
        {"key": key},
        {"$set": {"value": value, "updated_at": int(time.time())}},
        upsert=True,
    )


async def http_get(
    client: httpx.AsyncClient, url: str, params: Dict[str, Any]
) -> Optional[Dict]:
    attempt = 0
    while True:
        try:
            r = await client.get(
                url,
                params=params,
                headers=build_headers(),
                timeout=httpx.Timeout(15, connect=10),
            )
            if r.status_code >= 500:
                attempt += 1
                await asyncio.sleep(jitter_delay(0.8, attempt))
                continue
            if r.status_code == 429:
                await asyncio.sleep(2.0)
                continue
            r.raise_for_status()
            return r.json()
        except Exception:
            attempt += 1
            if attempt > 6:
                return None
            await asyncio.sleep(jitter_delay(0.8, attempt))


async def post_webhook(
    client: httpx.AsyncClient, payload: Dict[str, Any]
) -> Dict[str, Any]:
    if not WEBHOOK_URL:
        return {"status": "skipped_no_url", "code": 0}
    attempt = 0
    while True:
        try:
            r = await client.post(
                WEBHOOK_URL,
                json=payload,
                timeout=httpx.Timeout(15, connect=10),
                headers=WEBHOOK_HEADERS,
            )
            if r.status_code >= 500:
                attempt += 1
                await asyncio.sleep(jitter_delay(0.8, attempt))
                continue
            ok = 200 <= r.status_code < 300
            return {
                "status": "ok" if ok else "failed",
                "code": r.status_code,
                "resp": safe_get(
                    (
                        r.json()
                        if "application/json" in r.headers.get("content-type", "")
                        else {}
                    ),
                ),
            }
        except Exception as e:
            attempt += 1
            if attempt > 5:
                return {"status": "failed", "code": -1, "error": str(e)}
            await asyncio.sleep(jitter_delay(0.8, attempt))


def parse_memo_from_message(msg: Dict[str, Any]) -> Optional[str]:
    t = safe_get(msg, "message_content", "decoded", "comment")
    if t:
        return str(t)
    t = safe_get(msg, "comment")
    if t:
        return str(t)
    b = safe_get(msg, "msg_data", "text")
    if b:
        return str(b)
    b = safe_get(msg, "body", "text")
    if b:
        return str(b)
    return None


async def process_native(db, client: httpx.AsyncClient):
    key = "native_after_lt"
    after_lt = await load_cursor(db, key)
    params = {"direction": "in", "destination": ADDRESS, "limit": 128, "sort": "asc"}
    if after_lt:
        params["after_lt"] = after_lt
    data = await http_get(client, f"{BASE_URL}/messages", params)
    if not data or "messages" not in data:
        return
    msgs = data["messages"]
    if not msgs:
        return
    for m in msgs:
        try:
            src = safe_get(m, "source")
            val = safe_get(m, "value") or "0"
            if val == "1":
                continue
            created_lt = str(safe_get(m, "created_lt", "") or "")
            tx_hash = safe_get(m, "hash") or f"lt:{created_lt}"
            ts = safe_get(m, "created_at") or safe_get(m, "now") or int(time.time())
            memo = parse_memo_from_message(m)
            amount_hr = to_ton(val)
            payload = {
                "asset": "TON",
                "hash": tx_hash,
                "time_utc": utc_iso(int(ts)),
                "time_unix": int(ts),
                "amount": amount_hr,
                "amount_raw": str(val),
                "memo": memo,
                "webhook": {},
            }

            uid = f"ton:native:{tx_hash}"
            doc = {"uid": uid, **payload}
            res = await db[COL_TXS].update_one(
                {"uid": uid}, {"$setOnInsert": doc}, upsert=True
            )
            is_new = res.upserted_id is not None
            if is_new:
                print("received", amount_hr, "TON |||", "comment:", memo)
                wh = await post_webhook(
                    client,
                    payload,
                )
                await db[COL_TXS].update_one(
                    {"uid": uid},
                    {
                        "$set": {
                            "webhook": {
                                "status": wh.get("status"),
                                "code": wh.get("code"),
                                "at": int(time.time()),
                            }
                        }
                    },
                )
            after_lt = created_lt
        except Exception:
            pass
    if after_lt:
        await save_cursor(db, key, after_lt)


async def process_jetton(db, client: httpx.AsyncClient):
    key = "jetton_start_lt"
    start_lt = await load_cursor(db, key)
    params = {
        "direction": "in",
        "owner_address": ADDRESS,
        "limit": 64,
        "sort": "desc",
        "jetton_master": "EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs",
    }

    if start_lt:
        params["after_lt"] = start_lt

    data = await http_get(client, f"{BASE_URL}/jetton/transfers", params)

    if not data or "jetton_transfers" not in data:
        return
    transfers = data["jetton_transfers"]
    if not transfers:
        return
    start_lt = None
    for t in transfers:
        try:
            tx_hash = t.get("transaction_hash") or ""
            ts = t.get("transaction_now")
            amt = str(t.get("amount") or "0")
            memo = decode_ton_memo(t.get("forward_payload"))
            amount_hr = to_usdt(amt)
            tx_lt = t.get("transaction_lt")
            payload = {
                "asset": "USDT",
                "hash": tx_hash,
                "time_utc": utc_iso(ts),
                "time_unix": ts,
                "amount": amount_hr,
                "amount_raw": amt,
                "memo": memo,
                "webhook": {},
            }
            uid = f"ton:usdt:{tx_hash}"
            doc = {"uid": uid, **payload}
            res = await db[COL_TXS].update_one(
                {"uid": uid}, {"$setOnInsert": doc}, upsert=True
            )
            is_new = res.upserted_id is not None
            if is_new:
                print("received", amount_hr, "USDT |||", "comment:", memo)
                start_lt = tx_lt
                wh = await post_webhook(client, payload)
                await db[COL_TXS].update_one(
                    {"uid": uid},
                    {
                        "$set": {
                            "webhook": {
                                "status": wh.get("status"),
                                "code": wh.get("code"),
                                "at": int(time.time()),
                            }
                        }
                    },
                )
            else:
                break
        except Exception:
            pass
    if start_lt:
        await save_cursor(db, key, start_lt)


async def retry_failed_webhooks(db, client: httpx.AsyncClient):
    cur = (
        db[COL_TXS]
        .find(
            {"webhook.status": {"$in": ["failed", None]}},
            {
                "_id": 0,
                "uid": 1,
                "asset": 1,
                "from": 1,
                "to": 1,
                "hash": 1,
                "time_unix": 1,
                "time_utc": 1,
                "amount": 1,
                "memo": 1,
                "kind": 1,
            },
        )
        .limit(50)
    )
    async for d in cur:
        try:
            if not WEBHOOK_URL:
                await db[COL_TXS].update_one(
                    {"uid": d["uid"]},
                    {
                        "$set": {
                            "webhook": {
                                "status": "skipped_no_url",
                                "code": 0,
                                "at": int(time.time()),
                            }
                        }
                    },
                )
                continue
            wh = await post_webhook(
                client,
                {
                    "asset": d["asset"],
                    "sender": d["from"],
                    "recipient": d["to"],
                    "hash": d["hash"],
                    "unix_time": d["time_unix"],
                    "utc_time": d["time_utc"],
                    "amount": d["amount"],
                    "memo": d.get("memo"),
                    "kind": d.get("kind"),
                },
            )
            await db[COL_TXS].update_one(
                {"uid": d["uid"]},
                {
                    "$set": {
                        "webhook": {
                            "status": wh.get("status"),
                            "code": wh.get("code"),
                            "at": int(time.time()),
                        }
                    }
                },
            )
        except Exception:
            pass


async def main():
    mc = AsyncIOMotorClient(
        MONGO_URI,
        uuidRepresentation="standard",
        tls=True,
        serverSelectionTimeoutMS=15000,
    )
    db = mc[DB_NAME]
    await ensure_indexes(db)
    async with httpx.AsyncClient() as client:
        while True:
            t0 = time.time()
            try:
                await asyncio.gather(
                    process_native(db, client),
                    process_jetton(db, client),
                    retry_failed_webhooks(db, client),
                )
            except Exception:
                pass
            dt = time.time() - t0
            await asyncio.sleep(max(0.5, POLL_INTERVAL - dt))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
