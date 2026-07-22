import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.enums import ParseMode
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

router = Router()

@router.message(F.text == "/start")
async def start(message: Message):
    await message.answer("👋 ربات تست فعال شد!\nلینک اینستاگرام بفرست.", parse_mode=ParseMode.HTML)

@router.message(F.text)
async def echo(message: Message):
    await message.answer("ربات در حال توسعه است...")

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
