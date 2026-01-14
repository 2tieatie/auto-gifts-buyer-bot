from pydantic import BaseModel


class BaseInvoiceResult(BaseModel): ...


class StarsInvoiceResult(BaseInvoiceResult):
    stars: int
    receiver: str


class PremiumInvoiceResult(BaseInvoiceResult):
    months: int
    receiver: str


class AccountInvoiceResult(BaseInvoiceResult):
    amount: int


class AutoBuyInvoiceResult(BaseInvoiceResult):
    stars: int
    phone: str


class SubscriptionInvoiceResult(BaseInvoiceResult):
    type: str
