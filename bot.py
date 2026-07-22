import os
import datetime
import pytz
import sqlite3
import logging
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ====================== لاگ ======================
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEATHER_KEY = os.getenv("WEATHER_KEY")
DB_PATH = "data.db"
tehran_tz = pytz.timezone("Asia/Tehran")

# ====================== دیتابیس ======================
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                chat_id INTEGER PRIMARY KEY
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"DB Init Error: {e}")

def add_subscriber(chat_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Add subscriber error: {e}")

def get_subscribers():
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT chat_id FROM subscribers").fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        logger.error(f"Get subscribers error: {e}")
        return []

# ====================== APIها ======================
def safe_request(url, params=None, timeout=10):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        logger.warning(f"Request failed {url}: {e}")
        return None

def get_weather_qom():
    url = f"https://api.openweathermap.org/data/2.5/weather"
    data = safe_request(url, {"q": "Qom,IR", "appid": WEATHER_KEY, "units": "metric"})
    if data and "main" in data:
        return data["main"]["temp"], data["weather"][0]["description"]
    return "N/A", "نامشخص"

def get_prayer_times_qom():
    data = safe_request("https://api.aladhan.com/v1/timingsByCity?city=Qom&country=Iran&method=14")
    if data and "data" in data:
        t = data["data"]["timings"]
        return t.get("Fajr", "?"), t.get("Dhuhr", "?"), t.get("Maghrib", "?")
    return "?", "?", "?"

def get_shamsi_date():
    data = safe_request("https://api.keybit.ir/date/")
    return data["date"]["full"]["official"] if data else "نامشخص"

def get_hijri_date():
    today = datetime.datetime.now(tehran_tz).strftime("%Y-%m-%d")
    data = safe_request(f"https://api.aladhan.com/v1/gToH?date={today}")
    if data and "data" in data:
        h = data["data"]["hijri"]
        return f"{h['day']} {h['month']['ar']}"
    return "نامشخص"

def build_message():
    try:
        shamsi = get_shamsi_date()
        hijri = get_hijri_date()
        hijri_day, hijri_month = hijri.split(" ") if " " in hijri else ("?", "?")
        
        events = {("18", "ذی الحجه"): "عید غدیر خم 💛", ("10", "محرم"): "روز عاشورا 💔"}
        event = events.get((hijri_day, hijri_month), "یاد اهل‌بیت علیهم‌السلام 💛")

        fajr, dhuhr, maghrib = get_prayer_times_qom()
        temp, desc = get_weather_qom()

        return (
            "✨ گزارش شبانه قم ✨\n\n"
            f"📅 شمسی: {shamsi}\n"
            f"📆 قمری: {hijri}\n"
            f"🕊 مناسبت: {event}\n\n"
            f"🕌 صبح: {fajr} | ظهر: {dhuhr} | مغرب: {maghrib}\n\n"
            f"🌤 دما: {temp}°C | {desc}\n\n"
            "اللهم عجل لولیک الفرج 💛"
        )
    except Exception as e:
        logger.error(f"Build message error: {e}")
        return "گزارش امشب با مشکل مواجه شد."

# ====================== هندلر ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_subscriber(update.effective_chat.id)
    await update.message.reply_text("✅ ثبت شد!\nهر شب ساعت ۱۲ گزارش برات میاد 🌙")

async def nightly_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info("اجرای job شبانه...")
        subs = get_subscribers()
        if not subs:
            return

        msg = build_message()
        for chat_id in subs:
            try:
                await context.bot.send_message(chat_id, msg)
            except Exception as e:
                logger.warning(f"Send failed to {chat_id}: {e}")
    except Exception as e:
        logger.error(f"Job crashed: {e}")

# ====================== Flask ======================
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "✅ Bot is running!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

# ====================== اجرا ======================
def main():
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN پیدا نشد!")
        return

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.job_queue.run_daily(
        nightly_job,
        time=datetime.time(0, 0, tzinfo=tehran_tz),
        name="nightly_report"
    )

    logger.info("ربات شروع شد...")
    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
