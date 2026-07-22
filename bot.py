import os
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = "https://alxim-1.onrender.com/webhook"

app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

# ---------- Provider ها (سایت‌های دانلود) ----------

def from_dlydown(url):
    api = f"https://api.dlydown.com/instagram?url={url}"
    r = requests.get(api, timeout=10).json()
    return r["result"][0]["url"]

def from_site_a(url):
    # مثال فرضی – بعداً با API واقعی جایگزین کن
    api = f"https://site-a.com/api/instagram?url={url}"
    r = requests.get(api, timeout=10).json()
    return r.get("video_url")

def from_site_b(url):
    api = f"https://site-b.com/download?link={url}"
    r = requests.get(api, timeout=10).json()
    return r.get("download")

def from_site_c(url):
    api = f"https://site-c.com/insta?u={url}"
    r = requests.get(api, timeout=10).json()
    return r.get("result")

PROVIDERS = [
    from_dlydown,
    from_site_a,
    from_site_b,
    from_site_c,
    # هر وقت خواستی، اینجا Provider جدید اضافه کن
]

def get_best_video(url):
    for provider in PROVIDERS:
        try:
            video = provider(url)
            if video:
                return video
        except Exception:
            continue
    return None

# ---------- هندلر پیام ----------

async def handle_message(update, context):
    url = update.message.text.strip()
    video = get_best_video(url)

    if video:
        try:
            await update.message.reply_video(video)
        except Exception:
            await update.message.reply_text("لینک پیدا شد ولی ارسال ویدیو مشکل خورد.")
    else:
        await update.message.reply_text("هیچ‌کدوم از سایت‌های دانلود نتونستن این لینک رو بگیرن.")

application.add_handler(MessageHandler(filters.TEXT, handle_message))

# ---------- Webhook ----------

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "ok"

@app.route("/")
def home():
    return "Instagram Download Bridge Bot"

if __name__ == "__main__":
    application.bot.set_webhook(WEBHOOK_URL)
    app.run(host="0.0.0.0", port=10000)
