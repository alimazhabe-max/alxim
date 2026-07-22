import os
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@hmhermi"

# ---------- چک عضویت ----------
async def is_member(user_id, bot):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

# ---------- منوی اصلی ----------
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 سایت‌های ایرانی", callback_data="iran")],
        [InlineKeyboardButton("🌍 سایت‌های خارجی", callback_data="world")],
        [InlineKeyboardButton("⚡ سریع‌ترین‌ها", callback_data="fast")],
        [InlineKeyboardButton("📘 استوری و هایلایت", callback_data="story")],
        [InlineKeyboardButton("👤 عکس پروفایل", callback_data="profile")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
    ])

# ---------- دکمه عضویت ----------
def join_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/hmhermi")],
        [InlineKeyboardButton("🔄 بررسی عضویت", callback_data="check_join")]
    ])

# ---------- پیام ساده ----------
async def human(update, text):
    await update.message.reply_text(text)

# ---------- هندل پیام‌ها ----------
async def handle_message(update, context):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    # اول چک عضویت
    if not await is_member(user_id, context.bot):
        await human(update, "برای استفاده از ربات، ابتدا باید عضو کانال شوید 💛")
        await update.message.reply_text("👇 لطفاً عضو شوید:", reply_markup=join_buttons())
        return

    # اگر عضو بود → منو را نشان بده
    await update.message.reply_text(
        "👇 منوی اصلی:",
        reply_markup=main_menu()
    )

# ---------- هندل دکمه‌ها ----------
async def handle_callback(update, context):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    # بررسی عضویت
    if q.data == "check_join":
        if await is_member(user_id, context.bot):
            await q.edit_message_text(
                "🎉 تبریک! ربات برای شما **به صورت رایگان و نامحدود** فعال شد.\n\n"
                "👇 منوی اصلی:",
                reply_markup=main_menu()
            )
        else:
            await q.edit_message_text(
                "❌ هنوز عضو کانال نیستید!\n👇 لطفاً عضو شوید:",
                reply_markup=join_buttons()
            )
        return

    # ---------- دسته‌بندی سایت‌ها ----------
    if q.data == "iran":
        await q.edit_message_text(
            "🇮🇷 **سایت‌های ایرانی:**\n\n"
            "• fastdl.app\n"
            "• instadl.ir\n"
            "• savein.io/fa\n"
            "• igdownloader.ir\n"
            "• instasave.ir\n"
            "• instadl.net\n\n"
            "👇 منوی اصلی:",
            reply_markup=main_menu()
        )
        return

    if q.data == "world":
        await q.edit_message_text(
            "🌍 **سایت‌های خارجی:**\n\n"
            "• snapinsta.app\n"
            "• saveig.app\n"
            "• igram.io\n"
            "• downloadgram.org\n"
            "• instadownloader.co\n"
            "• toolzu.com\n"
            "• savefrom.net\n\n"
            "👇 منوی اصلی:",
            reply_markup=main_menu()
        )
        return

    if q.data == "fast":
        await q.edit_message_text(
            "⚡ **سریع‌ترین‌ها:**\n\n"
            "• fastdl.app\n"
            "• snapinsta.app\n"
            "• saveig.app\n"
            "• igram.io\n\n"
            "👇 منوی اصلی:",
            reply_markup=main_menu()
        )
        return

    if q.data == "story":
        await q.edit_message_text(
            "📘 **استوری و هایلایت:**\n\n"
            "• storiesig.info\n"
            "• storysaver.net\n"
            "• anonyig.com\n\n"
            "👇 منوی اصلی:",
            reply_markup=main_menu()
        )
        return

    if q.data == "profile":
        await q.edit_message_text(
            "👤 **عکس پروفایل:**\n\n"
            "• instadp.io\n"
            "• fullinstadp.com\n\n"
            "👇 منوی اصلی:",
            reply_markup=main_menu()
        )
        return

    if q.data == "help":
        await q.edit_message_text(
            "ℹ️ **راهنما:**\n\n"
            "1️⃣ لینک اینستاگرام را ارسال کنید.\n"
            "2️⃣ ربات لینک را بررسی می‌کند.\n"
            "3️⃣ برای دانلود، از سایت‌های منوی اصلی استفاده کنید.\n\n"
            "👇 منوی اصلی:",
            reply_markup=main_menu()
        )
        return

# ---------- اجرای ربات ----------
def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

# ---------- Flask برای Railway ----------
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is alive"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
