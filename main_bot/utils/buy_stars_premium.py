import aiohttp

API_KEY = "######"
BASE_URL = "https://fragment-purchase.fly.dev"

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {API_KEY}",
}


async def __buy_premium(session, months: int, username: str):
    url = f"{BASE_URL}/buy/premium"
    payload = {"months": months, "username": username}
    async with session.post(url, headers=HEADERS, json=payload) as r:
        try:
            return await r.json()

        except Exception as e:
            print(f"Error processing response: {e}")
            return None


async def __buy_stars(session, stars: int, username: str):
    url = f"{BASE_URL}/buy/stars"
    payload = {"username": username, "stars": stars}
    async with session.post(url, headers=HEADERS, json=payload) as r:
        try:
            return await r.json()
        except Exception as e:
            print(f"Error processing response: {e}")
            return None


async def buy_premium(months: int, username: str):
    async with aiohttp.ClientSession() as session:
        return await __buy_premium(session, months, username)


async def buy_stars(amount: int, username: str):
    async with aiohttp.ClientSession() as session:
        return await __buy_stars(session, amount, username)
