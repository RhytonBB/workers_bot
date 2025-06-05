from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from db import get_connection
from models import get_worker_by_telegram_id

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_connection()
    user = get_worker_by_telegram_id(conn, update.effective_user.id)
    if not user:
        await update.message.reply_text("Вы не авторизованы.")
        return

    full_name = user[3]
    phone = user[4]
    await update.message.reply_text(f"👤 Ваш профиль:\n\nФИО: {full_name}\nТелефон: {phone}")

profile_handler = CommandHandler("profile", profile)
