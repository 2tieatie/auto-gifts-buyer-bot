import asyncio
import pkg_resources  # из setuptools
from config import BOT_TOKEN, dp
from aiogram import Bot
from utils import ensure_dirs
from db import get_db

from routers.commands import router as commands_router
from routers.other import router as other_router
from account import relogin_loop, update_loop


async def main():
    print("==== Installed libraries ====")
    for dist in pkg_resources.working_set:
        print(f"{dist.project_name}=={dist.version}")
    print("=============================")

    bot = Bot(BOT_TOKEN)
    await ensure_dirs()
    await get_db()

    dp.include_router(commands_router)
    dp.include_router(other_router)

    asyncio.create_task(relogin_loop())
    asyncio.create_task(update_loop())

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
