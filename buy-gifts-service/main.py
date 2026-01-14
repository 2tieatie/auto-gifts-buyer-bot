import asyncio
import random
import time
import uuid
from operator import attrgetter

from motor.motor_asyncio import AsyncIOMotorClient

from pyrogram import Client
from pyrogram.raw.functions.payments import GetStarGifts, GetPaymentForm, SendStarsForm
from pyrogram.raw.types import StarGift, InputInvoiceStarGift, InputPeerSelf, InputPeerChat, InputPeerChannel

_GET_STAR_GIFTS_0 = GetStarGifts(hash=0)
_STAR_KEY = attrgetter("stars")

MONGO_URI = (
    "######"
)
DB_NAME = "gifts"
_cli = AsyncIOMotorClient(MONGO_URI, uuidRepresentation="standard")
db = _cli[DB_NAME]

API_ID = 123456
API_HASH = "######"

waiter_client = Client("WAITER", API_ID, API_HASH, phone_number="######")


async def get_available_gifts(client: Client) -> list[StarGift]:
    gifts = (await client.invoke(_GET_STAR_GIFTS_0)).gifts
    res = [g for g in gifts if g.limited and not g.sold_out]
    res.sort(key=_STAR_KEY, reverse=True)
    return res


def chunks(lst, size=15):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


async def buy_gifts(
    session_string: str,
    limit: int,
    gifts: list[StarGift],
    receiver_username: str = None,
    phone: str = None,
) -> list[int]:
    client = Client(
        str(uuid.uuid4()),
        api_id=API_ID,
        api_hash=API_HASH,
        device_model="AutoGifts",
        app_version="1.0",
        in_memory=True,
        session_string=session_string,
        no_updates=True,
    )
    async with client:
        results = []
        try:
            peer = await client.resolve_peer(receiver_username)
        except Exception as e:
            print(e, receiver_username, phone)
            peer = InputPeerSelf()
        # print(type(peer))
        # if isinstance(peer, InputPeerChannel):
        #     peer = InputPeerSelf()

        for gift in gifts:
            if gift.stars <= limit:
                invoice = InputInvoiceStarGift(
                    peer=peer, gift_id=gift.id, hide_name=True
                )
                print(gift.stars)
                while gift.stars <= limit:
                    try:
                        form = await client.invoke(GetPaymentForm(invoice=invoice))
                        result = await client.invoke(
                            SendStarsForm(form_id=form.form_id, invoice=invoice)
                        )
                        print("SUCCESS", receiver_username, phone)
                    except Exception as e:
                        print(e, receiver_username, phone)
                        break

                    limit -= gift.stars
                    results.append(gift.id)
        return results


async def get_accounts():
    return (
        await db.accounts.find(
            {
                # "owner": 720207278,
                "owner": {"$ne": None},
                "stars_limit": {"$gte": 50},
                "autobuy_enabled": True,
            }
        )
        .sort("stars_limit", -1)
        .to_list(None)
    )


async def wait_for_new_gifts():
    async with waiter_client:
        while True:
            gifts = await get_available_gifts(waiter_client)
            if gifts:
                return gifts
            print("no new gifts")
            await asyncio.sleep(0.75)


async def main():
    while True:
        gifts = await wait_for_new_gifts()
        start = time.time()
        accounts = await get_accounts()
        results = []
        for batch in chunks(accounts, 35):
            tasks = []
            for account in batch:
                tasks.append(
                    asyncio.create_task(
                        buy_gifts(
                            session_string=account["session_string"],
                            limit=account["stars_limit"],
                            gifts=gifts,
                            receiver_username=account["gifts_receiver"],
                            phone=account['phone']
                        )
                    )
                )
            r = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(r)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"[ERROR] {accounts[i]['phone']}: {result}")
            else:
                print(f"[OK] {accounts[i]['phone']}: {result}")
        print(time.time() - start)
        await asyncio.sleep(random.randrange(10, 20))


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
