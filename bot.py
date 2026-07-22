import os
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@hmhermi"
BOT_USERNAME = "almix1bot"

# ---------- چک عضویت ----------
async def is_member(user_id: int, bot) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


# ---------- دکمه‌های شیشه‌ای ----------
def menu_buttons() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 ایرانی", url=f"https://t.me/{BOT_USERNAME}?start=iran")],
        [InlineKeyboardButton("🌍 خارجی", url=f"https://t.me/{BOT_USERNAME}?start=world")],
        [InlineKeyboardButton("⚡ سریع‌ترین", url=f"https://t.me/{BOT_USERNAME}?start=fast")],
        [InlineKeyboardButton("📘 استوری", url=f"https://t.me/{BOT_USERNAME}?start=story")],
        [InlineKeyboardButton("👤 پروفایل", url=f"https://t.me/{BOT_USERNAME}?start=profile")],
        [InlineKeyboardButton("ℹ️ راهنما", url=f"https://t.me/{BOT_USERNAME}?start=help")],
    ])


# ---------- /start + Deep Link ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_member(user_id, context.bot):
        await update.message.reply_text(
            "برای استفاده از ربات، ابتدا باید عضو کانال شوید 💛\n\n"
            "https://t.me/hmhermi\n\n"
            "بعد از عضویت دوباره دستور /start را بزنید."
        )
        return

    # چک کردن آرگومان deep link
    args = context.args
    if args:
        command = args[0].lower()
        if command == "iran":
            await iran(update, context)
            return
        elif command == "world":
            await world(update, context)
            return
        elif command == "fast":
            await fast(update, context)
            return
        elif command == "story":
            await story(update, context)
            return
        elif command == "profile":
            await profile(update, context)
            return
        elif command == "help":
            await help_cmd(update, context)
            return

    # نمایش منو اصلی
    await update.message.reply_text("👇 منوی اصلی:", reply_markup=menu_buttons())


# ---------- دستورهای محتوا ----------
async def iran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🇮🇷 **ایرانی:**\n"
        "fastdl.app\n"
        "instadl.ir\n"
        "savein.io/fa\n"
        "igdownloader.ir\n"
        "instasave.ir\n"
        "instadl.net"
    )


async def world(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 **خارجی:**\n"
        "snapinsta.app\n"
        "saveig.app\n"
        "igram.io\n"
        "downloadgram.org\n"
        "instadownloader.co\n"
        "toolzu.com\n"
        "savefrom.net"
    )


async def fast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ **سریع‌ترین:**\n"
        "fastdl.app\n"
        "snapinsta.app\n"
        "saveig.app\n"
        "igram.io"
    )


async def story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 **استوری:**\n"
        "storiesig.info\n"
        "storysaver.net\n"
        "anonyig.com"
    )


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👤 **پروفایل:**\n"
        "instadp.io\n"
        "fullinstadp.com"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ **راهنما:**\n\n"
        "فقط کافیست لینک پست، ریلز یا استوری اینستاگرام را بفرستید.\n"
        "از سایت‌های بالا برای دانلود استفاده کنید."
    )


# ---------- Flask برای نگه‌داری زنده (Railway) ----------
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "✅ Bot is alive and running!"


def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)


# ---------- اجرای ربات ----------
def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN پیدا نشد!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("iran", iran))
    app.add_handler(CommandHandler("world", world))
    app.add_handler(CommandHandler("fast", fast))
    app.add_handler(CommandHandler("story", story))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("help", help_cmd))

    # فقط پیام‌های متنی در چت خصوصی با ربات → نمایش منو
    app.add_handler(MessageHandler(filters.TEXT & filters.CHAT_TYPE.PRIVATE, start))

    print("🤖 ربات در حال اجراست...")
    app.run_polling()


if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
