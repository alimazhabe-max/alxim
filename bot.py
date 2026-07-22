import os
import requests
from bs4 import BeautifulSoup
from flask import Flask
from telegram.ext import Application, MessageHandler, filters
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ---------- تمیز کردن لینک ----------
def clean_url(url):
    url = url.strip()
    if "?" in url:
        url = url.split("?")[0]
    if not url.endswith("/"):
        url += "/"
    return url

# ---------- ابزار استخراج لینک از HTML ----------
def extract_from_html(html):
    try:
        soup = BeautifulSoup(html, "html.parser")

        # 1) لینک داخل <a>
        a = soup.find("a", href=True)
        if a:
            return a["href"]

        # 2) لینک داخل meta
        meta = soup.find("meta", property="og:video")
        if meta and meta.get("content"):
            return meta["content"]

        # 3) لینک داخل script
        for script in soup.find_all("script"):
            if script.string and "https" in script.string:
                parts = script.string.split('"')
                for p in parts:
                    if p.startswith("https") and ".mp4" in p:
                        return p

        return None
    except:
        return None

# ---------- Scraper 1: instasupersave ----------
def scraper_instasupersave(url):
    try:
        r = requests.post("https://instasupersave.com/api/convert",
                          data={"url": url}, timeout=10)

        # JSON
        try:
            j = r.json()
            if isinstance(j, dict) and j.get("url"):
                return j["url"]
        except:
            pass

        # HTML
        return extract_from_html(r.text)
    except:
        return None

# ---------- Scraper 2: saveig ----------
def scraper_saveig(url):
    try:
        r = requests.post("https://saveig.app/api/ajax",
                          data={"url": url}, timeout=10)

        try:
            j = r.json()
            if isinstance(j, dict) and j.get("video"):
                return j["video"]
        except:
            pass

        return extract_from_html(r.text)
    except:
        return None

# ---------- Scraper 3: snapinsta ----------
def scraper_snapinsta(url):
    try:
        r = requests.post("https://snapinsta.app/api/ajax",
                          data={"url": url}, timeout=10)

        try:
            j = r.json()
            if isinstance(j, dict) and j.get("video"):
                return j["video"]
        except:
            pass

        return extract_from_html(r.text)
    except:
        return None

# ---------- Scraper 4: igdownloader ----------
def scraper_igdownloader(url):
    try:
        r = requests.post("https://igdownloader.com/ajax",
                          data={"link": url}, timeout=10)

        try:
            j = r.json()
            if isinstance(j, dict) and j.get("download_url"):
                return j["download_url"]
        except:
            pass

        return extract_from_html(r.text)
    except:
        return None

# ---------- Scraper 5: toolzu ----------
def scraper_toolzu(url):
    try:
        r = requests.post("https://toolzu.com/api/ajax",
                          data={"url": url}, timeout=10)

        try:
            j = r.json()
            if isinstance(j, dict) and j.get("video"):
                return j["video"]
        except:
            pass

        return extract_from_html(r.text)
    except:
        return None

# ---------- لیست Scraperها ----------
SCRAPERS = [
    scraper_instasupersave,
    scraper_saveig,
    scraper_snapinsta,
    scraper_igdownloader,
    scraper_toolzu
]

def get_download_link(url):
    url = clean_url(url)
    for scraper in SCRAPERS:
        try:
            link = scraper(url)
            if link:
                return link
        except:
            continue
    return None

# ---------- Telegram bot ----------
async def handle_message(update, context):
    text = update.message.text.strip()

    if text == "/start":
        await update.message.reply_text(
            "✨ سلام! من نسخهٔ GOD‑SCRAPER هستم.\n"
            "از ۵ سایت مختلف Scrape می‌کنم و لینک دانلود Reel رو برات میارم 💛"
        )
        return

    link = get_download_link(text)

    if link:
        await update.message.reply_text(
            f"✨ لینک دانلود آماده شد!\n\n🔗 {link}\n\nبا خیال راحت دانلود کن 💛"
        )
    else:
        await update.message.reply_text(
            "🌙✨ اوه‌اوه… این لینک واقعاً از خدایان اینستاگرام کمک گرفته!\n"
            "۵ تا سایت مختلف تست کردم، هیچ‌کدوم نتونستن بازش کنن…\n"
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
    return "✨ Instagram Downloader Bot — GOD‑SCRAPER Edition ✨"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
