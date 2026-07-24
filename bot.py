import os
import sys

print("1️⃣ شروع شد...")  # اولین خط

try:
    import requests
    print("2️⃣ requests نصب شد")
except Exception as e:
    print(f"❌ خطا در import requests: {e}")
    sys.exit(1)

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    print("3️⃣ telegram نصب شد")
except Exception as e:
    print(f"❌ خطا در import telegram: {e}")
    sys.exit(1)

try:
    import jdatetime
    print("4️⃣ jdatetime نصب شد")
except Exception as e:
    print(f"❌ خطا در import jdatetime: {e}")
    sys.exit(1)

# --- گرفتن توکن از محیط ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
print(f"5️⃣ BOT_TOKEN: {'✅ پیدا شد' if BOT_TOKEN else '❌ پیدا نشد!'}")

if not BOT_TOKEN:
    print("❌ متغیر BOT_TOKEN در محیط تنظیم نشده است!")
    sys.exit(1)

# --- بقیه کد ---
CITY = "Tehran"
COUNTRY = "Iran"
PRAYER_API_URL = f"https://api.aladhan.com/v1/timingsByCity?city={CITY}&country={COUNTRY}&method=8"

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
    except Exception as e:
        print(f"خطا در دریافت اوقات شرعی: {e}")
        return None

def get_weather():
    try:
        response = requests.get(f"https://wttr.in/{CITY}?format=j1", timeout=10)
        data = response.json()
        current = data["current_condition"][0]
        return {
            "دما": f"{current['temp_C']}°C",
            "وضعیت": current["weatherDesc"][0]["value"],
            "رطوبت": f"{current['humidity']}%",
        }
    except Exception as e:
        print(f"خطا در دریافت آب و هوا: {e}")
        return None

def get_persian_date():
    today = jdatetime.date.today()
    return today.strftime("%A %d %B %Y")

async def start(update, context):
    user = update.effective_user
    persian_date = get_persian_date()
    
    prayer_times = get_prayer_times()
    prayer_text = ""
    if prayer_times:
        for name, time in prayer_times.items():
            prayer_text += f"🕌 {name}: {time}\n"
    else:
        prayer_text = "⚠️ اوقات شرعی در دسترس نیست."
    
    weather = get_weather()
    weather_text = ""
    if weather:
        weather_text = f"🌡️ دما: {weather['دما']}\n🌤️ وضعیت: {weather['وضعیت']}\n💧 رطوبت: {weather['رطوبت']}"
    else:
        weather_text = "⚠️ اطلاعات آب و هوا در دسترس نیست."
    
    message = (
        f"👋 سلام {user.first_name} عزیز!\n\n"
        f"📅 {persian_date}\n\n"
        f"⏰ **اوقات شرعی امروز ({CITY}):**\n{prayer_text}\n"
        f"🌦️ **آب و هوای {CITY}:**\n{weather_text}"
    )
    
    await update.message.reply_text(message)

def main():
    print("6️⃣ در حال ساخت اپلیکیشن...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("✅ ربات روشن شد و منتظر پیام‌های شماست...")
    app.run_polling()

if __name__ == "__main__":
    print("🚀 در حال اجرا...")
    main()
