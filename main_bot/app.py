import asyncio
import importlib
import pkgutil
from contextlib import asynccontextmanager

from aiogram.types import LinkPreviewOptions
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from base.enums import InvoiceStatus, InvoiceType
from db.accounts import update_autobuy_stars_limit, transfer_account_ownership
from db.invoices import get_invoice_by_id, mark_paid

from config import dp, bot, router
from db.invoices import expire_invoices_loop
from db.users import get_user, update_subscription, increase_ref_balance
from utils.buy_stars_premium import buy_stars, buy_premium
from utils.get_price import ton_to_usdt
from utils.keyboards import get_return_to_main_menu_keyboard
from utils.texts import texts


def setup_routers(package="router"):
    pkg = importlib.import_module(package)
    for _, name, _ in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        mod = importlib.import_module(name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"BOT USERNAME @{(await bot.get_me()).username}")
    setup_routers()
    dp.include_router(router)
    asyncio.create_task(expire_invoices_loop())
    asyncio.create_task(dp.start_polling(bot))
    try:
        yield
    finally:
        return


API_TOKEN = "######"

app = FastAPI(title="MAIN SERVER", version="1.0.0", lifespan=lifespan)

PUBLIC_PATHS = {
    p
    for p in (app.docs_url, app.redoc_url, app.openapi_url, "/docs/oauth2-redirect")
    if p
}


@app.middleware("http")
async def auth(request: Request, call_next):
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {API_TOKEN}":
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return await call_next(request)


@app.post("/payment")
async def webhook(request: Request):
    tx_data = await request.json()
    print(tx_data)
    memo = tx_data.get("memo")
    if not memo:
        return

    invoice = await get_invoice_by_id(
        invoice_id=memo, filters={"status": InvoiceStatus.PENDING}
    )
    print("found invoice")
    if not invoice:
        return

    user_id = invoice["user_id"]

    user = await get_user(user_id)
    referrer = user["referrer"]

    amount_to_pay = invoice.get(f"amount_{tx_data['asset'].lower()}", None)

    if amount_to_pay is None or not amount_to_pay:
        return

    if round(amount_to_pay, 7) == round(float(tx_data["amount"]), 7):
        invoice = await mark_paid(
            invoice_id=invoice["id"],
            reason=f"paid in time by {tx_data['asset']}",
            tx_hash=tx_data["hash"],
        )
        print(invoice)
        invoice_result = invoice["result"]
        result = None
        if invoice["type"] == InvoiceType.STARS:
            result = await buy_stars(
                invoice_result["stars"], invoice_result["receiver"]
            )

            await bot.send_message(
                user_id,
                texts[user["language"]]["messages"]["stars_payment_success"].format(
                    stars=invoice_result["stars"], receiver=invoice_result["receiver"]
                ),
                reply_markup=get_return_to_main_menu_keyboard(lang=user["language"]),
                link_preview_options=LinkPreviewOptions(
                    show_above_text=True,
                    url=f"https://imggen.send.tg/checks/image?asset=STARS&asset_amount={invoice_result['stars']}&fiat=USD&fiat_amount=1&main=asset&v1",
                ),
            )
        elif invoice["type"] == InvoiceType.PREMIUM:
            result = await buy_premium(
                invoice_result["months"], invoice_result["receiver"]
            )
            await bot.send_message(
                user_id,
                texts[user["language"]]["messages"]["premium_payment_success"].format(
                    months=invoice_result["months"], receiver=invoice_result["receiver"]
                ),
                reply_markup=get_return_to_main_menu_keyboard(lang=user["language"]),
            )
        elif invoice["type"] == InvoiceType.AUTOBUY:
            result = await update_autobuy_stars_limit(
                invoice_result["phone"], invoice_result["stars"]
            )
            await bot.send_message(
                user_id,
                texts[user["language"]]["messages"]["autobuy_payment_success"].format(
                    phone=invoice_result["phone"], stars=invoice_result["stars"]
                ),
                reply_markup=get_return_to_main_menu_keyboard(lang=user["language"]),
            )
        elif invoice["type"] == InvoiceType.ACCOUNT:
            for _ in range(invoice_result["amount"]):
                result = await transfer_account_ownership(user_id)
                await bot.send_message(
                    user_id,
                    texts[user["language"]]["messages"][
                        "account_payment_success"
                    ].format(phone=result["phone"]),
                    reply_markup=get_return_to_main_menu_keyboard(
                        lang=user["language"]
                    ),
                )
        elif "subscription" in invoice["type"]:
            result = await update_subscription(user_id, invoice["type"])

            if referrer:
                referer_data = await get_user(referrer, from_cache=False)
                if tx_data["asset"] == "TON":
                    usdt_amount = await ton_to_usdt(amount_to_pay)
                else:
                    usdt_amount = amount_to_pay

                usdt_amount *= referer_data["ref_bonus"]

                await increase_ref_balance(referrer, round(usdt_amount, 4))

            await bot.send_message(
                user_id,
                f"подписка {invoice['type']} оплачена",
                reply_markup=get_return_to_main_menu_keyboard(lang=user["language"]),
            )
        else:
            return
        print(f"INVOICE PAYMENT RESULT: {result}")
    return JSONResponse({"status": "success"})
