from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LinkPreviewOptions

from base.callback_models import PremiumInvoice, StarsInvoice
from base.enums import InvoiceType
from base.invoice_results import PremiumInvoiceResult, StarsInvoiceResult
from config import router, TON_RECEIVER_ADDRESS
from db.invoices import create_invoice
from db.users import update_user
from utils.get_stars_premium_price import get_premium_price, get_stars_price
from utils.image_config import get_image_url
from utils.keyboards import get_invoice_menu_keyboard
from utils.texts import texts
from utils.utils import get_user_stars_commission_rate


@router.callback_query(PremiumInvoice.filter())
async def generate_premium_invoice_callback_query(
    c: CallbackQuery, callback_data: PremiumInvoice, state: FSMContext
):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()
    months = callback_data.months
    receiver = callback_data.receiver
    price = await get_premium_price(months=months)

    user_subscription = user["subscription"]
    user_commission_rate = get_user_stars_commission_rate(user_subscription)

    ton_price = round(price["ton"] * user_commission_rate, 4)
    usdt_price = round(price["usdt"] * user_commission_rate, 4)

    invoice = await create_invoice(
        user_id=c.from_user.id,
        invoice_type=InvoiceType.PREMIUM,
        amount_ton=ton_price,
        amount_usdt=usdt_price,
        result=PremiumInvoiceResult(
            months=months,
            receiver=receiver,
        ),
    )
    await c.message.edit_text(
        text=texts[lang]["messages"]["premium_payment"].format(
            months=months,
            ton_price=ton_price,
            usdt_price=usdt_price,
            receiver=receiver,
            invoice_id=invoice["id"],
            wallet_address=TON_RECEIVER_ADDRESS,
        ),
        reply_markup=get_invoice_menu_keyboard(lang=lang, invoice=invoice),
        link_preview_options=LinkPreviewOptions(
            show_above_text=True,
            url=get_image_url(lang, "premium_menu"),
        ),
    )
    await state.clear()


@router.callback_query(StarsInvoice.filter())
async def generate_stars_invoice_callback_query(
    c: CallbackQuery, callback_data: StarsInvoice, state: FSMContext
):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()
    stars_amount = callback_data.amount
    receiver = callback_data.receiver
    price = await get_stars_price(amount=stars_amount)

    user_subscription = user["subscription"]
    user_commission_rate = get_user_stars_commission_rate(user_subscription)

    ton_price = round(price["ton"] * user_commission_rate, 4)
    usdt_price = round(price["usdt"] * user_commission_rate, 4)

    invoice = await create_invoice(
        user_id=c.from_user.id,
        invoice_type=InvoiceType.STARS,
        amount_ton=ton_price,
        amount_usdt=usdt_price,
        result=StarsInvoiceResult(
            stars=stars_amount,
            receiver=receiver,
        ),
    )
    await c.message.edit_text(
        text=texts[lang]["messages"]["stars_payment"].format(
            ton_price=ton_price,
            usdt_price=usdt_price,
            receiver=receiver,
            invoice_id=invoice["id"],
            wallet_address=TON_RECEIVER_ADDRESS,
            amount=stars_amount,
        ),
        reply_markup=get_invoice_menu_keyboard(lang=lang, invoice=invoice),
        link_preview_options=LinkPreviewOptions(
            show_above_text=True,
            url=f"https://imggen.send.tg/checks/image?asset=STARS&asset_amount={stars_amount}&fiat=USD&fiat_amount=1&main=asset&v1",
        ),
    )
    await state.clear()
