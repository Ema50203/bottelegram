import os
import re
import asyncio
import logging
from urllib.parse import urlparse
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# ===========================
# Logging
# ===========================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(_name_)

# ===========================
# Environment
# ===========================
TOKEN = os.getenv("BOT_TOKEN")
CHAT_IDS = [-1002150232021]

if not TOKEN:
    raise ValueError("BOT_TOKEN not found")

# ===========================
# أنماط الفحص
# ===========================
TELEGRAM_PATTERN = r"(t\.me\/\S+|telegram\.me\/\S+|joinchat\/\S+|@\w+)"
GENERAL_LINK_PATTERN = r"(https?:\/\/[^\s]+)"

ALLOWED_DOMAINS = [
    "reuters.com",
    "bloomberg.com",
    "cnbc.com",
    "yahoo.com",
    "investing.com",
    "tradingview.com",
    "arabnews.com",
    "aawsat.com"
]

WARNING_TEXT = (
    "🚫 تم حظر مستخدم بسبب نشر رابط مخالف.\n"
    "🛡 القروب محمي تلقائيًا."
)

# ===========================
# أدوات مساعدة
# ===========================
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id
        )
        return member.status in ["administrator", "creator"]
    except:
        return False

def domain_allowed(url):
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    return any(domain.endswith(d) for d in ALLOWED_DOMAINS)

async def execute_ban(message, context):
    try:
        await message.delete()
        await context.bot.ban_chat_member(
            message.chat.id,
            message.from_user.id
        )
        await context.bot.send_message(
            chat_id=message.chat.id,
            text=WARNING_TEXT
        )
        logger.info(f"🔥 BANNED: {message.from_user.id}")
    except Exception as e:
        logger.error(f"Ban error: {e}")

# ===========================
# نظام الحظر الفوري
# ===========================
async def moderate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    if await is_admin(update, context):
        return

    text = (message.text or message.caption or "").lower()

    # أي رابط تيليجرام = حظر فوري
    if re.search(TELEGRAM_PATTERN, text):
        await execute_ban(message, context)
        return

    # أي رابط خارجي غير مسموح = حظر فوري
    links = re.findall(GENERAL_LINK_PATTERN, text)
    for link in links:
        if not domain_allowed(link):
            await execute_ban(message, context)
            return

# ===========================
# تحذير دوري
# ===========================
async def periodic_warning(context: ContextTypes.DEFAULT_TYPE):
    for chat_id in CHAT_IDS:
        try:
            await context.bot.send_message(chat_id, "🛡 الحماية مفعّلة 24/7")
        except:
            pass

# ===========================
# تشغيل
# ===========================
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, moderate)
    )

    app.job_queue.run_repeating(periodic_warning, interval=10800, first=20)

    logger.info("🚨 Military Mode Activated")
    await app.run_polling()

if _name_ == "_main_":
    asyncio.run(main())