"""
AI Telegram Bot - har bir xabarga avtomatik javob beradi (Claude AI orqali)
"""

import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from anthropic import Anthropic

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = (
    "Sen do'stona, yordamchi Telegram botsan. "
    "Foydalanuvchilarga o'zbek tilida, qisqa va aniq javob ber. "
    "Agar savol boshqa tilda bo'lsa, o'sha tilda javob ber."
)

chat_history = {}
MAX_HISTORY = 10

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

client = Anthropic(api_key=ANTHROPIC_API_KEY)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Men AI botman \U0001F916\n"
        "Menga istalgan savolni yozing - tez orada javob beraman."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_history.pop(chat_id, None)
    await update.message.reply_text("Suhbat tarixi tozalandi")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    history = chat_history.get(chat_id, [])
    history.append({"role": "user", "content": user_text})
    history = history[-MAX_HISTORY:]

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=history,
        )
        ai_reply = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
    except Exception as e:
        logger.error(f"AI xatosi: {e}")
        ai_reply = "Kechirasiz, hozir javob bera olmadim. Birozdan so'ng qayta urinib ko'ring."

    history.append({"role": "assistant", "content": ai_reply})
    chat_history[chat_id] = history[-MAX_HISTORY:]

    await update.message.reply_text(ai_reply)


def main():
    if not TELEGRAM_TOKEN or not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "TELEGRAM_TOKEN va ANTHROPIC_API_KEY muhit o'zgaruvchilarini sozlang!"
        )

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
