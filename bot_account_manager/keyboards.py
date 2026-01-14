from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from models import AccsPage


def kb(*rows):
    keyboard = []
    for row in rows:
        if isinstance(row, list):
            keyboard.append([KeyboardButton(text=b) for b in row])
        else:
            keyboard.append([KeyboardButton(text=row)])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )


MAIN_KB = kb(["✅ Добавить аккаунт", "📋 Список аккаунтов"], ["📊 Статистика"])
CANCEL_KB = kb(["❌ Отмена"])
CODE_KB = kb(["🔄 Отправить код повторно", "❌ Отмена"])


def build_pagination_kb(
    page: int, pages_total: int, view_mode: str = "compact"
) -> InlineKeyboardMarkup:
    prev_page = max(0, page - 1)
    next_page = min(pages_total - 1, page + 1)

    # Navigation buttons
    prev_btn = InlineKeyboardButton(
        text="◀",
        callback_data=AccsPage(page=prev_page, view_mode=view_mode).pack(),
    )
    cur_btn = InlineKeyboardButton(
        text=f"{page + 1}/{pages_total}",
        callback_data=AccsPage(page=page, view_mode=view_mode).pack(),
    )
    next_btn = InlineKeyboardButton(
        text="▶",
        callback_data=AccsPage(page=next_page, view_mode=view_mode).pack(),
    )

    # View mode toggle
    view_btn = InlineKeyboardButton(
        text="👁" if view_mode == "compact" else "🔍",
        callback_data=AccsPage(
            page=page, view_mode="detailed" if view_mode == "compact" else "compact"
        ).pack(),
    )

    # Disable navigation buttons when at limits
    if page == 0:
        prev_btn = InlineKeyboardButton(
            text=" ", callback_data=AccsPage(page=page, view_mode=view_mode).pack()
        )
    if page >= pages_total - 1:
        next_btn = InlineKeyboardButton(
            text=" ", callback_data=AccsPage(page=page, view_mode=view_mode).pack()
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[[prev_btn, cur_btn, next_btn], [view_btn]]
    )
