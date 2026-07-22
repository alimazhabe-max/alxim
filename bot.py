import os
import re
import threading
import asyncio
import aiohttp
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@hmhermi"
BOT_USERNAME = "almix1bot"

INSTAGRAM_REGEX = re.compile(r'(https?://(?:www\.)?(?:instagram\.com|instagr\.am)/[^\s]+)')

DOWNLOAD_APIS = [
    "https://api.vevioz.com/api/v2/instagram",
    "https://api.savetik.net/api/instagram",
]

# ---------- چک عضویت ----------
async def is_member(user_id: int, bot) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


def menu_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 ایرانی", url=f"https://t.me/{BOT_USERNAME}?start=iran")],
        [InlineKeyboardButton("🌍 خارجی", url=f"https://t.me/{BOT_USERNAME}?start=world")],
        [InlineKeyboardButton("⚡ سریع‌ترین", url=f"https://t.me/{BOT_USERNAME}?start=fast")],
        [InlineKeyboardButton("📘 استوری", url=f"https://t.me/{BOT_USERNAME}?start=story")],
        [InlineKeyboardButton("👤 پروفایل", url=f"https://t.me/{BOT_USERNAME}?start=profile")],
        [InlineKeyboardButton("ℹ️ راهنما", url=f"https://t.me/{BOT_USERNAME}?start=help")],
    ])


# ---------- دانلود با مدیریت خطا ----------
async def download_instagram(update: Update, url: str):
    status_msg = await update.message.reply_text("⏳ در حال دانلود...")

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        for api_url in DOWNLOAD_APIS:
            try:
                await status_msg.edit_text("🔄 در حال دریافت لینک دانلود...")

                async with session.get(api_url, params={"url": url}) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()

                media_items = data.get("data") or data.get("medias") or data.get("urls") or []
                if not media_items:
                    continue

                sent = 0
                for item in media_items[:4]:
                    media_url = item.get("url") if isinstance(item, dict) else str(item)
                    if not media_url.startswith("http"):
                        continue

                    if ".mp4" in media_url.lower():
                        await update.message.reply_video(media_url, supports_streaming=True)
                    else:
                        await update.message.reply_photo(media_url)

                    sent += 1

                if sent > 0:
                    await status_msg.edit_text("✅ دانلود با موفقیت انجام شد!")
                    return

            except Exception as e:
                print(f"API Error: {e}")
                continue

    await status_msg.edit_text("⚠️ دانلود مستقیم موقتاً در دسترس نیست. از دکمه‌ها استفاده کنید.")


async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update.effective_user.id, context.bot):
        await update.message.reply_text("ابتدا عضو کانال شوید.")
        return

    matches = INSTAGRAM_REGEX.findall(update.message.text)
    if matches:
        await download_instagram(update, matches[0])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update.effective_user.id, context.bot):
        await update.message.reply_text("لطفا عضو کانال شوید:\nhttps://t.me/hmhermi")
        return

    args = context.args
    if args:
        cmd = args[0].lower()
        if cmd in ["iran", "world", "fast", "story", "profile", "help"]:
            await globals()[cmd](update, context) if cmd in globals() else None
            return

    await update.message.reply_text("👇 منوی اصلی:", reply_markup=menu_buttons())


# دستورات ساده
async def iran(update, context): await update.message.reply_text("🇮🇷 ایرانی:\nfastdl.app\ninstadl.ir")
async def world(update, context): await update.message.reply_text("🌍 خارجی:\nsnapinsta.app")
async def fast(update, context): await update.message.reply_text("⚡ سریع‌ترین:\nfastdl.app")
async def story(update, context): await update.message.reply_text("📘 استوری:\nstoriesig.info")
async def profile(update, context): await update.message.reply_text("👤 پروفایل:\ninstadp.io")
async def help_cmd(update, context): await update.message.reply_text("لینک اینستاگرام بفرست.")


# ---------- Flask ----------
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "✅ Bot is alive!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)


def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN پیدا نشد! لطفا در تنظیمات Railway اضافه کنید.")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.CHAT_TYPE.PRIVATE, handle_instagram_link))
    app.add_handler(MessageHandler(filters.TEXT & filters.CHAT_TYPE.PRIVATE, start))

    print("✅ ربات شروع شد...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
