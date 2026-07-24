import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import jdatetime
import os
from rokh import get_today_events
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import random
import asyncio

# --- گرفتن توکن از محیط ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("متغیر BOT_TOKEN در محیط تنظیم نشده است!")

# --- دیکشنری برای ذخیره شهر هر کاربر ---
user_cities = {}

# --- مجموعه برای ذخیره کاربرانی که ربات رو استارت کردن ---
subscribed_users = set()

# --- لیست پیام‌های انگیزشی (غیرتکراری) ---
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
last_motivation_index = -1  # برای جلوگیری از تکرار پشت سر هم

def get_motivation():
    global last_motivation_index
    # انتخاب یک پیام غیرتکراری
    if len(motivation_messages) == 1:
        return motivation_messages[0]
    
    index = random.randint(0, len(motivation_messages) - 1)
    while index == last_motivation_index:
        index = random.randint(0, len(motivation_messages) - 1)
    last_motivation_index = index
    return motivation_messages[index]

# --- توابع اصلی ---
def get_user_city(user_id):
    return user_cities.get(user_id, "قم")  # پیش‌فرض: قم

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
    except Exception as e:
        print(f"خطا در دریافت اوقات شرعی برای {city}: {e}")
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
    except Exception as e:
        print(f"خطا در دریافت آب و هوا برای {city}: {e}")
        return None

def get_persian_date():
    today = jdatetime.date.today()
    return today.strftime("%A %d %B %Y")

def get_today_events():
    try:
        events_data = get_today_events()
        events_list = []
        if events_data and 'events' in events_data and 'jalali' in events_data['events']:
            for event in events_data['events']['jalali']:
                events_list.append(event['description'])
        if not events_list:
            return ["امروز هیچ مناسبت خاصی ثبت نشده است."]
        return events_list
    except Exception as e:
        print(f"خطا در دریافت رویدادهای امروز: {e}")
        return ["امکان دریافت مناسبت‌های امروز وجود ندارد."]

# --- تابع ساخت پیام کامل ---
def build_message(user_name, city):
    persian_date = get_persian_date()
    
    # اوقات شرعی
    prayer_times = get_prayer_times(city)
    prayer_text = ""
    if prayer_times:
        for name, time in prayer_times.items():
            prayer_text += f"🕌 {name}: {time}\n"
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
    today_events = get_today_events()
    events_text = "\n".join([f"• {event}" for event in today_events])
    
    # پیام انگیزشی
    motivation = get_motivation()
    
    # ساخت پیام نهایی (فانتزی‌تر)
    message = (
        f"🌟 **سلام {user_name} عزیز!** 🌟\n\n"
        f"📅 {persian_date}\n"
        f"📌 **مناسبت‌های امروز:**\n{events_text}\n\n"
        f"⏰ **اوقات شرعی امروز ({city}):**\n{prayer_text}\n"
        f"🌦️ **آب و هوای {city}:**\n{weather_text}\n\n"
        f"💖 **پیام انگیزشی روز:**\n{motivation}\n\n"
        f"🔔 برای تغییر شهر، دستور `/city` را بفرستید.\n"
        f"مثال: `/city مشهد`"
    )
    return message

# --- دستور /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    city = get_user_city(user_id)
    
    # ذخیره کاربر در لیست اشتراک
    subscribed_users.add(user_id)
    
    message = build_message(user.first_name, city)
    await update.message.reply_text(message)

# --- دستور /city برای تغییر شهر ---
async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    args = context.args
    if not args:
        await update.message.reply_text(
            "❌ لطفاً نام شهر را بعد از دستور وارد کن.\n"
            "مثال: `/city مشهد`"
        )
        return
    
    new_city = " ".join(args)
    
    # تست معتبر بودن شهر
    test_weather = get_weather(new_city)
    if not test_weather:
        await update.message.reply_text(
            f"❌ شهر '{new_city}' پیدا نشد. لطفاً نام شهر رو درست وارد کن."
        )
        return
    
    user_cities[user_id] = new_city
    await update.message.reply_text(
        f"✅ شهر شما به **{new_city}** تغییر کرد.\n"
        f"برای مشاهده اطلاعات، دوباره `/start` رو بفرست."
    )

# --- تابع ارسال خودکار روزانه (ساعت 00:00) ---
async def send_daily_messages(app):
    print("⏰ ارسال خودکار روزانه شروع شد...")
    for user_id in list(subscribed_users):
        try:
            city = get_user_city(user_id)
            # دریافت نام کاربر از ربات (اگه ممکن باشه)
            user_name = "کاربر گرامی"
            try:
                chat = await app.bot.get_chat(user_id)
                user_name = chat.first_name or "کاربر گرامی"
            except:
                pass
            
            message = build_message(user_name, city)
            await app.bot.send_message(chat_id=user_id, text=message)
            print(f"✅ پیام به کاربر {user_id} ارسال شد.")
        except Exception as e:
            print(f"❌ خطا در ارسال به کاربر {user_id}: {e}")
    print("🏁 ارسال خودکار روزانه پایان یافت.")

# --- تابع راه‌اندازی زمان‌بند ---
def start_scheduler(app):
    scheduler = BackgroundScheduler()
    # زمان‌بندی برای ساعت 00:00 هر روز (به وقت تهران)
    scheduler.add_job(
        lambda: asyncio.create_task(send_daily_messages(app)),
        CronTrigger(hour=0, minute=0, timezone="Asia/Tehran")
    )
    scheduler.start()
    print("⏰ زمان‌بند ارسال خودکار فعال شد (هر روز ساعت 00:00).")

# --- اجرای اصلی ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("city", set_city))
    
    # راه‌اندازی زمان‌بند
    start_scheduler(app)
    
    print("✅ ربات با ارسال خودکار و پیام انگیزشی روشن شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
