from enum import Enum


class ValueEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class SubscriptionType(ValueEnum):
    BASIC = "subscription_basic"
    STANDARD = "subscription_standard"
    PREMIUM = "subscription_premium"


class InvoiceType(ValueEnum):
    STARS = "stars"
    PREMIUM = "premium"
    ACCOUNT = "account"
    AUTOBUY = "autobuy"
    SUBSCRIPTION_BASIC = SubscriptionType.BASIC
    SUBSCRIPTION_STANDARD = SubscriptionType.STANDARD
    SUBSCRIPTION_PREMIUM = SubscriptionType.PREMIUM


class InvoiceStatus(ValueEnum):
    PENDING = "pending"
    CANCELED = "canceled"
    PAID = "paid"
    EXPIRED = "expired"


class AccountSource(ValueEnum):
    SHOP = "shop"
    MANUAL = "manual"
