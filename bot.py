import os
import datetime
import pytz
import requests
import sqlite3
from telegram.ext import Updater, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEATHER_KEY = os.getenv("WEATHER_KEY")
DB_PATH = "data.db"

tehran_tz = pytz.timezone("Asia/Tehran")


# ---------- دیتابیس ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            chat_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()


def add_subscriber(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)", (chat_id,))
    conn.commit()
    conn.close()


def get_subscribers():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT chat_id FROM subscribers")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


# ---------- API ----------
def safe_request(url):
    try:
        return requests.get(url, timeout=10).json()
    except:
        return None


def get_weather_qom():
    url = f"https://api.openweathermap.org/data/2.5/weather?q=Qom,IR&appid={WEATHER_KEY}&units=metric"
    r = safe_request(url)
    if not r or "main" not in r:
        return "نامشخص", "خطا در دریافت اطلاعات"
    return r["main"]["temp"], r["weather"][0]["description"]


def get_prayer_times_qom():
    url = "https://api.aladhan.com/v1/timingsByCity?city=Qom&country=Iran&method=14"
    r = safe_request(url)
    if not r:
        return "?", "?", "?"
    t = r["data"]["timings"]
    return t["Fajr"], t["Dhuhr"], t["Maghrib"]


def get_shamsi_date():
    r = safe_request("https://api.keybit.ir/date/")
    if not r:
        return "نامشخص"
    return r["date"]["full"]["official"]


def get_hijri_date():
    today = datetime.datetime.now(tehran_tz).strftime("%Y-%m-%d")
    url = f"https://api.aladhan.com/v1/gToH?date={today}"
    r = safe_request(url)
    if not r:
        return "نامشخص"
    h = r["data"]["hijri"]
    return f"{h['day']} {h['month']['ar']}"


def get_shia_event(day, month):
    events = {
        ("18", "ذی الحجه"): "عید غدیر خم 💛",
        ("24", "ذی الحجه"): "روز مباهله پیامبر اکرم ﷺ",
        ("25", "ذی الحجه"): "نزول آیه ولایت",
        ("10", "محرم"): "روز عاشورا 💔",
        ("20", "صفر"): "اربعین حسینی"
    }
    return events.get((day, month), "امروز روزی‌ست برای یاد اهل‌بیت علیهم‌السلام 💛")


def build_message():
    shamsi = get_shamsi_date()
    hijri = get_hijri_date()

    try:
        hijri_day, hijri_month = hijri.split(" ")
    except:
        hijri_day, hijri_month = "?", "?"

    event = get_shia_event(hijri_day, hijri_month)
    fajr, dhuhr, maghrib = get_prayer_times_qom()
    temp, desc = get_weather_qom()

    return (
        "✨ گزارش شبانه قم ✨\n\n"
        f"📅 تاریخ شمسی: {shamsi}\n"
        f"📆 تاریخ قمری: {hijri}\n"
        f"🕊 مناسبت امروز:\n{event}\n\n"
        "🕌 اوقات شرعی قم:\n"
        f"• اذان صبح: {fajr}\n"
        f"• اذان ظهر: {dhuhr}\n"
        f"• اذان مغرب: {maghrib}\n\n"
        "🌤 آب‌وهوا‌ی قم:\n"
        f"• دما: {temp}°C\n"
        f"• وضعیت: {desc}\n\n"
        "اللهم عجل لولیک الفرج 💛"
    )


# ---------- /start ----------
def start(update, context):
    add_subscriber(update.message.chat_id)
    update.message.reply_text(
        "از این به بعد هر شب ساعت ۱۲ شب گزارش کامل روز برات میاد 🌙✨"
    )


# ---------- کار شبانه ----------
def nightly_job(context):
    subs = get_subscribers()
    if not subs:
        return

    msg = build_message()

    for chat_id in subs:
        try:
            context.bot.send_message(chat_id, msg)
        except:
            pass


# ---------- اجرای ربات ----------
def main():
    init_db()

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))

    # Job Queue نسخه 13
    jq = updater.job_queue
    jq.run_daily(
        nightly_job,
        time=datetime.time(0, 0, tzinfo=tehran_tz)
    )

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
