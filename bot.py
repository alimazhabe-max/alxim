import os
import requests
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@hmhermi"  # کانال عضویت اجباری

API_URL = "https://instagram-downloader-api.vercel.app/api/reel?url="

# ---------- چک عضویت ----------
async def is_member(user_id, bot):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ---------- دکمه شیشه‌ای عضویت ----------
def join_buttons():
    keyboard = [
        [InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/hmhermi")],
        [InlineKeyboardButton("🔄 بررسی عضویت", callback_data="check_join")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------- دکمه شیشه‌ای دانلود ----------
def download_button(link):
    keyboard = [
        [InlineKeyboardButton("⬇️ دانلود مستقیم", url=link)]
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------- هندل پیام‌ها ----------
async def handle_message(update, context):
    user_id = update.message.from_user.id
    url = update.message.text.strip()

    # چک عضویت
    if not await is_member(user_id, context.bot):
        await update.message.reply_text(
            "✨ برای استفاده از ربات، ابتدا باید عضو کانال شوید:",
            reply_markup=join_buttons()
        )
        return

    # درخواست به API پایدار
    try:
        r = requests.get(API_URL + url, timeout=10).json()
    except:
        await update.message.reply_text("⚠️ اتصال به سرور مشکل پیدا کرد…")
        return

    if r.get("url"):
        await update.message.reply_text(
            "✨ لینک دانلود آماده شد!",
            reply_markup=download_button(r["url"])
        )
    else:
        await update.message.reply_text(
            "🌙 سایت نتونست لینک رو بسازه… بعداً امتحان کنیم 💛"
        )

# ---------- هندل دکمه بررسی عضویت ----------
async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "check_join":
        if await is_member(user_id, context.bot):
            await query.edit_message_text("✨ عضویت تایید شد! حالا لینک رو دوباره بفرست 💛")
        else:
            await query.edit_message_text(
                "❌ هنوز عضو کانال نیستی!\n\nلطفاً عضو شو و دوباره روی «بررسی عضویت» بزن:",
                reply_markup=join_buttons()
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
