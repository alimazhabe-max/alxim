import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import jdatetime
import os
from rokh import get_today_events, DateSystem  # اضافه کردن کتابخانه rokh

# --- گرفتن توکن از محیط (Render) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("متغیر BOT_TOKEN در محیط تنظیم نشده است!")

# --- دیکشنری برای ذخیره شهر هر کاربر ---
user_cities = {}

def get_user_city(user_id):
    return user_cities.get(user_id, "Tehran")

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

# --- تابع جدید برای دریافت رویدادهای امروز ---
def get_today_events():
    try:
        # دریافت رویدادهای امروز با کتابخانه rokh
        events_data = get_today_events()
        events_list = []
        
        # استخراج رویدادهای شمسی
        if events_data and 'events' in events_data and 'jalali' in events_data['events']:
            for event in events_data['events']['jalali']:
                events_list.append(event['description'])
        
        # اگر رویدادی نبود، پیام خاصی نمایش بده
        if not events_list:
            return ["امروز هیچ مناسبت خاصی ثبت نشده است."]
        return events_list
    except Exception as e:
        print(f"خطا در دریافت رویدادهای امروز: {e}")
        return ["امکان دریافت مناسبت‌های امروز وجود ندارد."]

# --- دستور /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    city = get_user_city(user_id)
    
    persian_date = get_persian_date()
    
    # دریافت اوقات شرعی
    prayer_times = get_prayer_times(city)
    prayer_text = ""
    if prayer_times:
        for name, time in prayer_times.items():
            prayer_text += f"🕌 {name}: {time}\n"
    else:
        prayer_text = "⚠️ اوقات شرعی در دسترس نیست."
    
    # دریافت آب و هوا
    weather = get_weather(city)
    weather_text = ""
    if weather:
        weather_text = f"🌡️ دما: {weather['دما']}\n🌤️ وضعیت: {weather['وضعیت']}\n💧 رطوبت: {weather['رطوبت']}"
    else:
        weather_text = "⚠️ اطلاعات آب و هوا در دسترس نیست."

    # دریافت رویدادهای امروز
    today_events = get_today_events()
    events_text = "\n".join([f"• {event}" for event in today_events])

    # ساخت پیام نهایی با بخش جدید رویدادها
    message = (
        f"👋 سلام {user.first_name} عزیز!\n\n"
        f"📅 {persian_date}\n"
        f"📌 **مناسبت‌های امروز:**\n{events_text}\n\n"
        f"⏰ **اوقات شرعی امروز ({city}):**\n{prayer_text}\n"
        f"🌦️ **آب و هوای {city}:**\n{weather_text}\n\n"
        f"💡 برای تغییر شهر، از دستور `/city` استفاده کن.\n"
        f"مثال: `/city مشهد`"
    )
    
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

# --- اجرای اصلی ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("city", set_city))
    print("✅ ربات با تقویم کامل و مناسبت‌ها روشن شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
