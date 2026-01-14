import asyncio
import random
from typing import Any, Coroutine

from tonsdk.contract.wallet import Wallets, WalletVersionEnum, WalletContract
from tonsdk.utils import to_nano, bytes_to_b64str
import aiohttp

from config import MNEMONICS, SENDER_ADDRESS, API_KEY

USE_API_KEY = True


async def initialization_wallet() -> tuple[WalletContract, Any]:
    version = WalletVersionEnum.v4r2

    mnemonics, pub_k, priv_k, wallet = Wallets.from_mnemonics(
        mnemonics=MNEMONICS, version=version, workchain=0
    )
    print(wallet)
    return wallet, wallet.address.to_string(True, True, False)


async def send(
    session,
    wallet: WalletVersionEnum.v4r2,
    recipient_address,
    seqnoo,
    post_url,
    payload,
    amount,
):
    query = wallet.create_transfer_message(
        to_addr=recipient_address,
        amount=to_nano(float(amount), "ton"),
        seqno=int(seqnoo),
        payload=payload,
    )

    boc = bytes_to_b64str(query["message"].to_boc(False))
    json = {"boc": str(boc)}
    async with session.post(post_url, json=json) as resp:
        if resp.status == 200:
            print(
                f"Successfully created transaction. Sending {amount} TON to {recipient_address}..."
            )
            return True, amount
        else:
            return False, None


async def wait_for_seqno_change(session, get_url, seqno):
    delay = 0.3 if USE_API_KEY and API_KEY else 2

    while True:
        await asyncio.sleep(delay)
        info = await get_wallet_info(session, get_url)
        if info and info["seqno"] > seqno:
            return True
        await asyncio.sleep(delay)


async def get_wallet_info(session, get_url):
    async with session.get(get_url) as response:
        if response.status == 200:
            return await response.json()
        else:
            print(
                f"Error getting wallet info: {response.status}, {await response.json()}"
            )
        return None


async def send_ton(recipient_address, amount, memo):
    wallet, _ = await initialization_wallet()

    get_url = (
        f"https://toncenter.com/api/v3/wallet?address={SENDER_ADDRESS}&api_key={API_KEY}"
        if API_KEY
        else f"https://toncenter.com/api/v3/wallet?address={SENDER_ADDRESS}"
    )
    post_url = (
        f"https://toncenter.com/api/v3/message?api_key={API_KEY}"
        if API_KEY
        else f"https://toncenter.com/api/v3/message"
    )

    async with aiohttp.ClientSession() as session:
        info = await get_wallet_info(session, get_url)
        print(info)
        seqno = 0 if info["status"] == "uninit" else info["seqno"]
        sending, amount = await send(
            session,
            wallet,
            recipient_address,
            seqno,
            post_url,
            memo,
            amount,
        )
        if sending:
            change = await wait_for_seqno_change(session, get_url, seqno)
            if change:
                seqno += 1
                print(f"{amount} TON was sent to {recipient_address}.")
            else:
                raise Exception(f"Error with {recipient_address}.")
