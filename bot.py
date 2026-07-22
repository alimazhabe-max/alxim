import os
import requests
from flask import Flask
from telegram.ext import Application, MessageHandler, filters
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ---------- تمیز کردن لینک اینستاگرام ----------
def clean_instagram_url(url):
    url = url.strip()
    if "?" in url:
        url = url.split("?")[0]
    if not url.endswith("/"):
        url += "/"
    return url

# ---------- Provider واقعی و پایدار ----------
def from_instasupersave(url):
    api = "https://instasupersave.com/api/convert"
    data = {"url": url}
    r = requests.post(api, data=data, timeout=10).json()
    return r.get("url")

# ---------- Providerهای کمکی ----------
def from_dlydown(url):
    try:
        api = f"https://api.dlydown.com/instagram?url={url}"
        r = requests.get(api, timeout=10).json()
        return r["result"][0]["url"]
    except:
        return None

def from_snapinsta(url):
    try:
        api = "https://snapinsta.app/api/ajax"
        data = {"url": url}
        r = requests.post(api, data=data, timeout=10).json()
        return r.get("video")
    except:
        return None

# ---------- لیست Providerها ----------
PROVIDERS = [
    from_instasupersave,   # بهترین و پایدارترین
    from_dlydown,
    from_snapinsta,
]

def get_best_video(url):
    url = clean_instagram_url(url)
    for provider in PROVIDERS:
        try:
            video = provider(url)
            if video:
                return video
        except:
            continue
    return None

# ---------- Telegram bot ----------
async def handle_message(update, context):
    url = update.message.text.strip()
    video = get_best_video(url)

    if video:
        try:
            await update.message.reply_video(video)
        except:
            await update.message.reply_text(
                "✨ اوه نه! لینک رو پیدا کردم ولی موقع فرستادنش یه چیزی قاطی کرد! دوباره امتحان کنیم؟ 💛"
            )
    else:
        await update.message.reply_text(
            "🌙✨ اوه‌اوه… انگار این لینک یه کم قهر کرده! "
            "هرچی گشتم، هیچ‌کدوم از سایت‌ها نتونستن پیداش کنن… "
            "یه لینک دیگه بده ببینم چی می‌شه! 💛"
        )

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.run_polling()

# ---------- Flask server ----------
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "✨ Instagram Download Bridge Bot on Railway ✨"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
