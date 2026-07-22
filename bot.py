import os
import requests
from flask import Flask
from telegram.ext import Application, MessageHandler, filters
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ---------- تمیز کردن لینک اینستاگرام ----------

def clean_instagram_url(url):
    url = url.strip()
    # حذف پارامترهای اضافه مثل utm و igsh
    if "?" in url:
        url = url.split("?")[0]
    # مطمئن شو آخرش / داره
    if not url.endswith("/"):
        url += "/"
    return url

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
    # مثال فرضی – بعداً با API واقعی جایگزین کن
    api = f"https://site-b.com/download?link={url}"
    r = requests.get(api, timeout=10).json()
    return r.get("download")

def from_site_c(url):
    # مثال فرضی – بعداً با API واقعی جایگزین کن
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
    url = clean_instagram_url(url)
    for provider in PROVIDERS:
        try:
            video = provider(url)
            if video:
                return video
        except Exception:
            continue
    return None

# ---------- Telegram bot ----------

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

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.run_polling()

# ---------- Flask server ----------

app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Instagram Download Bridge Bot on Railway!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
