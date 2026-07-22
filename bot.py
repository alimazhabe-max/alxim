import os
import requests
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@hmhermi"

SITES = [
    ("fastdl.app", "https://fastdl.app/fa2/video", "fastdl"),
    ("snapinsta.app", "https://snapinsta.app/api/ajax", "snapinsta"),
    ("saveig.app", "https://saveig.app/api/ajax", "saveig"),
    ("igram.io", "https://igram.io/api/ajax", "igram"),
]

async def is_member(user_id, bot):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇️ دانلود ویدیو از اینستاگرام", callback_data="download")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
    ])

def join_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/hmhermi")],
        [InlineKeyboardButton("🔄 بررسی عضویت", callback_data="check_join")]
    ])

def download_button(link):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇️ دانلود مستقیم", url=link)]
    ])

async def human(update, text):
    await update.message.reply_text(text)

def try_fastdl(url):
    try:
        r = requests.post("https://fastdl.app/fa2/video", data={"url": url}, timeout=10)
        j = r.json()
        return j.get("url")
    except:
        return None

def try_snapinsta(url):
    try:
        r = requests.post("https://snapinsta.app/api/ajax", data={"url": url, "action": "post"}, timeout=10)
        j = r.json()
        return j.get("media")
    except:
        return None

def try_saveig(url):
    try:
        r = requests.post("https://saveig.app/api/ajax", data={"url": url, "action": "post"}, timeout=10)
        j = r.json()
        return j.get("media")
    except:
        return None

def try_igram(url):
    try:
        r = requests.post("https://igram.io/api/ajax", data={"url": url, "action": "post"}, timeout=10)
        j = r.json()
        return j.get("media")
    except:
        return None

def get_best_link(url):
    link = try_fastdl(url)
    if link:
        return link, "fastdl.app"

    link = try_snapinsta(url)
    if link:
        return link, "snapinsta.app"

    link = try_saveig(url)
    if link:
        return link, "saveig.app"

    link = try_igram(url)
    if link:
        return link, "igram.io"

    return None, None

async def handle_message(update, context):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if "instagram.com" not in text:
        await human(update, "⚠️ لطفاً فقط لینک‌های اینستاگرام را ارسال کنید 💛")
        return

    if not await is_member(user_id, context.bot):
        await human(update, "برای استفاده از ربات، ابتدا باید عضو کانال شوید 💛")
        await update.message.reply_text("👇 لطفاً عضو شوید:", reply_markup=join_buttons())
        return

    await human(update, "⏳ در حال جستجو بین بهترین سرورها…")

    link, source = get_best_link(text)

    if link:
        await update.message.reply_text(
            f"✨ لینک دانلود آماده شد!\n\n"
            f"✅ سرور: {source}\n",
            reply_markup=download_button(link)
        )
    else:
        await human(update, "😔 هیچ‌کدام از سرورها نتوانستند لینک را پردازش کنند.\nلطفاً بعداً دوباره امتحان کنید 💛")

async def handle_callback(update, context):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    if q.data == "check_join":
        if await is_member(user_id, context.bot):
            await q.edit_message_text(
                "🎉 تبریک! ربات برای شما **به صورت رایگان و نامحدود** فعال شد.\n\n"
                "👇 منوی اصلی:",
                reply_markup=main_menu()
            )
        else:
            await q.edit_message_text(
                "❌ هنوز عضو کانال نیستید!\n👇 لطفاً عضو شوید:",
                reply_markup=join_buttons()
            )
        return

    if q.data == "download":
        await q.edit_message_text(
            "لینک اینستاگرام را ارسال کنید تا بهترین سرور برای دانلود انتخاب شود 💛"
        )
        return

    if q.data == "help":
        await q.edit_message_text(
            "ℹ️ **راهنما:**\n\n"
            "1️⃣ لینک اینستاگرام را ارسال کنید.\n"
            "2️⃣ ربات بین چند سرور (fastdl, snapinsta, saveig, igram) جستجو می‌کند.\n"
            "3️⃣ بهترین لینک دانلود را برای شما می‌فرستد.\n\n"
            "ربات برای شما به صورت **رایگان و نامحدود** فعال است 💛\n\n"
            "👇 منوی اصلی:",
            reply_markup=main_menu()
        )
        return

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is alive"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
