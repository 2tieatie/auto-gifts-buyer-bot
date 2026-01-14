from aiogram.filters import Command
from aiogram.types import Message, LinkPreviewOptions

from config import router
from db.users import update_user, get_user, update_user_language, set_referrer
from utils.image_config import get_image_url
from utils.keyboards import get_main_keyboard
from utils.texts import texts

@router.message(Command("start"))
async def handle_start(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        user = await update_user_language(
            message.from_user, message.from_user.language_code
        )

        referrer_user_id = message.text.replace("/start", "").strip()
        try:
            referrer_user_id = int(referrer_user_id)
            if referrer_user_id != message.from_user.id:
                referrer = await get_user(referrer_user_id)
                if referrer:
                    await set_referrer(message.from_user.id, referrer_user_id)
        except ValueError:
            pass

    lang = user["language"]

    await message.answer(
        texts[lang]["messages"]["welcome"],
        parse_mode="HTML",
        reply_markup=get_main_keyboard(lang),
        link_preview_options=LinkPreviewOptions(
            is_disabled=True,
        ),
    )


@router.message(Command("main"))
async def handle_main(message: Message):
    user = await update_user(message.from_user)
    lang = user["language"]

    await message.answer(
        text=texts[lang]["messages"]["main_menu"],
        reply_markup=get_main_keyboard(lang=lang),
        link_preview_options=LinkPreviewOptions(
            show_above_text=True,
            url=get_image_url(lang, "main_menu"),
        ),
    )
