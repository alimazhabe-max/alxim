import os
import requests
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
import threading
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@hmhermi"

INSTASUPER_API = "https://instasupersave.com/api/convert"

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

# ---------- استخراج لینک از HTML ----------
def extract_from_html(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        a = soup.find("a", href=True)
        if a and a["href"].startswith("http"):
            return a["href"]
        return None
    except:
        return None

# ---------- درخواست به instasupersave ----------
def get_download_link(url):
    try:
        r = requests.post(INSTASUPER_API, data={"url": url}, timeout=10)

        # JSON
        try:
            j = r.json()
            if j.get("url"):
                return j["url"]
        except:
            pass

        # HTML fallback
        return extract_from_html(r.text)

    except:
        return None

# ---------- رفتار انسانی ----------
async def human_reply(update, text):
    await update.message.reply_text(f"✨ {text}")

# ---------- هندل پیام‌ها ----------
async def handle_message(update, context):
    user_id = update.message.from_user.id
    url = update.message.text.strip()

    # چک عضویت
    if not await is_member(user_id, context.bot):
        await human_reply(update, "برای استفاده از ربات، اول باید عضو کانال بشی 💛")
        await update.message.reply_text("👇 لطفاً عضو شو:", reply_markup=join_buttons())
        return

    # رفتار انسانی قبل از پردازش
    await human_reply(update, "یه لحظه صبر کن… دارم لینک رو بررسی می‌کنم 🤔")

    link = get_download_link(url)

    if link:
        await update.message.reply_text(
            "✨ لینک دانلود آماده شد!\n\n"
            "اگه باز نشد، یه بار با VPN امتحان کن 💛",
            reply_markup=download_button(link)
        )
    else:
        await human_reply(update, "اوه… instasupersave امروز یه کم بداخلاقه 😅")
        await human_reply(update, "یه لینک دیگه بده، دوباره تست می‌کنم 🌙")

# ---------- هندل دکمه بررسی عضویت ----------
async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "check_join":
        if await is_member(user_id, context.bot):
            await query.edit_message_text("✨ عالیه! عضویت تایید شد. حالا لینک رو دوباره بفرست 💛")
        else:
            await query.edit_message_text(
                "❌ هنوز عضو کانال نیستی!\n\n"
                "لطفاً عضو شو و دوباره روی «بررسی عضویت» بزن:",
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
