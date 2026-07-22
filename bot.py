import os
import re
import threading
import asyncio
import aiohttp
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

INSTAGRAM_REGEX = re.compile(r'(https?://(?:www\.)?(?:instagram\.com|instagr\.am)/[^\s]+)')

# APIهای دانلود (اولویت‌دار)
DOWNLOAD_APIS = [
    "https://api.vevioz.com/api/v2/instagram",
    "https://api.savetik.net/api/instagram",
    "https://dlpanda.com/api",
]

# ---------- چک عضویت ----------
async def is_member(user_id: int, bot) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


def menu_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 ایرانی", url=f"https://t.me/{BOT_USERNAME}?start=iran")],
        [InlineKeyboardButton("🌍 خارجی", url=f"https://t.me/{BOT_USERNAME}?start=world")],
        [InlineKeyboardButton("⚡ سریع‌ترین", url=f"https://t.me/{BOT_USERNAME}?start=fast")],
        [InlineKeyboardButton("📘 استوری", url=f"https://t.me/{BOT_USERNAME}?start=story")],
        [InlineKeyboardButton("👤 پروفایل", url=f"https://t.me/{BOT_USERNAME}?start=profile")],
        [InlineKeyboardButton("ℹ️ راهنما", url=f"https://t.me/{BOT_USERNAME}?start=help")],
    ])


# ---------- دانلود async با aiohttp (بهینه) ----------
async def download_instagram(update: Update, url: str):
    status_msg = await update.message.reply_text("⏳ در حال دانلود...")

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=35)) as session:
        for api_url in DOWNLOAD_APIS:
            try:
                await status_msg.edit_text(f"🔄 اتصال به {api_url.split('//')[1].split('/')[0]}")

                async with session.get(api_url, params={"url": url}) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()

                # استخراج لینک‌ها
                media_items = []
                if isinstance(data, dict):
                    media_items = (
                        data.get("data") or 
                        data.get("medias") or 
                        data.get("urls") or 
                        data.get("download") or 
                        []
                    )

                if not media_items:
                    continue

                await status_msg.edit_text("⬇️ در حال ارسال...")

                sent = 0
                for item in media_items[:6]:   # حداکثر ۶ فایل
                    media_url = item.get("url") if isinstance(item, dict) else item.get("link") if isinstance(item, dict) else str(item)
                    if not media_url or not media_url.startswith("http"):
                        continue

                    try:
                        if any(ext in media_url.lower() for ext in ('.mp4', '.mov', '.mkv')):
                            await update.message.reply_video(media_url, supports_streaming=True, caption="✅ دانلود شد")
                        else:
                            await update.message.reply_photo(media_url, caption="✅ دانلود شد")
                        sent += 1
                    except:
                        await update.message.reply_document(media_url, caption="📄 فایل")

                if sent > 0:
                    await status_msg.edit_text(f"✅ {sent} فایل ارسال شد!")
                    return

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"خطا در API {api_url}: {e}")
                continue

    # Fallback
    await status_msg.edit_text(
        "⚠️ دانلود مستقیم در حال حاضر در دسترس نیست.\nاز لینک‌های زیر استفاده کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ FastDL", url=f"https://fastdl.app/?url={url}")],
            [InlineKeyboardButton("🌍 SnapInsta", url=f"https://snapinsta.app/?url={url}")],
        ])
    )


async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update.effective_user.id, context.bot):
        await update.message.reply_text("لطفاً ابتدا عضو کانال شوید.")
        return

    matches = INSTAGRAM_REGEX.findall(update.message.text)
    if matches:
        await download_instagram(update, matches[0])


# ---------- start و دستورات ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (کد قبلی start)
    user_id = update.effective_user.id
    if not await is_member(user_id, context.bot):
        await update.message.reply_text("برای استفاده عضو کانال شوید: https://t.me/hmhermi")
        return

    args = context.args or []
    cmd = args[0].lower() if args else ""
    
    if cmd == "iran": await iran(update, context)
    elif cmd == "world": await world(update, context)
    elif cmd == "fast": await fast(update, context)
    elif cmd == "story": await story(update, context)
    elif cmd == "profile": await profile(update, context)
    elif cmd == "help": await help_cmd(update, context)
    else:
        await update.message.reply_text("👇 منوی اصلی:", reply_markup=menu_buttons())


async def iran(update, context):
    await update.message.reply_text("🇮🇷 ایرانی:\nfastdl.app\ninstadl.ir\nsavein.io/fa")

async def world(update, context):
    await update.message.reply_text("🌍 خارجی:\nsnapinsta.app\nsaveig.app\nigram.io")

async def fast(update, context):
    await update.message.reply_text("⚡ سریع‌ترین:\nfastdl.app\nsnapinsta.app")

async def story(update, context):
    await update.message.reply_text("📘 استوری:\nstoriesig.info\nstorysaver.net")

async def profile(update, context):
    await update.message.reply_text("👤 پروفایل:\ninstadp.io")

async def help_cmd(update, context):
    await update.message.reply_text("لینک اینستاگرام را ارسال کنید.")


# ---------- Flask ----------
app_flask = Flask(__name__)
@app_flask.route("/")
def home(): return "✅ Bot is alive!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.CHAT_TYPE.PRIVATE, handle_instagram_link))
    app.add_handler(MessageHandler(filters.TEXT & filters.CHAT_TYPE.PRIVATE, start))

    print("🤖 ربات با aiohttp شروع شد...")
    app.run_polling()


if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
