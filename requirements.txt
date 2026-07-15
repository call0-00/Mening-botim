"""
AI Telegram Bot - Google Gemini orqali matn va rasmlarga javob beradi
"""

import os
import base64
import logging
import requests
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent?key=" + GEMINI_API_KEY
)

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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Men AI botman.\n"
        "Menga istalgan savolni yozing yoki rasm yuboring - men tahlil qilib javob beraman."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_history.pop(chat_id, None)
    await update.message.reply_text("Suhbat tarixi tozalandi")


def call_gemini(chat_id, parts):
    """parts - Gemini uchun kontent qismlari (matn va/yoki rasm)"""
    history = chat_history.get(chat_id, [])
    history.append({"role": "user", "parts": parts})
    history = history[-MAX_HISTORY:]

    payload = {
        "contents": history,
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
    }

    resp = requests.post(GEMINI_URL, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    ai_reply = data["candidates"][0]["content"]["parts"][0]["text"].strip()

    history.append({"role": "model", "parts": [{"text": ai_reply}]})
    chat_history[chat_id] = history[-MAX_HISTORY:]
    return ai_reply


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        ai_reply = call_gemini(chat_id, [{"text": user_text}])
    except Exception as e:
        logger.error(f"AI xatosi: {e}")
        ai_reply = f"Xatolik yuz berdi: {e}"

    await update.message.reply_text(ai_reply)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    caption = update.message.caption or "Bu rasmda nima ko'rsatilgan? Batafsil tushuntirib ber."

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()
        image_b64 = base64.b64encode(bytes(photo_bytes)).decode("utf-8")

        parts = [
            {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
            {"text": caption},
        ]

        ai_reply = call_gemini(chat_id, parts)
    except Exception as e:
        logger.error(f"Rasm tahlil xatosi: {e}")
        ai_reply = f"Rasmni tahlil qilishda xatolik: {e}"

    await update.message.reply_text(ai_reply)


def main():
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        raise RuntimeError(
            "TELEGRAM_TOKEN va GEMINI_API_KEY muhit o'zgaruvchilarini sozlang!"
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

