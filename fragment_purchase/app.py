import traceback
from email.policy import default
from enum import IntEnum

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from fragment_api import (
    retrieve_premium_transfer_info,
    buy_stars,
    retrieve_stars_transfer_info,
    buy_premium,
)

API_TOKEN = "######"
STAR_MIN, STAR_MAX = 50, 1_000_000
PREMIUM_ALLOWED_MONTHS = {3, 6, 12}

app = FastAPI(title="Billing API", version="1.0.0")


PUBLIC_PATHS = {
    p
    for p in (app.docs_url, app.redoc_url, app.openapi_url, "/docs/oauth2-redirect")
    if p
}


class PremiumMonths(IntEnum):
    three = 3
    six = 6
    twelve = 12


@app.middleware("http")
async def auth(request: Request, call_next):
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {API_TOKEN}":
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return await call_next(request)


class BuyStarsReq(BaseModel):
    username: str
    stars: int

    @field_validator("username")
    @classmethod
    def v_username(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 64:
            raise ValueError("invalid username")
        return v

    @field_validator("stars")
    @classmethod
    def v_stars(cls, v: int) -> int:
        if not (STAR_MIN <= v <= STAR_MAX):
            raise ValueError(f"stars must be between {STAR_MIN} and {STAR_MAX}")
        return v


class BuyPremiumReq(BaseModel):
    username: str
    months: int

    @field_validator("username")
    @classmethod
    def v_username(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 64:
            raise ValueError("invalid username")
        return v

    @field_validator("months")
    @classmethod
    def v_months(cls, v: int) -> int:
        if v not in PREMIUM_ALLOWED_MONTHS:
            raise ValueError("months must be one of 3, 6, 12")
        return v


@app.get("/price/stars")
async def get_stars_price(
    stars: int = Query(..., ge=STAR_MIN, le=STAR_MAX),
    username: str = Query(default="kjbfsdmhnfvjhmsdfb"),
):
    try:
        result = await retrieve_stars_transfer_info(username, quantity=stars)
        if isinstance(result, dict):
            return JSONResponse(result)
        _, amount, _, _ = result
    except Exception as e:
        print(traceback.format_exc())
        return {"error": str(e)}
    return {"stars": stars, "amount": amount}


@app.get("/price/premium")
async def get_premium_price(
    months: PremiumMonths = Query(...),
    username: str = Query(default="kjbfsdmhnfvjhmsdfb"),
):
    try:
        result = await retrieve_premium_transfer_info(username, months)
        if isinstance(result, dict):
            return JSONResponse(result)
        _, amount, _, _ = result
    except Exception as e:
        print(traceback.format_exc())
        return {"error": str(e)}
    return {"months": months, "amount": amount}


@app.post("/buy/stars")
async def _buy_stars(payload: BuyStarsReq):
    try:
        result = await buy_stars(payload.username, payload.stars)
        if isinstance(result, dict):
            return JSONResponse(result)
        amount = result
        return {
            "success": {
                "username": payload.username,
                "stars": payload.stars,
                "amount": amount,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})


@app.post("/buy/premium")
async def _buy_premium(payload: BuyPremiumReq):
    try:
        result = await buy_premium(payload.username, payload.months)
        if isinstance(result, dict):
            return JSONResponse(result)
        amount = result
        return {
            "success": {
                "username": payload.username,
                "months": payload.months,
                "amount": amount,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000)
