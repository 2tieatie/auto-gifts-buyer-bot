import os
import re

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from motor.motor_asyncio import AsyncIOMotorClient

DEBUG = True

BASE_COMMISSION_RATE = 1.2
BASE_STARS_COMMISSION_RATE = 1.15
BASE_ACCOUNT_PRICE = 3

BASE_REF_BONUS = 0.3

BASIC_SUBSCRIPTION_STARS_COMMISSION_RATE = 1.1
STANDARD_SUBSCRIPTION_STARS_COMMISSION_RATE = 1.06
PREMIUM_SUBSCRIPTION_STARS_COMMISSION_RATE = 1.03

BASIC_SUBSCRIPTION_MAX_AUTOBUY_ACCOUNTS = 1
STANDARD_SUBSCRIPTION_MAX_AUTOBUY_ACCOUNTS = 3
PREMIUM_SUBSCRIPTION_MAX_AUTOBUY_ACCOUNTS = 7

BASIC_SUBSCRIPTION_MAX_RENT_ACCOUNTS = 1
STANDARD_SUBSCRIPTION_MAX_RENT_ACCOUNTS = 3
PREMIUM_SUBSCRIPTION_MAX_RENT_ACCOUNTS = 7

INVOICE_TTL_SECONDS = 15 * 60

if DEBUG:
    TON_RECEIVER_ADDRESS = "######"
    USDT_TON_RECEIVER_ADDRESS = "######"
else:
    TON_RECEIVER_ADDRESS = "######"
    USDT_TON_RECEIVER_ADDRESS = "######"


USDT_TON_MASTER_ADDRESS = "######"

if DEBUG:
    BOT_TOKEN = "######"  # DEVELOPMENT
else:
    BOT_TOKEN = "######"  # PRODUCTION


MONGO_URI = (
    "######"
)
if DEBUG:
    DB_NAME = "gifts-test"
else:
    DB_NAME = "gifts"

API_ID = int(os.getenv("TG_API_ID", "######"))
API_HASH = os.getenv("TG_API_HASH", "######")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

_cli = AsyncIOMotorClient(MONGO_URI, uuidRepresentation="standard")
db = _cli[DB_NAME]

router = Router()

PHONE_RE = re.compile(r"^\+\d{7,15}$")
