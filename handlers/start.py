from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters
)
from db import get_connection
from models import (
    get_worker_by_telegram_id, get_executor_by_key,
    insert_worker_from_executor, increment_fail_attempts,
    block_executor
)

main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[["📄 Мои заказы", "✉️ Поддержка"]],
    resize_keyboard=True
)
ASK_KEY = 1

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    conn = get_connection()
    user = get_worker_by_telegram_id(conn, telegram_id)

    if user:
        # Пользователь уже авторизован — показываем меню
        await update.message.reply_text(
            "Вы уже авторизованы. Используйте меню.",
            reply_markup=main_menu_keyboard
        )
        return ConversationHandler.END

    # Пользователь не авторизован — просим ввести ключ и скрываем меню
    await update.message.reply_text(
        "Введите ваш ключ доступа:",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_KEY

# Проверка ключа
async def check_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = update.message.text.strip()
    nick = update.effective_user.username
    telegram_id = update.effective_user.id

    conn = get_connection()
    executor = get_executor_by_key(conn, key, nick)

    if not executor:
        increment_fail_attempts(conn, nick)
        await update.message.reply_text("Неверный ключ.")

        # Проверка количества попыток
        cur = conn.cursor()
        cur.execute("SELECT fail_attempts FROM executor WHERE telegram_nick = %s", (nick,))
        result = cur.fetchone()
        if result and result[0] >= 3:
            block_executor(conn, nick)
            await update.message.reply_text("Вы заблокированы из-за 3 неудачных попыток.")
            return ConversationHandler.END
        return ASK_KEY

    # Успешная авторизация
    insert_worker_from_executor(conn, executor, telegram_id)
    await update.message.reply_text(
        "✅ Вы авторизованы. Используйте меню.",
        reply_markup=main_menu_keyboard
    )
    return ConversationHandler.END

# Игнорирование сообщений от неавторизованных пользователей
async def ignore_unregistered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    conn = get_connection()
    worker = get_worker_by_telegram_id(conn, telegram_id)

    if not worker:
        # Отправляем сообщение с просьбой авторизоваться
        await update.message.reply_text(
            "❗ Сначала авторизуйтесь командой /start"
        )
        return
    # Если пользователь зарегистрирован — можно продолжить обработку
    # Другие хендлеры получат это сообщение

# ConversationHandler для /start
start_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ASK_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_key)],
    },
    fallbacks=[],
)

# Хендлер фильтрации незарегистрированных пользователей
# Должен идти ПЕРВЫМ в цепочке Dispatcher
ignore_handler = MessageHandler(filters.ALL, ignore_unregistered)
