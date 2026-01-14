import re
import time

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from motor.motor_asyncio import AsyncIOMotorCollection
from pyrogram.errors import (
    FloodWait,
    RPCError,
    SessionPasswordNeeded,
    PhoneCodeInvalid,
    PhoneCodeExpired,
)

from models import AccsPage, S
from db import get_db, fetch_page, save_account
from utils import format_accounts_block, ensure_dirs, format_account_summary, is_admin
from keyboards import build_pagination_kb, CANCEL_KB, MAIN_KB, CODE_KB
from config import SESS, PHONE_RE
from account import with_client, _get_me

from account import set_username, set_password

router = Router()


async def cleanup_success(m: Message, state: FSMContext):
    d = SESS.pop(m.from_user.id, None)
    if d and d.get("client"):
        try:
            await d["client"].disconnect()
        except Exception:
            pass
    await state.clear()
    await m.answer("Аккаунт добавлен", reply_markup=MAIN_KB)


@router.callback_query(AccsPage.filter())
async def paginate_accounts(cb: CallbackQuery, callback_data: AccsPage):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ Доступ запрещен", show_alert=True)
        return

    db = await get_db()
    accs: AsyncIOMotorCollection = db.accounts

    docs, total, page, pages_total = await fetch_page(accs, page=callback_data.page)
    text = format_accounts_block(docs, total, page, callback_data.view_mode)
    kb = build_pagination_kb(page, pages_total, callback_data.view_mode)

    try:
        await cb.message.edit_text(
            text, reply_markup=kb, disable_web_page_preview=True, parse_mode="html"
        )
    except Exception:
        await cb.message.answer(
            text, reply_markup=kb, disable_web_page_preview=True, parse_mode="html"
        )

    await cb.answer()


@router.message(F.text.casefold() == "✅ добавить аккаунт")
async def add_account(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        await m.answer("⛔ Доступ запрещен")
        return

    await state.set_state(S.phone)
    await m.answer(
        "Введите номер телефона в формате +XXXXXXXXXXX\n\nПример: +380931234567",
        reply_markup=CANCEL_KB,
    )


@router.message(F.text.casefold() == "📋 список аккаунтов")
async def list_accounts(m: Message):
    if not is_admin(m.from_user.id):
        await m.answer("⛔ Доступ запрещен")
        return

    try:
        db = await get_db()
        accs: AsyncIOMotorCollection = db.accounts

        docs, total, page, pages_total = await fetch_page(accs, page=0)
        text = format_accounts_block(docs, total, page, "compact")
        kb = build_pagination_kb(page, pages_total, "compact")

        await m.answer(
            text, reply_markup=kb, disable_web_page_preview=True, parse_mode="html"
        )
    except Exception as e:
        await m.answer(f"Ошибка при загрузке списка: {str(e)}", reply_markup=MAIN_KB)


@router.message(F.text.casefold() == "📊 статистика")
async def show_statistics(m: Message):
    if not is_admin(m.from_user.id):
        await m.answer("⛔ Доступ запрещен")
        return

    try:
        db = await get_db()
        accs: AsyncIOMotorCollection = db.accounts

        # Get all accounts for statistics
        all_accounts = await accs.find({}).to_list(length=None)
        text = format_account_summary(all_accounts)

        await m.answer(text, reply_markup=MAIN_KB, parse_mode="html")
    except Exception as e:
        await m.answer(
            f"Ошибка при загрузке статистики: {str(e)}", reply_markup=MAIN_KB
        )


@router.message(F.text.casefold() == "❌ отмена")
async def cancel_any(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        await m.answer("⛔ Доступ запрещен")
        return

    d = SESS.pop(m.from_user.id, None)
    if d and d.get("client"):
        try:
            await d["client"].disconnect()
        except Exception:
            pass
    await state.clear()
    await m.answer("Операция отменена", reply_markup=MAIN_KB)


@router.message(S.phone)
async def handle_phone(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        await m.answer("⛔ Доступ запрещен")
        return

    phone = m.text.strip()
    if not PHONE_RE.match(phone):
        await m.answer("Неверный формат номера. Пример: +380931234567")
        return
    db = await get_db()
    exists = await db.accounts.find_one({"phone": phone})
    if exists:
        await state.clear()
        await m.answer("Аккаунт уже существует", reply_markup=MAIN_KB)
        return
    try:
        await ensure_dirs()
        client = with_client()
        await client.connect()
        sent = await client.send_code(phone)
        SESS[m.from_user.id] = {
            "phone": phone,
            "client": client,
            "hash": sent.phone_code_hash,
        }
        await state.set_state(S.code)
        await m.answer(
            "Введите код из Telegram (5-6 цифр)",
            reply_markup=CODE_KB,
        )
    except FloodWait as e:
        await m.answer(f"Слишком много запросов. Подождите {e.value} сек")
    except RPCError as e:
        await m.answer(f"Ошибка: {e.MESSAGE or str(e)}")
    except Exception as e:
        await m.answer(f"Ошибка: {str(e)}")


@router.message(F.text.casefold() == "🔄 отправить код повторно", S.code)
async def resend_code(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        await m.answer("⛔ Доступ запрещен")
        return

    d = SESS.get(m.from_user.id)
    if not d:
        await state.clear()
        await m.answer("Сессия не найдена. Начни заново.", reply_markup=MAIN_KB)
        return
    try:
        sent = await d["client"].resend_code(d["phone"], d["hash"])
        d["hash"] = sent.phone_code_hash
        await m.answer("Код отправлен повторно")
    except FloodWait as e:
        await m.answer(f"Слишком много запросов. Подождите {e.value} сек")
    except RPCError as e:
        await m.answer(f"Ошибка: {e.MESSAGE or str(e)}")
    except Exception as e:
        await m.answer(f"Ошибка: {str(e)}")


@router.message(S.code)
async def handle_code(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        await m.answer("⛔ Доступ запрещен")
        return

    d = SESS.get(m.from_user.id)
    if not d:
        await state.clear()
        await m.answer("Сессия не найдена", reply_markup=MAIN_KB)
        return
    code = re.sub(r"\D", "", m.text or "")
    if not code:
        await m.answer("Введите числовой код")
        return
    try:
        await d["client"].sign_in(d["phone"], d["hash"], code)
        me = await _get_me(d["client"])
        if not me.username:
            me.username = f"u{me.id}"
            await set_username(d["client"], me.username)
        password = f"{int(time.time())}"
        await set_password(d["client"], password)
        await d["client"].disconnect()
        await save_account(
            me, d["phone"], password=password
        )  # убрал пароль чтоб не выдавало ошибку
        await cleanup_success(m, state)
    except SessionPasswordNeeded:
        await state.set_state(S.password)
        await m.answer(
            "Введите пароль двухфакторной аутентификации",
            reply_markup=CANCEL_KB,
        )
    except PhoneCodeInvalid:
        await m.answer("Неверный код")
    except PhoneCodeExpired:
        await m.answer("Код истёк")
    except FloodWait as e:
        await m.answer(f"Слишком много запросов. Подождите {e.value} сек")
    except RPCError as e:
        await m.answer(f"Ошибка: {e.MESSAGE or str(e)}")
    except Exception as e:
        await m.answer(f"Ошибка: {str(e)}")


@router.message(S.password)
async def handle_password(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        await m.answer("⛔ Доступ запрещен")
        return

    d = SESS.get(m.from_user.id)
    if not d:
        await state.clear()
        await m.answer("Сессия не найдена", reply_markup=MAIN_KB)
        return
    password = m.text or ""
    try:
        await d["client"].check_password(password)
        me = await _get_me(d["client"])
        if not me.username:
            me.username = f"u{me.id}"
            await set_username(me, me.username)
        await d["client"].disconnect()
        await save_account(me, d["phone"], password=password)
        await cleanup_success(m, state)
    except RPCError as e:
        msg = (e.MESSAGE or str(e)).upper()
        if "PASSWORD_HASH_INVALID" in msg or "PASSWORD_HASH_INVALID" in getattr(
            e, "x", ""
        ):
            await m.answer("Неверный пароль")
        else:
            await m.answer(f"Ошибка: {e.MESSAGE or str(e)}")
    except Exception as e:
        await m.answer(f"Ошибка: {str(e)}")
