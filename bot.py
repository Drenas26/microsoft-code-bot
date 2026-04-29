import asyncio
import logging
from time import time
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from microsoft_client import MicrosoftClient
from config import TELEGRAM_TOKEN, FIRSTMAIL_API_KEY, CHECK_ATTEMPTS, CHECK_INTERVAL_FIRST, CHECK_INTERVAL_SECOND

# === Rate limiting ===
user_last_request = defaultdict(float)
RATE_LIMIT_SECONDS = 5

# Настройка таймаутов
request_kwargs = {
    'connect_timeout': 60.0,
    'read_timeout': 60.0,
    'write_timeout': 60.0,
    'pool_timeout': 60.0,
}
request = HTTPXRequest(**request_kwargs)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


class MicrosoftCodeBot:
    def __init__(self):
        self.client = MicrosoftClient(FIRSTMAIL_API_KEY)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self._check_rate_limit(user_id, update):
            return
        await update.message.reply_text(
            "🔐 *Microsoft Code Bot*\n\n"
            "I help you get verification codes from Microsoft (e.g., for adding a recovery email).\n\n"
            "*How it works:*\n"
            "1️⃣ Request a verification code from Microsoft to your email\n"
            "2️⃣ Send me the email address and password in the format:\n"
            "   `email:password`\n"
            "3️⃣ I'll find the 6-digit code and send it to you\n\n"
            "*Commands:*\n"
            "/start - Start the bot\n"
            "/help - Get help\n\n"
            "*Example:*\n"
            "`hifmwaub@polosmail.com:biqzmrlnY!4552`\n\n"
            "Need help? @Drenas26",
            parse_mode='Markdown'
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self._check_rate_limit(user_id, update):
            return
        await update.message.reply_text(
            "📚 *Help & Instructions*\n\n"
            "*How to get a Microsoft verification code:*\n\n"
            "1. Request a code from Microsoft (e.g., when adding a recovery email)\n"
            "2. Microsoft will send an email to your Firstmail inbox\n"
            "3. Copy the email address and password and send me in format:\n"
            "   `email:password`\n"
            "4. I'll find the 6-digit code and send it to you\n\n"
            f"*Limitations:*\n"
            f"• {CHECK_ATTEMPTS} checks (at {CHECK_INTERVAL_FIRST} and {CHECK_INTERVAL_FIRST + CHECK_INTERVAL_SECOND} seconds)\n"
            f"• Works only with emails from `accountprotection.microsoft.com`\n\n"
            "*Commands:*\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n\n"
            "Need help? @Drenas26",
            parse_mode='Markdown'
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self._check_rate_limit(user_id, update):
            return

        text = update.message.text.strip()
        # Разделяем по первому двоеточию
        if ':' not in text:
            await update.message.reply_text(
                "❌ Please send email and password in format: `email:password`\n\n"
                "Example: `hifmwaub@polosmail.com:biqzmrlnY!4552`",
                parse_mode='Markdown'
            )
            return

        email, password = text.split(':', 1)
        email = email.strip()
        password = password.strip()

        if '@' not in email or not password:
            await update.message.reply_text("❌ Please provide a valid email address and non‑empty password.")
            return

        status_msg = await update.message.reply_text(
            f"📧 `{email}`\n🔄 Searching for Microsoft code...\n⏳ {CHECK_ATTEMPTS} checks (at {CHECK_INTERVAL_FIRST} and {CHECK_INTERVAL_FIRST + CHECK_INTERVAL_SECOND} seconds)",
            parse_mode='Markdown'
        )

        try:
            code = await asyncio.to_thread(
                self.client.find_microsoft_code,
                email=email,
                password=password,
                attempts=CHECK_ATTEMPTS,
                interval_first=CHECK_INTERVAL_FIRST,
                interval_second=CHECK_INTERVAL_SECOND
            )
            if code:
                await status_msg.edit_text(
                    f"✅ *Verification code found!*\n\n📧 `{email}`\n\n🔐 `{code}`",
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
            else:
                await status_msg.edit_text(
                    f"❌ *Code not found*\n\n📧 `{email}`\n\nPlease try:\n• Request a new code from Microsoft\n• Check email/password are correct",
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error processing {email}: {e}")
            await status_msg.edit_text(
                f"❌ *Error*\n\n📧 `{email}`\n\n```\n{str(e)[:150]}\n```",
                parse_mode='Markdown'
            )

    def _check_rate_limit(self, user_id: int, update: Update) -> bool:
        now = time()
        last = user_last_request[user_id]
        if now - last < RATE_LIMIT_SECONDS:
            wait = int(RATE_LIMIT_SECONDS - (now - last)) + 1
            asyncio.create_task(
                update.message.reply_text(f"⏳ Please wait {wait} seconds before sending another request.")
            )
            return False
        user_last_request[user_id] = now
        return True


def main():
    if not TELEGRAM_TOKEN:
        print("❌ Error: TELEGRAM_TOKEN not found in .env")
        return
    if not FIRSTMAIL_API_KEY:
        print("❌ Error: FIRSTMAIL_API_KEY not found in .env")
        return

    print("🤖 Starting Microsoft Code Bot...")
    print("✅ Firstmail client ready")
    print(f"⚙️ Settings: {CHECK_ATTEMPTS} checks (at {CHECK_INTERVAL_FIRST} and {CHECK_INTERVAL_FIRST + CHECK_INTERVAL_SECOND} seconds)")
    print("📌 Rate limiting: 5 seconds between requests per user")

    bot = MicrosoftCodeBot()
    app = Application.builder().token(TELEGRAM_TOKEN).request(request).build()
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CommandHandler("help", bot.help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))

    print("✅ Bot is running and ready!")
    app.run_polling()


if __name__ == "__main__":
    main()