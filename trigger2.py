import asyncio, sqlite3, logging, os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telethon import TelegramClient
from aiohttp import web

logging.basicConfig(level=logging.INFO)

API_ID, API_HASH = 23451898, "f0e79c505bbcc7728505df9108cc3d22"
BOT_TOKEN, ADMIN_ID = "8888017127:AAFywfUncgftwMA_f4JztHnf4L2fiIdtFWE", 7653039412
PHONE = "+380680434161"

# База данных
conn = sqlite3.connect("bot_data.db")
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS triggers (keyword TEXT PRIMARY KEY, file_id TEXT, delay INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS allowed_chats (chat_id INTEGER PRIMARY KEY)")
c.execute("CREATE TABLE IF NOT EXISTS allowed_users (user_id INTEGER PRIMARY KEY)")
c.execute("INSERT OR IGNORE INTO allowed_users (user_id) VALUES (?)", (ADMIN_ID,))
conn.commit()
conn.close()

bot, dp = Bot(token=BOT_TOKEN), Dispatcher()
client = TelegramClient('session_iphone', API_ID, API_HASH)

# Заглушка для сайта, чтобы Render не ругался
async def handle_web(request):
    return web.Response(text="Сервер работает! Бот авторизуется в фоне. Читайте логи на Render.")

async def run_tg_client():
    await asyncio.sleep(5) # Даем серверу 5 секунд успешно запуститься
    print("--- ЗАПУСК ТЕЛЕГРАМ КЛИЕНТА ---")
    try:
        await client.start(phone=PHONE)
        print("--- ЮЗЕРБОТ УСПЕШНО ПОДКЛЮЧЕН! ---")
        print("Запуск Админ-Панели...")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Ошибка при авторизации: {e}")

async def main():
    # Сначала железно запускаем веб-порт, чтобы Render успокоился
    app = web.Application()
    app.router.add_get('/', handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    print(f"Веб-сервер успешно запущен на порту {port}! Плашка на Render сейчас станет зеленой.")

    # Запускаем телегу фоновой задачей, чтобы она не блокировала порт
    asyncio.create_task(run_tg_client())
    
    # Держим сервер активным
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
