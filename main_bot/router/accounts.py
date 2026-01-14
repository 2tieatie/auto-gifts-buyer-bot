from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, LinkPreviewOptions
from pyrogram.errors import (
    FloodWait,
    RPCError,
    SessionPasswordNeeded,
    PhoneCodeInvalid,
    PhoneCodeExpired,
)

from config import router, PHONE_RE
from db.accounts import (
    get_account_by_phone,
    save_account,
    get_user_accounts,
    delete_account,
)
from db.users import update_user
from base.fsm_states import AddAccount, StarsLimit
from utils.account import with_client, _get_me, get_account_codes
from utils.get_stars_premium_price import get_stars_price
from utils.image_config import get_image_url
from utils.keyboards import (
    get_add_account_keyboard,
    get_return_to_main_menu_keyboard,
    AccountsPage,
    get_user_accounts_kb,
    Account,
    DeleteAccount,
    get_account_menu_keyboard,
    AccountCodes,
    ChooseStarsLimit,
    get_cancel_stars_limit_keyboard,
    get_create_autobuy_invoice,
    get_delete_account_confirmation_kb,
)
from utils.texts import texts

from db.accounts import change_gifts_receiver
from base.fsm_states import ChangeGiftsReceiverState
from utils.account import _ago, log_out
from utils.keyboards import ChangeGiftsReceiver
from utils.utils import is_valid_username

from utils.keyboards import PhoneCode

from utils.utils import inject_code_into_text

from base.enums import AccountSource


async def __cleanup_success(state: FSMContext):
    data = await state.get_data()
    d = data["session"]
    if d and d.get("client"):
        try:
            await d["client"].disconnect()
        except Exception:
            pass
    await state.clear()


@router.callback_query(F.data == "add_own_account")
async def add_account(c: CallbackQuery, state: FSMContext):
    user = await update_user(c.from_user)
    lang = user["language"]
    await state.set_state(AddAccount.phone)
    await c.message.edit_text(
        texts[lang]["messages"]["enter_phone"],
        reply_markup=get_add_account_keyboard(lang=lang),
    )
    await c.answer()
    await state.set_state(AddAccount.phone)


@router.message(AddAccount.phone)
async def handle_phone(m: Message, state: FSMContext):
    phone = m.text.strip()
    user = await update_user(m.from_user)
    lang = user["language"]
    if not PHONE_RE.match(phone):
        await m.answer(
            texts[lang]["messages"]["invalid_phone_format"],
            reply_markup=get_add_account_keyboard(lang=lang),
        )
        return
    exists = await get_account_by_phone(phone)
    if exists:
        await state.clear()
        await m.answer(
            texts[lang]["messages"]["account_exists"],
            reply_markup=get_add_account_keyboard(lang=lang),
        )
        return
    try:
        client = with_client()
        await client.connect()
        sent = await client.send_code(phone)
        await state.update_data(
            session={
                "phone": phone,
                "client": client,
                "hash": sent.phone_code_hash,
            }
        )
        await state.set_state(AddAccount.code)
        await m.answer(
            texts[lang]["messages"]["enter_code"],
            reply_markup=get_add_account_keyboard(
                lang=lang, resend_code=True, phone_code=""
            ),
        )
    except FloodWait as e:
        await m.answer(
            texts[lang]["messages"]["too_many_requests"].format(seconds=e.value)
        )
    except RPCError as e:
        await m.answer(f"{texts[lang]['messages']['error']}: {e.MESSAGE or str(e)}")
    except Exception as e:
        await m.answer(f"{texts[lang]['messages']['error']}: {str(e)}")


@router.callback_query(F.data == "terminate_add_account")
async def cancel_any(c: CallbackQuery, state: FSMContext):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()
    data = await state.get_data()
    d = data.get("session", {})

    if d and d.get("client"):
        try:
            await d["client"].disconnect()
        except Exception:
            pass

    await state.clear()
    await c.message.edit_text(
        texts[lang]["messages"]["operation_cancelled"],
        reply_markup=get_return_to_main_menu_keyboard(lang=lang),
    )


@router.callback_query(F.data == "resend_code")
async def resend_code(c: CallbackQuery, state: FSMContext):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()
    data = await state.get_data()
    phone = data["session"]["phone"]
    d = data.get("session", {})

    if d and d.get("client"):
        try:
            await d["client"].disconnect()
        except Exception:
            pass
    await state.clear()
    try:
        client = with_client()
        await client.connect()
        sent = await client.send_code(phone)
        await state.update_data(
            session={
                "phone": phone,
                "client": client,
                "hash": sent.phone_code_hash,
            }
        )
        await state.set_state(AddAccount.code)
        await c.answer(texts[lang]["messages"]["code_resent"])
    except FloodWait as e:
        await c.message.answer(
            texts[lang]["messages"]["too_many_requests"].format(seconds=e.value)
        )
    except RPCError as e:
        await c.message.answer(
            f"{texts[lang]['messages']['error']}: {e.MESSAGE or str(e)}"
        )
    except Exception as e:
        await c.message.answer(f"{texts[lang]['messages']['error']}: {str(e)}")


@router.callback_query(PhoneCode.filter())
async def handle_code(c: CallbackQuery, callback_data: PhoneCode, state: FSMContext):
    user = await update_user(c.from_user)
    lang = user["language"]
    data = await state.get_data()
    d = data["session"]
    code = callback_data.code
    print(code)
    await c.answer()
    if not d:
        await state.clear()
        await c.message.answer(
            texts[lang]["messages"]["session_not_found"],
            reply_markup=get_add_account_keyboard(lang=lang),
        )
        return

    if code.endswith("+"):
        try:
            await d["client"].sign_in(d["phone"], d["hash"], code)
            me = await _get_me(d["client"])
            await d["client"].disconnect()
            await save_account(me, d["phone"], password=None, owner=user["user_id"])
            await __cleanup_success(state)
            await c.message.edit_text(
                texts[lang]["messages"]["account_added"],
                reply_markup=get_return_to_main_menu_keyboard(lang=lang),
            )
        except SessionPasswordNeeded:
            await state.set_state(AddAccount.password)
            await c.message.edit_text(
                texts[lang]["messages"]["enter_two_factor_password"],
                reply_markup=get_add_account_keyboard(lang=lang),
            )
        except PhoneCodeInvalid:
            await c.message.answer(texts[lang]["messages"]["invalid_code"])
        except PhoneCodeExpired:
            await c.message.answer(texts[lang]["messages"]["code_expired"])
        except FloodWait as e:
            await c.message.answer(
                texts[lang]["messages"]["too_many_requests"].format(seconds=e.value)
            )
        except RPCError as e:
            await c.message.answer(
                f"{texts[lang]['messages']['error']}: {e.MESSAGE or str(e)}"
            )
        except Exception as e:
            await c.message.answer(f"{texts[lang]['messages']['error']}: {str(e)}")
    else:
        try:
            new_text = inject_code_into_text(c.message.text, lang, code)
            await c.message.edit_text(
                new_text,
                reply_markup=get_add_account_keyboard(
                    lang=lang, resend_code=True, phone_code=code
                ),
            )
        except TelegramBadRequest:
            pass


@router.message(AddAccount.password)
async def handle_password(m: Message, state: FSMContext):
    user = await update_user(m.from_user)
    lang = user["language"]
    data = await state.get_data()
    d = data["session"]
    if not d:
        await state.clear()
        await m.answer(
            texts[lang]["messages"]["session_not_found"],
            reply_markup=get_add_account_keyboard(lang=lang),
        )
        return
    password = m.text or ""
    print(password)
    try:
        await d["client"].check_password(password)
        me = await _get_me(d["client"])
        await d["client"].disconnect()
        await save_account(me, d["phone"], password=password, owner=user["user_id"])
        await __cleanup_success(state)
        await m.answer(
            texts[lang]["messages"]["account_added"],
            reply_markup=get_return_to_main_menu_keyboard(lang=lang),
        )
    except RPCError as e:
        msg = (e.MESSAGE or str(e)).upper()
        if "PASSWORD_HASH_INVALID" in msg or "PASSWORD_HASH_INVALID" in getattr(
            e, "x", ""
        ):
            await m.answer(texts[lang]["messages"]["invalid_password"])
        else:
            await m.answer(f"{texts[lang]['messages']['error']}: {e.MESSAGE or str(e)}")
    except Exception as e:
        await m.answer(f"{texts[lang]['messages']['error']}: {str(e)}")


@router.callback_query(AccountsPage.filter())
async def accounts_menu_callback_query(c: CallbackQuery, callback_data: AccountsPage):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()
    user_accounts = await get_user_accounts(
        user_id=c.from_user.id, page=callback_data.page + 1
    )
    await c.message.edit_text(
        texts[lang]["messages"]["accounts"],
        link_preview_options=LinkPreviewOptions(
            is_disabled=True,
        ),
        reply_markup=get_user_accounts_kb(
            lang=lang,
            page=callback_data.page,
            pages_total=user_accounts["pages"],
            accounts=user_accounts["items"],
        ),
    )


@router.callback_query(Account.filter())
async def account_menu_callback_query(
    c: CallbackQuery, callback_data: AccountsPage, state: FSMContext
):

    await state.clear()
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()

    account = await get_account_by_phone(callback_data.phone)
    can_delete = True if account["type"] == AccountSource.MANUAL else False
    await c.message.edit_text(
        f"{texts[lang]['messages']['account']}\n\n"
        f"{texts[lang]['messages']['username']}: @{account['username'] or texts[lang]['messages']['not_specified']}\n"
        f"{texts[lang]['messages']['phone']}: <code>{account['phone']}</code>\n"
        f"{texts[lang]['messages']['premium']}: {'✅' if account['is_premium'] else '❌'}\n"
        f"{texts[lang]['messages']['password']}: <code>{account['password']}</code>\n"
        f"{texts[lang]['messages']['stars_balance']}: {account['stars_balance']:,}\n"
        f"{texts[lang]['messages']['stars_limit']}: {account['stars_limit']:,}\n"
        f"{texts[lang]['messages']['autobuy_enabled']}: {'on ✅' if account['autobuy_enabled'] else 'off ❌'}\n"
        f"{texts[lang]['messages']['gifts_receiver']}: @{account['gifts_receiver']}\n"
        f"{texts[lang]['messages']['updated_at']}: {_ago(account['updated_at'], lang)}\n",
        reply_markup=get_account_menu_keyboard(
            lang=lang,
            account=account,
            prev=callback_data.prev,
            can_delete=can_delete,
        ),
    )


@router.callback_query(DeleteAccount.filter())
async def delete_account_confirmation(c: CallbackQuery, callback_data: DeleteAccount):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()
    account = await get_account_by_phone(callback_data.phone)
    if callback_data.confirmed:
        await log_out(account["session_string"])
        await delete_account(callback_data.phone)
        user_accounts = await get_user_accounts(user_id=c.from_user.id, page=0)
        await c.message.edit_text(
            texts[lang]["messages"]["accounts"],
            link_preview_options=LinkPreviewOptions(
                is_disabled=True,
            ),
            reply_markup=get_user_accounts_kb(
                lang=lang,
                page=0,
                pages_total=user_accounts["pages"],
                accounts=user_accounts["items"],
            ),
        )
        return

    if callback_data.confirmation:
        await c.message.edit_text(
            text=texts[lang]["messages"]["delete_account_confirmation"].format(
                phone=callback_data.phone, stars_limit=account["stars_limit"]
            ),
            reply_markup=get_delete_account_confirmation_kb(lang=lang, account=account),
        )
        return


@router.callback_query(AccountCodes.filter())
async def account_codes_menu_callback_query(
    c: CallbackQuery, callback_data: AccountCodes
):
    user = await update_user(c.from_user)
    lang = user["language"]
    await c.answer()
    account = await get_account_by_phone(callback_data.phone)
    codes = await get_account_codes(account["session_string"], lang=lang)
    await c.message.answer(
        text=codes,
    )


@router.callback_query(ChooseStarsLimit.filter())
async def choose_stars_limit(
    c: CallbackQuery, callback_data: ChooseStarsLimit, state: FSMContext
):
    user = await update_user(c.from_user)
    lang = user["language"]
    await state.set_state(StarsLimit.amount)
    await state.update_data(phone=callback_data.phone)
    await c.answer()
    account = await get_account_by_phone(callback_data.phone)
    await c.message.edit_text(
        texts[lang]["messages"]["enter_stars_limit"].format(
            phone=callback_data.phone,
            username=account["username"],
            stars_balance=account["stars_balance"],
        ),
        reply_markup=get_cancel_stars_limit_keyboard(
            lang=lang,
            phone=callback_data.phone,
        ),
    )


@router.message(StarsLimit.amount)
async def _choose_stars_limit(message: Message, state: FSMContext):
    user = await update_user(message.from_user)
    lang = user["language"]
    phone = (await state.get_data())["phone"]
    account = await get_account_by_phone(phone)
    try:
        amount = int(message.text)
    except ValueError:
        await message.answer(
            text=texts[lang]["messages"]["invalid_input_error"],
            reply_markup=get_cancel_stars_limit_keyboard(lang=lang, phone=phone),
            link_preview_options=LinkPreviewOptions(
                show_above_text=True,
                url=get_image_url(lang, "error"),
            ),
        )
        return

    if amount < 50:
        await message.answer(
            text=texts[lang]["messages"]["invalid_amount_error"],
            reply_markup=get_cancel_stars_limit_keyboard(lang=lang, phone=phone),
            link_preview_options=LinkPreviewOptions(
                show_above_text=True,
                url=get_image_url(lang, "error"),
            ),
        )
        return
    price = await get_stars_price(amount=amount)
    ton_price = round(price["ton"] * user["commission_rate"] - price["ton"], 4)
    usdt_price = round(price["usdt"] * user["commission_rate"] - price["usdt"], 4)

    await message.answer(
        text=texts[lang]["messages"]["autobuy_confirmation"].format(
            amount=amount,
            phone=phone,
            ton_price=ton_price,
            usdt_price=usdt_price,
            username=account["username"],
            stars_balance=account["stars_balance"],
            stars_limit=amount,
        ),
        reply_markup=get_create_autobuy_invoice(lang=lang, phone=phone, amount=amount),
    )

    await state.clear()


@router.callback_query(ChangeGiftsReceiver.filter())
async def handle_change_gifts_receiver(
    c: CallbackQuery, callback_data: ChangeGiftsReceiver, state: FSMContext
):
    user = await update_user(c.from_user)
    lang = user["language"]

    await c.message.edit_text(
        text=texts[lang]["messages"]["account_change_receiver"],
        reply_markup=get_return_to_main_menu_keyboard(lang=lang),
    )
    await state.update_data(phone=callback_data.phone)
    await state.set_state(ChangeGiftsReceiverState.username)
    await c.answer()


@router.message(ChangeGiftsReceiverState.username)
async def handle_change_gifts_receiver_username(message: Message, state: FSMContext):
    user = await update_user(message.from_user)
    lang = user["language"]
    receiver = message.text.strip()

    if not receiver or not is_valid_username(receiver):
        await message.answer(
            text=texts[lang]["messages"]["invalid_username_error"],
            reply_markup=get_return_to_main_menu_keyboard(lang=lang),
            link_preview_options=LinkPreviewOptions(
                show_above_text=True,
                url=get_image_url(lang, "error"),
            ),
        )
        return

    receiver = receiver.replace("@", "")

    data = await state.get_data()
    result = await change_gifts_receiver(data["phone"], receiver)
    account = await get_account_by_phone(data["phone"])
    sender_username = account.get("username")

    await message.answer(
        text=texts[lang]["messages"]["account_change_receiver_success"].format(
            phone=data["phone"],
            receiver=receiver,
            sender=sender_username,
        ),
        reply_markup=get_return_to_main_menu_keyboard(lang=lang),
    )
    await state.clear()
