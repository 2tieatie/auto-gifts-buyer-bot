import aiohttp
from utils.get_price import fetch_stars_price, fetch_premium_price


async def get_stars_price(
    amount: int, username: str = "kjbfsdmhnfvjhmsdfb"
) -> dict[str, float] | None:
    async with aiohttp.ClientSession() as session:
        data = await fetch_stars_price(session, amount, username)
        if data:
            ton = data["amount_ton"]
            usdt = data["amount_usdt"]
            return {"usdt": round(usdt, 6), "ton": round(ton, 6)}
    return None


async def get_premium_price(
    months: int, username: str = "kjbfsdmhnfvjhmsdfb"
) -> dict[str, float] | None:
    async with aiohttp.ClientSession() as session:
        data = await fetch_premium_price(session, months, username)
        if data:
            ton = data["amount_ton"]
            usdt = data["amount_usdt"]
            return {"usdt": round(usdt, 6), "ton": round(ton, 6)}
    return None
