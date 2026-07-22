import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 ربات فعال شد!\nلینک اینستاگرام بفرست.")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("در حال توسعه...")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    
    print("ربات شروع شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
