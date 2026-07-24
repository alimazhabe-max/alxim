import os
import asyncio
import datetime
import logging
import threading

import pytz
import psycopg2
import requests

from flask import Flask

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)

# ==========================================================
# LOGGING
# ==========================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# ==========================================================
# ENV VARIABLES
# ==========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEATHER_KEY = os.getenv("WEATHER_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

POSTER_URL = os.getenv(
    "POSTER_URL",
    "https://images.unsplash.com/photo-1519817650390-64a93db511aa"
)

PORT = int(os.getenv("PORT", 8080))

tehran_tz = pytz.timezone("Asia/Tehran")

# ==========================================================
# CACHE
# ==========================================================

CACHE = {
    "prayer": {},
    "weather": {},
    "date": {},
    "hijri": {}
}

CACHE_TTL_SECONDS = 600

# ==========================================================
# DATABASE
# ==========================================================

def get_db():
    return psycopg2.connect(DATABASE_URL)


def init_db():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscribers(
        chat_id BIGINT PRIMARY KEY,
        city TEXT DEFAULT 'Qom',
        is_vip BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW()
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

    logger.info("Database initialized")


def add_subscriber(chat_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO subscribers(chat_id)
        VALUES(%s)
        ON CONFLICT(chat_id)
        DO NOTHING
        """,
        (chat_id,)
    )

    conn.commit()

    cur.close()
    conn.close()


def remove_subscriber(chat_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM subscribers WHERE chat_id=%s",
        (chat_id,)
    )

    conn.commit()

    cur.close()
    conn.close()


def set_city(chat_id, city):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE subscribers
        SET city=%s
        WHERE chat_id=%s
        """,
        (city, chat_id)
    )

    conn.commit()

    cur.close()
    conn.close()


def set_vip(chat_id, is_vip=True):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE subscribers
        SET is_vip=%s
        WHERE chat_id=%s
        """,
        (is_vip, chat_id)
    )

    conn.commit()

    cur.close()
    conn.close()


def get_subscribers():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        chat_id,
        city,
        is_vip
    FROM subscribers
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "chat_id": row[0],
            "city": row[1],
            "is_vip": row[2]
        }
        for row in rows
    ]


def get_stats():

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM subscribers"
    )

    total_users = cur.fetchone()[0]

    cur.execute(
        """
        SELECT COUNT(*)
        FROM subscribers
        WHERE is_vip=TRUE
        """
    )

    vip_users = cur.fetchone()[0]

    cur.close()
    conn.close()

    return {
        "total": total_users,
        "vip": vip_users
    }

# ==========================================================
# CACHE HELPERS
# ==========================================================

def cache_get(section, key):

    now = datetime.datetime.now().timestamp()

    item = CACHE.get(section, {}).get(key)

    if not item:
        return None

    value, ts = item

    if now - ts > CACHE_TTL_SECONDS:
        return None

    return value


def cache_set(section, key, value):

    now = datetime.datetime.now().timestamp()

    if section not in CACHE:
        CACHE[section] = {}

    CACHE[section][key] = (
        value,
        now
    )
# ====================== کش و API ======================
def cache_get(section, key):
    now = datetime.datetime.now().timestamp()
    item = CACHE.get(section, {}).get(key)
    if not item:
        return None
    value, ts = item
    if now - ts > CACHE_TTL_SECONDS:
        return None
    return value

def cache_set(section, key, value):
    now = datetime.datetime.now().timestamp()
    if section not in CACHE:
        CACHE[section] = {}
    CACHE[section][key] = (value, now)

def safe_request(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"API request failed: {e}")
        return None

def get_prayer_times(city):
    key = city.lower()
    cached = cache_get("prayer", key)
    if cached:
        return cached

    data = safe_request(
        "https://api.aladhan.com/v1/timingsByCity",
        {"city": city, "country": "Iran", "method": 14}
    )
    if data and "data" in data:
        t = data["data"]["timings"]
        result = (
            t.get("Fajr", "?"),
            t.get("Dhuhr", "?"),
            t.get("Maghrib", "?"),
            t.get("Isha", "?")
        )
    else:
        result = ("?", "?", "?", "?")

    cache_set("prayer", key, result)
    return result

def get_weather(city):
    key = city.lower()
    cached = cache_get("weather", key)
    if cached:
        return cached

    data = safe_request(
        "https://api.openweathermap.org/data/2.5/weather",
        {"q": f"{city},IR", "appid": WEATHER_KEY, "units": "metric", "lang": "fa"}
    )
    if data:
        result = (data["main"]["temp"], data["weather"][0]["description"])
    else:
        result = ("N/A", "نامشخص")

    cache_set("weather", key, result)
    return result

def get_shamsi_date():
    cached = cache_get("date", "today")
    if cached:
        return cached

    data = safe_request("https://api.keybit.ir/date/")
    result = data["date"]["full"]["official"] if data else "نامشخص"
    cache_set("date", "today", result)
    return result

def get_hijri_date():
    cached = cache_get("hijri", "today")
    if cached:
        return cached

    today = datetime.datetime.now(tehran_tz).strftime("%Y-%m-%d")
    data = safe_request(f"https://api.aladhan.com/v1/gToH?date={today}")
    if data and "data" in data:
        h = data["data"]["hijri"]
        result = (f"{h['day']} {h['month']['ar']} {h['year']}", h['day'], h['month']['ar'])
    else:
        result = ("نامشخص", "?", "?")

    cache_set("hijri", "today", result)
    return result

# ====================== مناسبت‌ها و ذکر ======================
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
def build_message_text(city, is_vip=False):
    try:
        shamsi = get_shamsi_date()
        hijri, hijri_day, hijri_month = get_hijri_date()
        event = get_shia_event(hijri_day, hijri_month)
        fajr, dhuhr, maghrib, isha = get_prayer_times(city)
        temp, desc = get_weather(city)
    except Exception as e:
        logger.error(f"Build message failed: {e}")
        shamsi = "نامشخص"
        hijri = "نامشخص"
        event = "روز خوبی برای دعا و توسل به اهل‌بیت علیهم‌السلام"
        fajr = dhuhr = maghrib = isha = "?"
        temp, desc = "N/A", "نامشخص"

    dhikr = get_daily_dhikr()

    vip_line = ""
    if is_vip:
        vip_line = "⭐ گزارش ویژهٔ VIP برای شما آماده شد.\n\n"

    return (
        "✨ گزارش شبانه شیعی ✨\n\n"
        f"{vip_line}"
        "📂 بخش تاریخ:\n"
        f"• شمسی: {shamsi}\n"
        f"• قمری: {hijri}\n"
        f"• مناسبت: {event}\n\n"
        "🕌 بخش اوقات شرعی:\n"
        f"• شهر: {city}\n"
        f"• فجر: {fajr}\n"
        f"• ظهر: {dhuhr}\n"
        f"• مغرب: {maghrib}\n"
        f"• عشاء: {isha}\n\n"
        "🌤 بخش آب و هوا:\n"
        f"• دما: {temp}°C\n"
        f"• وضعیت: {desc}\n\n"
        "💬 بخش ذکر روز:\n"
        f"• {dhikr}\n\n"
        "اللهم عجل لولیک الفرج 💛"
    )

# ====================== هندلرهای اصلی ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    add_subscriber(chat_id)

    keyboard = [
        [InlineKeyboardButton("🏙 انتخاب شهر", callback_data="menu_city")],
        [InlineKeyboardButton("⭐ تنظیم VIP", callback_data="menu_vip")],
        [InlineKeyboardButton("📨 گزارش تستی", callback_data="menu_test")],
    ]
    await update.message.reply_text(
        "✅ ثبت شد!\nهر شب ساعت ۱۲ گزارش برات ارسال می‌شه.\n"
        "از دکمه‌های زیر استفاده کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    remove_subscriber(update.effective_chat.id)
    await update.message.reply_text("❌ از لیست دریافت گزارش حذف شدید.")

async def nightly_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("اجرای گزارش شبانه...")
    subs = get_subscribers()
    if not subs:
        return

    for s in subs:
        chat_id = s["chat_id"]
        city = s["city"]
        is_vip = s["is_vip"]
        try:
            msg = build_message_text(city, is_vip)
            await context.bot.send_message(chat_id=chat_id, text=msg)
            await context.bot.send_photo(chat_id=chat_id, photo=POSTER_URL)
        except Exception as e:
            logger.warning(f"Failed to send to {chat_id}: {e}")

# ====================== منوی شهر (اینلاین) ======================
async def choose_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("قم", callback_data="city_Qom")],
        [InlineKeyboardButton("تهران", callback_data="city_Tehran")],
        [InlineKeyboardButton("مشهد", callback_data="city_Mashhad")],
        [InlineKeyboardButton("شیراز", callback_data="city_Shiraz")],
    ]
    await update.message.reply_text(
        "🏙 شهر مورد نظر را انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def city_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    city = query.data.replace("city_", "")
    set_city(chat_id, city)

    await query.edit_message_text(f"✅ شهر شما روی «{city}» تنظیم شد.")

# ====================== منوی VIP (اینلاین) ======================
async def vip_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⭐ فعال کردن VIP", callback_data="vip_on")],
        [InlineKeyboardButton("❌ غیرفعال کردن VIP", callback_data="vip_off")],
    ]
    await update.message.reply_text(
        "وضعیت VIP را انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def vip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id

    if query.data == "vip_on":
        set_vip(chat_id, True)
        await query.edit_message_text("⭐ VIP فعال شد.")
    else:
        set_vip(chat_id, False)
        await query.edit_message_text("❌ VIP غیرفعال شد.")

# ====================== منوی تست گزارش (اینلاین) ======================
async def test_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📨 دریافت گزارش تستی", callback_data="test_report")]
    ]
    await update.message.reply_text(
        "برای تست گزارش دکمه زیر را بزن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def test_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    subs = get_subscribers()
    user = next((s for s in subs if s["chat_id"] == chat_id), None)

    if not user:
        await query.edit_message_text("❗ اول /start را بزن تا ثبت شوی.")
        return

    city = user["city"]
    is_vip = user["is_vip"]

    msg = build_message_text(city, is_vip)

    await query.edit_message_text("📨 گزارش تستی:\n\n" + msg)
    await query.message.reply_photo(POSTER_URL)

# ====================== پنل مدیریت (اینلاین) ======================
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("⛔ فقط مدیر می‌تواند وارد پنل شود.")
        return

    keyboard = [
        [InlineKeyboardButton("👥 تعداد اعضا", callback_data="admin_count")],
        [InlineKeyboardButton("⭐ VIP ها", callback_data="admin_vip")],
        [InlineKeyboardButton("🏙 شهرها", callback_data="admin_cities")],
    ]

    await update.message.reply_text(
        "🛠 پنل مدیریت:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.message.chat_id != ADMIN_ID:
        await query.edit_message_text("⛔ فقط مدیر می‌تواند این دکمه‌ها را استفاده کند.")
        return

    subs = get_subscribers()

    if query.data == "admin_count":
        await query.edit_message_text(f"👥 تعداد اعضا: {len(subs)}")

    elif query.data == "admin_vip":
        vip_count = sum(1 for s in subs if s["is_vip"])
        await query.edit_message_text(f"⭐ تعداد VIP: {vip_count}")

    elif query.data == "admin_cities":
        cities = {}
        for s in subs:
            cities[s["city"]] = cities.get(s["city"], 0) + 1
        text = "\n".join([f"• {c}: {n} نفر" for c, n in cities.items()]) or "هیچ شهری ثبت نشده."
        await query.edit_message_text("🏙 توزیع شهرها:\n" + text)

# ====================== منوی اصلی اینلاین ======================
async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "menu_city":
        # باز کردن منوی شهر
        fake_update = Update(
            update.update_id,
            message=query.message
        )
        await choose_city(fake_update, context)

    elif data == "menu_vip":
        fake_update = Update(
            update.update_id,
            message=query.message
        )
        await vip_menu(fake_update, context)

    elif data == "menu_test":
        fake_update = Update(
            update.update_id,
            message=query.message
        )
        await test_menu(fake_update, context)

# ====================== Flask ======================
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Nightly Shia Report Bot is running with cache, VIP, multi-city & inline buttons!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

# ====================== اجرا ======================
def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # دستورات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("admin", admin_menu))

    # اینلاین منو اصلی
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^menu_"))

    # اینلاین شهر
    app.add_handler(CallbackQueryHandler(city_callback, pattern="^city_"))

    # اینلاین VIP
    app.add_handler(CallbackQueryHandler(vip_callback, pattern="^vip_"))

    # اینلاین تست
    app.add_handler(CallbackQueryHandler(test_callback, pattern="^test_"))

    # اینلاین پنل مدیریت
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))

    # JobQueue
    app.job_queue.run_daily(
        nightly_job,
        time=datetime.time(0, 0, tzinfo=tehran_tz)
    )

    threading.Thread(target=run_flask, daemon=True).start()

    app.run_polling()

if __name__ == "__main__":
    main()
