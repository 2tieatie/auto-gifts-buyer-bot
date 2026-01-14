import logging
import os
import re
from zoneinfo import ZoneInfo

from aiogram import Router, Dispatcher

logging.basicConfig(
    level=logging.CRITICAL, format="%(asctime)s | %(levelname)s | %(message)s"
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "*********")

API_ID = int(os.getenv("TG_API_ID", "*********"))
API_HASH = os.getenv("TG_API_HASH", "*********")
MONGO_URI = os.getenv(
    "MONGO_URI",
    "*********",
)
DB_NAME = os.getenv("DB_NAME", "gifts")
SESS_DIR = os.getenv("SESS_DIR", "sessions")


ADMIN_IDS = [
    721947832,  # den main
    1668720886,  # sasha main
    720207278,  # misha main
]

PHONE_RE = re.compile(r"^\+\d{7,15}$")
SESS = {}

PAGE_SIZE = 3
TZ = ZoneInfo("Europe/Kyiv")


dp = Dispatcher()
