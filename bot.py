import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import jdatetime
from jdatetime import timedelta
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import random
import asyncio
from hijri_converter import Gregorian
from functools import lru_cache
from datetime import datetime, timedelta as dt_timedelta

# --- تنظیمات اولیه ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("متغیر BOT_TOKEN در محیط تنظیم نشده است!")

user_cities = {}
subscribed_users = set()

# --- لیست پیام‌های انگیزشی ---
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

# --- توابع با Retry و Cache ---
def retry_request(url, timeout=5, retries=2):
    for i in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                return response
        except:
            pass
    return None

def get_user_city(user_id):
    return user_cities.get(user_id, "قم")

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
        return {
            "دما": f"{current['temp_C']}°C",
            "وضعیت": current["weatherDesc"][0]["value"],
            "رطوبت": f"{current['humidity']}%",
        }
    except:
        return None

# --- قیمت طلا و دلار با سرویس جدید (Nerkh.io) ---
def get_gold_usd_prices():
    try:
        # سرویس Nerkh.io - کاملاً رایگان و بدون نیاز به ثبت‌نام
        url = "https://api.nerkh.io/v1/prices"  # آدرس جدید
        response = retry_request(url, timeout=5)
        if response:
            data = response.json()
            
            # پیدا کردن قیمت طلا و دلار
            gold_price = None
            usd_price = None
            
            # داده‌ها معمولاً به این شکل هستن
            if isinstance(data, dict):
                # اگر به صورت دیکشنری برگشت
                for key, value in data.items():
                    if 'gold' in key.lower() or 'طلا' in key:
                        if isinstance(value, dict) and 'price' in value:
                            gold_price = value['price']
                        else:
                            gold_price = value
                    elif 'usd' in key.lower() or 'دلار' in key:
                        if isinstance(value, dict) and 'price' in value:
                            usd_price = value['price']
                        else:
                            usd_price = value
            
            # اگر به صورت لیست برگشت
            elif isinstance(data, list):
                for item in data:
                    symbol = item.get('symbol', '').upper()
                    if symbol == 'GOLD' or symbol == 'GOLD18K' or 'طلا' in item.get('name', ''):
                        gold_price = item.get('price')
                    elif symbol == 'USD' or 'دلار' in item.get('name', ''):
                        usd_price = item.get('price')
            
            if gold_price and usd_price:
                return {
                    "طلا (۱۸ عیار)": int(gold_price),
                    "دلار": int(usd_price)
                }
    except Exception as e:
        print(f"خطا در دریافت قیمت از Nerkh.io: {e}")
    
    # --- سرویس پشتیبان: Navasan (نیاز به کلید) ---
    try:
        # این سرویس نیاز به دریافت کلید از @navasan_contact_bot دارد
        # فعلاً غیرفعال، در صورت نیاز فعالش کن
        pass
    except:
        pass
    
    return None

# --- تاریخ قمری ---
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

# --- کش کردن مناسبت‌ها ---
events_cache = {}
events_cache_time = {}

def get_events_for_jalali(year, month, day):
    cache_key = f"{year}-{month}-{day}"
    
    if cache_key in events_cache:
        cache_time = events_cache_time.get(cache_key)
        if cache_time and (datetime.now() - cache_time).seconds < 86400:
            return events_cache[cache_key]
    
    try:
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
        
        url = f"https://www.time.ir/fa/event/list/0/{year}/{month}/{day}"
        response = retry_request(url, timeout=3)
        if response:
            data = response.json()
            events = []
            if 'events' in data:
                for item in data['events']:
                    if item.get('type') == 'jalali' or 'description' in item:
                        events.append(item.get('description', item.get('title', 'رویداد')))
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

# --- ساخت پیام کامل ---
def build_message(user_name, city):
    today = jdatetime.date.today()
    persian_date = today.strftime("%A %d %B %Y")
    hijri_today = get_hijri_date(today.togregorian())
    
    tomorrow = today + timedelta(days=1)
    persian_tomorrow = tomorrow.strftime("%A %d %B %Y")
    hijri_tomorrow = get_hijri_date(tomorrow.togregorian())
    
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
        prayer_text = "⚠️ اوقات شرعی در دسترس نیست."
    
    weather = get_weather(city)
    weather_text = ""
    if weather:
        weather_text = f"🌡️ دما: {weather['دما']}\n🌤️ وضعیت: {weather['وضعیت']}\n💧 رطوبت: {weather['رطوبت']}"
    else:
        weather_text = "⚠️ اطلاعات آب و هوا در دسترس نیست."
    
    prices = get_gold_usd_prices()
    prices_text = ""
    if prices:
        prices_text = f"💰 طلا (۱۸ عیار): {prices['طلا (۱۸ عیار)']:,} تومان\n💵 دلار: {prices['دلار']:,} تومان"
    else:
        prices_text = "⚠️ قیمت طلا و دلار در دسترس نیست.\n(سرویس موقتاً در دسترس نیست، لطفاً بعداً امتحان کنید)"
    
    motivation = get_motivation()
    
    message = (
        f"🌟 **سلام {user_name} عزیز!** 🌟\n\n"
        f"📅 **امروز (شمسی):** {persian_date}\n"
        f"🌙 **امروز (قمری):** {hijri_today}\n\n"
        f"📌 **مناسبت‌های امروز:**\n{today_events_text}\n\n"
        f"🔮 **فردا (شمسی):** {persian_tomorrow}\n"
        f"🌙 **فردا (قمری):** {hijri_tomorrow}\n"
        f"📌 **وقایع فردا:**\n{tomorrow_events_text}\n\n"
        f"⏰ **اوقات شرعی امروز ({city}):**\n{prayer_text}\n"
        f"🌦️ **آب و هوای {city}:**\n{weather_text}\n\n"
        f"💰 **قیمت‌های بازار:**\n{prices_text}\n\n"
        f"💖 **پیام انگیزشی روز:**\n{motivation}\n\n"
        f"🔔 برای تغییر شهر، دستور `/city` را بفرستید.\n"
        f"مثال: `/city مشهد`"
    )
    return message

# --- دستورات ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    city = get_user_city(user_id)
    subscribed_users.add(user_id)
    message = build_message(user.first_name, city)
    await update.message.reply_text(message)

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

# --- ارسال خودکار ---
async def send_daily_messages(app):
    print("⏰ ارسال خودکار روزانه شروع شد...")
    for user_id in list(subscribed_users):
        try:
            city = get_user_city(user_id)
            user_name = "کاربر گرامی"
            try:
                chat = await app.bot.get_chat(user_id)
                user_name = chat.first_name or "کاربر گرامی"
            except:
                pass
            message = build_message(user_name, city)
            await app.bot.send_message(chat_id=user_id, text=message)
            print(f"✅ پیام به کاربر {user_id} ارسال شد.")
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"❌ خطا در ارسال به کاربر {user_id}: {e}")
    print("🏁 ارسال خودکار روزانه پایان یافت.")

def start_scheduler(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: asyncio.create_task(send_daily_messages(app)),
        CronTrigger(hour=0, minute=0, timezone="Asia/Tehran")
    )
    scheduler.start()
    print("⏰ زمان‌بند ارسال خودکار فعال شد.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("city", set_city))
    start_scheduler(app)
    print("✅ ربات بهینه‌شده با API جدید روشن شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
