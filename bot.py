import asyncio
import logging
import os
import re
from dotenv import load_dotenv

import instaloader
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.enums import ParseMode, ChatAction

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

# تنظیم Instaloader
L = instaloader.Instaloader(
    dirname_pattern="downloads/{target}",
    download_pictures=True,
    download_videos=True,
    download_video_thumbnails=False,
    compress_json=False,
)

router = Router()

WELCOME_MESSAGE = (
    "👋 <b>به ربات دانلودر اینستاگرام خوش آمدید!</b>\n\n"
    "هر لینک پست، ریلز، استوری یا هایلایت رو بفرستید، براتون دانلود می‌کنم.\n\n"
    "لینک رو paste کنید..."
)

@router.message(F.text == "/start")
async def start(message: Message):
    await message.answer(WELCOME_MESSAGE, parse_mode=ParseMode.HTML)

@router.message(F.text)
async def handle_link(message: Message):
    url = message.text.strip()
    if "instagram.com" not in url:
        await message.answer("لینک اینستاگرام نیست! لطفاً لینک درست بفرستید.")
        return

    status_msg = await message.answer("⏳ در حال دانلود... لطفاً صبر کنید.")

    try:
        # استخراج shortcode
        shortcode = re.search(r"instagram\.com/[^/]+/([^/?#]+)", url)
        if not shortcode:
            await status_msg.edit_text("لینک نامعتبر است.")
            return

        post = instaloader.Post.from_shortcode(L.context, shortcode.group(1))
        
        await status_msg.edit_text("📥 در حال دانلود فایل...")

        L.download_post(post, target="temp")

        # پیدا کردن فایل‌های دانلود شده
        for filename in os.listdir("temp"):
            if filename.endswith(('.jpg', '.mp4', '.png')):
                file_path = f"temp/{filename}"
                with open(file_path, "rb") as f:
                    if filename.endswith(('.mp4')):
                        await message.answer_video(
                            BufferedInputFile(f.read(), filename=filename),
                            caption="✅ دانلود شد"
                        )
                    else:
                        await message.answer_photo(
                            BufferedInputFile(f.read(), filename=filename),
                            caption="✅ دانلود شد"
                        )
                os.remove(file_path)

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ خطا: {str(e)[:200]}")

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    logging.info("ربات Instaloader فارسی شروع شد...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())