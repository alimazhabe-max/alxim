import os
import requests
from bs4 import BeautifulSoup
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

# ---------- Scraper instasupersave ----------
def scrape_instasupersave(url):
    try:
        session = requests.Session()

        # مرحله ۱: درخواست API
        api = "https://instasupersave.com/api/convert"
        data = {"url": url}

        response = session.post(api, data=data, timeout=10)

        # اگر JSON بود
        try:
            j = response.json()
            if "url" in j and j["url"]:
                return j["url"]
        except:
            pass

        # اگر JSON نبود → HTML Parse
        soup = BeautifulSoup(response.text, "html.parser")
        link_tag = soup.find("a", href=True)

        if link_tag:
            return link_tag["href"]

        return None

    except Exception:
        return None

# ---------- Telegram bot ----------
async def handle_message(update, context):
    text = update.message.text.strip()

    if text == "/start":
        await update.message.reply_text(
            "✨ سلام! لینک اینستاگرام رو بده، من می‌رم داخل instasupersave "
            "و لینک دانلود مستقیمش رو برات میارم 💛"
        )
        return

    url = clean_instagram_url(text)
    download_link = scrape_instasupersave(url)

    if download_link:
        await update.message.reply_text(
            "✨ لینک دانلود آماده شد!\n\n"
            f"🔗 {download_link}\n\n"
            "اگر باز نشد، با VPN امتحان کن 💛"
        )
    else:
        await update.message.reply_text(
            "🌙✨ اوه‌اوه… این لینک خیلی شیطونه!\n"
            "رفتم داخل سایت، لینک رو Paste کردم، سرچ کردم… ولی سایت نتونست دانلود بسازه 💛"
        )

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.run_polling()

# ---------- Flask server ----------
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "✨ Instagram Downloader Bot — Stable Scraper Edition ✨"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
