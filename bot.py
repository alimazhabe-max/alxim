# ====================== ربات گزارش شبانه قم ======================
import os
import datetime
import pytz
import sqlite3
import logging
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# ====================== تنظیمات ======================
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
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS subscribers (chat_id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

def add_subscriber(chat_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)", (chat_id,))
    conn.commit()
    conn.close()

def get_subscribers():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT chat_id FROM subscribers").fetchall()
    conn.close()
    return [r[0] for r in rows]

def remove_subscriber(chat_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM subscribers WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

# ====================== API Helper ======================
def safe_request(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=12)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"API request failed: {e}")
        return None

# ====================== داده‌ها ======================
def get_prayer_times_qom():
    data = safe_request(
        "https://api.aladhan.com/v1/timingsByCity",
        {"city": "Qom", "country": "Iran", "method": 14}
    )
    if data and "data" in data:
        t = data["data"]["timings"]
        return (
            t.get("Fajr", "?"),
            t.get("Dhuhr", "?"),
            t.get("Maghrib", "?"),
            t.get("Isha", "?")
        )
    return "?", "?", "?", "?"

def get_weather_qom():
    data = safe_request(
        "https://api.openweathermap.org/data/2.5/weather",
        {"q": "Qom,IR", "appid": WEATHER_KEY, "units": "metric", "lang": "fa"}
    )
    if data:
        return data["main"]["temp"], data["weather"][0]["description"]
    return "N/A", "نامشخص"

def get_shamsi_date():
    data = safe_request("https://api.keybit.ir/date/")
    return data["date"]["full"]["official"] if data else "نامشخص"

def get_hijri_date():
    today = datetime.datetime.now(tehran_tz).strftime("%Y-%m-%d")
    data = safe_request(f"https://api.aladhan.com/v1/gToH?date={today}")
    if data and "data" in data:
        h = data["data"]["hijri"]
        return f"{h['day']} {h['month']['ar']} {h['year']}", h['day'], h['month']['ar']
    return "نامشخص", "?", "?"

# ====================== مناسبت‌ها ======================
def get_shia_event(day, month):
    events = {
        ("18", "ذی الحجه"): "عید سعید غدیر خم 💛",
        ("24", "ذی الحجه"): "روز مباهله",
        ("25", "ذی الحجه"): "نزول آیه ولایت",
        ("10", "محرم"): "شهادت امام حسین (ع) 💔",
        ("20", "صفر"): "اربعین حسینی",
        ("28", "صفر"): "رحلت پیامبر اکرم (ص)",
        ("29", "صفر"): "شهادت امام حسن مجتبی (ع)",
    }
    return events.get((day, month), "روز خوبی برای دعا و توسل به اهل‌بیت علیهم‌السلام")

def get_daily_dhikr():
    return "لا حول و لا قوة إلا بالله العلی العظیم"

# ====================== ساخت پیام ======================
async def build_message():
    shamsi = get_shamsi_date()
    hijri, hijri_day, hijri_month = get_hijri_date()
    event = get_shia_event(hijri_day, hijri_month)
    fajr, dhuhr, maghrib, isha = get_prayer_times_qom()
    temp, desc = get_weather_qom()
    dhikr = get_daily_dhikr()

    return (
        "✨ گزارش شبانه قم ✨\n\n"
        f"📅 شمسی: {shamsi}\n"
        f"📆 قمری: {hijri}\n"
        f"🕊 مناسبت: {event}\n\n"
        "🕌 اوقات شرعی:\n"
        f"• فجر: {fajr}\n"
        f"• ظهر: {dhuhr}\n"
        f"• مغرب: {maghrib}\n"
        f"• عشاء: {isha}\n\n"
        f"🌤 آب و هوا: {temp}°C - {desc}\n\n"
        f"💬 ذکر روز: {dhikr}\n\n"
        "اللهم عجل لولیک الفرج 💛"
    )

# ====================== هندلرها ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_subscriber(update.effective_chat.id)
    await update.message.reply_text("ثبت شد! هر شب ساعت ۱۲ گزارش برات ارسال می‌شه.")

async def test_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await build_message()
    await update.message.reply_text("📨 گزارش تستی:\n\n" + msg)

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    remove_subscriber(update.effective_chat.id)
    await update.message.reply_text("❌ از لیست دریافت گزارش حذف شدید.")

async def nightly_job(context: ContextTypes.DEFAULT_TYPE):
    subs = get_subscribers()
    if not subs:
        return
    msg = await build_message()
    for chat_id in subs:
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg)
        except Exception as e:
            logger.warning(f"Failed to send to {chat_id}: {e}")

# ====================== Flask ======================
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Nightly Shia Report Bot is running!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

# ====================== اجرا ======================
def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test_report))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))

    app.job_queue.run_daily(
        nightly_job,
        time=datetime.time(0, 0, tzinfo=tehran_tz)
    )

    threading.Thread(target=run_flask, daemon=True).start()

    app.run_polling()

if __name__ == "__main__":
    main()
