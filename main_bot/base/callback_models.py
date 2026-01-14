from aiogram.filters.callback_data import CallbackData


class ChooseStarsAmount(CallbackData, prefix="choose_stars_amount"):
    amount: int


class ChoosePremiumPeriod(CallbackData, prefix="choose_premium_period"):
    months: int


class ChooseStarsLimit(CallbackData, prefix="choose_stars_limit"):
    phone: str


class StarsInvoice(CallbackData, prefix="stars_invoice"):
    amount: int
    receiver: str


class PremiumInvoice(CallbackData, prefix="premium_invoice"):
    months: int
    receiver: str


class StarsLimitInvoice(CallbackData, prefix="stars_limit_invoice"):
    phone: str
    stars: int


class CancelInvoice(CallbackData, prefix="cancel_invoice"):
    invoice_id: str


class Invoice(CallbackData, prefix="invoice", sep="-"):
    invoice_id: str
    prev: str


class InvoicesPage(CallbackData, prefix="invoices_page"):
    page: int
    show_expired: bool = True


class AccountsPage(CallbackData, prefix="accounts_page"):
    page: int


class Account(CallbackData, prefix="account", sep="-"):
    phone: str
    prev: str


class AccountCodes(CallbackData, prefix="account_codes"):
    phone: str


class ChangeGiftsReceiver(CallbackData, prefix="change_gifts_receiver"):
    phone: str


class PhoneCode(CallbackData, prefix="phone_code_number"):
    code: str


class DeleteAccount(CallbackData, prefix="delete_account"):
    phone: str
    confirmation: bool
    confirmed: bool


class SubscriptionMenu(CallbackData, prefix="subscription_menu"):
    type: str


class SubscriptionInvoice(CallbackData, prefix="subscription_invoice"):
    type: str
