from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from motor.motor_asyncio import AsyncIOMotorCollection

from keyboards import MAIN_KB, build_pagination_kb
from db import get_db, fetch_page
from utils import format_accounts_block, format_account_summary, is_admin

router = Router()


@router.message(Command("start"))
async def start(m: Message, state: FSMContext):
    # Verify admin access
    if not is_admin(m.from_user.id):
        await m.answer("⛔ Доступ запрещен")
        return

    await state.clear()
    await m.answer(
        "Менеджер аккаунтов Telegram\n\nВыберите действие:",
        reply_markup=MAIN_KB,
    )


@router.message(Command("accs"))
async def retrieve_accounts(m: Message):
    if not is_admin(m.from_user.id):
        await m.answer("⛔ Доступ запрещен")
        return

    db = await get_db()
    accs: AsyncIOMotorCollection = db.accounts

    docs, total, page, pages_total = await fetch_page(accs, page=0)
    text = format_accounts_block(docs, total, page, "compact")
    kb = build_pagination_kb(page, pages_total, "compact")

    await m.answer(
        text, reply_markup=kb, disable_web_page_preview=True, parse_mode="html"
    )


@router.message(Command("stats"))
async def show_statistics(m: Message):
    if not is_admin(m.from_user.id):
        await m.answer("⛔ Доступ запрещен")
        return

    db = await get_db()
    accs: AsyncIOMotorCollection = db.accounts

    # Get all accounts for statistics
    all_accounts = await accs.find({}).to_list(length=None)
    text = format_account_summary(all_accounts)

    await m.answer(text, reply_markup=MAIN_KB, parse_mode="html")
