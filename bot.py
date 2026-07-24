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
# 5. دیکشنری مناسبت‌های شمسی (داخلی، بدون نیاز به rokh)
# ============================================================
shamsi_events = {
    "1-1": ["جشن نوروز", "سال نو"],
    "1-13": ["روز طبیعت"],
    "2-14": ["ولادت حضرت معصومه (س)"],
    "3-21": ["ولادت امام رضا (ع)"],
    "12-29": ["شهادت امام علی (ع)"],
    "12-30": ["شهادت امام علی (ع)"],
}

def get_shamsi_events(year, month, day):
    key = f"{month}-{day}"
    return shamsi_events.get(key, ["هیچ مناسبت خاصی ثبت نشده است."])

# ============================================================
# 6. دیکشنری کامل رویدادهای قمری (تمام ماه‌ها - خلاصه شده)
# ============================================================
hijri_events = {
    "1-1": ["آغاز سال هجرى قمرى", "يورش ابرهه به مكه", "آغاز ایام حسینی"],
    "1-10": ["شهادت امام حسین (ع)"],
    "7-27": ["عید مبعث"],
    "8-15": ["ولادت حضرت بقیه الله الاعظم (عج)"],
    "9-1": ["نزول صحف ابراهیم"],
    "10-1": ["عید فطر"],
    "11-1": ["ولادت حضرت معصومه (س)"],
    "12-10": ["عید قربان"],
    "12-18": ["عید غدیر"],
}

def get_hijri_events(hijri_month, hijri_day):
    key = f"{hijri_month}-{hijri_day}"
    return hijri_events.get(key, ["هیچ مناسبت قمری خاصی ثبت نشده است."])

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
# 8. ساخت پیام اصلی
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
    
    # مناسبت‌های شمسی (از دیکشنری داخلی)
    today_events = get_shamsi_events(today.year, today.month, today.day)
    today_events_text = "\n".join([f"• {event}" for event in today_events])
    
    tomorrow_events = get_shamsi_events(tomorrow.year, tomorrow.month, tomorrow.day)
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
                events = get_shamsi_events(year, month, d)
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
# 12. ارسال خودکار روزانه (با BackgroundScheduler)
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
