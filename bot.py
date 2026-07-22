import os
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@hmhermi"
BOT_USERNAME = "YOUR_BOT_USERNAME"  # بدون @

async def is_member(user_id, bot):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

def menu_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 ایرانی", url=f"tg://resolve?domain={BOT_USERNAME}&start=iran")],
        [InlineKeyboardButton("🌍 خارجی", url=f"tg://resolve?domain={BOT_USERNAME}&start=world")],
        [InlineKeyboardButton("⚡ سریع‌ترین", url=f"tg://resolve?domain={BOT_USERNAME}&start=fast")],
        [InlineKeyboardButton("📘 استوری", url=f"tg://resolve?domain={BOT_USERNAME}&start=story")],
        [InlineKeyboardButton("👤 پروفایل", url=f"tg://resolve?domain={BOT_USERNAME}&start=profile")],
        [InlineKeyboardButton("ℹ️ راهنما", url=f"tg://resolve?domain={BOT_USERNAME}&start=help")]
    ])

async def start(update, context):
    user_id = update.message.from_user.id

    if not await is_member(user_id, context.bot):
        await update.message.reply_text(
            "برای استفاده از ربات، ابتدا باید عضو کانال شوید 💛\n\n"
            "https://t.me/hmhermi\n\n"
            "بعد از عضویت دستور /start را بزنید."
        )
        return

    await update.message.reply_text(
        "👇 منوی اصلی:",
        reply_markup=menu_buttons()
    )

async def iran(update, context):
    await update.message.reply_text(
        "🇮🇷 ایرانی:\nfastdl.app\ninstadl.ir\nsavein.io/fa\nigdownloader.ir\ninstasave.ir\ninstadl.net"
    )

async def world(update, context):
    await update.message.reply_text(
        "🌍 خارجی:\nsnapinsta.app\nsaveig.app\nigram.io\ndownloadgram.org\ninstadownloader.co\ntoolzu.com\nsavefrom.net"
    )

async def fast(update, context):
    await update.message.reply_text(
        "⚡ سریع‌ترین:\nfastdl.app\nsnapinsta.app\nsaveig.app\nigram.io"
    )

async def story(update, context):
    await update.message.reply_text(
        "📘 استوری:\nstorysaver.net\nstoriesig.info\nanonyig.com"
    )

async def profile(update, context):
    await update.message.reply_text(
        "👤 پروفایل:\ninstadp.io\nfullinstadp.com"
    )

async def help_cmd(update, context):
    await update.message.reply_text(
        "ℹ️ راهنما:\nلینک اینستاگرام را بفرست.\nبرای دانلود از سایت‌های معرفی‌شده استفاده کن."
    )

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("iran", iran))
    app.add_handler(CommandHandler("world", world))
    app.add_handler(CommandHandler("fast", fast))
    app.add_handler(CommandHandler("story", story))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("help", help_cmd))

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
