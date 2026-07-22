import os
import requests
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@hmhermi"

SNAP_API = "https://snapinsta.app/api/ajax"

async def is_member(user_id, bot):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

def join_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/hmhermi")],
        [InlineKeyboardButton("🔄 بررسی عضویت", callback_data="check_join")]
    ])

def download_button(link):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇️ دانلود مستقیم", url=link)]
    ])

def get_snapinsta(url):
    try:
        r = requests.post(SNAP_API, data={"url": url, "action": "post"}, timeout=10)
        j = r.json()
        return j.get("media")
    except:
        return None

async def human(update, text):
    await update.message.reply_text(f"✨ {text}")

async def handle_message(update, context):
    user_id = update.message.from_user.id
    url = update.message.text.strip()

    if not await is_member(user_id, context.bot):
        await human(update, "برای استفاده از ربات، اول باید عضو کانال بشی 💛")
        await update.message.reply_text("👇 لطفاً عضو شو:", reply_markup=join_buttons())
        return

    await human(update, "یه لحظه صبر کن… دارم لینک رو بررسی می‌کنم 🤔")

    link = get_snapinsta(url)

    if link:
        await update.message.reply_text(
            "✨ لینک دانلود آماده شد!\n\nاگه باز نشد، با VPN تست کن 💛",
            reply_markup=download_button(link)
        )
    else:
        await human(update, "اوه… امروز یه کم سخت می‌گیره 😅")
        await human(update, "یه لینک دیگه بده، دوباره تست می‌کنم 🌙")

async def handle_callback(update, context):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id

    if q.data == "check_join":
        if await is_member(user_id, context.bot):
            await q.edit_message_text("✨ عضویت تایید شد! حالا لینک رو دوباره بفرست 💛")
        else:
            await q.edit_message_text(
                "❌ هنوز عضو کانال نیستی!\n👇 لطفاً عضو شو:",
                reply_markup=join_buttons()
            )

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
