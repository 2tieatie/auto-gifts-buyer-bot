from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import StatesGroup, State


class S(StatesGroup):
    phone = State()
    code = State()
    password = State()


class AccsPage(CallbackData, prefix="accs"):
    page: int
    view_mode: str = "compact"
