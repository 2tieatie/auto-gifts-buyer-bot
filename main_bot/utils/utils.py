import asyncio
import re
from typing import Any
from base.enums import SubscriptionType as SubscriptionTypeEnum
from config import (
    BASE_STARS_COMMISSION_RATE,
    PREMIUM_SUBSCRIPTION_STARS_COMMISSION_RATE,
    STANDARD_SUBSCRIPTION_STARS_COMMISSION_RATE,
    BASIC_SUBSCRIPTION_STARS_COMMISSION_RATE,
)
from utils.get_stars_premium_price import get_premium_price


async def get_profile_text(user: dict[str, Any]) -> str:
    stars_bought = 0

    if user["language"] == "ru":
        return f"""
<b>Профиль пользователя</b>

👤 Имя: {('@' + user['username']) if user['username'] else user['first_name']}
🆔 ID: <code>{user['user_id']}</code>
📅 Зарегистрирован: <b>{user['created_at'].strftime('%d.%m.%Y')}</b>
"""

    return f"""
<b>User Profile</b>

👤 Name: {('@' + user['username']) if user['username'] else user['first_name']}
🆔 ID: <code>{user['user_id']}</code>
📅 Registered: <b>{user['created_at'].strftime('%d.%m.%Y')}</b>
"""


async def get_premium_price_text(user: dict[str, Any]) -> str:
    months = (3, 6, 12)
    m_prices = await asyncio.gather(*(get_premium_price(m) for m in months))

    user_subscription = user["subscription"]
    commission = get_user_stars_commission_rate(user_subscription)

    def fmt(p: dict) -> str:
        ton = round(p["ton"] * commission, 2)
        usdt = round(p["usdt"] * commission, 2)
        return f"{ton} TON / ${usdt}"

    lang = user.get("language", "ru")
    title = (
        "💎 <b>Premium подписка</b>"
        if lang == "ru"
        else "💎 <b>Premium Subscription</b>"
    )

    if lang == "en":
        lines = [f"📅 {m} months ≈ {fmt(p)}" for m, p in zip(months, m_prices)]
    else:

        def ru_months(m: int) -> str:
            if m == 3:
                return "3 месяца"
            if m == 6:
                return "6 месяцев"
            return "12 месяцев"

        lines = [f"📅 {ru_months(m)} ≈ {fmt(p)}" for m, p in zip(months, m_prices)]

    return "\n".join([title, "", *lines, ""])


def is_valid_username(username: str) -> bool:
    username = username.replace("@", "")
    pattern = r"^[a-zA-Z][a-zA-Z0-9_]{3,31}$"
    if not re.match(pattern, username):
        return False
    if username.endswith("_"):
        return False
    return True


def _render_code_progress(code: str, total: int = 5) -> str:
    # Показываем уже введённые символы и плейсхолдеры на оставшиеся позиции
    shown = list(code[:total])
    placeholders = ["·"] * max(total - len(shown), 0)  # можно заменить на "•" или "▫"
    return " ".join(shown + placeholders[: total - len(shown)])


def inject_code_into_text(original_text: str, lang: str, code: str) -> str:
    """
    Удаляет старую строку "🔢 ..." (если была) и добавляет актуальную.
    Не трогает остальной текст (с учётом того, что он уже локализован через texts[lang]).
    """
    # срежем предыдущую вставку, если пользователь нажал ещё одну цифру
    base = re.sub(r"\n{0,2}🔢.*$", "", original_text.strip())
    label = "Code"
    progress = _render_code_progress(code, total=5)
    return f"{base}\n\n🔢 {label}: {progress}"


def get_user_stars_commission_rate(subscription_type: str):
    if subscription_type == SubscriptionTypeEnum.BASIC:
        user_commission_rate = BASIC_SUBSCRIPTION_STARS_COMMISSION_RATE
    elif subscription_type == SubscriptionTypeEnum.STANDARD:
        user_commission_rate = STANDARD_SUBSCRIPTION_STARS_COMMISSION_RATE
    elif subscription_type == SubscriptionTypeEnum.PREMIUM:
        user_commission_rate = PREMIUM_SUBSCRIPTION_STARS_COMMISSION_RATE
    else:
        user_commission_rate = BASE_STARS_COMMISSION_RATE

    return user_commission_rate
