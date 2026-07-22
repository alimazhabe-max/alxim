import os
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@hmhermi"

async def is_member(user_id, bot):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 ایرانی", callback_data="iran")],
        [InlineKeyboardButton("🌍 خارجی", callback_data="world")],
        [InlineKeyboardButton("⚡ سریع‌ترین", callback_data="fast")],
        [InlineKeyboardButton("📘 استوری", callback_data="story")],
        [InlineKeyboardButton("👤 پروفایل", callback_data="profile")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
    ])

def join_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 عضویت", url="https://t.me/hmhermi")],
        [InlineKeyboardButton("🔄 بررسی", callback_data="check_join")]
    ])

async def handle_message(update, context):
    user_id = update.message.from_user.id

    if not await is_member(user_id, context.bot):
        await update.message.chat.send_message(
            "برای استفاده از ربات، ابتدا باید عضو کانال شوید 💛",
            reply_markup=join_buttons()
        )
        return

    await update.message.chat.send_message(
        "👇 منوی اصلی:",
        reply_markup=main_menu()
    )

async def handle_callback(update, context):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    if q.data == "check_join":
        if await is_member(user_id, context.bot):
            await q.edit_message_text(
                "🎉 فعال شد!\n👇 منوی اصلی:",
                reply_markup=main_menu()
            )
        else:
            await q.edit_message_text(
                "❌ هنوز عضو نیستید!",
                reply_markup=join_buttons()
            )
        return

    if q.data == "iran":
        await q.edit_message_text(
            "🇮🇷 ایرانی:\nfastdl.app\ninstadl.ir\nsavein.io/fa\n\n👇 منوی اصلی:",
            reply_markup=main_menu()
        )
        return

    if q.data == "world":
        await q.edit_message_text(
            "🌍 خارجی:\nsnapinsta.app\nsaveig.app\nigram.io\n\n👇 منوی اصلی:",
            reply_markup=main_menu()
        )
        return

    if q.data == "fast":
        await q.edit_message_text(
            "⚡ سریع‌ترین:\nfastdl.app\nsnapinsta.app\nsaveig.app\n\n👇 منوی اصلی:",
            reply_markup=main_menu()
        )
        return

    if q.data == "story":
        await q.edit_message_text(
            "📘 استوری:\nstorysaver.net\nstoriesig.info\n\n👇 منوی اصلی:",
            reply_markup=main_menu()
        )
        return

    if q.data == "profile":
        await q.edit_message_text(
            "👤 پروفایل:\ninstadp.io\nfullinstadp.com\n\n👇 منوی اصلی:",
            reply_markup=main_menu()
        )
        return

    if q.data == "help":
        await q.edit_message_text(
            "ℹ️ راهنما:\nلینک اینستاگرام را بفرست.\n👇 منوی اصلی:",
            reply_markup=main_menu()
        )
        return

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is alive"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
