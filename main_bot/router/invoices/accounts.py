from aiogram import F
from aiogram.types import CallbackQuery, LinkPreviewOptions

from base.enums import InvoiceType
from base.invoice_results import AutoBuyInvoiceResult, AccountInvoiceResult
from config import router, USDT_TON_RECEIVER_ADDRESS, TON_RECEIVER_ADDRESS
from base.callback_models import StarsLimitInvoice
from db.accounts import get_account_by_phone, get_available_accounts
from db.invoices import create_invoice
from db.users import update_user
from utils.get_price import usdt_to_ton
from utils.get_stars_premium_price import get_stars_price
from utils.image_config import get_image_url
from utils.keyboards import get_invoice_menu_keyboard
from utils.texts import texts


@router.callback_query(StarsLimitInvoice.filter())
async def _handle_create_autobuy_invoice(
    c: CallbackQuery, callback_data: StarsLimitInvoice
):
    user = await update_user(c.from_user)
    lang = user["language"]
    phone = callback_data.phone
    account = await get_account_by_phone(phone)
    amount = callback_data.stars

    price = await get_stars_price(amount=int(amount * user["commission_rate"] - amount))
    ton_price = round(price["ton"], 4)
    usdt_price = round(price["usdt"], 4)

    invoice = await create_invoice(
        user_id=c.from_user.id,
        invoice_type=InvoiceType.AUTOBUY,
        amount_ton=ton_price,
        amount_usdt=usdt_price,
        result=AutoBuyInvoiceResult(
            stars=amount,
            phone=phone,
        ),
    )

    await c.answer()

    await c.message.edit_text(
        text=texts[lang]["messages"]["autobuy_invoice_created"].format(
            username=account["username"],
            phone=phone,
            stars_balance=account["stars_balance"],
            stars_limit=amount,
            ton_price=ton_price,
            usdt_price=usdt_price,
            wallet_address=USDT_TON_RECEIVER_ADDRESS,
            invoice_id=invoice["id"],
        ),
        reply_markup=get_invoice_menu_keyboard(lang=lang, invoice=invoice),
        link_preview_options=LinkPreviewOptions(
            show_above_text=True,
            url=f"https://imggen.send.tg/checks/image?asset=STARS&asset_amount={amount}&fiat=USD&fiat_amount=1&main=asset&v1",
        ),
    )


@router.callback_query(F.data == "create_account_invoice")
async def create_account_invoice_callback_query(c: CallbackQuery):
    user = await update_user(c.from_user)
    lang = user["language"]
    amount_usdt = user["account_price"]
    available_accounts_amount = await get_available_accounts()

    if available_accounts_amount == 0:
        return await c.answer(
            "Out of stock, try again later.\n\nНет в наличии, попробуйте позже.",
            show_alert=True,
        )

    amount_ton = await usdt_to_ton(amount_usdt)
    invoice = await create_invoice(
        user_id=c.from_user.id,
        invoice_type=InvoiceType.ACCOUNT,
        amount_ton=amount_ton,
        amount_usdt=amount_usdt,
        result=AccountInvoiceResult(amount=1),
    )
    await c.message.edit_text(
        text=texts[lang]["messages"]["account_invoice_created"].format(
            ton_price=amount_ton,
            usdt_price=amount_usdt,
            invoice_id=invoice["id"],
            wallet_address=TON_RECEIVER_ADDRESS,
        ),
        reply_markup=get_invoice_menu_keyboard(lang=lang, invoice=invoice),
        link_preview_options=LinkPreviewOptions(
            show_above_text=True,
            url=get_image_url(lang, "autobuy"),
        ),
    )
    await c.answer()
