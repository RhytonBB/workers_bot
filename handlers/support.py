from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from db import get_connection
import uuid
from telegram.ext import MessageHandler, filters

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
    cur.execute("""
    INSERT INTO support_request (worker_id, session_token, status)
    VALUES (%s, %s, %s)
""", (worker[0], token, 'new'))
    conn.commit()

    link = f"http://127.0.0.1:5000/chat/{token}"
    await query.edit_message_text(f"✅ Обращение создано. Перейдите по ссылке: {link}")

# 👇 вот что нужно экспортировать
support_handlers = [
    CommandHandler("support", support_command),
    CallbackQueryHandler(confirm_support, pattern="^confirm_support$"),
    MessageHandler(filters.TEXT & filters.Regex("^✉️ Поддержка$"), support_command),  # 👈 вот это
]