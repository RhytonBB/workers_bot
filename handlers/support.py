from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from db import get_connection
import uuid
from telegram.ext import MessageHandler, filters
from datetime import datetime


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM worker WHERE telegram_id = %s", (telegram_id,))
    worker = cur.fetchone()
    if not worker:
        await update.message.reply_text("Вы не авторизованы.")
        return

    cur.execute("""
        SELECT id FROM support_request 
        WHERE worker_id = %s AND status != 'closed'
    """, (worker[0],))
    if cur.fetchone():
        await update.message.reply_text("У вас уже есть активное обращение. Дождитесь завершения.")
        return

    keyboard = [[InlineKeyboardButton("Подтвердить обращение", callback_data="confirm_support")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Вы хотите начать обращение в поддержку?", reply_markup=reply_markup)

async def confirm_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM worker WHERE telegram_id = %s", (telegram_id,))
    worker = cur.fetchone()
    if not worker:
        await query.edit_message_text("Вы не авторизованы.")
        return

    token = str(uuid.uuid4())
    created_at = datetime.utcnow()

    # 1. Создаём обращение
    cur.execute("""
        INSERT INTO support_request (worker_id, session_token, status, created_at)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (worker[0], token, 'new', created_at))
    request_id = cur.fetchone()[0]

    # 2. Добавляем авто-сообщение
    cur.execute("""
        INSERT INTO support_message (request_id, sender_role, text, created_at)
        VALUES (%s, %s, %s, %s)
    """, (request_id, 'admin', 'Ожидайте, оператор скоро подключится.', created_at))

    conn.commit()

    link = f"https://support-panel-5uxc.onrender.com/chat/{token}/{telegram_id}"
    await query.edit_message_text(f"✅ Обращение создано. Перейдите по ссылке: {link}")


support_handlers = [
    CommandHandler("support", support_command),
    CallbackQueryHandler(confirm_support, pattern="^confirm_support$"),
    MessageHandler(filters.TEXT & filters.Regex("^✉️ Поддержка$"), support_command),  # 👈 вот это
]