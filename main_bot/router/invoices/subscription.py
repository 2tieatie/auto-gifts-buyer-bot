from aiogram.types import CallbackQuery

from base.callback_models import SubscriptionInvoice
from base.enums import SubscriptionType
from base.invoice_results import SubscriptionInvoiceResult
from config import router, TON_RECEIVER_ADDRESS
from db.invoices import create_invoice
from db.users import update_user
from utils.get_price import usdt_to_ton
from utils.keyboards import get_invoice_menu_keyboard
from utils.texts import texts


@router.callback_query(SubscriptionInvoice.filter())
async def process_subscription_invoice(
    c: CallbackQuery, callback_data: SubscriptionInvoice
):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()
    subscription_type = callback_data.type

    # Set prices for each subscription type
    if callback_data.type == SubscriptionType.BASIC:
        price_usdt = 5
    elif callback_data.type == SubscriptionType.STANDARD:
        price_usdt = 10
    else:  # PREMIUM
        price_usdt = 15

    price_ton = await usdt_to_ton(price_usdt)

    invoice = await create_invoice(
        user_id=c.from_user.id,
        invoice_type=subscription_type,
        amount_ton=price_ton,
        amount_usdt=price_usdt,
        result=SubscriptionInvoiceResult(
            type=subscription_type,
        ),
    )

    # Get the correct payment text for each subscription type
    if callback_data.type == SubscriptionType.BASIC:
        payment_text = texts[lang]["messages"]["subscription_basic_payment"]
    elif callback_data.type == SubscriptionType.STANDARD:
        payment_text = texts[lang]["messages"]["subscription_standard_payment"]
    else:  # PREMIUM
        payment_text = texts[lang]["messages"]["subscription_premium_payment"]

    # Replace placeholders with actual values
    formatted_text = payment_text.replace(
        "[PRICE]", f"{price_ton} TON | {price_usdt} USDT"
    )
    formatted_text = formatted_text.replace("[TON_PRICE]", str(price_ton))
    formatted_text = formatted_text.replace("[USDT_PRICE]", str(price_usdt))
    formatted_text = formatted_text.replace("[WALLET ADDRESS]", TON_RECEIVER_ADDRESS)
    formatted_text = formatted_text.replace("[MEMO]", invoice["id"])

    await c.message.edit_text(
        text=formatted_text,
        reply_markup=get_invoice_menu_keyboard(lang=lang, invoice=invoice),
    )
