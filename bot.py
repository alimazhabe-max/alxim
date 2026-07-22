import os
import requests
from telegram.ext import Application, MessageHandler, filters
from flask import Flask
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Telegram bot ---
def download_instagram(url):
    api = f"https://api.dlydown.com/instagram?url={url}"
    r = requests.get(api).json()
    return r["result"][0]["url"]

async def handle_message(update, context):
    url = update.message.text
    try:
        video = download_instagram(url)
        await update.message.reply_video(video)
    except:
        await update.message.reply_text("لینک اشتباه یا ویدیو پیدا نشد.")

def run_bot():
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(MessageHandler(filters.TEXT, handle_message))
    bot_app.run_polling()

# --- Flask server ---
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is running!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    # Run Flask in a thread
    threading.Thread(target=run_flask).start()

    # Run bot in main thread
    run_bot()
