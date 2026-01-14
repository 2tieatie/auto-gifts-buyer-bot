import time

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from base.enums import InvoiceStatus, SubscriptionType
from config import (
    TON_RECEIVER_ADDRESS,
    USDT_TON_MASTER_ADDRESS,
    USDT_TON_RECEIVER_ADDRESS,
)
from pyrogram.raw.functions.account import DeleteAccount

from base.callback_models import *
from utils.get_stars_premium_price import get_stars_price, get_premium_price
from utils.texts import texts

INVOICE_STATUS_EMOJI = {
    InvoiceStatus.PAID: "🟩",
    InvoiceStatus.PENDING: "🟨",
    InvoiceStatus.EXPIRED: "🟥",
    InvoiceStatus.CANCELED: "🟥",
}


def get_main_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🎁 {texts[lang]['inline_buttons']['autobuy_menu']}",
                    callback_data="autobuy_menu",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⭐️ {texts[lang]['inline_buttons']['buy_stars_menu']}",
                    callback_data="buy_stars_menu",
                ),
                InlineKeyboardButton(
                    text=f"💎 {texts[lang]['inline_buttons']['buy_premium_menu']}",
                    callback_data="buy_premium_menu",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"👤 {texts[lang]['inline_buttons']['me_menu']}",
                    callback_data="me_menu",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⚙️ {texts[lang]['inline_buttons']['settings']}",
                    callback_data="settings",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"📢 {texts[lang]['inline_buttons']['channel']}",
                    url="https://t.me/GIFTSZONECHANNEL",
                ),
                InlineKeyboardButton(
                    text=f"💬 {texts[lang]['inline_buttons']['chat']}",
                    url="https://t.me/GIFTSZONECHAT",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🆘 {texts[lang]['inline_buttons']['support']}",
                    url="https://t.me/GIFTSZONESUPPORT",
                )
            ],
        ]
    )


def get_settings_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🌐 {texts[lang]['inline_buttons']['change_language']}",
                    callback_data="change_language",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data="main_menu",
                )
            ],
        ]
    )


def get_change_language_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ 🇷🇺 Русский" if lang == "ru" else "🇷🇺 Русский",
                    callback_data="change_lang_ru",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ 🇺🇸 English" if lang == "en" else "🇺🇸 English",
                    callback_data="change_lang_en",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data="settings",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🏠 {texts[lang]['inline_buttons']['main_menu']}",
                    callback_data="main_menu",
                )
            ],
        ]
    )


def get_profile_menu_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"📋 {texts[lang]['inline_buttons']['invoices_menu']}",
                    callback_data=InvoicesPage(page=0).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Реферальная программа",
                    callback_data="referral_program",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data="main_menu",
                )
            ],
        ]
    )


async def get_buy_stars_keyboard(lang: str, comm_rate: float):
    stars_amount_arr = (5, 10, 25, 50, 100)
    prices = {
        amount: await get_stars_price(amount * 1000) for amount in stars_amount_arr
    }
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *[
                [
                    InlineKeyboardButton(
                        text=f"⭐️ {stars_amount}k • {round(values['ton'] * comm_rate, 2)} TON • ${round(values['usdt'] * comm_rate, 2)}",
                        callback_data=ChooseStarsAmount(
                            amount=stars_amount * 1000
                        ).pack(),
                    )
                ]
                for stars_amount, values in prices.items()
            ],
            [
                InlineKeyboardButton(
                    text=f"✏️ {texts[lang]['inline_buttons']['choose_own_stars_amount']}",
                    callback_data="choose_own_stars_amount",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data="main_menu",
                )
            ],
        ]
    )


async def get_buy_premium_keyboard(lang: str, comm_rate: float):
    months_arr = (3, 6, 12)
    prices = {months: await get_premium_price(months) for months in months_arr}
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *[
                [
                    InlineKeyboardButton(
                        text=(
                            f"💎 {months} мес • {round(price['ton'] * comm_rate, 2)} TON • ${round(price['usdt'] * comm_rate, 2)}"
                            if lang == "ru"
                            else f"💎 {months} months • {round(price['ton'] * comm_rate, 2)} TON • ${round(price['usdt'] * comm_rate, 2)}"
                        ),
                        callback_data=ChoosePremiumPeriod(months=months).pack(),
                    )
                ]
                for months, price in prices.items()
            ],
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data="main_menu",
                )
            ],
        ]
    )


def get_cancel_stars_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data="buy_stars_menu",
                )
            ],
        ]
    )


def get_cancel_premium_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data="buy_premium_menu",
                )
            ],
        ]
    )


def get_cancel_stars_limit_keyboard(lang: str, phone: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data=Account(phone=phone, prev="autobuy_menu").pack(),
                )
            ]
        ]
    )


def get_generate_stars_invoice_keyboard(lang: str, amount: int, receiver: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💳 {texts[lang]['inline_buttons']['pay']}",
                    callback_data=StarsInvoice(amount=amount, receiver=receiver).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data="buy_stars_menu",
                )
            ],
        ]
    )


def get_generate_premium_invoice_keyboard(lang: str, months: int, receiver: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💳 {texts[lang]['inline_buttons']['pay']}",
                    callback_data=PremiumInvoice(
                        months=months, receiver=receiver
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data="buy_premium_menu",
                )
            ],
        ]
    )


def get_autobuy_menu_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🛒 {texts[lang]['inline_buttons']['buy_account']}",
                    callback_data="buy_account_menu",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"➕ {texts[lang]['inline_buttons']['add_own_account']}",
                    callback_data="add_own_account",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"📱 {texts[lang]['inline_buttons']['my_accounts']}",
                    callback_data=AccountsPage(page=0).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"💎 {texts[lang]['inline_buttons']['subscription_plans']}",
                    callback_data="subscription_plans_menu",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data="main_menu",
                )
            ],
        ]
    )


def get_buy_account_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💳 {texts[lang]['inline_buttons']['pay']}",
                    callback_data="create_account_invoice",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data="autobuy_menu",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🏠 {texts[lang]['inline_buttons']['main_menu']}",
                    callback_data="main_menu",
                )
            ],
        ]
    )


def get_invoice_menu_keyboard(lang: str, invoice: dict, prev: str = None):
    callbacks = []
    invoice_id = invoice["id"]
    amount_ton = invoice["amount_ton"]
    amount_usdt = invoice["amount_usdt"]
    ton_nanos = int(amount_ton * 1e9)
    usdt_nanos = int(amount_usdt * 1e6)

    if invoice["status"] == InvoiceStatus.PENDING:
        callbacks.append(
            [
                InlineKeyboardButton(
                    text="❌ Отменить" if lang == "ru" else "❌ Cancel",
                    callback_data=CancelInvoice(invoice_id=invoice_id).pack(),
                )
            ]
        )
        callbacks.extend(
            [
                [
                    InlineKeyboardButton(
                        text="💎 TON (любой)" if lang == "ru" else "💎 TON (any)",
                        url=f"ton://transfer/{TON_RECEIVER_ADDRESS}?amount={ton_nanos}&text={invoice_id}",
                    ),
                    InlineKeyboardButton(
                        text="💵 USDT (любой)" if lang == "ru" else "💵 USDT (any)",
                        url=f"ton://transfer/{USDT_TON_RECEIVER_ADDRESS}?amount={usdt_nanos}&jetton={USDT_TON_MASTER_ADDRESS}&text={invoice_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=(
                            "💎 TON (TONKEEPER)"
                            if lang == "ru"
                            else "💎 TON (TONKEEPER)"
                        ),
                        url=f"https://app.tonkeeper.com/transfer/{TON_RECEIVER_ADDRESS}?amount={ton_nanos}&text={invoice_id}",
                    ),
                    InlineKeyboardButton(
                        text=(
                            "💵 USDT (TONKEEPER)"
                            if lang == "ru"
                            else "💵 USDT (TONKEEPER)"
                        ),
                        url=f"https://app.tonkeeper.com/transfer/{USDT_TON_RECEIVER_ADDRESS}?amount={usdt_nanos}&jetton={USDT_TON_MASTER_ADDRESS}&text={invoice_id}",
                    ),
                ],
            ]
        )
    if prev:
        callbacks.append(
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data=prev,
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            *callbacks,
            [
                InlineKeyboardButton(
                    text=f"🏠 {texts[lang]['inline_buttons']['main_menu']}",
                    callback_data="main_menu",
                )
            ],
        ]
    )


def get_user_invoices_kb(
    lang: str,
    invoices: list,
    page: int,
    pages_total: int,
    show_all_button: bool = False,
):
    pages_total = max(1, pages_total)
    page = max(0, min(page, pages_total - 1))

    invoices_buttons = []
    for invoice in invoices:
        status = INVOICE_STATUS_EMOJI[invoice["status"]]
        time_left = ""
        if invoice["status"] == InvoiceStatus.PENDING:
            time_unit = "мин" if lang == "ru" else "min"
            time_left = f" · ⏰ {int(invoice['expires_at_unix'] - time.time()) // 60} {time_unit}"

        # Format amount for better readability
        amount_display = f"${round(invoice['amount_usdt'], 2)}"

        invoices_buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{status} · {invoice['type'].capitalize()} · {amount_display}{time_left}",
                    callback_data=Invoice(
                        invoice_id=invoice["id"], prev=InvoicesPage(page=page).pack()
                    ).pack(),
                )
            ]
        )

    # Add toggle button for hiding/showing expired invoices
    if show_all_button:
        toggle_text = "👁️ Скрыть истекшие" if lang == "ru" else "👁️ Hide expired"
        toggle_callback = InvoicesPage(page=0, show_expired=False).pack()
    else:
        toggle_text = "👁️ Показать все" if lang == "ru" else "👁️ Show all"
        toggle_callback = InvoicesPage(page=page, show_expired=True).pack()

    toggle_button = [
        InlineKeyboardButton(text=toggle_text, callback_data=toggle_callback)
    ]

    prev_exists = page > 0
    next_exists = page < pages_total - 1
    invisible = "\u2063"

    prev_btn = InlineKeyboardButton(
        text="◀️" if prev_exists else invisible,
        callback_data=(
            InvoicesPage(page=page - 1, show_expired=show_all_button).pack()
            if prev_exists
            else "noop"
        ),
    )
    page_btn = InlineKeyboardButton(
        text=f"📄 {page + 1}/{pages_total}",
        callback_data="noop",
    )
    next_btn = InlineKeyboardButton(
        text="▶️" if next_exists else invisible,
        callback_data=(
            InvoicesPage(page=page + 1, show_expired=show_all_button).pack()
            if next_exists
            else "noop"
        ),
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            toggle_button,
            *invoices_buttons,
            [prev_btn, page_btn, next_btn],
            [
                InlineKeyboardButton(
                    text=f"🏠 {texts[lang]['inline_buttons']['main_menu']}",
                    callback_data="main_menu",
                )
            ],
        ]
    )


def get_return_to_main_menu_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🏠 {texts[lang]['inline_buttons']['main_menu']}",
                    callback_data="main_menu",
                )
            ]
        ]
    )


# 1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣8️⃣9️⃣⬅️✅
def get_add_account_keyboard(
    lang: str, resend_code: bool = False, phone_code: str = None
):
    phone_code_kb = []
    if phone_code is not None:
        phone_code_kb = [
            [
                InlineKeyboardButton(
                    text=i,
                    callback_data=PhoneCode(
                        code=phone_code + num if len(phone_code) < 5 else phone_code
                    ).pack(),
                )
                for i, num in [("1️⃣", "1"), ("2️⃣", "2"), ("3️⃣", "3")]
            ],
            [
                InlineKeyboardButton(
                    text=i,
                    callback_data=PhoneCode(
                        code=phone_code + num if len(phone_code) < 5 else phone_code
                    ).pack(),
                )
                for i, num in [("4️⃣", "4"), ("5️⃣", "5"), ("6️⃣", "6")]
            ],
            [
                InlineKeyboardButton(
                    text=i,
                    callback_data=PhoneCode(
                        code=phone_code + num if len(phone_code) < 5 else phone_code
                    ).pack(),
                )
                for i, num in [("7️⃣", "7"), ("8️⃣", "8"), ("9️⃣", "9")]
            ],
            [
                InlineKeyboardButton(
                    text="⬅️", callback_data=PhoneCode(code=phone_code[:-1]).pack()
                ),
                InlineKeyboardButton(
                    text="0️⃣",
                    callback_data=PhoneCode(
                        code=phone_code + "0" if len(phone_code) < 5 else phone_code
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="✅",
                    callback_data=PhoneCode(
                        code=f"{phone_code}+" if len(phone_code) == 5 else ""
                    ).pack(),
                ),
            ],
        ]

    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=texts[lang]["inline_buttons"]["cancel"],
                callback_data="terminate_add_account",
            )
        ]
    ]
    phone_code_kb.extend(inline_keyboard)
    if resend_code:
        phone_code_kb.append(
            [
                InlineKeyboardButton(
                    text=texts[lang]["inline_buttons"]["resend_code"],
                    callback_data="resend_code",
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=phone_code_kb,
    )


def get_user_accounts_kb(lang: str, accounts: list, page: int, pages_total: int):
    pages_total = max(1, pages_total)
    page = max(0, min(page, pages_total - 1))

    accounts_buttons = []
    for account in accounts:
        accounts_buttons.append(
            [
                InlineKeyboardButton(
                    text=f"📱 {account['phone']}",
                    callback_data=Account(
                        phone=account["phone"], prev=AccountsPage(page=page).pack()
                    ).pack(),
                )
            ]
        )

    prev_exists = page > 0
    next_exists = page < pages_total - 1
    invisible = "\u2063"

    prev_btn = InlineKeyboardButton(
        text="◀️" if prev_exists else invisible,
        callback_data=AccountsPage(page=page - 1).pack() if prev_exists else "noop",
    )
    page_btn = InlineKeyboardButton(
        text=f"📄 {page + 1}/{pages_total}",
        callback_data="noop",
    )
    next_btn = InlineKeyboardButton(
        text="▶️" if next_exists else invisible,
        callback_data=AccountsPage(page=page + 1).pack() if next_exists else "noop",
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            *accounts_buttons,
            [prev_btn, page_btn, next_btn],
            [
                InlineKeyboardButton(
                    text=f"🏠 {texts[lang]['inline_buttons']['main_menu']}",
                    callback_data="main_menu",
                )
            ],
        ]
    )


def get_account_menu_keyboard(
    lang: str, account: dict, prev: str = None, can_delete: bool = False
):
    callbacks = [
        [
            InlineKeyboardButton(
                text=texts[lang]["inline_buttons"]["get_codes"],
                callback_data=AccountCodes(
                    phone=account["phone"],
                ).pack(),
            )
        ]
    ]

    if account["stars_limit"] == 0:
        callbacks.append(
            [
                InlineKeyboardButton(
                    text=texts[lang]["inline_buttons"]["setup_autobuy"],
                    callback_data=ChooseStarsLimit(phone=account["phone"]).pack(),
                )
            ]
        )

    callbacks.append(
        [
            InlineKeyboardButton(
                text=texts[lang]["inline_buttons"]["change_gifts_receiver"],
                callback_data=ChangeGiftsReceiver(phone=account["phone"]).pack(),
            )
        ],
    )

    if can_delete:
        callbacks.append(
            [
                InlineKeyboardButton(
                    text=texts[lang]["inline_buttons"]["delete_account"],
                    callback_data=DeleteAccount(
                        phone=account["phone"], confirmation=True, confirmed=False
                    ).pack(),
                )
            ]
        )

    if prev:
        callbacks.append(
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data=prev,
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            *callbacks,
            [
                InlineKeyboardButton(
                    text=f"🏠 {texts[lang]['inline_buttons']['main_menu']}",
                    callback_data="main_menu",
                )
            ],
        ]
    )


def get_delete_account_confirmation_kb(lang: str, account: dict):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts[lang]["inline_buttons"]["confirm"],
                    callback_data=DeleteAccount(
                        phone=account["phone"], confirmation=True, confirmed=True
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text=texts[lang]["inline_buttons"]["cancel"],
                    callback_data=Account(
                        phone=account["phone"], prev="autobuy_menu"
                    ).pack(),
                ),
            ]
        ]
    )


def get_create_autobuy_invoice(lang: str, phone: str, amount: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💳 {texts[lang]['inline_buttons']['pay']}",
                    callback_data=StarsLimitInvoice(phone=phone, stars=amount).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data=Account(phone=phone, prev="autobuy_menu").pack(),
                )
            ],
        ]
    )


def get_subscription_plans_menu_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🥇 {texts[lang]['inline_buttons']['subscription_premium']}",
                    callback_data=SubscriptionMenu(
                        type=SubscriptionType.PREMIUM
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🥈 {texts[lang]['inline_buttons']['subscription_standard']}",
                    callback_data=SubscriptionMenu(
                        type=SubscriptionType.STANDARD
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🥉 {texts[lang]['inline_buttons']['subscription_basic']}",
                    callback_data=SubscriptionMenu(type=SubscriptionType.BASIC).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data="main_menu",
                )
            ],
        ]
    )


def get_create_subscription_invoice(lang: str, subscription_type: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💳 {texts[lang]['inline_buttons']['pay']}",
                    callback_data=SubscriptionInvoice(type=subscription_type).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⬅️ {texts[lang]['inline_buttons']['back']}",
                    callback_data="autobuy_menu",
                )
            ],
        ]
    )
