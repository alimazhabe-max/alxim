import os
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = "https://alxim-1.onrender.com/webhook"

app = Flask(__name__)

# Telegram bot setup
application = Application.builder().token(BOT_TOKEN).build()

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

application.add_handler(MessageHandler(filters.TEXT, handle_message))

# Webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "ok"

# Home page
@app.route("/")
def home():
    return "Bot is running!"

if __name__ == "__main__":
    # Set webhook
    application.bot.set_webhook(WEBHOOK_URL)

    # Run Flask server
    app.run(host="0.0.0.0", port=10000)
