import os
import re
from datetime import datetime
from typing import Optional

from config import SESS_DIR, TZ, PAGE_SIZE, ADMIN_IDS


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def ensure_dirs():
    os.makedirs(SESS_DIR, exist_ok=True)


def fmt_dt(dt: datetime | None) -> str:
    if not dt:
        return "—"
    try:
        return dt.astimezone(TZ).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return dt.isoformat(sep=" ", timespec="seconds")


def format_accounts_block(
    accounts: list[dict], total: int, page: int, view_mode: str = "compact"
) -> str:
    if not accounts:
        return "📭 Аккаунты не найдены"

    start = page * PAGE_SIZE + 1

    # Header with statistics
    premium_count = sum(1 for a in accounts if a.get("is_premium"))
    total_stars = sum(a.get("stars_balance", 0) for a in accounts)

    header = f"""📊 <b>Аккаунты ({total})</b>
📱 Страница {page + 1} • {len(accounts)} показано
💎 Premium: {premium_count} • ⭐ Всего звезд: {total_stars}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    if view_mode == "compact":
        return _format_compact_view(accounts, start, header)
    else:
        return _format_detailed_view(accounts, start, header)


def _format_compact_view(accounts: list[dict], start: int, header: str) -> str:
    lines = [header]

    for i, a in enumerate(accounts, start=start):
        phone = a.get("phone", "")
        fn = a.get("first_name") or ""
        ln = a.get("last_name") or ""
        uname = a.get("username")
        premium = "💎" if a.get("is_premium") else "📱"
        stars = a.get("stars_balance", 0)
        updated = a.get("updated_at")

        # Status indicator based on last update
        status = _get_status_indicator(updated)

        # Compact line format
        name = f"{fn} {ln}".strip() or "Без имени"
        uname_display = f" @{uname}" if uname else ""
        stars_display = f" ⭐{stars}" if stars > 0 else ""

        lines.append(
            f"{status} <b>{i}.</b> {phone} • {name}{uname_display} {premium}{stars_display}"
        )

    return "\n".join(lines)


def _format_detailed_view(accounts: list[dict], start: int, header: str) -> str:
    lines = [header]

    for i, a in enumerate(accounts, start=start):
        phone = a.get("phone", "")
        fn = a.get("first_name") or ""
        ln = a.get("last_name") or ""
        uname = a.get("username")
        user_id = a.get("user_id")
        premium = a.get("is_premium", False)
        stars = a.get("stars_balance", 0)
        updated = a.get("updated_at")
        created = a.get("created_at")

        status = _get_status_indicator(updated)
        status_text = _get_status_text(updated)

        lines.append(
            f"""
{status} <b>{i}. {phone}</b>
<blockquote expandable>
🆔 <code>{user_id}</code>
👤 {fn} {ln}
{'🔗 @' + uname if uname else '🔗 Без username'}
{'💎 Premium аккаунт' if premium else '📱 Обычный аккаунт'}
⭐ Баланс звезд: {stars}
📅 Создан: {fmt_dt(created)}
🔄 Обновлен: {fmt_dt(updated)}
📊 Статус: {status_text}
</blockquote>"""
        )

    return "\n".join(lines)


def _get_status_indicator(updated_at) -> str:
    if not updated_at:
        return "❓"

    from datetime import datetime, UTC

    now = datetime.now(UTC)

    if isinstance(updated_at, str):
        try:
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        except:
            return "❓"

    # Ensure both datetimes are timezone-aware
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)

    diff = now - updated_at

    if diff.days > 7:
        return "🔴"  # Very old
    elif diff.days > 1:
        return "🟡"  # Old
    elif diff.total_seconds() > 6 * 3600:  # 6 hours in seconds
        return "🟠"  # Recent
    else:
        return "🟢"  # Fresh


def _get_status_text(updated_at) -> str:
    if not updated_at:
        return "Неизвестно"

    from datetime import datetime, UTC

    now = datetime.now(UTC)

    if isinstance(updated_at, str):
        try:
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        except:
            return "Неизвестно"

    # Ensure both datetimes are timezone-aware
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)

    diff = now - updated_at

    if diff.days > 7:
        return f"Неактивен {diff.days} дн."
    elif diff.days > 1:
        return f"Неактивен {diff.days} дн."
    elif diff.days == 1:
        return "Вчера"
    elif diff.total_seconds() > 6 * 3600:  # 6 hours in seconds
        hours = int(diff.total_seconds() // 3600)
        return f"{hours} ч. назад"
    else:
        return "Сегодня"


def format_account_summary(accounts: list[dict]) -> str:
    if not accounts:
        return "📭 Нет аккаунтов для анализа"

    total = len(accounts)
    premium = sum(1 for a in accounts if a.get("is_premium"))
    with_username = sum(1 for a in accounts if a.get("username"))
    total_stars = sum(a.get("stars_balance", 0) for a in accounts)

    # Status breakdown
    from datetime import UTC

    now = datetime.now(UTC)
    fresh = sum(1 for a in accounts if _is_recent(a.get("updated_at"), now, hours=6))
    recent = sum(1 for a in accounts if _is_recent(a.get("updated_at"), now, days=1))
    old = sum(1 for a in accounts if _is_recent(a.get("updated_at"), now, days=7))
    very_old = total - fresh - recent - old

    return f"""📊 <b>Статистика аккаунтов</b>

📱 Всего: {total}
💎 Premium: {premium} ({premium/total*100:.1f}%)
🔗 С username: {with_username} ({with_username/total*100:.1f}%)
⭐ Всего звезд: {total_stars}

📅 Активность:
🟢 Свежие (6ч): {fresh}
🟠 Недавние (1д): {recent}
🟡 Старые (7д): {old}
🔴 Очень старые: {very_old}"""


def _is_recent(updated_at, now, hours=None, days=None):
    if not updated_at:
        return False

    if isinstance(updated_at, str):
        try:
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        except:
            return False

    # Ensure both datetimes are timezone-aware
    if updated_at.tzinfo is None:
        from datetime import UTC

        updated_at = updated_at.replace(tzinfo=UTC)

    diff = now - updated_at

    if hours:
        return diff.total_seconds() < hours * 3600
    elif days:
        return diff.days < days
    return False


def _extract_verification_code(text: str) -> Optional[str]:
    column_index = text.find(":")
    original_text = text
    text = text[column_index + 1 :]

    if "my.telegram.org" in original_text:
        match = re.search(r"[a-zA-Z0-9_-]{9,}", text)
        if match:
            code = match.group()
            return code
        text = text.strip()
        new_line_index = text.find("\n")
        text = text[:new_line_index]
        return text.strip()

    elif "❗️" in text:
        text = text.strip()
        dot_index = text.find(".")
        text = text[:dot_index]
        return text.strip()

    return None
