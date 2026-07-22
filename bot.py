import os
import requests
from flask import Flask
from telegram.ext import Application, MessageHandler, filters
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ---------- تمیز کردن لینک ----------
def clean_instagram_url(url):
    url = url.strip()
    if "?" in url:
        url = url.split("?")[0]
    if not url.endswith("/"):
        url += "/"
    return url

# ---------- Provider 1: instasupersave ----------
def from_instasupersave(url):
    try:
        api = "https://instasupersave.com/api/convert"
        data = {"url": url}
        r = requests.post(api, data=data, timeout=10).json()
        return r.get("url")
    except Exception:
        return None

# ---------- Provider 2: saveig (پشتیبان) ----------
def from_saveig(url):
    try:
        api = "https://saveig.app/api/ajax"
        data = {"url": url}
        r = requests.post(api, data=data, timeout=10).json()
        return r.get("video")
    except Exception:
        return None

# ---------- انتخاب بهترین لینک ----------
PROVIDERS = [
    from_instasupersave,  # اولویت اول
    from_saveig,          # پشتیبان
]

def get_best_download_link(url):
    url = clean_instagram_url(url)
    for provider in PROVIDERS:
        link = provider(url)
        if link:
            return link
    return None

# ---------- Telegram bot ----------
async def handle_message(update, context):
    text = update.message.text.strip()

    # اگر کاربر /start فرستاد
    if text == "/start":
        await update.message.reply_text(
            "✨ سلام! من پل دانلود اینستاگرام هستم.\n"
            "فقط لینک Reel یا پست رو برام بفرست، من برات لینک دانلود مستقیمش رو می‌فرستم 💛"
        )
        return

    download_link = get_best_download_link(text)

    if download_link:
        await update.message.reply_text(
            "✨ لینک دانلود آماده شد!\n\n"
            f"🔗 {download_link}\n\n"
            "اگر باز نشد، با مرورگر دیگه یا VPN امتحان کن 💛"
        )
    else:
        await update.message.reply_text(
            "🌙✨ اوه‌اوه… این لینک خیلی شیطونه!\n"
            "هم instasupersave هم سایت پشتیبان نتونستن پیداش کنن…\n"
            "یه لینک دیگه بده، یا بعداً دوباره امتحان کنیم 💛"
        )

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.run_polling()

# ---------- Flask server ----------
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "✨ Instagram Download Bridge Bot — Pro Edition ✨"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
