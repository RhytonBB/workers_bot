from telegram.ext import ApplicationBuilder
from config import BOT_TOKEN
from handlers.start import start_handler, ignore_handler
from handlers.profile import profile_handler
from handlers.orders import (
    orders_handler, 
    order_details_handler, 
    back_to_orders_handler,
    photo_upload_handler,
    complete_order_handler
)
from handlers.support import support_handlers

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(ignore_handler, group=999)
app.add_handler(start_handler)
app.add_handler(profile_handler)
app.add_handler(orders_handler)
app.add_handler(order_details_handler)
app.add_handler(back_to_orders_handler)
app.add_handler(photo_upload_handler)
app.add_handler(complete_order_handler)

# Добавляем все обработчики из support_handlers
for handler in support_handlers:
    app.add_handler(handler)

if __name__ == "__main__":
    print("✅ Бот запущен")
    app.run_polling()
