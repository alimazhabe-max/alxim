import os
import logging
from flask import Flask
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

# ====================== لاگ ======================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ====================== Flask ======================
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return f"✅ Bot is alive!<br>Time: {__import__('datetime').datetime.now()}"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

# ====================== ربات ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! ربات فعاله ✅\n\nبرای تست /status بزن.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ ربات سالم کار می‌کنه.")

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN تنظیم نشده است!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))

    logger.info("ربات شروع شد...")
    application.run_polling()

if __name__ == "__main__":
    import threading
    threading.Thread(target=run_flask, daemon=True).start()
    main()
