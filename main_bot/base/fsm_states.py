from aiogram.fsm.state import StatesGroup, State


class Stars(StatesGroup):
    amount = State()
    receiver = State()
    invoice = State()


class Premium(StatesGroup):
    receiver = State()
    invoice = State()


class AddAccount(StatesGroup):
    phone = State()
    code = State()
    password = State()


class StarsLimit(StatesGroup):
    amount = State()


class ChangeGiftsReceiverState(StatesGroup):
    username = State()
