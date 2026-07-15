"""
AI Telegram Bot - matn va rasmlarga javob beradi (Claude AI orqali)
"""

import os
import base64
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
    "Sen do'stona, yordamchi va bilimli Telegram botsan. "
    "Foydalanuvchilarga o'zbek tilida javob ber, agar ular boshqa tilda yozsa o'sha tilda javob ber. "
    "Savollarga aniq, tushunarli va foydali javob ber. Agar rasm yuborilsa, uni diqqat bilan tasvirlab ber "
    "va foydalanuvchi so'ragan savolga rasm asosida javob ber."
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
        "Salom! Men AI botman.\n"
        "Menga istalgan savolni yozing yoki rasm yuboring - men tahlil qilib javob beraman."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_history.pop(chat_id, None)
    await update.message.reply_text("Suhbat tarixi tozalandi")


def call_claude(chat_id, content):
    """content - user xabarining kontenti (matn yoki matn+rasm ro'yxati)"""
    history = chat_history.get(chat_id, [])
    history.append({"role": "user", "content": content})
    history = history[-MAX_HISTORY:]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=history,
    )
    ai_reply = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()

    history.append({"role": "assistant", "content": ai_reply})
    chat_history[chat_id] = history[-MAX_HISTORY:]
    return ai_reply


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        ai_reply = call_claude(chat_id, user_text)
    except Exception as e:
        logger.error(f"AI xatosi: {e}")
        ai_reply = f"Xatolik yuz berdi: {e}"

    await update.message.reply_text(ai_reply)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    caption = update.message.caption or "Bu rasmda nima ko'rsatilgan? Batafsil tushuntirib ber."

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        # Eng katta o'lchamdagi rasmni olamiz
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()
        image_b64 = base64.b64encode(bytes(photo_bytes)).decode("utf-8")

        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_b64,
                },
            },
            {"type": "text", "text": caption},
        ]

        ai_reply = call_claude(chat_id, content)
    except Exception as e:
        logger.error(f"Rasm tahlil xatosi: {e}")
        ai_reply = f"Rasmni tahlil qilishda xatolik: {e}"

    await update.message.reply_text(ai_reply)


def main():
    if not TELEGRAM_TOKEN or not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "TELEGRAM_TOKEN va ANTHROPIC_API_KEY muhit o'zgaruvchilarini sozlang!"
        )

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()



