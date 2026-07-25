import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import jdatetime
from jdatetime import timedelta
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import random
import asyncio
from hijri_converter import Gregorian
from datetime import datetime
import sqlite3
import pytz

# ============================================================
# دیکشنری‌های فارسی برای تاریخ
# ============================================================
PERSIAN_MONTHS = {
    1: "فروردین", 2: "اردیبهشت", 3: "خرداد", 4: "تیر",
    5: "مرداد", 6: "شهریور", 7: "مهر", 8: "آبان",
    9: "آذر", 10: "دی", 11: "بهمن", 12: "اسفند"
}

PERSIAN_WEEKDAYS = {
    0: "شنبه", 1: "یکشنبه", 2: "دوشنبه", 3: "سه‌شنبه",
    4: "چهارشنبه", 5: "پنجشنبه", 6: "جمعه"
}

# ============================================================
# 1. تنظیمات اولیه
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("متغیر BOT_TOKEN در محیط تنظیم نشده است!")

ADMIN_IDS = [int(id.strip()) for id in os.environ.get("ADMIN_IDS", "").split(",") if id.strip()]

# ⚠️ آیدی عددی کانال را اینجا قرار دهید (با -100 شروع می‌شود)
# برای پیدا کردن آیدی کانال، ربات خود را به کانال اضافه کنید و پیامی بفرستید
# سپس در لاگ‌های Render یا با دستور /id در ربات پیدا کنید
REQUIRED_CHANNEL_ID = -1004385593103  # ← این را با آیدی واقعی کانال جایگزین کنید
REQUIRED_CHANNEL_LINK = "https://t.me/HmHermi"

loop = asyncio.new_event_loop()

def get_today_tehran():
    tehran_tz = pytz.timezone('Asia/Tehran')
    now = datetime.now(tehran_tz)
    return jdatetime.datetime.fromgregorian(datetime=now).date()

# ============================================================
# 2. دیتابیس (SQLite)
# ============================================================
DB_PATH = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        city TEXT DEFAULT 'قم',
        language TEXT DEFAULT 'fa',
        subscribed INTEGER DEFAULT 1,
        register_date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        total_users INTEGER,
        active_users INTEGER
    )''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result

def save_user(user_id, first_name, city="قم", language="fa"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO users 
        (user_id, first_name, city, language, subscribed, register_date)
        VALUES (?, ?, ?, ?, 1, datetime('now'))''',
        (user_id, first_name, city, language))
    conn.commit()
    conn.close()

def update_user_city(user_id, city):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET city = ? WHERE user_id = ?", (city, user_id))
    conn.commit()
    conn.close()

def update_user_language(user_id, language):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, city, language FROM users WHERE subscribed = 1")
    result = c.fetchall()
    conn.close()
    return result

def get_user_city(user_id):
    user = get_user(user_id)
    if user:
        return user[2]
    return "قم"

def get_user_language(user_id):
    user = get_user(user_id)
    if user:
        return user[3]
    return "fa"

# ============================================================
# 3. چندزبانه
# ============================================================
TEXTS = {
    "fa": {
        "welcome": "🌟 سلام {name} عزیز! 🌟",
        "prayer": "⏰ **اوقات شرعی امروز ({city}):**",
        "weather": "🌦️ **آب و هوای {city}:**",
        "motivation": "💖 **پیام انگیزشی روز:**",
        "change_city": "🔔 برای تغییر شهر، از دکمه‌های زیر استفاده کن.",
        "city_changed": "✅ شهر شما به **{city}** تغییر کرد.",
        "city_not_found": "❌ شهر '{city}' پیدا نشد.",
        "help": "🤖 **راهنمای ربات:**\n\n"
                "/start - نمایش اطلاعات امروز\n"
                "/city [نام شهر] - تغییر شهر\n"
                "/language - تغییر زبان\n"
                "/calendar - مشاهده تقویم تعاملی\n"
                "/stats - آمار ربات (فقط ادمین)\n"
                "/broadcast [پیام] - ارسال همگانی (فقط ادمین)",
        "language_changed": "✅ زبان شما به **{lang}** تغییر کرد.",
        "no_events": "هیچ مناسبت خاصی ثبت نشده است.",
        "admin_only": "❌ این دستور فقط برای ادمین‌ها قابل استفاده است.",
        "broadcast_sent": "✅ پیام به {count} کاربر ارسال شد.",
        "stats": "📊 **آمار ربات:**\n\n"
                 "👥 تعداد کل کاربران: {total}\n"
                 "📅 کاربران فعال امروز: {active}",
        "calendar_title": "📅 **تقویم {month} {year}**\n\n",
        "calendar_today": "📌 امروز: {date}",
        "calendar_event": "• {event}",
        "not_member": "❌ برای استفاده از این ربات، ابتدا در کانال زیر عضو شوید:\n{channel_link}\n\nپس از عضویت، دوباره `/start` را بفرستید.",
    },
    "en": {
        "welcome": "🌟 Hello dear {name}! 🌟",
        "prayer": "⏰ **Prayer Times ({city}):**",
        "weather": "🌦️ **Weather in {city}:**",
        "motivation": "💖 **Daily Motivation:**",
        "change_city": "🔔 Use the buttons below to change city.",
        "city_changed": "✅ Your city has been changed to **{city}**.",
        "city_not_found": "❌ City '{city}' not found.",
        "help": "🤖 **Bot Commands:**\n\n"
                "/start - Show today's info\n"
                "/city [city name] - Change city\n"
                "/language - Change language\n"
                "/calendar - Interactive calendar\n"
                "/stats - Bot stats (admin only)\n"
                "/broadcast [message] - Broadcast (admin only)",
        "language_changed": "✅ Your language has been changed to **{lang}**.",
        "no_events": "No specific events recorded.",
        "admin_only": "❌ This command is for admins only.",
        "broadcast_sent": "✅ Message sent to {count} users.",
        "stats": "📊 **Bot Stats:**\n\n"
                 "👥 Total users: {total}\n"
                 "📅 Active users today: {active}",
        "calendar_title": "📅 **Calendar {month} {year}**\n\n",
        "calendar_today": "📌 Today: {date}",
        "calendar_event": "• {event}",
        "not_member": "❌ To use this bot, please join the channel below first:\n{channel_link}\n\nAfter joining, send `/start` again.",
    },
    "ar": {
        "welcome": "🌟 مرحباً عزيزي {name}! 🌟",
        "prayer": "⏰ **أوقات الصلاة اليوم ({city}):**",
        "weather": "🌦️ **الطقس في {city}:**",
        "motivation": "💖 **رسالة تحفيزية اليوم:**",
        "change_city": "🔔 استخدم الأزرار أدناه لتغيير المدينة.",
        "city_changed": "✅ تم تغيير مدينتك إلى **{city}**.",
        "city_not_found": "❌ المدينة '{city}' غير موجودة.",
        "help": "🤖 **تعليمات البوت:**\n\n"
                "/start - عرض معلومات اليوم\n"
                "/city [اسم المدينة] - تغيير المدينة\n"
                "/language - تغيير اللغة\n"
                "/calendar - تقويم تفاعلي\n"
                "/stats - إحصائيات البوت (للمشرفين)\n"
                "/broadcast [رسالة] - إرسال جماعي (للمشرفين)",
        "language_changed": "✅ تم تغيير لغتك إلى **{lang}**.",
        "no_events": "لا توجد مناسبات خاصة مسجلة.",
        "admin_only": "❌ هذا الأمر مخصص للمشرفين فقط.",
        "broadcast_sent": "✅ تم إرسال الرسالة إلى {count} مستخدم.",
        "stats": "📊 **إحصائيات البوت:**\n\n"
                 "👥 إجمالي المستخدمين: {total}\n"
                 "📅 المستخدمين النشطين اليوم: {active}",
        "calendar_title": "📅 **تقويم {month} {year}**\n\n",
        "calendar_today": "📌 اليوم: {date}",
        "calendar_event": "• {event}",
        "not_member": "❌ لاستخدام هذا البوت، يرجى الانضمام إلى القناة أدناه أولاً:\n{channel_link}\n\nبعد الانضمام، أرسل `/start` مرة أخرى.",
    }
}

def get_text(user_id, key, **kwargs):
    lang = get_user_language(user_id)
    text = TEXTS.get(lang, TEXTS["fa"]).get(key, TEXTS["fa"].get(key, key))
    return text.format(**kwargs) if kwargs else text

# ============================================================
# 4. توابع API و تاریخ
# ============================================================
def retry_request(url, timeout=5, retries=2):
    for i in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                return response
        except:
            pass
    return None

def get_prayer_times(city, country="Iran"):
    try:
        url = f"https://api.aladhan.com/v1/timingsByCity?city={city}&country={country}&method=8"
        response = retry_request(url)
        if not response:
            return None
        data = response.json()
        timings = data["data"]["timings"]
        return {
            "اذان صبح": timings["Fajr"],
            "طلوع آفتاب": timings["Sunrise"],
            "اذان ظهر": timings["Dhuhr"],
            "اذان عصر": timings["Asr"],
            "اذان مغرب": timings["Maghrib"],
            "اذان عشاء": timings["Isha"],
        }
    except:
        return None

def get_weather(city):
    try:
        url = f"https://wttr.in/{city}?format=j1"
        response = retry_request(url)
        if not response:
            return None
        data = response.json()
        current = data["current_condition"][0]
        condition = current["weatherDesc"][0]["value"]
        return {
            "دما": f"{current['temp_C']}°C",
            "وضعیت": condition,
            "رطوبت": f"{current['humidity']}%",
        }
    except:
        return None

def get_hijri_date(g_date):
    try:
        from datetime import timedelta as dt_timedelta
        g_date_adjusted = g_date - dt_timedelta(days=1)
        hijri = Gregorian(g_date_adjusted.year, g_date_adjusted.month, g_date_adjusted.day).to_hijri()
        hijri_months = {
            1: "محرم", 2: "صفر", 3: "ربیع‌الاول", 4: "ربیع‌الثانی",
            5: "جمادی‌الاول", 6: "جمادی‌الثانی", 7: "رجب", 8: "شعبان",
            9: "رمضان", 10: "شوال", 11: "ذی‌قعده", 12: "ذی‌الحجه"
        }
        return {
            "day": hijri.day,
            "month": hijri.month,
            "month_name": hijri_months[hijri.month],
            "year": hijri.year,
            "full": f"{hijri.day} {hijri_months[hijri.month]} {hijri.year}"
        }
    except:
        return {"day": 0, "month": 0, "month_name": "نامشخص", "year": 0, "full": "نامشخص"}

# ============================================================
# 5. دیکشنری کامل رویدادهای قمری (تمام روزها - خلاصه شده)
# ============================================================
hijri_events = {
    "1-1": ["آغاز سال هجرى قمرى", "يورش ابرهه به مكه", "آغاز ایام حسینی"],
    "1-2": ["درگذشت حضرت آدم(ع)", "ورود امام حسين به كربلا"],
    "1-3": ["نجات یوسف از زندان", "ورود عمر بن سعد به كربلا"],
    "1-4": ["سخنرانی عبیدالله بن زیاد", "شهادت قیس بن مسهر"],
    "1-5": ["عبور حضرت موسى از دریا", "ولادت میرحامد حسین هندی"],
    "1-6": ["شهادت حضرت یحیى", "درگذشت سید رضى"],
    "1-7": ["مبعوث شدن حضرت موسى", "بستن آب بر اهل بیت"],
    "1-8": ["ديدار امام حسين با عمر بن سعد", "قحط آب در كاروان"],
    "1-9": ["رهائى حضرت یونس", "ورود شمر به كربلا"],
    "1-10": ["شهادت امام حسین (ع)", "قیام حضرت مهدی (عج)"],
    "1-11": ["اسارت بازماندگان شهداي كربلا", "حرکت کاروان اسرا"],
    "1-12": ["ورود اهل بیت به کوفه", "شهادت امام سجاد"],
    "1-13": ["تدفين پيكرهاي شهيدان كربلا", "اسراى اهل بیت در مجلس ابن زیاد"],
    "1-14": ["نامه نوشتن ابن زیاد به یزید"],
    "1-15": ["آغاز غزوه خيبر", "ولادت سید بن طاووس"],
    "1-16": ["هجوم مسلمانان به دمشق", "تدوين تاريخ اسلامى"],
    "1-17": ["نزول عذاب بر اصحاب فیل"],
    "1-19": ["حركت كاروان اسرا به شام", "درگذشت حسن بن بویه"],
    "1-20": ["دفن بدن جون، غلام امام حسين"],
    "1-21": ["درگذشت علامه حلى"],
    "1-22": ["ورود امیرالمؤمنین به صفين", "درگذشت شیخ طوسی"],
    "1-23": ["آگاهى اصحاب کهف", "مرگ مهدي عباسي"],
    "1-25": ["شهادت امام سجاد", "كشته شدن امين"],
    "1-26": ["محاصره و سنگباران مكه", "شهادت علي بن حسن مثلث"],
    "1-27": ["لشكركشي مأمون عباسي"],
    "1-28": ["درگذشت حذیفه بن یمان", "انقراض حکومت عباسی"],
    "1-29": ["ورود كاروان اسرا به شام", "تصرف قم توسط قوای روسیه"],
    "1-30": ["درگذشت ماريه قبطيه", "قتل جعفر بن يحيي برمكي"],
    "2-1": ["وارد کردن سر مطهر امام حسین به شام", "ورود اهل بیت به شام", "شروع جنگ صفین"],
    "2-2": ["مجلس یزید", "شهادت زید بن علی"],
    "2-5": ["شهادت حضرت رقیه"],
    "2-7": ["شهادت امام مجتبی"],
    "2-8": ["وفات حضرت سلمان"],
    "2-9": ["شهادت عمار و خزیمه", "جنگ نهروان"],
    "2-11": ["لیله الهریر در جنگ صفین"],
    "2-12": ["حکمین در صفین"],
    "2-14": ["شهادت محمد بن ابی بکر"],
    "2-15": ["ابتدای بیماری پیامبر"],
    "2-17": ["شهادت امام رضا"],
    "2-20": ["اربعین سید الشهداء", "زیارت جابر از کربلا"],
    "2-24": ["طلب کتف و دوات توسط پیامبر"],
    "2-25": ["دستور پیامبر به پیروی از ثقلین"],
    "2-26": ["تجهیز لشکر اسامه"],
    "2-28": ["شهادت رسول خدا", "آغاز امامت امیر المومنین", "آغاز غصب خلافت", "شهادت امام حسن مجتبی"],
    "3-1": ["دفن بدن مطهر پیامبر", "هجرت رسول خدا", "ليلة المبيت", "هجوم به خانه وحی"],
    "3-3": ["احتجاج سلمان فارسي", "تخريب كعبه توسط يزيد"],
    "3-4": ["خروج پیامبر از غار ثور"],
    "3-5": ["وفات حضرت سكينه"],
    "3-6": ["ولادت مولانا جلال الدین رومی"],
    "3-8": ["شهادت امام حسن عسکری"],
    "3-9": ["مرگ عمر بن سعد", "آغاز امامت حضرت ولى عصر"],
    "3-10": ["درگذشت حضرت لوط", "رحلت عبدالمطلب", "ازدواج پیامبر با خديجه"],
    "3-11": ["ولادت امام رضا"],
    "3-12": ["ولادت پیامبر به روایت اهل سنت", "ورود پیامبر به مدينه", "قيام مختار"],
    "3-14": ["مرگ يزيد بن معاويه", "خلافت هارون الرشيد"],
    "3-15": ["بنای مسجد قبا"],
    "3-16": ["درگذشت مسعودی"],
    "3-17": ["ولادت پیامبر", "زادروز امام جعفر صادق"],
    "3-20": ["قتل جالوت به دست داود"],
    "3-22": ["غزوه بنی نضیر"],
    "3-23": ["ورود حضرت معصومه به قم"],
    "3-25": ["غزوه دومه الجندل", "صلح امام حسن مجتبى"],
    "3-26": ["درگذشت ابن سماک"],
    "3-28": ["شکست ایرانیان از اعراب"],
    "4-1": ["قیام توابین", "شهادت امام باقر"],
    "4-2": ["قتل عبدالله بن معتز"],
    "4-3": ["پيمان شكنى امين", "سفر امام عسکری به جرجان"],
    "4-4": ["غزوه غابه", "ولادت عبد العظیم حسنی"],
    "4-5": ["خلافت مستعين عباسى"],
    "4-6": ["مرگ هشام بن عبدالملک"],
    "4-8": ["شهادت حضرت فاطمه", "ميلاد امام حسن عسكرى"],
    "4-10": ["وفات حضرت معصومه", "تخریب گنبد حرم امام رضا"],
    "4-12": ["اضافه شدن ركعات نماز"],
    "4-13": ["شهادت حضرت زهرا"],
    "4-14": ["قیام مختار"],
    "4-27": ["درگذشت عبدالمطلب", "تخریب دو گلدسته حرم عسکریین"],
    "4-29": ["آغاز حکومت شاه اسماعیل اول"],
    "4-30": ["وفات زينب بنت خزيمه", "مرگ خالد بن ولید"],
    "5-1": ["میلاد حضرت زینب", "جنگ موته"],
    "5-5": ["میلاد حضرت زینب"],
    "5-10": ["كشته شدن خسرو پرويز", "آغاز جنگ جمل"],
    "5-13": ["شهادت حضرت فاطمه زهرا"],
    "5-15": ["ميلاد امام زين العابدين"],
    "5-16": ["قتل عبدالله بن زبير"],
    "5-17": ["ولادت ذوالقرنین"],
    "5-22": ["نبرد توابين", "وفات قاسم بن موسی"],
    "5-27": ["درگذشت عبدالمطلب"],
    "7-1": ["ولادت امام محمد باقر", "زیارت امام حسین"],
    "7-2": ["ولادت امام علی النقی"],
    "7-3": ["ولادت امام هادی", "شهادت ایشان"],
    "7-5": ["ولادت امام موسی بن جعفر"],
    "7-7": ["طلب امام رضا برای ولیعهدی"],
    "7-8": ["هلاکت مامون عباسی"],
    "7-9": ["ولادت حضرت علی اصغر"],
    "7-10": ["ولادت امام محمد جواد"],
    "7-12": ["شکافته شدن دیوار کعبه", "مرگ معاویه", "ورود امیر المومنین به کوفه"],
    "7-13": ["ولادت امیر المومنین علی"],
    "7-14": ["ولادت امیر المومنین علی"],
    "7-15": ["ولادت امیر المومنین علی", "شهادت حضرت زینب", "تغییر قبله", "شهادت امام صادق"],
    "7-16": ["خروج فاطمه بنت اسد از کعبه"],
    "7-17": ["مرگ مامون"],
    "7-18": ["رحلت ابراهیم فرزند رسول خدا", "ورود امام رضا به نیشابور"],
    "7-19": ["وفات شاه اسماعیل صفوی"],
    "7-21": ["شهادت حضرت زهرا"],
    "7-22": ["فرار ابوبکر در جنگ خیبر"],
    "7-23": ["مجروح شدن امام حسن", "مسموم شدن امام موسی بن جعفر"],
    "7-24": ["فتح خیبر به دست امیر المومنین", "بازگشت جعفر طیار"],
    "7-25": ["شهادت امام موسی بن جعفر"],
    "7-26": ["رحلت حضرت ابوطالب"],
    "7-27": ["عید مبعث"],
    "7-28": ["شهادت امام موسی بن جعفر روز سوم"],
    "7-29": ["رحلت حضرت خدیجه", "حرکت امام حسین به سوی کربلا"],
    "7-30": ["اولین اقامه نماز در اسلام"],
    "8-1": ["آغاز وجوب روزه", "تولد حضرت زینب کبری"],
    "8-2": ["مرگ معتز عباسی"],
    "8-3": ["ولادت امام حسین", "ورود امام حسین به مکه"],
    "8-4": ["ولادت حضرت عباس"],
    "8-5": ["ولادت امام زین العابدین"],
    "8-10": ["توقیع امام زمان برای شیعیان"],
    "8-11": ["ولادت علی اکبر"],
    "8-15": ["ولادت حضرت بقیه الله الاعظم", "وفات علی بن محمد سمری"],
    "8-16": ["رحلت آخرین نائب خاص امام زمان"],
    "8-18": ["وفات حسین بن روح نوبختی"],
    "8-19": ["جنگ بنی المصطلق"],
    "8-22": ["ولادت رقیه خاتون"],
    "8-23": ["وفات ناصر کبیر"],
    "8-25": ["هلاکت ابو مسلم خراسانی"],
    "8-27": ["شهادت سعید بن جبیر"],
    "8-29": ["روزه ماه مبارک رمضان"],
    "9-1": ["نزول صحف ابراهیم", "غزوه تبوک"],
    "9-2": ["ولایت عهدی امام رضا"],
    "9-3": ["رحلت شیخ مفید", "شهادت حضرت زهرا"],
    "9-4": ["مرگ زیاد بن ابیه"],
    "9-6": ["بیعت با امام رضا", "نزول تورات"],
    "9-10": ["رحلت حضرت زینب", "وفات حضرت خدیجه"],
    "9-12": ["عقد اخوت بین اصحاب", "نزول انجیل"],
    "9-13": ["هلاکت حجاج ثقفی"],
    "9-14": ["شهادت مختار ثقفی"],
    "9-15": ["ولادت امام حسن مجتبی", "حرکت حضرت مسلم به کوفه"],
    "9-16": ["معراج پیامبر"],
    "9-17": ["معراج پیامبر", "جنگ بدر", "فرمان ساختن مسجد جمکران"],
    "9-18": ["نزول زبور"],
    "9-19": ["لیله القدر", "ضربت خوردن امام علی"],
    "9-20": ["شدت بیماری امام علی", "شکستن بتهای کعبه"],
    "9-21": ["لیله القدر", "شهادت امام علی", "عروج حضرت عیسی"],
    "9-23": ["لیله القدر", "شب سوم شهادت امام علی"],
    "9-24": ["مرگ ابو لهب"],
    "9-27": ["شب قدر", "رحلت علامه مجلسی"],
    "9-28": ["وفات میرزا محمد تقی موسوی"],
    "9-30": ["وفات سلطان الجایتو"],
    "10-1": ["عید فطر", "مرگ عمرو بن عاص"],
    "10-2": ["قتل موکل"],
    "10-4": ["جنگ حنین"],
    "10-5": ["حرکت به سوی جنگ صفین"],
    "10-8": ["ویرانی قبور ائمه بقیع"],
    "10-10": ["آغاز غیبت صغری"],
    "10-13": ["رحلت آیت الله بروجردی"],
    "10-15": ["جنگ احد", "رد الشمس", "وفات عبد العظیم"],
    "10-17": ["جنگ خندق"],
    "10-18": ["وفات ادریس حلی"],
    "10-20": ["دستگیری امام کاظم"],
    "10-25": ["شهادت امام صادق"],
    "10-29": ["رحلت امام خمینی"],
    "11-1": ["ولادت حضرت معصومه", "جنگ بدر صغری", "درگذشت ابوطالب"],
    "11-9": ["نامه مسلم بن عقیل"],
    "11-11": ["ولادت امام رضا"],
    "11-12": ["نامه حضرت مسلم"],
    "11-17": ["دستگیری امام کاظم"],
    "11-23": ["شهادت امام رضا", "جنگ بنی قریظه"],
    "11-24": ["حرکت امام رضا به مرو", "روز دحو الارض"],
    "11-25": ["حرکت پیامبر برای حجه الوداع", "آغاز بیان ولایت"],
    "11-28": ["شهادت امام جواد"],
    "11-29": ["صلح حدیبیه"],
    "12-1": ["عزل ابوبکر از تبلیغ سوره برائت"],
    "12-3": ["ورود پیامبر به مکه"],
    "12-5": ["جنگ سویق"],
    "12-6": ["ازدواج امام علی و حضرت زهرا", "مرگ منصور دوانیقی"],
    "12-7": ["شهادت امام باقر", "بردن امام کاظم به زندان"],
    "12-8": ["توطئه ترور امام حسین", "حرکت امام حسین از مکه"],
    "12-9": ["روز عرفه", "شهادت حضرت مسلم"],
    "12-10": ["عید قربان", "شهادت عبد الله محض"],
    "12-11": ["روز نوشتن دعای صباح"],
    "12-13": ["شق القمر"],
    "12-14": ["بخشیدن فدک", "افشاء سر ولایت"],
    "12-15": ["ولادت امام هادی"],
    "12-18": ["عید غدیر", "قتل عثمان", "خلافت ظاهری امیر المومنین"],
    "12-22": ["شهادت میثم تمار"],
    "12-24": ["روز مباهله", "روز خاتم بخشی"],
    "12-25": ["نزول سوره هل اتی", "اولین نماز جمعه امام علی"],
    "12-27": ["مرگ مروان", "واقعه حره"],
    "12-30": ["مرگ پدر ابوبکر", "مرگ هند جگر خوار"]
}

def get_hijri_events(hijri_month, hijri_day):
    key = f"{hijri_month}-{hijri_day}"
    return hijri_events.get(key, ["هیچ مناسبت قمری خاصی ثبت نشده است."])

# ============================================================
# 6. دیکشنری مناسبت‌های شمسی
# ============================================================
shamsi_events = {
    "1-1": ["جشن نوروز", "سال نو"],
    "1-2": ["عید نوروز"],
    "1-3": ["عید نوروز"],
    "1-4": ["عید نوروز"],
    "1-6": ["روز امید", "روز شادباش نویسی", "زادروز آشو زرتشت"],
    "1-7": ["روز جهانی تئاتر"],
    "1-10": ["جشن آبانگاه"],
    "1-12": ["روز جمهوری اسلامی"],
    "1-13": ["جشن سیزده به در"],
    "1-17": ["سروش روز", "جشن سروشگان"],
    "1-18": ["روز جهانی بهداشت"],
    "1-19": ["فروردین روز", "جشن فروردینگان"],
    "1-23": ["روز دندانپزشک"],
    "1-25": ["روز بزرگداشت عطار نیشابوری"],
    "1-29": ["روز ارتش جمهوری اسلامی ایران"],
    "1-30": ["روز علوم آزمایشگاهی", "زاد روز حکیم سید اسماعیل جرجانی"],
    "2-1": ["روز بزرگداشت سعدی"],
    "2-2": ["جشن گیاه آوری", "روز زمین"],
    "2-3": ["روز بزرگداشت شیخ بهایی", "روز ملی کارآفرینی"],
    "2-9": ["روز شوراها", "روز جهانی روانشناس و مشاور"],
    "2-10": ["جشن چهلم نوروز", "روز ملی خلیج فارس"],
    "2-11": ["روز جهانی کارگر"],
    "2-12": ["شهادت استاد مرتضی مطهری", "روز معلم"],
    "2-15": ["جشن میانه بهار", "جشن بهاربد", "روز شیراز", "روز جهانی ماما"],
    "2-17": ["روز اسناد ملی و میراث مکتوب"],
    "2-18": ["روز جهانی صلیب سرخ و هلال احمر"],
    "2-25": ["روز بزرگداشت فردوسی"],
    "2-27": ["روز ارتباطات و روابط عمومی"],
    "2-28": ["روز بزرگداشت حکیم عمر خیام", "روز جهانی موزه و میراث فرهنگی"],
    "3-1": ["روز بهره وری و بهینه سازی مصرف", "روز بزرگداشت ملاصدرا"],
    "3-3": ["فتح خرمشهر", "روز مقاومت، ایثار و پیروزی"],
    "3-4": ["روز دزفول", "روز مقاومت و پایداری"],
    "3-6": ["خرداد روز", "جشن خردادگان"],
    "3-14": ["رحلت حضرت امام خمینی"],
    "3-15": ["قیام 15 خرداد", "روز جهانی محیط زیست"],
    "3-20": ["روز جهانی صنایع دستی"],
    "3-22": ["روز جهانی مبارزه با کار کودکان"],
    "3-24": ["روز جهانی اهدای خون"],
    "3-25": ["روز ملی گل و گیاه"],
    "3-27": ["روز جهاد کشاورزی", "روز جهانی بیابان زدایی"],
    "4-1": ["جشن آب پاشونک", "جشن آغاز تابستان", "روز اصناف"],
    "4-5": ["روز جهانی مبارزه با مواد مخدر"],
    "4-7": ["انفجار دفتر حزب جمهوری اسلامی", "شهادت دکتر بهشتی", "روز قوه قضاییه"],
    "4-8": ["روز مبارزه با سلاح های شیمیایی و میکروبی"],
    "4-10": ["روز صنعت و معدن"],
    "4-13": ["تیر روز", "جشن تیرگان"],
    "4-14": ["روز قلم"],
    "4-15": ["جشن خام خواری"],
    "4-25": ["روز بهزیستی و تامین اجتماعی"],
    "4-27": ["اعلام پذیرش قطعنامه 598 شورای امنیت از سوی ایران"],
    "5-6": ["روز ترویج آموزش های فنی و حرفه ای"],
    "5-7": ["مرداد روز", "جشن مردادگان"],
    "5-8": ["روز بزرگداشت شیخ شهاب الدین سهروردی"],
    "5-10": ["جشن چله تابستان", "آغاز هفته جهانی شیردهی"],
    "5-14": ["صدور فرمان مشروطیت"],
    "5-17": ["روز خبرنگار"],
    "5-22": ["روز جهانی چپ دست ها"],
    "5-26": ["سالروز ورود آزادگان سرافراز به وطن"],
    "5-28": ["سالروز وقایع 28 مرداد", "سالروز فاجعه سینما رکس آبادان", "روز جهانی عکاسی"],
    "6-1": ["روز بزرگداشت ابوعلی سینا", "روز پزشک"],
    "6-2": ["آغاز هفته دولت"],
    "6-4": ["زادروز داراب (کوروش)", "شهریور روز", "جشن شهریورگان", "روز کارمند"],
    "6-5": ["روز بزرگداشت محمدبن زکریای رازی", "روز داروساز"],
    "6-8": ["انفجار در دفتر نخست‌وزیری", "روز مبارزه با تروریسم"],
    "6-11": ["روز صنعت چاپ"],
    "6-13": ["روز بزرگداشت ابوریحان بیرونی", "روز تعاون"],
    "6-17": ["قیام 17 شهریور"],
    "6-19": ["درگذشت آیت الله سید محمود طالقانی", "روز جهانی پیشگیری از خودکشی"],
    "6-20": ["حمله به برج‌های دوقلوی مرکز تجارت جهانی"],
    "6-21": ["روز سینما", "روز گرامیداشت برنامه نویسان"],
    "6-27": ["روز شعر و ادب پارسی", "روز بزرگداشت استاد شهریار"],
    "6-30": ["روز گفتگوی تمدنها", "روز جهانی صلح"],
    "6-31": ["آغاز هفته دفاع مقدس"],
    "7-1": ["آغاز حمله مغول به ایران"],
    "7-5": ["روز جهانی جهانگردی"],
    "7-7": ["روز آتش نشانی و ایمنی", "سقوط هواپیمای حامل فرماندهان جنگ"],
    "7-8": ["روز بزرگداشت مولوی", "روز جهانی ناشنوایان", "روز جهانی ترجمه و مترجم"],
    "7-9": ["روز جهانی سالمندان"],
    "7-10": ["مهر روز", "جشن مهرگان"],
    "7-13": ["روز نیروی انتظامی", "روز جهانی معلم"],
    "7-14": ["روز دامپزشکی"],
    "7-16": ["روز ملی کودک"],
    "7-17": ["روز جهانی پست"],
    "7-18": ["روز جهانی مبارزه با حکم اعدام"],
    "7-19": ["روز جهانی دختر"],
    "7-20": ["روز بزرگداشت حافظ"],
    "7-21": ["جشن پیروزی کاوه و فریدون"],
    "7-22": ["روز جهانی استاندارد"],
    "7-23": ["روز جهانی عصای سفید"],
    "7-24": ["روز جهانی غذا"],
    "7-25": ["روز جهانی ریشه کنی فقر"],
    "7-26": ["روز تربیت بدنی و ورزش"],
    "7-29": ["روز ملی کوهنورد"],
    "8-1": ["روز آمار و برنامه ریزی"],
    "8-7": ["سالروز ورود کوروش بزرگ به بابل"],
    "8-8": ["روز نوجوان"],
    "8-10": ["آبان روز", "جشن آبانگان"],
    "8-13": ["روز دانش آموز"],
    "8-14": ["روز فرهنگ عمومی"],
    "8-15": ["جشن میانه پاییز"],
    "8-18": ["روز ملی کیفیت"],
    "8-23": ["روز جهانی دیابت"],
    "8-24": ["روز کتاب و کتابخوانی"],
    "8-28": ["روز جهانی فلسفه", "روز جهانی آقایان"],
    "8-29": ["روز جهانی کودک"],
    "9-1": ["آذر جشن"],
    "9-4": ["روز جهانی مبارزه با خشونت علیه زنان"],
    "9-5": ["روز بسیج مستضعفان"],
    "9-7": ["روز نیروی دریایی"],
    "9-9": ["جشن آذرگان", "آذر روز"],
    "9-10": ["روز مجلس", "روز جهانی ایدز"],
    "9-12": ["روز جهانی معلولان"],
    "9-13": ["روز بیمه"],
    "9-15": ["روز حسابدار"],
    "9-16": ["روز دانشجو"],
    "9-20": ["روز جهانی کوه نوردی"],
    "9-25": ["روز پژوهش"],
    "9-26": ["روز حمل و نقل"],
    "9-30": ["جشن شب یلدا"],
    "10-1": ["روز میلاد خورشید", "جشن خرم روز", "نخستین جشن دیگان"],
    "10-4": ["جشن کریسمس"],
    "10-5": ["سالروز زمین لرزه ی بم", "سالروز شهادت آشو زرتشت"],
    "10-8": ["دی به آذر روز", "دومین جشن دیگان"],
    "10-11": ["جشن آغاز سال نو میلادی"],
    "10-13": ["شهادت سردار حاج قاسم سلیمانی"],
    "10-15": ["دی به مهر روز", "سومین جشن دیگان"],
    "10-20": ["سالروز قتل امیرکبیر"],
    "10-23": ["دی به دین روز", "چهارمین جشن دیگان"],
    "11-1": ["زادروز فردوسی"],
    "11-2": ["بهمن روز", "جشن بهمنگان"],
    "11-5": ["جشن نوسره"],
    "11-10": ["جشن سده"],
    "11-12": ["بازگشت امام خمینی (ره) به ایران"],
    "11-15": ["جشن میانه زمستان"],
    "11-19": ["روز نیروی هوایی"],
    "11-22": ["پیروزی انقلاب اسلامی", "حمله به سفارت روسیه و قتل گریبایدوف"],
    "11-25": ["روز ولنتاین"],
    "11-29": ["جشن سپندارمذگان", "روز عشق"],
    "12-2": ["روز جهانی زبان مادری"],
    "12-5": ["روز بزرگداشت زمین و بانوان", "روز بزرگداشت خواجه نصیر الدین طوسی", "روز مهندس"],
    "12-7": ["سالروز استقلال کانون وکلای دادگستری", "روز وکیل مدافع", "سالروز درگذشت علی اکبر دهخدا"],
    "12-15": ["روز درختکاری"],
    "12-17": ["روز جهانی زنان"],
    "12-25": ["پایان سرایش شاهنامه"],
    "12-29": ["روز ملی شدن صنعت نفت ایران", "روز جهانی شادی"],
}

def get_shamsi_events(year, month, day):
    key = f"{month}-{day}"
    return shamsi_events.get(key, ["هیچ مناسبت خاصی ثبت نشده است."])

# ============================================================
# 7. پیام انگیزشی
# ============================================================
motivation_messages = [
    "🌱 امروز روز جدیدی برای ساختن است. قدر لحظات را بدان!",
    "💪 موفقیت از دل تلاش‌های کوچک روزانه زاده می‌شود.",
    "🌟 هر روز یک فرصت تازه برای بهتر شدن است.",
    "😊 لبخند بزن، دنیا جای قشنگی‌ست!",
    "✨ به خودت ایمان داشته باش، می‌توانی!",
    "🌺 آرامش را در دل خود پیدا کن، نه در بیرون.",
    "🔥 امروز را با انرژی مثبت شروع کن.",
    "🌸 زندگی زیباست، پس لذت ببر.",
    "⭐ هر قدم کوچک، تو را به هدف نزدیک‌تر می‌کند.",
    "🌈 پس از هر شب تاریک، صبحی روشن می‌آید.",
    "🍀 شانس را با تلاش خود بساز.",
    "💎 ارزش تو به دانسته‌هایت نیست، به رفتارت است.",
    "🌿 امروز را با عشق به خود و دیگران بگذران.",
    "🎯 هدف خود را امروز مرور کن و گام بردار.",
    "🕊️ آرامش را در دل خود پرورش بده.",
    "🌞 هر روز طلوعی دوباره است، از آن استفاده کن.",
    "🍃 ساده زیستن، زیباترین راه زندگی است.",
    "💫 رویاهایت را باور کن، آنها به واقعیت می‌پیوندند.",
    "🌼 مهربانی، بهترین هدیه‌ای است که می‌توانی بدهی.",
    "🏆 موفقیت، حاصل تکرار کارهای کوچک است."
]
last_motivation_index = -1

def get_motivation():
    global last_motivation_index
    if len(motivation_messages) == 1:
        return motivation_messages[0]
    index = random.randint(0, len(motivation_messages) - 1)
    while index == last_motivation_index:
        index = random.randint(0, len(motivation_messages) - 1)
    last_motivation_index = index
    return motivation_messages[index]

# ============================================================
# 8. ساخت پیام اصلی (با فرمت جدید تاریخ)
# ============================================================
def build_message(user_id, user_name, city):
    lang = get_user_language(user_id)
    
    today = get_today_tehran()
    
    # تاریخ شمسی (نوشتاری + عددی در یک خط)
    persian_weekday = PERSIAN_WEEKDAYS[today.weekday()]
    persian_month = PERSIAN_MONTHS[today.month]
    persian_day_text = str(today.day).replace("0", "۰").replace("1", "۱").replace("2", "۲").replace("3", "۳").replace("4", "۴").replace("5", "۵").replace("6", "۶").replace("7", "۷").replace("8", "۸").replace("9", "۹")
    persian_year_text = str(today.year).replace("0", "۰").replace("1", "۱").replace("2", "۲").replace("3", "۳").replace("4", "۴").replace("5", "۵").replace("6", "۶").replace("7", "۷").replace("8", "۸").replace("9", "۹")
    
    # عددی
    persian_year_num = str(today.year).replace("0", "۰").replace("1", "۱").replace("2", "۲").replace("3", "۳").replace("4", "۴").replace("5", "۵").replace("6", "۶").replace("7", "۷").replace("8", "۸").replace("9", "۹")
    persian_month_num = str(today.month).zfill(2).replace("0", "۰").replace("1", "۱").replace("2", "۲").replace("3", "۳").replace("4", "۴").replace("5", "۵").replace("6", "۶").replace("7", "۷").replace("8", "۸").replace("9", "۹")
    persian_day_num = str(today.day).zfill(2).replace("0", "۰").replace("1", "۱").replace("2", "۲").replace("3", "۳").replace("4", "۴").replace("5", "۵").replace("6", "۶").replace("7", "۷").replace("8", "۸").replace("9", "۹")
    
    # فرمت نهایی شمسی: "شنبه ۰۳ مرداد ۱۴۰۵/۰۵/۰۳"
    persian_date_final = f"{persian_weekday} {persian_day_text} {persian_month} {persian_year_text}/{persian_month_num}/{persian_day_num}"
    
    # تاریخ میلادی با فرمت "July 25, Saturday 2026/09/1"
    gregorian_today = today.togregorian()
    miladi_date_text = gregorian_today.strftime("%B %d, %A")
    miladi_year = str(gregorian_today.year)
    miladi_month = str(gregorian_today.month).zfill(2)
    miladi_day = str(gregorian_today.day).zfill(2)
    miladi_date_final = f"{miladi_date_text} {miladi_year}/{miladi_month}/{miladi_day}"
    
    # تاریخ قمری امروز
    hijri_today = get_hijri_date(today.togregorian())
    hijri_today_formatted = f"{hijri_today['day']} {hijri_today['month_name']} {hijri_today['year']} / {hijri_today['month']} / {hijri_today['day']}"
    
    # مناسبت‌های قمری امروز
    hijri_today_events = get_hijri_events(hijri_today['month'], hijri_today['day'])
    hijri_today_text = "\n".join([f"• {event}" for event in hijri_today_events])
    
    # تاریخ فردا
    tomorrow = today + timedelta(days=1)
    gregorian_tomorrow = tomorrow.togregorian()
    miladi_tomorrow = gregorian_tomorrow.strftime("%B %d, %A")
    
    hijri_tomorrow = get_hijri_date(tomorrow.togregorian())
    hijri_tomorrow_formatted = f"{hijri_tomorrow['day']} {hijri_tomorrow['month_name']} {hijri_tomorrow['year']} / {hijri_tomorrow['month']} / {hijri_tomorrow['day']}"
    hijri_tomorrow_events = get_hijri_events(hijri_tomorrow['month'], hijri_tomorrow['day'])
    hijri_tomorrow_text = "\n".join([f"• {event}" for event in hijri_tomorrow_events])
    
    # مناسبت‌های شمسی
    today_events = get_shamsi_events(today.year, today.month, today.day)
    today_events_text = "\n".join([f"• {event}" for event in today_events])
    
    tomorrow_events = get_shamsi_events(tomorrow.year, tomorrow.month, tomorrow.day)
    tomorrow_events_text = "\n".join([f"• {event}" for event in tomorrow_events])
    
    # اوقات شرعی
    prayer_times = get_prayer_times(city)
    prayer_text = ""
    if prayer_times:
        for name, time in prayer_times.items():
            prayer_text += f"🕌 {name}: {time}\n"
    else:
        prayer_text = "⚠️ " + TEXTS[lang].get("no_events", "در دسترس نیست.")
    
    # آب و هوا
    weather = get_weather(city)
    weather_text = ""
    if weather:
        weather_text = f"🌡️ دما: {weather['دما']}\n🌤️ وضعیت: {weather['وضعیت']}\n💧 رطوبت: {weather['رطوبت']}"
    else:
        weather_text = "⚠️ اطلاعات آب و هوا در دسترس نیست."
    
    motivation = get_motivation()
    
    message = (
        TEXTS[lang]["welcome"].format(name=user_name) + "\n\n" +
        "📅 **امروز (شمسی):** " + persian_date_final + "\n" +
        "📅 **امروز (میلادی):** " + miladi_date_final + "\n" +
        "🌙 **امروز (قمری):** " + hijri_today_formatted + "\n\n" +
        "📌 **مناسبت‌های قمری امروز:**\n" + hijri_today_text + "\n\n" +
        "🔮 **فردا (میلادی):** " + miladi_tomorrow + "\n" +
        "🌙 **فردا (قمری):** " + hijri_tomorrow_formatted + "\n" +
        "📌 **مناسبت‌های قمری فردا:**\n" + hijri_tomorrow_text + "\n\n" +
        "📌 **مناسبت‌های شمسی امروز:**\n" + today_events_text + "\n\n" +
        "🔮 **مناسبت‌های شمسی فردا:**\n" + tomorrow_events_text + "\n\n" +
        TEXTS[lang]["prayer"].format(city=city) + "\n" + prayer_text + "\n" +
        TEXTS[lang]["weather"].format(city=city) + "\n" + weather_text + "\n\n" +
        TEXTS[lang]["motivation"] + "\n" + motivation + "\n\n" +
        TEXTS[lang]["change_city"]
    )
    return message

# ============================================================
# 9. دکمه‌ها
# ============================================================
def get_city_buttons(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("تهران", callback_data="city_تهران"),
         InlineKeyboardButton("مشهد", callback_data="city_مشهد"),
         InlineKeyboardButton("قم", callback_data="city_قم")],
        [InlineKeyboardButton("اصفهان", callback_data="city_اصفهان"),
         InlineKeyboardButton("شیراز", callback_data="city_شیراز"),
         InlineKeyboardButton("تبریز", callback_data="city_تبریز")],
        [InlineKeyboardButton("🌍 زبان", callback_data="language_menu"),
         InlineKeyboardButton("📅 تقویم", callback_data="calendar_menu")]
    ])

def get_language_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("فارسی 🇮🇷", callback_data="lang_fa"),
         InlineKeyboardButton("English 🇬🇧", callback_data="lang_en")],
        [InlineKeyboardButton("العربية 🇸🇦", callback_data="lang_ar"),
         InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
    ])

def get_calendar_buttons(year, month, day, user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ روز قبل", callback_data=f"day_{year}_{month}_{day-1}"),
         InlineKeyboardButton("📅 امروز", callback_data="calendar_today"),
         InlineKeyboardButton("روز بعد ▶️", callback_data=f"day_{year}_{month}_{day+1}")],
        [InlineKeyboardButton("◀️ ماه قبل", callback_data=f"cal_{year}_{month-1}_{day}"),
         InlineKeyboardButton("ماه بعد ▶️", callback_data=f"cal_{year}_{month+1}_{day}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
    ])

def get_calendar_text(year, month, day, user_id):
    lang = get_user_language(user_id)
    try:
        target_date = jdatetime.date(year, month, day)
        
        # تاریخ شمسی (نوشتاری + عددی در یک خط)
        persian_weekday = PERSIAN_WEEKDAYS[target_date.weekday()]
        persian_month = PERSIAN_MONTHS[target_date.month]
        persian_day_text = str(target_date.day).replace("0", "۰").replace("1", "۱").replace("2", "۲").replace("3", "۳").replace("4", "۴").replace("5", "۵").replace("6", "۶").replace("7", "۷").replace("8", "۸").replace("9", "۹")
        persian_year_text = str(target_date.year).replace("0", "۰").replace("1", "۱").replace("2", "۲").replace("3", "۳").replace("4", "۴").replace("5", "۵").replace("6", "۶").replace("7", "۷").replace("8", "۸").replace("9", "۹")
        persian_year_num = str(target_date.year).replace("0", "۰").replace("1", "۱").replace("2", "۲").replace("3", "۳").replace("4", "۴").replace("5", "۵").replace("6", "۶").replace("7", "۷").replace("8", "۸").replace("9", "۹")
        persian_month_num = str(target_date.month).zfill(2).replace("0", "۰").replace("1", "۱").replace("2", "۲").replace("3", "۳").replace("4", "۴").replace("5", "۵").replace("6", "۶").replace("7", "۷").replace("8", "۸").replace("9", "۹")
        persian_day_num = str(target_date.day).zfill(2).replace("0", "۰").replace("1", "۱").replace("2", "۲").replace("3", "۳").replace("4", "۴").replace("5", "۵").replace("6", "۶").replace("7", "۷").replace("8", "۸").replace("9", "۹")
        date_str = f"{persian_weekday} {persian_day_text} {persian_month} {persian_year_text}/{persian_month_num}/{persian_day_num}"
        
        # مناسبت‌های شمسی و قمری
        shamsi_events = get_shamsi_events(year, month, day)
        shamsi_text = "\n".join([f"• {event}" for event in shamsi_events])
        
        hijri = get_hijri_date(target_date.togregorian())
        hijri_formatted = f"{hijri['day']} {hijri['month_name']} {hijri['year']} / {hijri['month']} / {hijri['day']}"
        hijri_events = get_hijri_events(hijri['month'], hijri['day'])
        hijri_text = "\n".join([f"• {event}" for event in hijri_events])
        
        city = get_user_city(user_id)
        prayer = get_prayer_times(city)
        prayer_text = ""
        if prayer:
            for name, time in prayer.items():
                prayer_text += f"🕌 {name}: {time}\n"
        else:
            prayer_text = "⚠️ در دسترس نیست."
        
        weather = get_weather(city)
        weather_text = ""
        if weather:
            weather_text = f"🌡️ دما: {weather['دما']}\n🌤️ وضعیت: {weather['وضعیت']}\n💧 رطوبت: {weather['رطوبت']}"
        else:
            weather_text = "⚠️ در دسترس نیست."
        
        message = (
            f"📅 **{date_str}**\n"
            f"🌙 **قمری:** {hijri_formatted}\n\n"
            f"📌 **مناسبت‌های شمسی:**\n{shamsi_text}\n\n"
            f"📌 **مناسبت‌های قمری:**\n{hijri_text}\n\n"
            f"⏰ **اوقات شرعی ({city}):**\n{prayer_text}\n"
            f"🌦️ **آب و هوا ({city}):**\n{weather_text}\n\n"
            "🔄 با دکمه‌های زیر روز یا ماه را تغییر دهید."
        )
        return message
    except Exception as e:
        print(f"خطا در تقویم: {e}")
        return "❌ خطا در نمایش تقویم."

# ============================================================
# 10. تابع بررسی عضویت در کانال
# ============================================================
async def check_membership(user_id, bot):
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ============================================================
# 11. دستورات
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name or "کاربر"
    lang = get_user_language(user_id)
    
    # بررسی عضویت در کانال
    is_member = await check_membership(user_id, context.bot)
    if not is_member:
        await update.message.reply_text(
            TEXTS[lang]["not_member"].format(channel_link=REQUIRED_CHANNEL_LINK)
        )
        return
    
    save_user(user_id, first_name)
    city = get_user_city(user_id)
    message = build_message(user_id, first_name, city)
    await update.message.reply_text(message, reply_markup=get_city_buttons(user_id))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    await update.message.reply_text(TEXTS[lang]["help"])

async def city_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("❌ لطفاً نام شهر را وارد کن. مثال: `/city مشهد`")
        return
    new_city = " ".join(args)
    test_weather = get_weather(new_city)
    if not test_weather:
        lang = get_user_language(user_id)
        await update.message.reply_text(TEXTS[lang]["city_not_found"].format(city=new_city))
        return
    update_user_city(user_id, new_city)
    lang = get_user_language(user_id)
    await update.message.reply_text(TEXTS[lang]["city_changed"].format(city=new_city))

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(
        "🌍 زبان خود را انتخاب کنید / Choose your language / اختر لغتك:",
        reply_markup=get_language_buttons()
    )

async def calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = get_today_tehran()
    text = get_calendar_text(today.year, today.month, today.day, user_id)
    await update.message.reply_text(
        text,
        reply_markup=get_calendar_buttons(today.year, today.month, today.day, user_id)
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ این دستور فقط برای ادمین‌هاست.")
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE subscribed = 1")
    active = c.fetchone()[0]
    conn.close()
    lang = get_user_language(user_id)
    await update.message.reply_text(TEXTS[lang]["stats"].format(total=total, active=active))

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ این دستور فقط برای ادمین‌هاست.")
        return
    if not context.args:
        await update.message.reply_text("❌ لطفاً پیام را وارد کن. مثال: `/broadcast سلام به همه`")
        return
    message_text = " ".join(context.args)
    users = get_all_users()
    count = 0
    for user in users:
        try:
            await context.bot.send_message(chat_id=user[0], text=message_text)
            count += 1
            await asyncio.sleep(0.1)
        except:
            pass
    lang = get_user_language(user_id)
    await update.message.reply_text(TEXTS[lang]["broadcast_sent"].format(count=count))

# ============================================================
# 12. دکمه‌ها (CallbackQuery)
# ============================================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    if data.startswith("city_"):
        city = data.replace("city_", "")
        test_weather = get_weather(city)
        if not test_weather:
            await query.edit_message_text(
                TEXTS[lang]["city_not_found"].format(city=city),
                reply_markup=get_city_buttons(user_id)
            )
            return
        update_user_city(user_id, city)
        first_name = get_user(user_id)[1] if get_user(user_id) else "کاربر"
        message = build_message(user_id, first_name, city)
        await query.edit_message_text(message, reply_markup=get_city_buttons(user_id))
    
    elif data.startswith("lang_"):
        lang_code = data.replace("lang_", "")
        update_user_language(user_id, lang_code)
        first_name = get_user(user_id)[1] if get_user(user_id) else "کاربر"
        city = get_user_city(user_id)
        message = build_message(user_id, first_name, city)
        await query.edit_message_text(message, reply_markup=get_city_buttons(user_id))
    
    elif data == "language_menu":
        await query.edit_message_text(
            "🌍 انتخاب زبان / Choose Language / اختر اللغة:",
            reply_markup=get_language_buttons()
        )
    
    elif data == "calendar_menu":
        today = get_today_tehran()
        text = get_calendar_text(today.year, today.month, today.day, user_id)
        await query.edit_message_text(text, reply_markup=get_calendar_buttons(today.year, today.month, today.day, user_id))
    
    elif data == "calendar_today":
        today = get_today_tehran()
        text = get_calendar_text(today.year, today.month, today.day, user_id)
        await query.edit_message_text(text, reply_markup=get_calendar_buttons(today.year, today.month, today.day, user_id))
    
    elif data.startswith("day_"):
        parts = data.split("_")
        year = int(parts[1])
        month = int(parts[2])
        day = int(parts[3])
        try:
            jdatetime.date(year, month, day)
        except ValueError:
            if day < 1:
                month -= 1
                if month < 1:
                    month = 12
                    year -= 1
                last_day = jdatetime.date(year, month, 1) - timedelta(days=1)
                day = last_day.day
            else:
                month += 1
                if month > 12:
                    month = 1
                    year += 1
                day = 1
        text = get_calendar_text(year, month, day, user_id)
        await query.edit_message_text(text, reply_markup=get_calendar_buttons(year, month, day, user_id))
    
    elif data.startswith("cal_"):
        parts = data.split("_")
        year = int(parts[1])
        month = int(parts[2])
        day = int(parts[3])
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        text = get_calendar_text(year, month, day, user_id)
        await query.edit_message_text(text, reply_markup=get_calendar_buttons(year, month, day, user_id))
    
    elif data == "back_to_main":
        first_name = get_user(user_id)[1] if get_user(user_id) else "کاربر"
        city = get_user_city(user_id)
        message = build_message(user_id, first_name, city)
        await query.edit_message_text(message, reply_markup=get_city_buttons(user_id))

# ============================================================
# 13. ارسال خودکار
# ============================================================
def send_daily_messages(app):
    async def send():
        print("⏰ ارسال خودکار روزانه شروع شد...")
        users = get_all_users()
        for user_id, first_name, city, lang in users:
            try:
                message = build_message(user_id, first_name, city)
                await app.bot.send_message(chat_id=user_id, text=message)
                print(f"✅ پیام به کاربر {user_id} ارسال شد.")
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"❌ خطا در ارسال به کاربر {user_id}: {e}")
        print("🏁 ارسال خودکار روزانه پایان یافت.")
    
    asyncio.run_coroutine_threadsafe(send(), loop)

def start_scheduler(app):
    scheduler = BackgroundScheduler(timezone="Asia/Tehran")
    scheduler.add_job(
        send_daily_messages,
        CronTrigger(hour=0, minute=0, timezone="Asia/Tehran"),
        args=[app]
    )
    scheduler.start()
    print("⏰ زمان‌بند ارسال خودکار فعال شد (هر روز ساعت ۰۰:۰۰ به وقت تهران).")

# ============================================================
# 14. اجرای اصلی
# ============================================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("city", city_command))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CommandHandler("calendar", calendar_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    
    start_scheduler(app)
    
    print("✅ ربات با تمام قابلیت‌های جدید روشن شد...")
    app.run_polling()

from flask import Flask
import threading

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "ربات روشن است! ✅"

def run_flask():
    app_flask.run(host='0.0.0.0', port=8080)

# اجرای Flask در یک ترد جداگانه
threading.Thread(target=run_flask, daemon=True).start()

if __name__ == "__main__":
    main()
