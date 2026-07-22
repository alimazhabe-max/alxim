import os
import logging
import requests
from bs4 import BeautifulSoup
from flask import Flask
from telegram.ext import Application, MessageHandler, filters
import threading

# ---------- تنظیمات لاگ ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ---------- تمیز کردن لینک ----------
def clean_url(url: str) -> str:
    url = url.strip()
    if "?" in url:
        url = url.split("?")[0]
    if not url.endswith("/"):
        url += "/"
    return url

# ---------- استخراج لینک از HTML ----------
def extract_from_html(html: str) -> str | None:
    try:
        soup = BeautifulSoup(html, "html.parser")

        # لینک داخل <a>
        a = soup.find("a", href=True)
        if a and a["href"].startswith("http"):
            return a["href"]

        # لینک داخل meta og:video
        meta = soup.find("meta", property="og:video")
        if meta and meta.get("content"):
            return meta["content"]

        # لینک داخل script
        for script in soup.find_all("script"):
            if script.string and "https" in script.string:
                parts = script.string.split('"')
                for p in parts:
                    if p.startswith("https") and ".mp4" in p:
                        return p

        return None
    except Exception as e:
        logger.warning(f"HTML parse error: {e}")
        return None

# ---------- Scraper instasupersave ----------
def get_download_link_from_instasupersave(url: str) -> str | None:
    try:
        api = "https://instasupersave.com/api/convert"
        data = {"url": url}

        r = requests.post(api, data=data, timeout=10)

        # اول JSON
        try:
            j = r.json()
            if isinstance(j, dict) and j.get("url"):
                return j["url"]
        except Exception:
            pass

        # بعد HTML
        return extract_from_html(r.text)

    except Exception as e:
        logger.error(f"instasupersave error: {e}")
        return None

# ---------- گرفتن بهترین لینک ----------
def get_best_download_link(raw_url: str) -> str | None:
    url = clean_url(raw_url)
    logger.info(f"Trying to get download link for: {url}")
    return get_download_link_from_instasupersave(url)

# ---------- Telegram bot ----------
async def handle_message(update, context):
    text = update.message.text.strip()

    # /start
    if text == "/start":
        await update.message.reply_text(
            "✨ سلام! من یک ربات دانلود اینستاگرام هستم.\n"
            "فقط لینک Reel یا پست رو برام بفرست، من لینک دانلود مستقیمش رو برات می‌فرستم 💛"
        )
        return

    # اگر اصلاً شبیه لینک اینستاگرام نیست
    if "instagram.com" not in text:
        await update.message.reply_text(
            "✨ این شبیه لینک اینستاگرام نیست…\n"
            "لطفاً لینک کامل Reel یا پست رو بفرست 💛"
        )
        return

    download_link = get_best_download_link(text)

    if download_link:
        await update.message.reply_text(
            "✨ لینک دانلود آماده شد!\n\n"
            f"🔗 {download_link}\n\n"
            "اگر باز نشد، با VPN یا مرورگر دیگه امتحان کن 💛"
        )
    else:
        await update.message.reply_text(
            "🌙✨ اوه‌اوه… این لینک یه کم قهر کرده!\n"
            "رفتم داخل instasupersave، تست کردم، ولی نتونست لینک دانلود بسازه…\n"
            "یه لینک دیگه بده، یا بعداً دوباره امتحان کنیم 💛"
        )

def run_bot():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set!")
        raise SystemExit("BOT_TOKEN env var is missing")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    logger.info("Telegram bot is running...")
    app.run_polling()

# ---------- Flask server ----------
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "✨ Instagram Downloader Bot — Pro Edition ✨"

def run_flask():
    logger.info("Flask server is running...")
    app_flask.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
