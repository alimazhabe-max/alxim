import os
import requests
from flask import Flask
from telegram.ext import Application, MessageHandler, filters
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")

def clean_instagram_url(url):
    url = url.strip()
    if "?" in url:
        url = url.split("?")[0]
    if not url.endswith("/"):
        url += "/"
    return url

# -------- Provider جدید و قوی --------
def from_saveig(url):
    api = "https://saveig.app/api/ajax"
    data = {"url": url}
    r = requests.post(api, data=data, timeout=10).json()
    return r.get("video")

# -------- Providerهای کمکی --------
def from_instasupersave(url):
    try:
        api = "https://instasupersave.com/api/convert"
        data = {"url": url}
        r = requests.post(api, data=data, timeout=10).json()
        return r.get("url")
    except:
        return None

def from_dlydown(url):
    try:
        api = f"https://api.dlydown.com/instagram?url={url}"
        r = requests.get(api, timeout=10).json()
        return r["result"][0]["url"]
    except:
        return None

PROVIDERS = [
    from_saveig,          # قوی‌ترین
    from_instasupersave,
    from_dlydown,
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
            "🌙✨ اوه‌اوه… این لینک خیلی شیطونه! حتی قوی‌ترین سایت‌ها هم نتونستن بازش کنن… "
            "یه لینک دیگه بده ببینم چی می‌شه! 💛"
        )

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.run_polling()

app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "✨ Instagram Download Bridge Bot on Railway ✨"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
