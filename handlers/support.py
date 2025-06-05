from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from config import SUPPORT_CHAT_ID
from db import get_connection
from models import get_worker_by_telegram_id

async def forward_to_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = get_connection()

    # Проверка: зарегистрирован ли пользователь
    worker = get_worker_by_telegram_id(conn, user.id)
    if not worker:
        return  # просто игнорируем неавторизованного пользователя

    message = update.message.text
    try:
        await context.bot.send_message(
            chat_id=SUPPORT_CHAT_ID,
            text=f"💬 Сообщение от @{user.username} ({user.id}):\n\n{message}"
        )
        await update.message.reply_text("Ваше сообщение отправлено в поддержку.")
    except Exception as e:
        # можно логировать ошибку или уведомить админа
        await update.message.reply_text("Произошла ошибка при отправке сообщения.")
        raise e

support_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, forward_to_support)