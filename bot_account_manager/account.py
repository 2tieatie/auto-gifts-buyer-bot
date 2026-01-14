import asyncio
import time
import uuid
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorCollection
from pyrogram.errors import SessionPasswordNeeded

from db import update_account
from config import API_ID, API_HASH
from pyrogram import Client as PyroClient
from pyrogram.raw.functions.payments import GetStarsStatus
from pyrogram.raw.types import InputPeerSelf
from utils import _extract_verification_code
from db import fetch_page, get_db
from pyrogram.raw.functions.account import GetAuthorizations, ResetAuthorization


async def _get_me(client: PyroClient):
    me = await client.get_me()
    stars_balance_raw = await client.invoke(GetStarsStatus(peer=InputPeerSelf()))
    stars_balance = stars_balance_raw.balance.amount
    session_string = await client.export_session_string()
    me.session_string = session_string
    me.stars_balance = stars_balance
    return me


async def wait_for_message(client, last_message, chat=777000, timeout=60):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        await asyncio.sleep(1)
        async for message in client.get_chat_history(chat, limit=1):
            if not last_message or message.id != last_message.id:
                return message
    raise TimeoutError("No new code message in 777000")


def with_client(session_string: Optional[str] = None):
    if session_string:
        return PyroClient(
            str(uuid.uuid4()),
            api_id=API_ID,
            api_hash=API_HASH,
            device_model="AutoGifts",
            app_version="1.0",
            in_memory=True,
            session_string=session_string,
            no_updates=True,
        )
    return PyroClient(
        str(uuid.uuid4()),
        api_id=API_ID,
        api_hash=API_HASH,
        device_model="AutoGifts",
        app_version="1.1",
        in_memory=True,
        no_updates=True,
    )


async def revoke_old_sessions(client: PyroClient):
    auths = await client.invoke(GetAuthorizations())
    for a in auths.authorizations:
        if getattr(a, "current", False):
            continue
        if getattr(a, "device_model", "") == "AutoGifts":
            try:
                await client.invoke(ResetAuthorization(hash=a.hash))
                print(f"[revoke] removed old session hash={a.hash}")
            except Exception as e:
                print(f"[revoke] fail hash={a.hash}: {e!r}")


async def relogin(session_string: str, phone: str, password: Optional[str]) -> None:
    try:
        old_client = with_client(session_string)
        await old_client.connect()
        last = None
        async for m in old_client.get_chat_history(777000, limit=1):
            last = m

        new_client = with_client()
        await new_client.connect()
        print(f"[relogin] {phone} CHECK {bool((await old_client.get_me()).id)}")

        sent = await new_client.send_code(phone_number=phone)
        code_msg = await wait_for_message(old_client, last)
        code = _extract_verification_code(code_msg.text)

        try:
            await new_client.sign_in(phone, sent.phone_code_hash, code)
        except SessionPasswordNeeded:
            await new_client.check_password(password)

        async def __terminate():
            await asyncio.sleep(300)
            try:
                await old_client.log_out()
            except ConnectionError as e:
                if "already terminated" not in str(e):
                    print(f"[relogin] warn while logging out old session: {e!r}")

            finally:
                try:
                    await old_client.disconnect()
                except Exception:
                    pass

        asyncio.create_task(__terminate())

        me = await _get_me(new_client)
        await update_account(me, phone=phone)

        await new_client.disconnect()
        print(f"[relogin] {phone} ok")
    except Exception as e:
        print(f"[relogin] {phone} {e!r}")


async def update_data(session_string: str, phone: str, password: Optional[str]) -> None:
    try:
        new_client = with_client(session_string)
        await new_client.connect()
        me = await _get_me(new_client)
        await update_account(me, phone=phone)
        await new_client.disconnect()
        print(f"[update] {phone} ok")
    except Exception as e:
        print(f"[update] {phone} {e!r}")


async def relogin_loop():
    await asyncio.sleep(23 * 60 * 60)
    while True:
        start = time.time()
        db = await get_db()
        accs: AsyncIOMotorCollection = db.accounts
        page = 0
        while True:
            docs, total, _, pages_total = await fetch_page(accs, page=page)
            tasks = []
            for account in docs:
                session_string = account.get("session_string")
                phone = account.get("phone")
                password = account.get("password")
                tasks.append(
                    asyncio.create_task(relogin(session_string, phone, password))
                )
            await asyncio.gather(*tasks)
            if pages_total - 1 <= page:
                break
            page += 1
        print(f"elapsed time: {(time.time() - start)}")
        await asyncio.sleep(max(60 * 60 * 23 - (time.time() - start), 0))

async def update_loop():
    while True:
        start = time.time()
        db = await get_db()
        accs: AsyncIOMotorCollection = db.accounts
        page = 0
        while True:
            docs, total, _, pages_total = await fetch_page(accs, page=page)
            tasks = []
            for account in docs:
                session_string = account.get("session_string")
                phone = account.get("phone")
                password = account.get("password")
                tasks.append(
                    asyncio.create_task(update_data(session_string, phone, password))
                )
            await asyncio.gather(*tasks)
            if pages_total - 1 <= page:
                break
            page += 1
        print(f"elapsed time: {(time.time() - start)}")
        await asyncio.sleep(max(60 * 60 - (time.time() - start), 0))

async def set_username(client: PyroClient, username: str):
    await client.set_username(username)


async def set_password(client: PyroClient, password: str):
    await client.enable_cloud_password(password=password)
