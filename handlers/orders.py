from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from db import get_connection

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM workers WHERE telegram_id = %s", (update.effective_user.id,))
    row = cur.fetchone()
    if not row:
        await update.message.reply_text("Вы не авторизованы.")
        return
    worker_id = row[0]
    cur.execute("SELECT id, title, status FROM orders WHERE worker_id = %s", (worker_id,))
    orders = cur.fetchall()
    if not orders:
        await update.message.reply_text("Нет активных заказов.")
        return
    text = "\n".join([f"📝 {o[1]} (#{o[0]}) - {o[2]}" for o in orders])
    await update.message.reply_text("Ваши заказы:\n" + text)

orders_handler = CommandHandler("orders", my_orders)
