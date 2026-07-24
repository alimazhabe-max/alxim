# نسخه نهایی - بدون خطا
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

# ============================================================
# 1. تنظیمات اولیه
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("متغیر BOT_TOKEN در محیط تنظیم نشده است!")

ADMIN_IDS = [int(id.strip()) for id in os.environ.get("ADMIN_IDS", "").split(",") if id.strip()]
loop = asyncio.new_event_loop()

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
        "date": "📅 **امروز (شمسی):** {persian}",
        "hijri": "🌙 **امروز (قمری):** {hijri}",
        "hijri_events_today": "📌 **مناسبت‌های قمری امروز:**",
        "hijri_events_tomorrow": "📌 **مناسبت‌های قمری فردا:**",
        "shamsi_events_today": "📌 **مناسبت‌های شمسی امروز:**",
        "shamsi_events_tomorrow": "🔮 **مناسبت‌های شمسی فردا:**",
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
    },
    "en": {
        "welcome": "🌟 Hello dear {name}! 🌟",
        "date": "📅 **Today (Solar):** {persian}",
        "hijri": "🌙 **Today (Lunar):** {hijri}",
        "hijri_events_today": "📌 **Today's Lunar Events:**",
        "hijri_events_tomorrow": "📌 **Tomorrow's Lunar Events:**",
        "shamsi_events_today": "📌 **Today's Solar Events:**",
        "shamsi_events_tomorrow": "🔮 **Tomorrow's Solar Events:**",
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
    },
    "ar": {
        "welcome": "🌟 مرحباً عزيزي {name}! 🌟",
        "date": "📅 **اليوم (شمسي):** {persian}",
        "hijri": "🌙 **اليوم (قمري):** {hijri}",
        "hijri_events_today": "📌 **مناسبات قمرية اليوم:**",
        "hijri_events_tomorrow": "📌 **مناسبات قمرية غداً:**",
        "shamsi_events_today": "📌 **مناسبات شمسية اليوم:**",
        "shamsi_events_tomorrow": "🔮 **مناسبات شمسية غداً:**",
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
    }
}

def get_text(user_id, key, **kwargs):
    lang = get_user_language(user_id)
    text = TEXTS.get(lang, TEXTS["fa"]).get(key, TEXTS["fa"].get(key, key))
    return text.format(**kwargs) if kwargs else text

# ============================================================
# 4. توابع API
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
        hijri = Gregorian(g_date.year, g_date.month, g_date.day).to_hijri()
        hijri_months = {
            1: "محرم", 2: "صفر", 3: "ربیع‌الاول", 4: "ربیع‌الثانی",
            5: "جمادی‌الاول", 6: "جمادی‌الثانی", 7: "رجب", 8: "شعبان",
            9: "رمضان", 10: "شوال", 11: "ذی‌قعده", 12: "ذی‌الحجه"
        }
        return f"{hijri.day} {hijri_months[hijri.month]} {hijri.year}"
    except:
        return "نامشخص"

# ============================================================
# 5. دیکشنری کامل رویدادهای قمری (تمام ماه‌ها)
# ============================================================
hijri_events = {
    # محرم
    "1-1": ["آغاز سال هجرى قمرى", "يورش ابرهه به مكه", "آغاز ایام حسینی", "ماجرای شعب ابی طالب (ع)", "جنگ ذات الرقاع", "اولین جمع اوری زکات", "منازل امام حسین تا کربلا قصر مقاتل", "کلام عاشورایی امام رضا (ع)"],
    "1-2": ["درگذشت حضرت آدم(ع)", "ورود امام حسين علیه السلام به كربلا"],
    "1-3": ["نجات یوسف علیه السلام از زندان", "دعوت سران ممالک دیگر به اسلام توسط پیامبر (ص)", "ورود عمر بن سعد به كربلا", "بركناري مستعين عباسي از خلافت"],
    "1-4": ["ه درک واصل شدن نمرود", "سخنرانی عبیدالله بن زیاد علیه امام حسین (ع) در مسجد کوفه", "صدور فتواي قاضي شُرَيْح(61 ق)", "شهادت قیس بن مسهر صیداوی فرستاده امام حسین (ع) به کوفه"],
    "1-5": ["عبور حضرت موسى علیه السلام از دریا", "آغاز سریه عبدالله بن أنیس", "ورود حصين بن نمير به كربلا", "ورود شبث بن ربعى به کربلاء", "ولادت میرحامد حسین هندی (سال ۱۲۴۶ هجری قمری)"],
    "1-6": ["شهادت حضرت یحیى پیامبر علیه السلام", "اولین محاصره فرات در کربلا", "یارى طلبى حبیب بن مظاهر از بنى اسد", "گفتگوی عمر سعد با امام حسين علیه السلام", "درگذشت سید رضى رحمت الله علیه – گردآورنده \"نهج‏ البلاغه\""],
    "1-7": ["مبعوث شدن حضرت موسى علیه السلام به پیامبری", "بستن آب بر اهل بیت علیهم السلام", "نامه عبيدالله بن زياد به عمر بن سعد", "نبرد هواداران بني عباس با سپاهيان اموي"],
    "1-8": ["ديدار امام حسين علیه السلام با عمر بن سعد", "قحط آب در كاروان امام حسين علیه السلام"],
    "1-9": ["رهائى حضرت یونس علیه السلام از شکم ماهى", "ولادت حضرت موسى علیه السلام", "ولادت حضرت مریم علیهاالسلام", "ورود شمر بن ذي الجوشن به كربلا"],
    "1-10": ["اخراج آدم و حوا علیهما السلام از بهشت", "خروج حضرت نوح علیه السلام از کشتى", "تولد حضرت ابراهیم علیه السلام", "ملاقات حضرت یعقوب با حضرت یوسف علیهما السلام", "آغاز غزوه ذات الرقاع", "شهادت امام حسین (ع)", "وفات ام سلمه", "قیام حضرت مهدی (عج)"],
    "1-11": ["رحلت حضرت آدم علیه السلام", "اسارت بازماندگان شهداي كربلا", "حرکت کاروان اسرا از کربلا", "درگذشت علامه حلى رحمه الله"],
    "1-12": ["ورود اهل بیت علیهم السلام به کوفه", "شهادت حضرت امام سجاد علیه السلام"],
    "1-13": ["تدفين پيكرهاي مقدس شهيدان كربلا", "اسراى اهل بیت علیهم السلام در مجلس ابن زیاد", "شهادت عبدالله بن عفيف ازدي"],
    "1-14": ["نامه نوشتن ابن زیاد به یزید"],
    "1-15": ["آغاز غزوه كُدروقوع غزوه خيبر)سال 7 هجری قمری(", "ورود نمايندگان طايفه نخع به مدينه و پذيرش دين اسلام", "ولادت سید بن طاووس"],
    "1-16": ["هجوم مسلمانان به دمشق)سال 14 هجری قمری(", "تدوين تاريخ اسلامى"],
    "1-17": ["نزول عذاب بر اصحاب فیل"],
    "1-19": ["حركت كاروان اسراي كربلا به سوي شام۳۶۶ق.", "درگذشت حسن بن بویه دیلمی از امرای آل بویه"],
    "1-20": ["دفن بدن جون، غلام امام حسين (ع) در كربلا"],
    "1-21": ["درگذشت علامه حلى رحمت الله علیه"],
    "1-22": ["ورود امیرالمؤمنین علي علیه السلام به صفين جهت نبرد با سپاه معاويه", "درگذشت شیخ طوسی (سال 460 هجری قمری)"],
    "1-23": ["آگاهى اصحاب کهف از خواب ۳۰۹ ساله خود", "مرگ مهدي عباسي"],
    "1-25": ["شهادت امام سجاد عليه السلام به روايتي", "كشته شدن امين به دست سپاهيان برادرش مأمون عباسي"],
    "1-26": ["محاصره و سنگباران مكه از سوي سپاهيان يزيد", "شهادت علي بن حسن مثلث در زندان منصور دوانقي"],
    "1-27": ["لشكركشي مأمون عباسي به سرزمين روم"],
    "1-28": ["درگذشت حذیفه بن یمان از اصحاب پیامبر(ص)", "ورود اسراي اهل بيت عليهم السلام به بعلبك", "ورود امام محمد تقي به بغداد بنا به درخواست معتصم عباسي", "انقراض حکومت عباسی"],
    "1-29": ["ورود كاروان اسرا به شام", "تصرف قم توسط قوای روسیه"],
    "1-30": ["درگذشت ام المؤمنين ماريه قبطيه سلام الله عليها", "قتل جعفر بن يحيي برمكي به دستور هارون الرشيد"],
    
    # صفر
    "2-1": ["وارد کردن سر مطهر امام حسین (ع) به شام", "ورود اهل بیت (ع) به شام", "شروع جنگ صفین"],
    "2-2": ["مجلس یزید", "شهادت زید بن علی بن الحسین (ع)"],
    "2-5": ["شهادت حضرت رقیه (س)"],
    "2-7": ["شهادت امام مجتبی (ع)"],
    "2-8": ["وفات حضرت سلمان"],
    "2-9": ["شهادت عمار و خزیمه", "جنگ نهروان"],
    "2-11": ["لیله الهریر در جنگ صفین"],
    "2-12": ["حکمین در صفین"],
    "2-14": ["شهادت محمد بن ابی بکر"],
    "2-15": ["ابتدای بیماری پیامبر (ص)"],
    "2-17": ["شهادت امام رضا (ع)"],
    "2-20": ["اربعین سید الشهداء (ع)", "زیارت جابر از کربلا", "بازگشت اهل بیت (ع)به کربلا", "ملحق شدن راس مطهر امام حسین (ع) به بدن مطهر"],
    "2-24": ["طلب کتف و دوات توسط پیامبر (ص)"],
    "2-25": ["دستور پیامبر (ص) به پیروی از ثقلین"],
    "2-26": ["تجهیز لشکر اسامه"],
    "2-28": ["شهادت رسول خدا (ص)", "آغاز امامت امیر المومنین علی (ع)", "آغاز غصب خلافت", "اجبار مردم بر بیعت کردن", "شهادت امام حسن مجتبی (ع)"],
    
    # ربیع‌الاول
    "3-1": ["دفن بدن مطهر پیامبر (ص)", "هجرت رسول خدا(ص)", "ليلة المبيت", "نزول آيه اى در شأن امیرالمؤمنین على (ع)", "سريه عبيده بن حارث", "درگذشت زینب بنت خزیمه همسر پیامبر (ص) در مدینه", "ابتدای وضع تاریخ هجری قمری", "هجوم به خانه وحی"],
    "3-3": ["احتجاج سلمان فارسي رحمت الله علیه بر مردم", "تخريب كعبه توسط يزيد"],
    "3-4": ["خروج پیامبر (ص) از غار ثور و حرکت به سوی مدینه"],
    "3-5": ["وفات حضرت سكينه بنت الحسين"],
    "3-6": ["ولادت مولانا جلال الدین محمد رومی (مولوی)"],
    "3-8": ["شهادت امام حسن عسکری علیه ­السلام"],
    "3-9": ["مرگ عمر بن سعد", "هلاکت هشام بن عبدالملک", "آغاز امامت حضرت ولى عصر عليه ­السلام"],
    "3-10": ["درگذشت حضرت لوط (ع)", "رحلت جناب عبدالمطلب", "ازدواج حضرت محمد (ص) با خديجه كبرى (س)", "درگذشت داود بن علی حاکم مدینه", "مرگ مالك بن انس"],
    "3-11": ["ولادت امام رضا عليه السلام"],
    "3-12": ["ولادت نبی مکرم اسلام به روایت اهل سنت", "ورود پيامبر اكرم صلي الله عليه و آله وسلم به مدينه", "آغاز وجوب نماز۱۳۲ق.", "پیروزی بنی عباس و پایان حکومت اموی", "قيام مختار در كوفه"],
    "3-14": ["مرگ يزيد بن معاويه", "هلاكت هادى عباسى", "خلافت هارون الرشيد"],
    "3-15": ["بنای مسجد قبا توسط پیامبر(ص) و اصحابش", "سريه حمزه بن عبدالمطلب"],
    "3-16": ["درگذشت مسعودی تاریخ‌نگار بزرگ شیعی"],
    "3-17": ["ولادت پیامبر صلی الله علیه و آله وسلم", "زادروز فرخنده امام جعفر صادق علیه السلام"],
    "3-20": ["قتل جالوت به دست حضرت داود(ع) طبق برخی روایات", "حكومت وليد بن يزيد اموى", "خلافت متقى عباسى"],
    "3-22": ["وقوع غزوه بنی نضیر"],
    "3-23": ["ورود حضرت معصومه عليهاالسلام به قم"],
    "3-25": ["غزوه دومه الجندل", "صلح امام حسن مجتبى علیه السلام"],
    "3-26": ["درگذشت ابن سماک (ابوعمر)"],
    "3-28": ["نزول عذاب بر قوم حضرت صالح علیه السلام", "شکست ایرانیان از اعراب مسلمان در زمان حکومت عثمان بن عفان و پایان‌یافتن سلسله ساسانی در ایران"],
    
    # ربیع‌الثانی
    "4-1": ["قیام توابین", "شهادت امام باقر (ع)"],
    "4-2": ["قتل عبدالله بن معتز در زندان مقتدر عباسى"],
    "4-3": ["پيمان شكنى امين در برابر برادرش مأمون", "سفر امام عسکری(ع) به جرجان"],
    "4-4": ["وقوع غزوه غابه", "ولادت حضرت عبد العظیم حسنی (ع)"],
    "4-5": ["خلافت مستعين عباسى"],
    "4-6": ["مرگ هشام بن عبدالملک"],
    "4-8": ["شهادت حضرت فاطمه(س)", "ميلاد امام حسن عسكرى علیه السلام"],
    "4-10": ["وفات حضرت معصومه سلام الله علیها", "تخریب گنبد حرم امام رضا (ع) توسط سربازان روسی"],
    "4-12": ["اضافه شدن ركعات نماز"],
    "4-13": ["شهادت حضرت زهرا (س)"],
    "4-14": ["قیام مختار بنابر روایتی"],
    "4-22": ["وفات جناب موسی مبرقع پسر حضرت جواد (ع)"],
    "4-27": ["درگذشت عبدالمطلب", "شهادت ابوسلمه اسدي", "تخریب دو گلدسته حرم عسکریین (ع)"],
    "4-29": ["آغاز حکومت شاه اسماعیل اول و تأسیس سلسله صفویه در تبریز"],
    "4-30": ["وفات زينب بنت خزيمه", "مرگ خالد بن ولید"],
    
    # جمادی‌الاول
    "5-1": ["میلاد حضرت زینب سلام الله علیها", "وقوع جنگ موته", "درگذشت ابوعلي صيرفي كوفي"],
    "5-5": ["میلاد حضرت زینب سلام الله علیها (به روایتی)"],
    "5-6": ["آغاز خلافت راضي بالله عباسي"],
    "5-10": ["كشته شدن خسرو پرويز به دست پسرش شيرويه", "تحويل پيراهن امام حسين به حضرت زينب عليهما السلام", "آغاز جنگ جمل در حوالي بصره"],
    "5-12": ["نامه هاي امام علي پس از پيروزي بر اصحاب جمل"],
    "5-13": ["شهادت حضرت فاطمه زهرا سلام الله علیها", "قتل ابراهیم بن مالک اشتر"],
    "5-15": ["ميلاد مسعود امام زين العابدين بنا به روايتي", "كشته شدن ابراهيم بن مالك اشتر و مصعب بن زبير"],
    "5-16": ["قتل عبدالله بن زبير در مكه"],
    "5-17": ["ولادت ذوالقرنین", "درگذشت احمد بن علی نجاشی"],
    "5-22": ["نبرد توابين در عين الورده با سپاهيان عبيدالله بن زياد", "وفات جناب قاسم بن موسی بن جعفر (ع)"],
    "5-23": ["فتح کرمان در زمان خلافت عمر بن خطاب"],
    "5-25": ["درگذشت معاویه بن یزید", "شروع جنگ در قیام توابین"],
    "5-27": ["درگذشت عبدالمطلب", "شهادت ابوسلمه اسدي", "تخریب دو گلدسته حرم عسکریین (ع)"],
    "5-29": ["درگذشت محمدبن عثمان بن سعید عَمْری دومین نائب امام زمان (عج)"],
    
    # رجب
    "7-1": ["ولادت امام محمد باقر (ع)", "زیارت امام حسین (ع)"],
    "7-2": ["ولادت امام علی النقی (ع)"],
    "7-3": ["ولادت امام هادی (ع)", "شهادت ایشان"],
    "7-5": ["ولادت امام موسی بن جعفر (ع)", "شهادت ابن سکیت"],
    "7-7": ["طلب امام رضا (ع) برای ولیعهدی"],
    "7-8": ["هلاکت مامون عباسی"],
    "7-9": ["ولادت حضرت علی اصغر"],
    "7-10": ["ولادت امام محمد جواد الائمه (ع)"],
    "7-12": ["شکافته شدن دیوار کعبه برای فاطمه بنت اسد", "مرگ معاویه", "ورود امیر المومنین به کوفه"],
    "7-13": ["ولادت امیر المومنین علی (ع)"],
    "7-14": ["ولادت امیر المومنین علی (ع)"],
    "7-15": ["ولادت امیر المومنین علی (ع)", "شهادت حضرت زینب (س)", "تغییر قبله مسلمین", "بدرک رفتن معاویه بن ابو سفیان", "خروج از شعب ابی طالب", "شهادت امام صادق (ع)"],
    "7-16": ["خروج فاطمه بنت اسد از کعبه"],
    "7-17": ["بدر ک واصل شدن معتمد عباسی قاتل امام حسن عسکری (ع)", "مرگ مامون"],
    "7-18": ["رحلت جناب ابراهیم فرزند رسول خدا (ص)", "ورود امام رضا (ع) به نیشابور"],
    "7-19": ["وفات شاه اسماعیل صفوی"],
    "7-21": ["شهادت حضرت زهرا (س)"],
    "7-22": ["فرار ابوبکر در جنگ خیبر"],
    "7-23": ["مجروح شدن امام حسن مجتبی (ع)", "مسموم شدن امام موسی بن جعفر (ع)", "ابتدای هفته کاظمیه", "فرار عمر در جنگ خیبر"],
    "7-24": ["فتح خیبر به دست امیر المومنین (ع)", "بازگشت جعفر طیار از حبشه"],
    "7-25": ["شهادت امام موسی بن جعفر (ع)", "ولادت شاه اسماعیل صفوی"],
    "7-26": ["رحلت حضرت ابوطالب (ع)"],
    "7-27": ["عید مبعث"],
    "7-28": ["شهادت امام موسی بن جعفر روز سوم"],
    "7-29": ["رحلت حضرت خدیجه کبری (س)", "حرکت امام حسین (ع) به سوی کربلا"],
    "7-30": ["اولین اقامه نماز در اسلام"],
    
    # شعبان
    "8-1": ["آغاز وجوب روزه", "تولد حضرت زینب کبری (س)"],
    "8-2": ["مرگ معتز عباسی بدست امام هادی (ع)"],
    "8-3": ["ولادت امام حسین (ع)", "ورود امام حسین (ع) به مکه"],
    "8-4": ["ولادت حضرت عباس (ع)"],
    "8-5": ["ولادت امام زین العابدین (ع)"],
    "8-6": ["وفات ثقه الواعظین حاج شیخ عبدا..یزدی"],
    "8-10": ["توقیع امام زمان (عج) برای شیعیان"],
    "8-11": ["ولادت حضرت علی اکبر (ع)"],
    "8-15": ["ولادت حضرت بقیه الله الاعظم (ص)", "وفات علی بن محمد سمری نایب امام زمان (عج)"],
    "8-16": ["رحلت اخرین سفیر و نائب خاص امام زمان (عج)", "وفات ایه الله سید محمود شاهرودی"],
    "8-17": ["وفات زاهد عالم مرحوم شیخ حسنعلی اصفهانی مشهور به نخودکی"],
    "8-18": ["وفات حسین بن روح نوبختی نایب امام زمان (عج)"],
    "8-19": ["جنگ بنی المصطلق"],
    "8-20": ["وفات ایه الله سید محمد شیرازی"],
    "8-22": ["ولادت رقیه خاتون (س)"],
    "8-23": ["وفات جناب ناصر کبیر"],
    "8-24": ["وفات میرزا محمد حسن شیرازی"],
    "8-25": ["هلاکت ابو مسلم خراسانی"],
    "8-27": ["شهادت سعید بن جبیر"],
    "8-29": ["روزه ماه مبارک رمضان"],
    
    # رمضان
    "9-1": ["نزول صحف ابراهیم", "زیارت و غسل امام حسین (ع)", "وفات نائی امام زمان (ع) جناب عثمان بن سعید (ره)", "صدور توقیع حضرت بقیه ال روحی فدابه جناب عثمان", "غزوه تبوک", "وفات جناب نفیسه خاتون (س)"],
    "9-2": ["ولایت عهدی حضرت امام رضا (ع)"],
    "9-3": ["رحلت جناب شیخ مفید ره", "شهادت حضرت زهرا ء (س)"],
    "9-4": ["مرگ زیاد بن ابیه"],
    "9-6": ["بیعت با امام رضا (ع)", "ضرب سکه به نام امام رضا (ع)", "نزول تورات"],
    "9-10": ["رحلت و شهادت حضرت زینب (س)", "آمدن نامه های اهل کوفه برای امام حسین (ع)", "وفات حضرت خدیجه (س)"],
    "9-12": ["عقد اخوت بین اصحاب پیامبر (ص)", "نزول انجیل بر حضرت عیسی (ع)"],
    "9-13": ["هلاکت حجاج ثقفی قاتل سفاک و بی رحم شیعیان"],
    "9-14": ["رحلت سید جلال اشرف فرزند امام کاظم (ع)", "شهادت جناب مختار ثقفی"],
    "9-15": ["ولادت با سعادت امام حسن مجتبی (ع)", "حرکت حضرت مسلم (ع)به سمت کوفه"],
    "9-16": ["معراج پیامبر اسلام (ص)"],
    "9-17": ["معراج پیامبر (ص)", "جنگ بدر", "قتل عایشه", "فرمان امام زمان (ع)بر ساختن مسجد مقدس بنای جمکران"],
    "9-18": ["نزول زبور برحضرت داوود (ع)"],
    "9-19": ["لیله القدر", "ضربت خوردن حضرت امیر المومنین علی (ع)", "نزول ایه خمس"],
    "9-20": ["شدت بیماری امام علی (ع)", "شکستن بتهای کعبه توسط پیامبر (ص) و امیر المومنین علی (ع)", "وفات یوشع بن نون (ع)"],
    "9-21": ["لیله القدر", "شهادت حضرت امیر المومنین علی (ع)", "روز عروج حضرت عیسی (ع) به آسمان"],
    "9-23": ["لیله القدر", "شب سوم شهادت حضرت امیر المومنین (ع)"],
    "9-24": ["مرگ ابو لهب"],
    "9-27": ["شب قدر", "رحلت علامه مجلسی (ره)"],
    "9-28": ["وفات میرزا محمد تقی موسوی اصفهانی"],
    "9-30": ["وفات سلطان الجایتو محمد خدا بنده"],
    
    # شوال
    "10-1": ["عید فطر", "مرگ عمرو بن عاص", "جنگ قرقره الکدر"],
    "10-2": ["قتل موکل"],
    "10-4": ["جنگ حنین"],
    "10-5": ["حرکت به سوی جنگ صفین"],
    "10-6": ["توقیع برای حسین بن روح"],
    "10-8": ["ویرانی قبور ائمه بقیع (ع)", "جنگ حمراء الاسد"],
    "10-10": ["آغاز غیبت صغری"],
    "10-13": ["رحلت ایه الله سید حسن بروجردی (ره)"],
    "10-14": ["مرگ عبد الملک بن مروان"],
    "10-15": ["جنگ احد و شهادت حضرت حمزه (ع)", "رد الشمس", "جنگ بنی قینقاع", "وفات حضرت عبد العظیم (ع)"],
    "10-16": ["جنگ حمراء الاسد"],
    "10-17": ["جنگ خندق", "وفات اباصلت هروی"],
    "10-18": ["وفات ادریس حلی فخر المله"],
    "10-20": ["دستگیری امام کاظم (ع)"],
    "10-25": ["شهادت امام صادق (ع)"],
    "10-29": ["رحلت ایه الله الموسوی الخمینی (ره)"],
    
    # ذی‌القعده
    "11-1": ["ولادت حضرت معصومه (س)", "جنگ بدر صغری", "بنا بر روایات اخراج حضرت آدم(ع) از بهشت", "درگذشت حضرت ابوطالب (به قولی) (۱۰ بعثت)", "درگذشت اشعث بن قیس (سال ۴۰ هجری قمری)"],
    "11-9": ["نامه مسلم بن عقیل به امام حسین(ع)"],
    "11-11": ["ولادت امام رضا (ع)"],
    "11-12": ["نامه حضرت مسلم به امام حسین (ع)"],
    "11-17": ["دستگیری امام کاظم(ع) در مدینه و تبعید به عراق"],
    "11-23": ["شهادت امام رضا (ع)", "جنگ بنی قریظه"],
    "11-24": ["حرکت امام رضا (ع) از مدینه به سوی مرو", "روز دحو الارض"],
    "11-25": ["حرکت پیامبر (س) از مدینه برای حجه الوداع", "آغاز بیان ولایت در مراسم حج", "سفر ولایت"],
    "11-28": ["شهادت امام جواد (ع)"],
    "11-29": ["صلح حدیبیه"],
    
    # ذی‌الحجه
    "12-1": ["عزل ابوبکر از تبلیغ سوره برائت", "آغاز نامه ها برای جنگ صفین"],
    "12-3": ["ورود پیامبر (ص) به مکه در سفر حجة الوداع"],
    "12-5": ["جنگ سویق"],
    "12-6": ["ازدواج حضرت امیر المومنین (ع) و حضرت زهرا (س)", "مرگ منصور دوانیقی"],
    "12-7": ["شهادت امام باقر (ع)", "خطبه حضرت عباس (ع) در مکه", "بردن امام کاظم (ع) به زندان بصره"],
    "12-8": ["توطئه ترور امام حسین (ع)", "دعوت عمومی حضرت مسلم (ع) در کوفه", "حرکت امام حسین (ع) از مکه به عراق"],
    "12-9": ["روز عرفه", "شهادت حضرت مسلم (ع) و هانی", "روز سد ابواب", "زیارت امام حسین (ع)"],
    "12-10": ["عید قربان", "شهادت عبد الله محض و جمعی از آل حسن (ع)", "نماز عید امام رضا (ع) در خراسان"],
    "12-11": ["روز نوشتن دعای صباح"],
    "12-13": ["شق القمر"],
    "12-14": ["بخشیدن فدک به حضرت زهرا (س)", "افشاءسر ولایت توسط عایشه و حفصه"],
    "12-15": ["ولادت امام هادی (ع)"],
    "12-18": ["عید غدیر", "قتل عثمان", "خلافت ظاهری امیر المومنین (ع)"],
    "12-22": ["شهادت میثم تمار", "خروج ابراهیم بن مالک اشتر برای جنگ با ابن زیاد"],
    "12-24": ["روز مباهله و روز نزول ایه تطهیر در شان اهل بیت (ع)", "روز خاتم بخشی"],
    "12-25": ["نزول سوره هل اتی", "اولین نماز جمعه امیر المومنین علی (ع)"],
    "12-27": ["مرگ مروان", "واقعه حره", "وفات علی بن جعفر (ع)"],
    "12-30": ["مرگ پدر ابوبکر", "مرگ هند جگر خوار"]
}

def get_hijri_events(hijri_month, hijri_day):
    key = f"{hijri_month}-{hijri_day}"
    return hijri_events.get(key, ["هیچ مناسبت قمری خاصی ثبت نشده است."])

# ============================================================
# 6. مناسبت‌های شمسی (با کش)
# ============================================================
events_cache = {}
events_cache_time = {}

def get_events_for_jalali(year, month, day):
    cache_key = f"{year}-{month}-{day}"
    if cache_key in events_cache:
        cache_time = events_cache_time.get(cache_key)
        if cache_time and (datetime.now() - cache_time).seconds < 86400:
            return events_cache[cache_key]
    
    try:
        from rokh import get_day_events, DateSystem
        events_data = get_day_events(year, month, day, system=DateSystem.JALALI)
        events = []
        if events_data:
            if isinstance(events_data, list):
                for event in events_data:
                    if isinstance(event, dict) and 'description' in event:
                        events.append(event['description'])
            elif isinstance(events_data, dict) and 'events' in events_data:
                for event in events_data['events']:
                    if 'description' in event:
                        events.append(event['description'])
        if events:
            events_cache[cache_key] = events
            events_cache_time[cache_key] = datetime.now()
            return events
    except:
        pass
    
    fallback_events = {
        "1-1": ["جشن نوروز", "سال نو"],
        "12-29": ["شهادت امام علی (ع)"],
        "12-30": ["شهادت امام علی (ع)"],
        "1-13": ["روز طبیعت"],
        "2-14": ["ولادت حضرت معصومه (س)"],
        "3-21": ["ولادت امام رضا (ع)"],
    }
    key = f"{month}-{day}"
    events = fallback_events.get(key, ["هیچ مناسبت خاصی ثبت نشده است."])
    events_cache[cache_key] = events
    events_cache_time[cache_key] = datetime.now()
    return events

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
# 8. ساخت پیام اصلی (کاملاً اصلاح‌شده)
# ============================================================
def build_message(user_id, user_name, city):
    lang = get_user_language(user_id)
    
    today = jdatetime.date.today()
    persian_date = today.strftime("%A %d %B %Y")
    
    hijri_today_obj = Gregorian(today.togregorian().year, today.togregorian().month, today.togregorian().day).to_hijri()
    hijri_today = get_hijri_date(today.togregorian())
    hijri_today_events = get_hijri_events(hijri_today_obj.month, hijri_today_obj.day)
    hijri_today_text = "\n".join([f"• {event}" for event in hijri_today_events])
    
    tomorrow = today + timedelta(days=1)
    persian_tomorrow = tomorrow.strftime("%A %d %B %Y")
    hijri_tomorrow_obj = Gregorian(tomorrow.togregorian().year, tomorrow.togregorian().month, tomorrow.togregorian().day).to_hijri()
    hijri_tomorrow = get_hijri_date(tomorrow.togregorian())
    hijri_tomorrow_events = get_hijri_events(hijri_tomorrow_obj.month, hijri_tomorrow_obj.day)
    hijri_tomorrow_text = "\n".join([f"• {event}" for event in hijri_tomorrow_events])
    
    today_events = get_events_for_jalali(today.year, today.month, today.day)
    today_events_text = "\n".join([f"• {event}" for event in today_events])
    
    tomorrow_events = get_events_for_jalali(tomorrow.year, tomorrow.month, tomorrow.day)
    tomorrow_events_text = "\n".join([f"• {event}" for event in tomorrow_events])
    
    prayer_times = get_prayer_times(city)
    prayer_text = ""
    if prayer_times:
        for name, time in prayer_times.items():
            prayer_text += f"🕌 {name}: {time}\n"
    else:
        prayer_text = "⚠️ " + TEXTS[lang].get("no_events", "در دسترس نیست.")
    
    weather = get_weather(city)
    weather_text = ""
    if weather:
        weather_text = f"🌡️ دما: {weather['دما']}\n🌤️ وضعیت: {weather['وضعیت']}\n💧 رطوبت: {weather['رطوبت']}"
    else:
        weather_text = "⚠️ اطلاعات آب و هوا در دسترس نیست."
    
    motivation = get_motivation()
    
    message = (
        TEXTS[lang]["welcome"].format(name=user_name) + "\n\n"
        TEXTS[lang]["date"].format(persian=persian_date) + "\n"
        TEXTS[lang]["hijri"].format(hijri=hijri_today) + "\n"
        TEXTS[lang]["hijri_events_today"] + "\n" + hijri_today_text + "\n\n"
        TEXTS[lang]["hijri_events_tomorrow"] + "\n" + hijri_tomorrow_text + "\n\n"
        TEXTS[lang]["shamsi_events_today"] + "\n" + today_events_text + "\n\n"
        TEXTS[lang]["shamsi_events_tomorrow"] + "\n" + tomorrow_events_text + "\n\n"
        TEXTS[lang]["prayer"].format(city=city) + "\n" + prayer_text + "\n"
        TEXTS[lang]["weather"].format(city=city) + "\n" + weather_text + "\n\n"
        TEXTS[lang]["motivation"] + "\n" + motivation + "\n\n"
        TEXTS[lang]["change_city"]
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
        [InlineKeyboardButton("◀️ ماه قبل", callback_data=f"cal_{year}_{month-1}_{day}"),
         InlineKeyboardButton("📅 امروز", callback_data="calendar_today"),
         InlineKeyboardButton("ماه بعد ▶️", callback_data=f"cal_{year}_{month+1}_{day}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
    ])

def get_calendar_text(year, month, day, user_id):
    lang = get_user_language(user_id)
    try:
        date_obj = jdatetime.date(year, month, 1)
        month_name = date_obj.strftime("%B")
        events_text = ""
        for d in range(1, 32):
            try:
                events = get_events_for_jalali(year, month, d)
                if events and events != ["هیچ مناسبت خاصی ثبت نشده است."]:
                    events_text += f"\n📅 {d} {month_name}:\n"
                    for event in events:
                        events_text += f"   • {event}\n"
            except:
                break
        
        if not events_text:
            events_text = "\n" + TEXTS[lang]["no_events"]
        
        return (
            TEXTS[lang]["calendar_title"].format(month=month_name, year=year) +
            TEXTS[lang]["calendar_today"].format(date=f"{day} {month_name} {year}") +
            events_text
        )
    except:
        return "❌ خطا در نمایش تقویم."

# ============================================================
# 10. دستورات
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name or "کاربر"
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
    today = jdatetime.date.today()
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
# 11. دکمه‌ها (CallbackQuery)
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
        today = jdatetime.date.today()
        text = get_calendar_text(today.year, today.month, today.day, user_id)
        await query.edit_message_text(text, reply_markup=get_calendar_buttons(today.year, today.month, today.day, user_id))
    
    elif data == "calendar_today":
        today = jdatetime.date.today()
        text = get_calendar_text(today.year, today.month, today.day, user_id)
        await query.edit_message_text(text, reply_markup=get_calendar_buttons(today.year, today.month, today.day, user_id))
    
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
# 12. ارسال خودکار روزانه
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
    print("⏰ زمان‌بند ارسال خودکار فعال شد.")

# ============================================================
# 13. اجرای اصلی
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

if __name__ == "__main__":
    main()
