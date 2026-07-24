import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import jdatetime
import os
import json
import random
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from rokh import get_today_events

# --- گرفتن توکن از محیط ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("متغیر BOT_TOKEN در محیط تنظیم نشده است!")

# --- فایل‌های ذخیره‌سازی ---
USERS_FILE = "users.json"
LAST_MOTIVATIONAL_FILE = "last_motivational.txt"

# --- لیست پیام‌های انگیزشی (۳۰ پیام) ---
MOTIVATIONAL_MESSAGES = [
    "🌟 امروز روز جدیدی برای نوشتن داستان زیبای زندگی‌ت است.",
    "💪 قدرتی که داری، بیش از چیزی است که فکر می‌کنی.",
    "🌸 هر روز یک فرصت تازه برای شروع دوباره است.",
    "🌱 امروز روز رشد و پیشرفت توست.",
    "✨ به خودت ایمان داشته باش، تو می‌تونی.",
    "🌈 بعد از هر باران، رنگین‌کمانی در انتظار توست.",
    "🚀 برای رسیدن به اهداف‌ت، همین امروز قدم بردار.",
    "🌞 لبخند بزن، امروز روز خوبی است.",
    "💖 محبت کن، محبت ببین.",
    "🦋 تغییر از درون تو شروع می‌شود.",
    "🌟 بهترین زمان برای شروع، همیشه الان است.",
    "💪 هیچ چیز غیرممکن نیست، فقط نیاز به تلاش بیشتر دارد.",
    "🌸 زندگی زیباست، اگر نگاهت را عوض کنی.",
    "🌱 امروز را غنیمت بشمار، فردا ممکن نیست.",
    "✨ تو از آنچه فکر می‌کنی، قدرتمندتری.",
    "🌈 باور کن که می‌توانی، نیمی از راه را رفته‌ای.",
    "🚀 موفقیت، نتیجه‌ی تلاش‌های کوچک روزانه است.",
    "🌞 روزت را با انرژی مثبت شروع کن.",
    "💖 شکرگزار باش، نعمت‌هایت را ببین.",
    "🦋 هر روز یک صفحه‌ی سفید برای نوشتن است.",
    "🌟 به خودت افتخار کن، تو خاصی.",
    "💪 اگر امروز را شروع نکنی، فردا هم دیر خواهد بود.",
    "🌸 زیبایی‌های زندگی را در لحظات ساده ببین.",
    "🌱 برای رویاهایت بجنگ، ارزشش را دارد.",
    "✨ هر قدمی که برمی‌داری، تو را به هدف نزدیک‌تر می‌کند.",
    "🌈 خوشبینی، کلید موفقیت است.",
    "🚀 امروز روز تصمیم‌های بزرگ است.",
    "🌞 زندگی هدیه‌ست، از آن لذت ببر.",
    "💖 مهربانی کن، دنیا را زیباتر کن.",
    "🦋 تو می‌توانی هر چیزی که بخواهی باشی."
]

# --- دیکشنری شهرهای کاربران ---
user_cities = {}

# --- توابع ذخیره‌سازی کاربران ---
def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

# --- توابع ذخیره آخرین پیام انگیزشی ---
def get_last_motivational():
    try:
        with open(LAST_MOTIVATIONAL_FILE, "r") as f:
            return f.read().strip()
    except:
        return None

def save_last_motivational(msg):
    with open(LAST_MOTIVATIONAL_FILE, "w") as f:
        f.write(msg)

# --- انتخاب پیام انگیزشی جدید (غیرتکراری) ---
def get_new_motivational():
    last = get_last_motivational()
    available = [m for m in MOTIVATIONAL_MESSAGES if m != last]
    if not available:  # اگر همه پیام‌ها استفاده شدن، لیست رو ریست کن
        available = MOTIVATIONAL_MESSAGES
    choice = random.choice(available)
    save_last_motivational(choice)
    return choice

# --- توابع اصلی ربات ---
def get_user_city(user_id):
    return user_cities.get(str(user_id), "Tehran")

def get_prayer_times(city, country="Iran"):
    try:
        url = f"https://api.aladhan.com/v1/timingsByCity?city={city}&country={country}&method=8"
        response = requests.get(url, timeout=10)
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
        response = requests.get(url, timeout=10)
        data = response.json()
        current = data["current_condition"][0]
        return {
            "دما": f"{current['temp_C']}°C",
            "وضعیت": current["weatherDesc"][0]["value"],
            "رطوبت": f"{current['humidity']}%",
        }
    except:
        return None

def get_persian_date():
    today = jdatetime.date.today()
    return today.strftime("%A %d %B %Y")

def get_today_events_rokh():
    try:
        events_data = get_today_events()
        events_list = []
        if events_data and 'events' in events_data and 'jalali' in events_data['events']:
            for event in events_data['events']['jalali']:
                events_list.append(event['description'])
        if not events_list:
            return ["امروز هیچ مناسبت خاصی ثبت نشده است."]
        return events_list
    except:
        return ["امکان دریافت مناسبت‌های امروز وجود ندارد."]

# --- ساخت پیام کامل روز (با قالب فانتزی) ---
def build_daily_message(user_name, city, motivational):
    persian_date = get_persian_date()
    
    # اوقات شرعی
    prayer_times = get_prayer_times(city)
    prayer_text = ""
    if prayer_times:
        prayer_text = "\n".join([f"🕌 {name}: {time}" for name, time in prayer_times.items()])
    else:
        prayer_text = "⚠️ اوقات شرعی در دسترس نیست."
    
    # آب و هوا
    weather = get_weather(city)
    weather_text = ""
    if weather:
        weather_text = f"🌡️ دما: {weather['دما']}\n🌤️ وضعیت: {weather['وضعیت']}\n💧 رطوبت: {weather['رطوبت']}"
    else:
        weather_text = "⚠️ اطلاعات آب و هوا در دسترس نیست."
    
    # مناسبت‌ها
    events = get_today_events_rokh()
    events_text = "\n".join([f"• {e}" for e in events])
    
    # پیام نهایی (فانتزی با ایموجی‌های زیاد)
    message = (
        f"🌅 **صبح بخیر {user_name} جان!** 🌅\n\n"
        f"📅 **{persian_date}**\n"
        f"📌 **مناسبت‌های امروز:**\n{events_text}\n\n"
        f"⏰ **اوقات شرعی ({city}):**\n{prayer_text}\n\n"
        f"🌦️ **آب و هوای {city}:**\n{weather_text}\n\n"
        f"✨ **پیام انگیزشی روز:**\n» {motivational} «\n\n"
        f"🤖 ربات همیشه همراه شماست. روز خوبی داشته باشید! 🌸"
    )
    return message

# --- دستور /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    city = get_user_city(user_id)
    
    # ذخیره کاربر
    users = load_users()
    users.add(user_id)
    save_users(users)
    
    # انتخاب پیام انگیزشی جدید
    motivational = get_new_motivational()
    
    message = build_daily_message(user.first_name, city, motivational)
    await update.message.reply_text(message)

# --- دستور /city ---
async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    args = context.args
    if not args:
        await update.message.reply_text(
            "❌ لطفاً نام شهر را بعد از دستور وارد کن.\n"
            "مثال: `/city مشهد`"
        )
        return
    new_city = " ".join(args)
    test_weather = get_weather(new_city)
    if not test_weather:
        await update.message.reply_text(f"❌ شهر '{new_city}' پیدا نشد.")
        return
    user_cities[user_id] = new_city
    await update.message.reply_text(f"✅ شهر شما به **{new_city}** تغییر کرد.")

# --- تابع ارسال خودکار روزانه در ساعت ۰۰:۰۰ ---
async def send_daily_messages(app):
    users = load_users()
    if not users:
        print("⏳ هیچ کاربری برای ارسال خودکار وجود ندارد.")
        return
    
    # برای هر کاربر پیام ارسال کن
    for user_id in users:
        try:
            user_id_int = int(user_id)
            city = get_user_city(user_id)
            
            # دریافت اطلاعات کاربر از تلگرام (برای اسم)
            try:
                user_info = await app.bot.get_chat(user_id_int)
                user_name = user_info.first_name or "کاربر گرامی"
            except:
                user_name = "کاربر گرامی"
            
            motivational = get_new_motivational()
            message = build_daily_message(user_name, city, motivational)
            
            await app.bot.send_message(chat_id=user_id_int, text=message)
            print(f"✅ پیام روزانه برای کاربر {user_id} ارسال شد.")
            
            # تاخیر ۱ ثانیه‌ای برای جلوگیری از محدودیت
            await asyncio.sleep(1)
        except Exception as e:
            print(f"❌ خطا در ارسال برای {user_id}: {e}")

# --- اجرای اصلی ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # اضافه کردن هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("city", set_city))
    
    # تنظیم برنامه زمان‌بندی برای ارسال خودکار در ۰۰:۰۰ هر روز
    scheduler = AsyncIOScheduler(timezone="Asia/Tehran")
    scheduler.add_job(send_daily_messages, "cron", hour=0, minute=0, args=[app])
    scheduler.start()
    
    print("✅ ربات با قابلیت ارسال خودکار روزانه روشن شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
