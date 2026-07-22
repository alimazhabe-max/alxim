import os
import requests
from telegram.ext import Application, MessageHandler, filters
from flask import Flask

BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Flask server for Render ---
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is running!"

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

def main():
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(MessageHandler(filters.TEXT, handle_message))
    bot_app.run_polling()

if __name__ == "__main__":
    # Run Telegram bot
    import threading
    threading.Thread(target=main).start()

    # Run Flask server
    app_flask.run(host="0.0.0.0", port=10000)
