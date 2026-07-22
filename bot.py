import os
import requests
from telegram.ext import Application, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

def download_instagram(url):
    api = f"https://api.dlydown.com/instagram?url={url}"
    r = requests.get(api).json()
    return r["result"][0]["url"]

async def handle_message(update, context):
    url = update.message.text
    try:
        video = download_instagram(url)
        await update.message.reply_video(video)
    except Exception as e:
        await update.message.reply_text("یا لینک اشتباهه، یا ویدیو پیدا نشد.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
