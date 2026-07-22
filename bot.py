import os
import requests
from flask import Flask
from telegram.ext import Application, MessageHandler, filters
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")

PROXY = "https://api.instavideosave.com/convert"

async def handle_message(update, context):
    url = update.message.text.strip()

    try:
        r = requests.post(PROXY, json={"url": url}, timeout=10).json()
    except:
        await update.message.reply_text("⚠️ اتصال به سرور مشکل پیدا کرد…")
        return

    if r.get("download_url"):
        await update.message.reply_text(
            f"✨ لینک دانلود آماده شد!\n\n🔗 {r['download_url']}"
        )
    else:
        await update.message.reply_text(
            "🌙 سایت نتونست لینک رو بسازه… بعداً امتحان کنیم 💛"
        )

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
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
