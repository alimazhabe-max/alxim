import os
import datetime
import pytz
import requests
import sqlite3
from telegram.ext import Application, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
tehran_tz = pytz.timezone("Asia/Tehran")

DB_PATH = "data.db"


# ---------- راه‌اندازی دیتابیس ----------
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


def add_subscriber(chat_id: int):
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


# ---------- API ها ----------
def get_weather_qom():
    API_KEY = os.getenv("WEATHER_KEY")  # کلید OpenWeatherMap
    url = f"https://api.openweathermap.org/data/2.5/weather?q=Qom,IR&appid={API_KEY}&units=metric"
    r = requests.get(url).json()
    temp = r["main"]["temp"]
    desc = r["weather"][0]["description"]
    return temp, desc


def get_prayer_times_qom():
    url = "https://api.aladhan.com/v1/timingsByCity?city=Qom&country=Iran&method=14"
    r = requests.get(url).json()
    t = r["data"]["timings"]
    return t["Fajr"], t["Dhuhr"], t["Maghrib"]


def get_shamsi_date():
    r = requests.get("https://api.keybit.ir/date/").json()
    return r["date"]["full"]["official"]


def get_hijri_date():
    today = datetime.datetime.now(tehran_tz).strftime("%Y-%m-%d")
    url = f"https://api.aladhan.com/v1/gToH?date={today}"
    r = requests.get(url).json()
    h = r["data"]["hijri"]
    return f"{h['day']} {h['month']['ar']}"


def get_shia_event(hijri_day, hijri_month):
    events = {
        ("18", "ذی الحجه"): "عید غدیر خم 💛",
        ("24", "ذی الحجه"): "روز مباهله پیامبر اکرم ﷺ",
        ("25", "ذی الحجه"): "نزول آیه ولایت (صدقه دادن امیرالمؤمنین در رکوع)",
        ("10", "محرم"): "روز عاشورا، شهادت امام حسین علیه‌السلام 💔",
        ("20", "صفر"): "اربعین حسینی"
    }
    return events.get((hijri_day, hijri_month), "امروز روزی‌ست برای یاد اهل‌بیت علیهم‌السلام 💛")


def build_message():
    shamsi = get_shamsi_date()
    hijri = get_hijri_date()
    hijri_day, hijri_month = hijri.split(" ")

    event = get_shia_event(hijri_day, hijri_month)
    fajr, dhuhr, maghrib = get_prayer_times_qom()
    temp, desc = get_weather_qom()

    text = (
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
    return text


# ---------- /start ----------
async def start(update, context):
    chat_id = update.message.chat_id
    add_subscriber(chat_id)
    await update.message.reply_text(
        "از این به بعد هر شب ساعت ۱۲ شب گزارش کامل روز برات میاد 🌙✨"
    )


# ---------- کار شبانه ----------
async def nightly_job(context):
    subs = get_subscribers()
    if not subs:
        return

    msg = build_message()

    for chat_id in subs:
        try:
            await context.bot.send_message(chat_id, msg)
        except:
            pass


# ---------- اجرای ربات ----------
def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    app.job_queue.run_daily(
        nightly_job,
        time=datetime.time(0, 0, tzinfo=tehran_tz)
    )

    app.run_polling()


if __name__ == "__main__":
    main()
