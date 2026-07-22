import os
import datetime
import pytz
import asyncio
import aiohttp
import sqlite3
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEATHER_KEY = os.getenv("WEATHER_KEY")

tehran_tz = pytz.timezone("Asia/Tehran")
DB_PATH = "data.db"

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

# ---------- APIهای async ----------
async def get_weather_qom():
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.openweathermap.org/data/2.5/weather?q=Qom,IR&appid={WEATHER_KEY}&units=metric"
            async with session.get(url) as resp:
                data = await resp.json()
                temp = data["main"]["temp"]
                desc = data["weather"][0]["description"]
                return temp, desc
    except:
        return "N/A", "نامشخص"

async def get_prayer_times_qom():
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.aladhan.com/v1/timingsByCity?city=Qom&country=Iran&method=14"
            async with session.get(url) as resp:
                data = await resp.json()
                t = data["data"]["timings"]
                return t["Fajr"], t["Dhuhr"], t["Maghrib"]
    except:
        return "N/A", "N/A", "N/A"

async def get_shamsi_date():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.keybit.ir/date/") as resp:
                data = await resp.json()
                return data["date"]["full"]["official"]
    except:
        return "نامشخص"

async def get_hijri_date():
    try:
        today = datetime.datetime.now(tehran_tz).strftime("%Y-%m-%d")
        async with aiohttp.ClientSession() as session:
            url = f"https://api.aladhan.com/v1/gToH?date={today}"
            async with session.get(url) as resp:
                data = await resp.json()
                h = data["data"]["hijri"]
                return f"{h['day']} {h['month']['ar']}"
    except:
        return "نامشخص"

# ---------- ساخت پیام ----------
async def build_message():
    shamsi = await get_shamsi_date()
    hijri = await get_hijri_date()
    
    # استخراج روز و ماه قمری
    try:
        hijri_day, hijri_month = hijri.split(" ")
    except:
        hijri_day, hijri_month = "??", "??"

    # مناسبت‌ها
    events = {
        ("18", "ذی الحجه"): "عید غدیر خم 💛",
        ("10", "محرم"): "روز عاشورا 💔",
        ("20", "صفر"): "اربعین حسینی",
    }
    event = events.get((hijri_day, hijri_month), "یاد اهل‌بیت علیهم‌السلام 💛")

    fajr, dhuhr, maghrib = await get_prayer_times_qom()
    temp, desc = await get_weather_qom()

    text = (
        "✨ گزارش شبانه قم ✨\n\n"
        f"📅 تاریخ شمسی: {shamsi}\n"
        f"📆 تاریخ قمری: {hijri}\n"
        f"🕊 مناسبت امروز: {event}\n\n"
        "🕌 اوقات شرعی قم:\n"
        f"• اذان صبح: {fajr}\n"
        f"• اذان ظهر: {dhuhr}\n"
        f"• اذان مغرب: {maghrib}\n\n"
        "🌤 آب و هوای قم:\n"
        f"• دما: {temp}°C\n"
        f"• وضعیت: {desc}\n\n"
        "اللهم عجل لولیک الفرج 💛"
    )
    return text

# ---------- هندلرها ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    add_subscriber(chat_id)
    await update.message.reply_text(
        "✅ ثبت شد!\nاز این به بعد هر شب ساعت ۱۲ گزارش کامل برات میاد 🌙"
    )

async def nightly_job(context: ContextTypes.DEFAULT_TYPE):
    subs = get_subscribers()
    if not subs:
        return

    msg = await build_message()
    for chat_id in subs:
        try:
            await context.bot.send_message(chat_id, msg)
        except Exception as e:
            print(f"Failed to send to {chat_id}: {e}")

# ---------- Flask ----------
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "✅ Nightly Bot is alive!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

# ---------- اجرا ----------
def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN تنظیم نشده!")
        return
    if not WEATHER_KEY:
        print("⚠️ WEATHER_KEY تنظیم نشده!")

    init_db()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    # job شبانه ساعت ۰۰:۰۰ به وقت تهران
    application.job_queue.run_daily(
        nightly_job,
        time=datetime.time(0, 0, tzinfo=tehran_tz),
        name="nightly_report"
    )

    print("🤖 ربات گزارش شبانه راه‌اندازی شد...")
    application.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
