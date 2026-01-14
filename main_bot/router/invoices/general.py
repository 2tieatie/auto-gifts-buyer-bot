from aiogram.types import CallbackQuery, LinkPreviewOptions

from base.callback_models import CancelInvoice, InvoicesPage, Invoice
from base.enums import InvoiceStatus
from config import router, TON_RECEIVER_ADDRESS
from db.invoices import mark_canceled, get_invoice_by_id, get_user_invoices
from db.users import update_user
from utils.image_config import get_image_url
from utils.keyboards import (
    get_return_to_main_menu_keyboard,
    get_invoice_menu_keyboard,
    get_user_invoices_kb,
)
from utils.texts import texts


@router.callback_query(CancelInvoice.filter())
async def cancel_invoice(c: CallbackQuery, callback_data: CancelInvoice):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()
    invoice_id = callback_data.invoice_id
    invoice = await mark_canceled(invoice_id=invoice_id, reason="user cancelled")
    await c.message.edit_text(
        text=texts[lang]["messages"]["order_cancelled"].format(
            invoice_id=invoice["id"]
        ),
        reply_markup=get_return_to_main_menu_keyboard(lang=lang),
        link_preview_options=LinkPreviewOptions(
            show_above_text=True,
            url=get_image_url(lang, "autobuy"),
        ),
    )


@router.callback_query(Invoice.filter())
async def invoice_menu_callback_query(c: CallbackQuery, callback_data: Invoice):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()
    invoice = await get_invoice_by_id(invoice_id=callback_data.invoice_id)

    created_at = (
        invoice["created_at"].strftime("%d.%m.%Y")
        if hasattr(invoice["created_at"], "strftime")
        else str(invoice["created_at"])
    )

    expires_at = invoice["expires_at_unix"]
    if isinstance(expires_at, (int, float)):
        import time

        current_time = time.time()
        time_left = expires_at - current_time

        if time_left <= 0:
            time_display = "Истек" if lang == "ru" else "Expired"
        else:
            hours = int(time_left // 3600)
            minutes = int((time_left % 3600) // 60)

            if lang == "ru":
                if hours > 0:
                    time_display = f"{hours}ч {minutes}мин"
                else:
                    time_display = f"{minutes}мин"
            else:
                if hours > 0:
                    time_display = f"{hours}h {minutes}m"
                else:
                    time_display = f"{minutes}m"
    else:
        time_display = str(expires_at)

    status_translated = texts[lang]["status_translations"].get(
        invoice["status"], invoice["status"]
    )
    type_translated = texts[lang]["type_translations"].get(
        invoice["type"], invoice["type"]
    )

    if str(invoice["status"]) == InvoiceStatus.PENDING:
        payment_instructions = texts[lang]["messages"]["payment_instructions"].format(
            ton_amount=round(invoice["amount_ton"], 4),
            usdt_amount=round(invoice["amount_usdt"], 2),
            wallet_address=TON_RECEIVER_ADDRESS,
            invoice_id=invoice["id"],
        )
    else:
        payment_instructions = ""

    invoice_type = str(invoice["type"]).lower() if invoice["type"] else ""

    if invoice_type == "stars":
        result_data = invoice.get("result", {})
        if isinstance(result_data, str):
            try:
                import json

                result_data = json.loads(result_data)
            except:
                result_data = {}

        stars_amount = result_data.get("stars", 0) if result_data else 0
        receiver = result_data.get("receiver", "unknown") if result_data else "unknown"

        if not stars_amount:
            stars_amount = 1000

        message_text = texts[lang]["messages"]["invoice_details_stars"].format(
            invoice_id=invoice["id"],
            stars_amount=stars_amount,
            usdt_amount=round(invoice["amount_usdt"], 2),
            ton_amount=round(invoice["amount_ton"], 4),
            status=status_translated,
            receiver=receiver,
            created_at=created_at,
            expires_at=time_display,
            payment_instructions=payment_instructions,
        )
    elif invoice_type == "premium":
        result_data = invoice.get("result", {})
        if isinstance(result_data, str):
            try:
                import json

                result_data = json.loads(result_data)
            except:
                result_data = {}

        months = result_data.get("months", 0) if result_data else 0
        receiver = result_data.get("receiver", "unknown") if result_data else "unknown"

        if not months:
            months = 1

        message_text = texts[lang]["messages"]["invoice_details_premium"].format(
            invoice_id=invoice["id"],
            months=months,
            usdt_amount=round(invoice["amount_usdt"], 2),
            ton_amount=round(invoice["amount_ton"], 4),
            status=status_translated,
            receiver=receiver,
            created_at=created_at,
            expires_at=time_display,
            payment_instructions=payment_instructions,
        )
    else:
        message_text = texts[lang]["messages"]["invoice_details"].format(
            invoice_id=invoice["id"],
            type=type_translated,
            usdt_amount=round(invoice["amount_usdt"], 2),
            ton_amount=round(invoice["amount_ton"], 4),
            status=status_translated,
            created_at=created_at,
            expires_at=time_display,
        )

    await c.message.edit_text(
        message_text,
        reply_markup=get_invoice_menu_keyboard(
            lang=lang, invoice=invoice, prev=callback_data.prev
        ),
    )


@router.callback_query(InvoicesPage.filter())
async def invoices_menu_callback_query(c: CallbackQuery, callback_data: InvoicesPage):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()
    user_invoices = await get_user_invoices(
        user_id=c.from_user.id,
        page=callback_data.page + 1,
        show_expired=callback_data.show_expired,
    )
    await c.message.edit_text(
        texts[lang]["messages"]["invoices_list"],
        reply_markup=get_user_invoices_kb(
            lang=lang,
            page=callback_data.page,
            pages_total=user_invoices["pages"],
            invoices=user_invoices["items"],
            show_all_button=callback_data.show_expired,
        ),
    )
