import asyncio
import math
import aiohttp
from aiohttp import ClientTimeout
from aiocache import cached, SimpleMemoryCache


API_KEY = "######"
BASE_URL = "https://fragment-purchase.fly.dev"
HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {API_KEY}",
}

API_KEY_2 = "######"
BASE_URL_2 = "https://pro-api.coinmarketcap.com/v2/tools/price-conversion"
HEADERS_2 = {"Accepts": "application/json", "X-CMC_PRO_API_KEY": API_KEY_2}
TIMEOUT = ClientTimeout(total=10)

BASE_STARS = 1000000
USER_STARS = 10000
USER_MONTHS = 12


def _const_key(func, *_, **__) -> str:
    return f"{func.__name__}:rate"


def _stars_key(func, _session, stars: int, username: str, *_, **__) -> str:
    return f"{func.__name__}:stars:={stars}:username={username}"


def _premium_key(func, _session, months: int, username: str, *_, **__) -> str:
    return f"{func.__name__}:months={months}:username={username}"


@cached(ttl=60, cache=SimpleMemoryCache, key_builder=_const_key)
async def __rate_ton_usdt() -> float:
    params = {"amount": 1, "symbol": "TON", "convert": "USDT"}
    async with aiohttp.ClientSession(timeout=TIMEOUT) as s:
        async with s.get(BASE_URL_2, headers=HEADERS_2, params=params) as r:
            if r.status != 200:
                raise RuntimeError(f"CMC HTTP {r.status}: {await r.text()}")
            data = await r.json()
            payload = data.get("data")
            if isinstance(payload, list) and payload:
                return float(payload[0]["quote"]["USDT"]["price"])
            return float(payload["quote"]["USDT"]["price"])


@cached(ttl=60, cache=SimpleMemoryCache, key_builder=_const_key)
async def __rate_usdt_ton() -> float:
    params = {"amount": 1, "symbol": "USDT", "convert": "TON"}
    async with aiohttp.ClientSession(timeout=TIMEOUT) as s:
        async with s.get(BASE_URL_2, headers=HEADERS_2, params=params) as r:
            if r.status != 200:
                raise RuntimeError(f"CMC HTTP {r.status}: {await r.text()}")
            data = await r.json()
            payload = data.get("data")
            if isinstance(payload, list) and payload:
                return float(payload[0]["quote"]["TON"]["price"])
            return float(payload["quote"]["TON"]["price"])


async def ton_to_usdt(amount_ton: float) -> float:
    if (
        not isinstance(amount_ton, (int, float))
        or not math.isfinite(amount_ton)
        or amount_ton <= 0
    ):
        raise ValueError("amount_ton must be a positive finite number.")
    return round(amount_ton * (await __rate_ton_usdt()), 4)


async def usdt_to_ton(amount_usdt: float) -> float:
    if (
        not isinstance(amount_usdt, (int, float))
        or not math.isfinite(amount_usdt)
        or amount_usdt <= 0
    ):
        raise ValueError("amount_ton must be a positive finite number.")
    return round(amount_usdt * (await __rate_usdt_ton()), 4)


@cached(ttl=120, cache=SimpleMemoryCache, key_builder=_stars_key)
async def __fetch_price_per_star(
    session, stars: int = 0, username: str = "kjbfsdmhnfvjhmsdfb"
):
    url = f"{BASE_URL}/price/stars"
    params = {"stars": BASE_STARS, "username": username}
    async with session.get(url, headers=HEADERS, params=params) as r:
        try:
            baseline_response = await r.json()
            if "error" in baseline_response:
                return None
            baseline_amount = baseline_response.get("amount", 0)
            price_per_star = baseline_amount / BASE_STARS
            return price_per_star

        except Exception as e:
            print(f"Error processing response: {e}")
            return None


@cached(ttl=120, cache=SimpleMemoryCache, key_builder=_stars_key)
async def fetch_stars_price(session, stars: int, username):
    price_per_star = await __fetch_price_per_star(session, 0, username)
    if price_per_star is None:
        return None
    total_amount_ton = price_per_star * stars
    total_amount_usdt = await ton_to_usdt(total_amount_ton)

    result = {
        "stars": stars,
        "amount_ton": round(total_amount_ton, 4),
        "amount_usdt": round(total_amount_usdt, 4),
    }
    return result


@cached(ttl=120, cache=SimpleMemoryCache, key_builder=_premium_key)
async def fetch_premium_price(session, months: int, username: str):
    url = f"{BASE_URL}/price/premium"
    params = {"months": months, "username": username}
    async with session.get(url, headers=HEADERS, params=params) as r:
        try:
            baseline_response = await r.json()
            if "error" in baseline_response:
                return None
            baseline_amount = baseline_response.get("amount", 0)
            total_amount_ton = baseline_amount
            total_amount_usdt = await ton_to_usdt(total_amount_ton)

            result = {
                "months": months,
                "amount_ton": round(total_amount_ton, 4),
                "amount_usdt": round(total_amount_usdt, 4),
            }
            return result

        except Exception as e:
            print(f"Error processing response: {e}")
            return None


async def main():
    print(await usdt_to_ton(3))
    # async with aiohttp.ClientSession() as session:
    # data = await fetch_stars_price(session, USER_STARS)
    # if data:
    #     print(
    #         f"{USER_STARS} stars = {data['amount_ton']} TON or {data['amount_usdt']} USDT\n"
    #     )
    # else:
    #     print("Failed to get price data")
    #
    # data = await fetch_premium_price(session, USER_MONTHS)
    # if data:
    #     print(
    #         f"{USER_MONTHS} months = {data['amount_ton']} TON or {data['amount_usdt']} USDT"
    #     )
    # else:
    #     print("Failed to get price data")
    #
    # data = await fetch_stars_price(session, 50)
    # if data:
    #     print(
    #         f"{USER_STARS} stars = {data['amount_ton']} TON or {data['amount_usdt']} USDT\n"
    #     )
    # else:
    #     print("Failed to get price data")
    #
    # data = await fetch_premium_price(session, USER_MONTHS)
    # if data:
    #     print(
    #         f"{USER_MONTHS} months = {data['amount_ton']} TON or {data['amount_usdt']} USDT"
    #     )
    # else:
    #     print("Failed to get price data")
    #
    # data = await fetch_premium_price(session, 3)
    # if data:
    #     print(
    #         f"{3} months = {data['amount_ton']} TON or {data['amount_usdt']} USDT"
    #     )
    # else:
    #     print("Failed to get price data")


if __name__ == "__main__":
    asyncio.run(main())
