import os
import requests
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@hmhermi"

FASTDL_API = "https://fastdl.app/fa2/video"

# ---------- چک عضویت ----------
async def is_member(user_id, bot):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

# ---------- منوی اصلی ----------
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇️ دانلود ویدیو", callback_data="download")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
    ])

# ---------- دکمه عضویت ----------
def join_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/hmhermi")],
        [InlineKeyboardButton("🔄 بررسی عضویت", callback_data="check_join")]
    ])

# ---------- دکمه دانلود ----------
def download_button(link):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇️ دانلود مستقیم", url=link)]
    ])

# ---------- API fastdl ----------
def get_fastdl(url):
    try:
        r = requests.post(FASTDL_API, data={"url": url}, timeout=10)
        j = r.json()
        if j.get("url"):
            return j["url"]
        return None
    except:
        return None

# ---------- پیام انسانی ----------
async def human(update, text):
    await update.message.reply_text(f"{text}")

# ---------- هندل پیام‌ها ----------
async def handle_message(update, context):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    # فقط لینک اینستاگرام
    if "instagram.com" not in text:
        await human(update, "⚠️ لطفاً فقط لینک‌های اینستاگرام را ارسال کنید 💛")
        return

    # چک عضویت
    if not await is_member(user_id, context.bot):
        await human(update, "برای استفاده از ربات، ابتدا باید عضو کانال شوید 💛")
        await update.message.reply_text("👇 لطفاً عضو شوید:", reply_markup=join_buttons())
        return

    # ساعت‌شنی هنگام جستجو
    await human(update, "⏳ در حال جستجو… لطفاً صبر کنید")

    link = get_fastdl(text)

    if link:
        await update.message.reply_text(
            "✨ لینک دانلود آماده شد!",
            reply_markup=download_button(link)
        )
    else:
        await human(update, "😔 امروز یکم سخت می‌گیره… دوباره امتحان کن")

# ---------- هندل دکمه‌ها ----------
async def handle_callback(update, context):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    # بررسی عضویت
    if q.data == "check_join":
        if await is_member(user_id, context.bot):
            await q.edit_message_text(
                "🎉 تبریک! ربات برای شما **رایگان و نامحدود** فعال شد.\n\n"
                "👇 منوی اصلی:",
                reply_markup=main_menu()
            )
        else:
            await q.edit_message_text(
                "❌ هنوز عضو کانال نیستید!\n👇 لطفاً عضو شوید:",
                reply_markup=join_buttons()
            )

    # منوی اصلی
    if q.data == "download":
        await q.edit_message_text("لینک اینستاگرام را ارسال کنید تا دانلود کنم 💛")

    if q.data == "help":
        await q.edit_message_text(
            "📘 راهنما:\n\n"
            "1️⃣ لینک اینستاگرام را بفرست\n"
            "2️⃣ ربات لینک دانلود مستقیم می‌دهد\n"
            "3️⃣ کاملاً رایگان و نامحدود\n\n"
            "👇 منوی اصلی:",
            reply_markup=main_menu()
        )

# ---------- اجرای ربات ----------
def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

# ---------- Flask برای Railway ----------
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is alive"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
