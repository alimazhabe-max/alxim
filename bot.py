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

# ---------- Scraper 1: instasupersave ----------
def scrape_instasupersave(url):
    try:
        api = "https://instasupersave.com/api/convert"
        data = {"url": url}
        r = requests.post(api, data=data, timeout=10)

        # JSON
        try:
            j = r.json()
            if "url" in j and j["url"]:
                return j["url"]
        except:
            pass

        # HTML fallback
        soup = BeautifulSoup(r.text, "html.parser")
        a = soup.find("a", href=True)
        if a:
            return a["href"]

        return None
    except:
        return None

# ---------- Scraper 2: saveig ----------
def scrape_saveig(url):
    try:
        api = "https://saveig.app/api/ajax"
        data = {"url": url}
        r = requests.post(api, data=data, timeout=10)

        try:
            j = r.json()
            if "video" in j and j["video"]:
                return j["video"]
        except:
            pass

        return None
    except:
        return None

# ---------- Scraper 3: snapinsta ----------
def scrape_snapinsta(url):
    try:
        api = "https://snapinsta.app/api/ajax"
        data = {"url": url}
        r = requests.post(api, data=data, timeout=10)

        try:
            j = r.json()
            if "video" in j and j["video"]:
                return j["video"]
        except:
            pass

        return None
    except:
        return None

# ---------- انتخاب بهترین لینک ----------
SCRAPERS = [
    scrape_instasupersave,
    scrape_saveig,
    scrape_snapinsta,
]

def get_best_download_link(url):
    url = clean_instagram_url(url)
    for scraper in SCRAPERS:
        link = scraper(url)
        if link:
            return link
    return None

# ---------- Telegram bot ----------
async def handle_message(update, context):
    text = update.message.text.strip()

    if text == "/start":
        await update.message.reply_text(
            "✨ سلام! من نسخهٔ Ultra‑Scraper هستم.\n"
            "لینک Reel رو بده، من از ۳ سایت مختلف Scrape می‌کنم "
            "و لینک دانلود مستقیمش رو برات میارم 💛"
        )
        return

    url = clean_instagram_url(text)
    download_link = get_best_download_link(url)

    if download_link:
        await update.message.reply_text(
            "✨ لینک دانلود آماده شد!\n\n"
            f"🔗 {download_link}\n\n"
            "اگر باز نشد، با VPN امتحان کن 💛"
        )
    else:
        await update.message.reply_text(
            "🌙✨ اوه‌اوه… این لینک واقعاً شیطونه!\n"
            "از ۳ سایت مختلف تست کردم، هیچ‌کدوم نتونستن بازش کنن…\n"
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
    return "✨ Instagram Downloader Bot — Ultra‑Scraper Edition ✨"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
