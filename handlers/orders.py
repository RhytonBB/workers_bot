from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
    Application
)
from db import get_connection
from datetime import datetime

# Состояния для ConversationHandler
WAITING_FOR_PHOTO = 1

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_connection()
    cur = conn.cursor()
    
    # Получаем telegram_nick работника
    cur.execute("SELECT telegram_nick FROM worker WHERE telegram_id = %s", (update.effective_user.id,))
    worker = cur.fetchone()
    
    if not worker:
        await update.message.reply_text("Вы не авторизованы.")
        return
    
    telegram_nick = worker[0]
    
    # Получаем заказы для данного исполнителя
    cur.execute("""
        SELECT id, title, status, created_at, completed_at 
        FROM "order" 
        WHERE telegram_nick = %s 
        ORDER BY created_at DESC
    """, (telegram_nick,))
    
    orders = cur.fetchall()
    
    if not orders:
        await update.message.reply_text("У вас пока нет заказов.")
        return
    
    # Создаем клавиатуру с заказами
    keyboard = []
    for order in orders:
        order_id, title, status, created_at, completed_at = order
        status_emoji = "✅" if status == "completed" else "🔄"
        button_text = f"{status_emoji} {title} (#{order_id})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"order_{order_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Ваши заказы:", reply_markup=reply_markup)

async def order_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split('_')[1])
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Получаем детальную информацию о заказе
    cur.execute("""
        SELECT title, description, status, created_at, completed_at
        FROM "order"
        WHERE id = %s
    """, (order_id,))
    
    order = cur.fetchone()
    
    if not order:
        await query.edit_message_text("Заказ не найден.")
        return
    
    title, description, status, created_at, completed_at = order
    
    # Форматируем даты
    created_at_str = created_at.strftime("%d.%m.%Y %H:%M")
    completed_at_str = completed_at.strftime("%d.%m.%Y %H:%M") if completed_at else "Не завершен"
    
    # Формируем текст сообщения
    text = f"""
📋 Заказ #{order_id}

📌 Название: {title}
📝 Описание: {description or 'Нет описания'}
📊 Статус: {'✅ Завершен' if status == 'completed' else '🔄 Активен'}
📅 Создан: {created_at_str}
🏁 Завершен: {completed_at_str}
"""
    
    # Создаем кнопки
    keyboard = []
    
    # Если заказ не завершен, добавляем кнопку для загрузки фотоотчета
    if status != 'completed':
        keyboard.append([InlineKeyboardButton("📸 Загрузить фотоотчет", callback_data=f"upload_photo_{order_id}")])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад к списку", callback_data="back_to_orders")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем текстовое сообщение с информацией о заказе
    await query.edit_message_text(text=text, reply_markup=reply_markup)

async def start_photo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split('_')[2])
    context.user_data['current_order_id'] = order_id
    
    await query.edit_message_text(
        "Пожалуйста, отправьте фотографию для фотоотчета.\n"
        "После загрузки фото вы сможете завершить заказ."
    )
    return WAITING_FOR_PHOTO

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("=== Начало обработки фото ===")
    print(f"Context user_data: {context.user_data}")
    
    if 'current_order_id' not in context.user_data:
        print("Ошибка: current_order_id не найден в context.user_data")
        await update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте снова.")
        return ConversationHandler.END
    
    order_id = context.user_data['current_order_id']
    print(f"Обработка фото для заказа #{order_id}")
    
    # Получаем фото с наилучшим качеством
    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    print(f"Получено фото для заказа #{order_id}")
    print(f"File ID: {file_id}")
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Обновляем photo_file_id в базе данных
        cur.execute("""
            UPDATE "order"
            SET photo_file_id = %s
            WHERE id = %s
        """, (file_id, order_id))
        conn.commit()
        print(f"Фото успешно сохранено в базе для заказа #{order_id}")
        
        # Создаем кнопку завершения заказа
        keyboard = [[InlineKeyboardButton("✅ Завершить заказ", callback_data=f"complete_order_{order_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем подтверждение с фото и кнопкой завершения
        await update.message.reply_photo(
            photo=file_id,
            caption="✅ Фотоотчет успешно загружен!\nТеперь вы можете завершить заказ.",
            reply_markup=reply_markup
        )
        print(f"Подтверждение отправлено для заказа #{order_id}")
        
        # Очищаем данные из контекста
        context.user_data.pop('current_order_id', None)
        print("Контекст очищен")
        
        return ConversationHandler.END
        
    except Exception as e:
        print(f"Ошибка при сохранении фото для заказа #{order_id}: {e}")
        await update.message.reply_text(
            "Произошла ошибка при сохранении фото. Пожалуйста, попробуйте снова."
        )
        return ConversationHandler.END

async def complete_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split('_')[2])
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Обновляем статус заказа
    cur.execute("""
        UPDATE "order"
        SET status = 'completed', completed_at = %s
        WHERE id = %s
    """, (datetime.utcnow(), order_id))
    conn.commit()
    
    # Отправляем новое сообщение о завершении заказа
    await query.message.reply_text(
        "✅ Заказ успешно завершен!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Назад к списку", callback_data="back_to_orders")
        ]])
    )

async def back_to_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Повторяем логику отображения списка заказов
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT telegram_nick FROM worker WHERE telegram_id = %s", (query.from_user.id,))
    worker = cur.fetchone()
    
    if not worker:
        await query.message.reply_text("Вы не авторизованы.")
        return
    
    telegram_nick = worker[0]
    
    cur.execute("""
        SELECT id, title, status, created_at, completed_at 
        FROM "order" 
        WHERE telegram_nick = %s 
        ORDER BY created_at DESC
    """, (telegram_nick,))
    
    orders = cur.fetchall()
    
    if not orders:
        await query.message.reply_text("У вас пока нет заказов.")
        return
    
    keyboard = []
    for order in orders:
        order_id, title, status, created_at, completed_at = order
        status_emoji = "✅" if status == "completed" else "🔄"
        button_text = f"{status_emoji} {title} (#{order_id})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"order_{order_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем новое сообщение со списком заказов
    await query.message.reply_text("Ваши заказы:", reply_markup=reply_markup)

# Создаем ConversationHandler для обработки загрузки фото
photo_upload_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_photo_upload, pattern="^upload_photo_")],
    states={
        WAITING_FOR_PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
    },
    fallbacks=[],
    per_message=False,
    per_chat=True,
    name="photo_upload"
)

# Регистрируем обработчики
orders_handler = MessageHandler(filters.Regex("^📄 Мои заказы$"), my_orders)
order_details_handler = CallbackQueryHandler(order_details, pattern="^order_")
back_to_orders_handler = CallbackQueryHandler(back_to_orders, pattern="^back_to_orders$")
complete_order_handler = CallbackQueryHandler(complete_order, pattern="^complete_order_")

def register_handlers(application: Application):
    # ... existing code ...
    
    # Регистрируем обработчик загрузки фото
    photo_upload_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(upload_photo, pattern=r"^upload_photo_(\d+)$")],
        states={
            PHOTO_UPLOAD: [MessageHandler(filters.PHOTO, handle_photo)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="photo_upload",
        persistent=False,
        per_message=False,
        per_chat=True
    )
    
    print("Регистрация обработчика загрузки фото")
    application.add_handler(photo_upload_handler)
    print("Обработчик загрузки фото зарегистрирован")
