import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import pytz
import jdatetime

# --- توکن ربات را اینجا قرار بده (از @BotFather بگیر) ---
BOT_TOKEN = "توکن_ربات_خودت_را_اینجا_بگذار"

# --- شهر و کشور برای اوقات شرعی و آب و هوا ---
CITY = "Tehran"
COUNTRY = "Iran"

# --- کلید API برای آب و هوا (از سایت openweathermap.org بگیر) ---
WEATHER_API_KEY = "کلید_ایپی_آب_و_هوا_خودت_را_اینجا_بگذار"

# --- آدرس‌های API ---
PRAYER_API_URL = f"https://api.aladhan.com/v1/timingsByCity?city={CITY}&country={COUNTRY}&method=8"
WEATHER_API_URL = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_API_KEY}&units=metric&lang=fa"

# --- تابع دریافت اوقات شرعی ---
def get_prayer_times():
    try:
        response = requests.get(PRAYER_API_URL, timeout=10)
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

# --- تابع دریافت آب و هوا ---
def get_weather():
    try:
        response = requests.get(WEATHER_API_URL, timeout=10)
        data = response.json()
        return {
            "دما": f"{data['main']['temp']}°C",
            "وضعیت": data["weather"][0]["description"],
            "رطوبت": f"{data['main']['humidity']}%",
        }
    except:
        return None

# --- تابع دریافت تاریخ شمسی امروز با کتابخانه jdatetime ---
def get_persian_date():
    today = jdatetime.date.today()
    return today.strftime("%A %d %B %Y")  # مثلاً: یکشنبه ۰۳ مرداد ۱۴۰۴

# --- دستور /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # دریافت تاریخ شمسی
    persian_date = get_persian_date()

    # دریافت اوقات شرعی
    prayer_times = get_prayer_times()
    prayer_text = ""
    if prayer_times:
        for name, time in prayer_times.items():
            prayer_text += f"🕌 {name}: {time}\n"
    else:
        prayer_text = "⚠️ اوقات شرعی در دسترس نیست."

    # دریافت آب و هوا
    weather = get_weather()
    weather_text = ""
    if weather:
        weather_text = f"🌡️ دما: {weather['دما']}\n🌤️ وضعیت: {weather['وضعیت']}\n💧 رطوبت: {weather['رطوبت']}"
    else:
        weather_text = "⚠️ اطلاعات آب و هوا در دسترس نیست."

    # ساخت پیام نهایی
    message = (
        f"👋 سلام {user.first_name} عزیز!\n\n"
        f"📅 {persian_date}\n\n"
        f"⏰ **اوقات شرعی امروز ({CITY}):**\n{prayer_text}\n"
        f"🌦️ **آب و هوای {CITY}:**\n{weather_text}"
    )

    await update.message.reply_text(message)

# --- اجرای اصلی ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("ربات روشن شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
