from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
    LinkPreviewOptions,
)

from config import (
    router,
)
from db.users import update_user, update_user_language, get_referrals_count
from base.fsm_states import Stars, Premium
from base.callback_models import *
from utils.get_stars_premium_price import get_stars_price, get_premium_price
from utils.image_config import get_image_url
from utils.keyboards import (
    get_change_language_keyboard,
    get_cancel_stars_keyboard,
    get_generate_stars_invoice_keyboard,
    get_cancel_premium_keyboard,
    get_generate_premium_invoice_keyboard,
)
from utils.texts import texts
from utils.utils import (
    is_valid_username,
    get_user_stars_commission_rate,
)


@router.callback_query(F.data == "change_language")
async def open_settings(c: CallbackQuery):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()

    await c.message.edit_text(
        text=texts[lang]["messages"]["change_language"],
        reply_markup=get_change_language_keyboard(lang=lang),
    )


@router.callback_query(F.data.startswith("change_lang_"))
async def change_lang(c: CallbackQuery):
    new_lang = c.data.split("_", 2)[-1]
    old_user = await update_user(c.from_user)
    user = await update_user_language(c.from_user, new_lang)
    await c.answer()
    if old_user["language"] != user["language"]:
        await c.message.edit_text(
            texts[new_lang]["messages"]["change_language"],
            reply_markup=get_change_language_keyboard(lang=user["language"]),
        )


@router.callback_query(F.data == "choose_own_stars_amount")
async def choose_stars_quantity(c: CallbackQuery, state: FSMContext):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()
    await state.set_state(Stars.amount)
    await c.message.edit_text(
        text=texts[lang]["messages"]["enter_stars_amount"],
        reply_markup=get_cancel_stars_keyboard(lang=lang),
        link_preview_options=LinkPreviewOptions(
            show_above_text=True,
            url=get_image_url(lang, "stars_input"),
        ),
    )


@router.callback_query(ChooseStarsAmount.filter())
async def choose_stars_amount(
    c: CallbackQuery, callback_data: ChooseStarsAmount, state: FSMContext
):
    user = await update_user(c.from_user)
    lang = user["language"]
    amount = callback_data.amount
    await state.set_state(Stars.receiver)
    await state.update_data(amount=amount)
    price = await get_stars_price(amount=amount)

    user_subscription = user["subscription"]
    user_commission_rate = get_user_stars_commission_rate(user_subscription)

    ton_price = round(price["ton"] * user_commission_rate, 4)
    usdt_price = round(price["usdt"] * user_commission_rate, 4)

    await c.answer()
    await c.message.edit_text(
        text=texts[lang]["messages"]["stars_purchase_confirmation"].format(
            amount=amount, ton_price=ton_price, usdt_price=usdt_price
        ),
        reply_markup=get_cancel_stars_keyboard(lang=lang),
        link_preview_options=LinkPreviewOptions(
            show_above_text=True,
            url=f"https://imggen.send.tg/checks/image?asset=STARS&asset_amount={amount}&fiat=USD&fiat_amount=1&main=asset&v1",
        ),
    )


@router.message(Stars.amount)
async def handle_amount(message: Message, state: FSMContext):
    user = await update_user(message.from_user)
    lang = user["language"]
    try:
        amount = int(message.text)
    except ValueError:
        await message.answer(
            text=texts[lang]["messages"]["invalid_input_error"],
            reply_markup=get_cancel_stars_keyboard(lang=lang),
            link_preview_options=LinkPreviewOptions(
                show_above_text=True,
                url=get_image_url(lang, "error"),
            ),
        )
        return

    if amount not in range(50, 1_000_000):
        await message.answer(
            text=texts[lang]["messages"]["invalid_amount_error"],
            reply_markup=get_cancel_stars_keyboard(lang=lang),
            link_preview_options=LinkPreviewOptions(
                show_above_text=True,
                url=get_image_url(lang, "error"),
            ),
        )
        return
    price = await get_stars_price(amount=amount)

    user_subscription = user["subscription"]
    user_commission_rate = get_user_stars_commission_rate(user_subscription)

    ton_price = round(price["ton"] * user_commission_rate, 4)
    usdt_price = round(price["usdt"] * user_commission_rate, 4)

    await state.set_state(Stars.receiver)
    await state.update_data(amount=amount)
    await message.answer(
        text=texts[lang]["messages"]["stars_purchase_confirmation"].format(
            amount=amount, ton_price=ton_price, usdt_price=usdt_price
        ),
        reply_markup=get_cancel_stars_keyboard(lang=lang),
        link_preview_options=LinkPreviewOptions(
            show_above_text=True,
            url=f"https://imggen.send.tg/checks/image?asset=STARS&asset_amount={amount}&fiat=USD&fiat_amount=1&main=asset&v1",
        ),
    )


@router.message(Stars.receiver)
async def handle_receiver(message: Message, state: FSMContext):
    user = await update_user(message.from_user)
    lang = user["language"]
    receiver = message.text.strip()

    if not receiver or not is_valid_username(receiver):
        await message.answer(
            text=texts[lang]["messages"]["invalid_username_error"],
            reply_markup=get_cancel_stars_keyboard(lang=lang),
            link_preview_options=LinkPreviewOptions(
                show_above_text=True,
                url=get_image_url(lang, "error"),
            ),
        )
        return

    receiver = receiver.replace("@", "")

    data = await state.get_data()
    price = await get_stars_price(amount=data["amount"], username=receiver)

    if not price:
        await message.answer(
            text=texts[lang]["messages"]["receiver_stars_not_found"].format(
                receiver=receiver
            ),
            reply_markup=get_cancel_stars_keyboard(lang=lang),
        )
        return

    user_subscription = user["subscription"]
    user_commission_rate = get_user_stars_commission_rate(user_subscription)

    ton_price = round(price["ton"] * user_commission_rate, 4)
    usdt_price = round(price["usdt"] * user_commission_rate, 4)

    receiver = receiver.strip().replace("@", "")
    await state.set_state(Stars.invoice)
    await state.update_data(receiver=receiver)
    await message.answer(
        text=texts[lang]["messages"]["stars_confirmation"].format(
            ton_price=ton_price,
            usdt_price=usdt_price,
            receiver=receiver,
            amount=data["amount"],
        ),
        reply_markup=get_generate_stars_invoice_keyboard(
            lang=lang, amount=data["amount"], receiver=receiver
        ),
        link_preview_options=LinkPreviewOptions(
            show_above_text=True,
            url=f"https://imggen.send.tg/checks/image?asset=STARS&asset_amount={data['amount']}&fiat=USD&fiat_amount=1&main=asset&v1",
        ),
    )


@router.callback_query(ChoosePremiumPeriod.filter())
async def choose_premium_receiver(
    c: CallbackQuery, callback_data: ChoosePremiumPeriod, state: FSMContext
):
    user = await update_user(c.from_user)
    lang = user["language"]
    months = callback_data.months
    await state.set_state(Premium.receiver)
    await state.update_data(months=months)
    price = await get_premium_price(months=months)

    user_subscription = user["subscription"]
    user_commission_rate = get_user_stars_commission_rate(user_subscription)

    ton_price = round(price["ton"] * user_commission_rate, 4)
    usdt_price = round(price["usdt"] * user_commission_rate, 4)

    await c.message.edit_text(
        text=texts[lang]["messages"]["premium_purchase_confirmation"].format(
            months=months, ton_price=ton_price, usdt_price=usdt_price
        ),
        reply_markup=get_cancel_premium_keyboard(lang=lang),
        link_preview_options=LinkPreviewOptions(
            show_above_text=True,
            url=f"https://imggen.send.tg/checks/image?asset=PREMIUM&months={months}&main=menu&v1",
        ),
    )
    await c.answer()


@router.message(Premium.receiver)
async def handle_premium_receiver(message: Message, state: FSMContext):
    user = await update_user(message.from_user)
    lang = user["language"]
    receiver = message.text.strip()

    if not receiver or not is_valid_username(receiver):
        await message.answer(
            text=texts[lang]["messages"]["invalid_username_error"],
            reply_markup=get_cancel_premium_keyboard(lang=lang),
            link_preview_options=LinkPreviewOptions(
                show_above_text=True,
                url=get_image_url(lang, "error"),
            ),
        )
        return

    receiver = receiver.replace("@", "")

    data = await state.get_data()
    price = await get_premium_price(months=data["months"], username=receiver)

    if not price:
        await message.answer(
            texts[lang]["messages"]["receiver_premium_not_found"].format(
                receiver=receiver
            ),
            reply_markup=get_cancel_premium_keyboard(lang=lang),
        )
        return

    await state.update_data(receiver=receiver)

    user_subscription = user["subscription"]
    user_commission_rate = get_user_stars_commission_rate(user_subscription)

    ton_price = round(price["ton"] * user_commission_rate, 4)
    usdt_price = round(price["usdt"] * user_commission_rate, 4)

    await message.answer(
        text=texts[lang]["messages"]["premium_confirmation"].format(
            ton_price=ton_price,
            usdt_price=usdt_price,
            receiver=receiver,
            months=data["months"],
        ),
        reply_markup=get_generate_premium_invoice_keyboard(
            lang=lang, months=data["months"], receiver=receiver
        ),
        link_preview_options=LinkPreviewOptions(
            show_above_text=True,
            url=f"https://imggen.send.tg/checks/image?asset=PREMIUM&months={data['months']}&main=menu&v1",
        ),
    )


@router.callback_query(F.data == "referral_program")
async def open_referral_program(c: CallbackQuery):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()
    referrals_count = await get_referrals_count(c.from_user.id)
    await c.message.edit_text(
        "Реф ссылка:\n"
        f"<code>t.me/GIFTSZONEBOT?start={c.from_user.id}</code>\n"
        f"кол-во: {referrals_count}\n"
        f"баланс: {user['ref_balance']}"
    )
