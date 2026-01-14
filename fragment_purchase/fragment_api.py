import asyncio
import string
from typing import List, Optional, Dict, Any, Union
import json
import base64
import re
import aiohttp
from tonsdk.boc import Cell
import tonutils.client
import tonutils.wallet

from config import MNEMONICS, FRAGMENT_HASH, DEVICE
from config import API_KEY, FRAGMENT_COOKIES
from send_ton import send_ton

FRAGMENT_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded",
}


def decode_ton_memo(b64: str) -> str:
    data = base64.b64decode(b64)
    printable = set(bytes(string.printable, "ascii")) | set(b"\n\r\t")
    chunks, buf = [], bytearray()
    for ch in data:
        if ch in printable:
            buf.append(ch)
        else:
            if buf:
                chunks.append(buf.decode("ascii", "ignore"))
                buf.clear()
    if buf:
        chunks.append(buf.decode("ascii", "ignore"))
    return "".join(chunks).replace("\r\n", "\n").strip()


def strip_html_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;?", " ", text)
    return text.strip()


def clean_and_filter(
    obj: Union[Dict, List, str, int, float, None]
) -> Union[Dict, List, str, int, float, None]:
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            if k.endswith("_html"):
                continue
            clean_v = clean_and_filter(v)
            new[k] = clean_v
        return new
    if isinstance(obj, list):
        return [clean_and_filter(v) for v in obj]
    if isinstance(obj, str):
        return strip_html_tags(obj)
    return obj


class WalletManager:
    def __init__(self, api_key: str, mnemonic: List[str]):
        self.api_key = api_key
        self.mnemonic = mnemonic
        self.ton_client: Optional[tonutils.client.TonapiClient] = None
        self.wallet = None

    async def init_wallet(self):
        pass

    async def transfer(
        self,
        address: str,
        amount: float,
        comment: str,
    ) -> Dict[str, Any]:
        result = {
            "address": address,
            "amount": amount,
            "comment": comment,
            "success": False,
            "tx_hash": None,
            "error": None,
        }
        try:
            tx_hash = await send_ton(address, amount, comment)
            result["success"] = True
            result["tx_hash"] = tx_hash
        except Exception as e:
            result["error"] = str(e)
        return result

    async def close(self):
        pass


def parse_transfer_data(data, premium=False):
    addr = data["address"]
    if isinstance(data["amount"], str):
        data["amount"] = float(data["amount"])
    amount_ton = data["amount"] / 1e9
    raw_payload = data.get("payload", "")
    if premium:
        decoded = decode_payload_b64_premium(payload=raw_payload)
    else:
        decoded = decode_payload_b64(raw_payload)
    return addr, amount_ton, decoded


def decode_payload_b64(payload: str) -> str:
    try:
        payload += "=" * (-len(payload) % 4)
        cell = Cell.one_from_boc(base64.b64decode(payload))
        sl = cell.begin_parse()
        return sl.read_string().strip()
    except Exception as e:
        return f"decode_error: {e}"


def decode_payload_b64_premium(payload: str) -> str:
    try:
        payload += "=" * (-len(payload) % 4)
        raw_bytes = base64.b64decode(payload)
        decoded = raw_bytes.decode("utf-8", errors="ignore")
        filtered = "".join(ch for ch in decoded if 32 <= ord(ch) <= 126 or ch in "\r\n")
        filtered = re.sub(r"\r\n?", "\n", filtered)
        filtered = re.sub(r"[ ]*\n+", "\n\n", filtered).strip()
        idx = filtered.find("Telegram Premium")
        if idx != -1:
            filtered = filtered[idx:]
        return filtered
    except Exception as e:
        return f"decode_error: {e}"


async def retrieve_premium_transfer_info(
    login: str,
    months: int,
    hide_sender: int = 0,
):
    wm = WalletManager(API_KEY, MNEMONICS)
    await wm.init_wallet()
    async with aiohttp.ClientSession(
        cookies=FRAGMENT_COOKIES, headers=FRAGMENT_HEADERS
    ) as session:
        async with session.post(
            f"https://fragment.com/api?hash={FRAGMENT_HASH}",
            data={
                "query": login,
                "months": months,
                "method": "searchPremiumGiftRecipient",
            },
        ) as resp:
            print(await resp.text())
            raw = await resp.json()
        data = clean_and_filter(raw)
        if "error" in data:
            print(f"error (recipient): {data['error']}")
            return {"error": "invalid username"}
        recipient = data.get("found", {}).get("recipient")
        if not recipient:
            return {"error": "invalid recipient"}
        async with session.post(
            f"https://fragment.com/api?hash={FRAGMENT_HASH}",
            data={
                "recipient": recipient,
                "months": months,
                "method": "initGiftPremiumRequest",
            },
        ) as resp:
            raw = await resp.json()
        data = clean_and_filter(raw)
        if "error" in data:
            print(f"error (init request): {data['error']}")
            return False

        req_id = data.get("req_id")
        account = ""
        data5 = {
            "account": json.dumps(account),
            "device": json.dumps(DEVICE),
            "transaction": "1",
            "id": req_id,
            "show_sender": str(hide_sender),
            "method": "getGiftPremiumLink",
        }
        async with session.post(
            f"https://fragment.com/api?hash={FRAGMENT_HASH}", data=data5
        ) as resp:
            raw = await resp.json()
    data = clean_and_filter(raw)
    print(data)
    messages = data["transaction"].get("messages", [])
    addr, amount_ton, decoded = parse_transfer_data(messages[0], premium=True)
    return addr, amount_ton, decoded, wm


async def retrieve_stars_transfer_info(
    login: str,
    quantity: int,
    hide_sender: int = 0,
):
    wm = WalletManager(API_KEY, MNEMONICS)
    await wm.init_wallet()
    results: Dict[str, Any] = {}
    async with aiohttp.ClientSession(
        cookies=FRAGMENT_COOKIES, headers=FRAGMENT_HEADERS
    ) as session:
        steps = [
            (
                "updateStarsBuyState",
                {
                    "mode": "new",
                    "lv": "false",
                    "dh": "1",
                    "method": "updateStarsBuyState",
                },
            ),
            (
                "searchStarsRecipient",
                {
                    "query": login,
                    "quantity": str(quantity),
                    "method": "searchStarsRecipient",
                },
            ),
            (
                "updateStarsPrices",
                {"stars": "", "quantity": str(quantity), "method": "updateStarsPrices"},
            ),
            (
                "initBuyStarsRequest",
                {
                    "recipient": None,
                    "quantity": str(quantity),
                    "method": "initBuyStarsRequest",
                },
            ),
        ]
        for name, data in steps:
            if name == "initBuyStarsRequest":
                recipient = (
                    results["searchStarsRecipient"].get("found", {}).get("recipient")
                )
                data["recipient"] = recipient
            async with session.post(
                f"https://fragment.com/api?hash={FRAGMENT_HASH}", data=data
            ) as resp:
                raw = await resp.json()
            results[name] = clean_and_filter(raw)
            if name == "searchStarsRecipient" and "found" not in raw:
                await wm.close()
                # return clean_and_filter(results)
                return {"error": "invalid username"}

            if name == "initBuyStarsRequest" and not raw.get("req_id"):
                await wm.close()
                return clean_and_filter(results)
        req_id = results["initBuyStarsRequest"]["req_id"]
        account = ""
        data5 = {
            "account": json.dumps(account),
            "device": json.dumps(DEVICE),
            "transaction": "1",
            "id": req_id,
            "show_sender": str(hide_sender),
            "method": "getBuyStarsLink",
        }
        async with session.post(
            f"https://fragment.com/api?hash={FRAGMENT_HASH}", data=data5
        ) as resp5:
            raw5 = await resp5.json()
        results["getBuyStarsLink"] = clean_and_filter(raw5)
        if "transaction" not in results["getBuyStarsLink"]:
            await wm.close()
            return clean_and_filter(results)
    messages = results["getBuyStarsLink"]["transaction"].get("messages", [])
    addr, amount_ton, decoded = parse_transfer_data(messages[0])
    return addr, amount_ton, decoded, wm


async def buy_stars(
    login: str,
    quantity: int,
    hide_sender: int = 0,
):
    result = await retrieve_stars_transfer_info(login, quantity, hide_sender)
    if isinstance(result, dict):
        return result
    addr, amount_ton, decoded, wm = result
    await wm.transfer(addr, amount_ton, decoded)
    await wm.close()
    return amount_ton


async def buy_premium(
    login: str,
    months: int,
    hide_sender: int = 0,
):
    result = await retrieve_premium_transfer_info(login, months, hide_sender)
    if isinstance(result, dict):
        return result
    addr, amount_ton, decoded, wm = result
    await wm.transfer(addr, amount_ton, decoded)
    await wm.close()
    return amount_ton


#
#
# async def main() -> None:
# print(await buy_stars("kjbfsdmhnfvjhmsdfb11111", 1000))

# print(await retrieve_premium_transfer_info("kjbfsdmhnfvjhmsdfb", 12))


# asyncio.run(main())
