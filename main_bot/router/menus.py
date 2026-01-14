from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LinkPreviewOptions

from base.callback_models import SubscriptionMenu
from base.enums import SubscriptionType
from config import router
from db.users import get_user, update_user
from utils.get_price import usdt_to_ton
from utils.image_config import get_image_url
from utils.keyboards import (
    get_autobuy_menu_keyboard,
    get_subscription_plans_menu_keyboard,
    get_buy_account_keyboard,
    get_create_subscription_invoice,
    get_profile_menu_keyboard,
    get_buy_stars_keyboard,
    get_buy_premium_keyboard,
    get_settings_keyboard,
    get_main_keyboard,
)
from utils.texts import texts
from utils.utils import get_profile_text, get_user_stars_commission_rate


@router.callback_query(F.data == "autobuy_menu")
async def autobuy_menu_callback_query(c: CallbackQuery):
    user = await get_user(user_id=c.from_user.id, from_cache=False)
    lang = user["language"]

    subscription = user.get("subscription")
    await c.answer()

    if subscription:
        await c.message.edit_text(
            texts[lang]["messages"]["autobuy_menu"],
            reply_markup=get_autobuy_menu_keyboard(lang=lang),
            link_preview_options=LinkPreviewOptions(
                show_above_text=True,
                url=get_image_url(lang, "autobuy"),
            ),
        )
        return

    await c.message.edit_text(
        texts[lang]["messages"]["subscription_plans_menu"],
        reply_markup=get_subscription_plans_menu_keyboard(lang=lang),
    )


@router.callback_query(F.data == "subscription_plans_menu")
async def subscription_plans_menu_callback_query(c: CallbackQuery):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()

    await c.message.edit_text(
        texts[lang]["messages"]["subscription_plans_menu"],
        reply_markup=get_subscription_plans_menu_keyboard(lang=lang),
    )


@router.callback_query(F.data == "buy_account_menu")
async def buy_account_callback_query(c: CallbackQuery):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()

    await c.message.edit_text(
        text=texts[lang]["messages"]["buy_account_invoice"],
        reply_markup=get_buy_account_keyboard(lang=lang),
        link_preview_options=LinkPreviewOptions(
            show_above_text=True,
            url=get_image_url(lang, "autobuy"),
        ),
    )


@router.callback_query(SubscriptionMenu.filter())
async def process_subscription_type(c: CallbackQuery, callback_data: SubscriptionMenu):
    user = await update_user(c.from_user)
    lang = user["language"]

    await c.answer()

    # Set prices for each subscription type
    if callback_data.type == SubscriptionType.BASIC:
        price_usdt = 5
        details_key = "subscription_basic_details"
    elif callback_data.type == SubscriptionType.STANDARD:
        price_usdt = 10
        details_key = "subscription_standard_details"
    else:  # PREMIUM
        price_usdt = 15
        details_key = "subscription_premium_details"

    price_ton = await usdt_to_ton(price_usdt)

    # Get the detailed subscription text and replace placeholders
    subscription_text = texts[lang]["messages"][details_key]
    subscription_text = subscription_text.replace(
        "[ЦЕНА]", f"{price_ton} TON | {price_usdt} USDT"
    )
    subscription_text = subscription_text.replace(
        "[PRICE]", f"{price_ton} TON | {price_usdt} USDT"
    )

    await c.message.edit_text(
        text=subscription_text,
        reply_markup=get_create_subscription_invoice(
            lang=lang, subscription_type=callback_data.type
        ),
    )


@router.callback_query(F.data == "me_menu")
async def open_me_menu(c: CallbackQuery):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()

    await c.message.edit_text(
        text=await get_profile_text(user=user),
        reply_markup=get_profile_menu_keyboard(lang=lang),
    )


@router.callback_query(F.data == "stars_premium_menu")
async def open_buy_stars_premium(c: CallbackQuery):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()
    await c.message.edit_text(
        text=texts[lang]["messages"]["buy_stars_premium"],
        # reply_markup=get_buy_stars_premium_keyboard(lang=lang),
    )


@router.callback_query(F.data == "buy_stars_menu")
async def open_buy_stars(c: CallbackQuery, state: FSMContext):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()
    await state.clear()

    user_subscription = user["subscription"]
    user_commission_rate = get_user_stars_commission_rate(user_subscription)

    await c.message.edit_text(
        text=texts[lang]["messages"]["buy_stars"],
        reply_markup=await get_buy_stars_keyboard(
            lang=lang, comm_rate=user_commission_rate
        ),
        link_preview_options=LinkPreviewOptions(
            show_above_text=True,
            url=get_image_url(lang, "stars_menu"),
        ),
    )


@router.callback_query(F.data == "buy_premium_menu")
async def open_buy_premium(c: CallbackQuery, state: FSMContext):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()
    await state.clear()

    user_subscription = user["subscription"]
    user_commission_rate = get_user_stars_commission_rate(user_subscription)

    await c.message.edit_text(
        text=texts[lang]["messages"]["buy_premium"],
        reply_markup=await get_buy_premium_keyboard(
            lang=lang, comm_rate=user_commission_rate
        ),
        link_preview_options=LinkPreviewOptions(
            show_above_text=True,
            url=get_image_url(lang, "premium_menu"),
        ),
    )


@router.callback_query(F.data == "settings")
async def open_settings(c: CallbackQuery):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()

    await c.message.edit_text(
        text=texts[lang]["messages"]["settings"],
        reply_markup=get_settings_keyboard(lang=lang),
    )


@router.callback_query(F.data == "main_menu")
async def open_main_menu(c: CallbackQuery):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()

    await c.message.edit_text(
        text=texts[lang]["messages"]["main_menu"],
        reply_markup=get_main_keyboard(lang=lang),
        link_preview_options=LinkPreviewOptions(
            show_above_text=True,
            url=get_image_url(lang, "main_menu"),
        ),
    )
