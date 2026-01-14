import asyncio
import time
import uuid
from datetime import datetime, timezone

from pyrogram import Client
from typing import Optional

from pyrogram.raw.functions.payments import GetStarsStatus
from pyrogram.raw.types import InputPeerSelf

from config import API_ID, API_HASH


def _extract_verification_code(text: str) -> Optional[str]:
    column_index = text.find(":")
    text = text[column_index + 1 :]

    if "❗️" in text:
        text = text.strip()
        dot_index = text.find(".")
        text = text[:dot_index]
        return text.strip()

    return None


def with_client(session_string: Optional[str] = None) -> Client:
    if session_string:
        return Client(
            str(uuid.uuid4()),
            api_id=API_ID,
            api_hash=API_HASH,
            device_model="AutoGifts",
            app_version="1.0",
            in_memory=True,
            session_string=session_string,
            no_updates=True,
        )
    return Client(
        str(uuid.uuid4()),
        api_id=API_ID,
        api_hash=API_HASH,
        device_model="AutoGifts",
        app_version="1.1",
        in_memory=True,
        no_updates=True,
    )


async def _get_me(client: Client):
    me = await client.get_me()
    stars_balance_raw = await client.invoke(GetStarsStatus(peer=InputPeerSelf()))
    stars_balance = stars_balance_raw.balance.amount
    session_string = await client.export_session_string()
    me.session_string = session_string
    me.stars_balance = stars_balance
    return me


def _plural_ru(n: int, forms: tuple[str, str, str]) -> str:
    n = abs(n)
    cases = [2, 0, 1, 1, 1, 2]
    return forms[2 if (n % 100 in range(5, 20)) else cases[min(n % 10, 5)]]


def _plural_en(n: int, singular: str, plural: str) -> str:
    return singular if abs(n) == 1 else plural


def _seconds_since(dt: datetime) -> int:
    # Если dt без tzinfo — считаем, что это локальное время и сравниваем с локальным now()
    if dt.tzinfo is None:
        now = datetime.now()
        return max(0, int((now - dt).total_seconds()))
    # Если dt aware — приводим обе стороны к UTC
    now_utc = datetime.now(timezone.utc)
    return max(0, int((now_utc - dt.astimezone(timezone.utc)).total_seconds()))


def _ago(dt: datetime, lang: str) -> str:
    sec = _seconds_since(dt)
    if lang == "ru":
        if sec < 60:
            n = sec
            unit = _plural_ru(n, ("секунду", "секунды", "секунд"))
            return f"{n} {unit} назад"
        elif sec < 3600:
            n = sec // 60
            unit = _plural_ru(n, ("минуту", "минуты", "минут"))
            return f"{n} {unit} назад"
        elif sec < 86400:
            n = sec // 3600
            unit = _plural_ru(n, ("час", "часа", "часов"))
            return f"{n} {unit} назад"
        else:
            n = sec // 86400
            unit = _plural_ru(n, ("день", "дня", "дней"))
            return f"{n} {unit} назад"
    else:
        if sec < 60:
            n = sec
            unit = _plural_en(n, "second", "seconds")
            return f"{n} {unit} ago"
        elif sec < 3600:
            n = sec // 60
            unit = _plural_en(n, "minute", "minutes")
            return f"{n} {unit} ago"
        elif sec < 86400:
            n = sec // 3600
            unit = _plural_en(n, "hour", "hours")
            return f"{n} {unit} ago"
        else:
            n = sec // 86400
            unit = _plural_en(n, "day", "days")
            return f"{n} {unit} ago"


async def get_account_codes(session_string: str, lang: str = "ru"):
    start = time.time()
    lang = "ru" if lang == "ru" else "en"
    client = with_client(session_string=session_string)
    async with client:
        codes = []
        async for message in client.get_chat_history(777000, limit=10):
            if not message.text:
                continue
            code = _extract_verification_code(message.text)
            if code:
                when = _ago(message.date, lang)
                codes.append(f"<code>{code}</code>, {when}")
                if len(codes) == 5:
                    break
        print(time.time() - start)
        return (
            (
                "Коды подтверждения не найдены"
                if lang == "ru"
                else "No verification codes found"
            )
            if not codes
            else "\n".join(codes)
        )


async def log_out(session_string: str):
    client: Client = with_client(session_string=session_string)
    async with client:
        try:
            result = await client.log_out()
            print(result)
        except Exception as ex:
            print("Error logging out", ex)


# async def main():
#     session_string = "######"
#     client = with_client(session_string=session_string)
#     async with client:
#         print(await client.get_me())
#
#
# asyncio.run(main())
