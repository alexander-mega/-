import asyncio, sqlite3, logging, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telethon import TelegramClient, events
from aiohttp import web

logging.basicConfig(level=logging.INFO)

# ТВОИ ДАННЫЕ (Уже вшиты)
API_ID, API_HASH = 23451898, "f0e79c505bbcc7728505df9108cc3d22"
BOT_TOKEN, ADMIN_ID = "8888017127:AAFywfUncgftwMA_f4JztHnf4L2fiIdtFWE", 7653039412

# Тут пиши свой номер телефона, привязанный к Телеге (ВМЕСТО ПЛЮСОВ)
PHONE = "+380680434161" 

def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS triggers (keyword TEXT PRIMARY KEY, file_id TEXT, delay INTEGER)")
    cursor.execute("CREATE TABLE IF NOT EXISTS allowed_chats (chat_id INTEGER PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS allowed_users (user_id INTEGER PRIMARY KEY)")
    cursor.execute("INSERT OR IGNORE INTO allowed_users (user_id) VALUES (?)", (ADMIN_ID,))
    conn.commit()
    conn.close()

init_db()
bot, dp = Bot(token=BOT_TOKEN), Dispatcher()
storage = {}

def main_menu(uid):
    b = InlineKeyboardBuilder()
    b.button(text="🎵 Триггеры и Аудио", callback_data="menu_triggers")
    b.button(text="💬 Разрешенные Чаты", callback_data="menu_chats")
    if uid == ADMIN_ID: b.button(text="👥 Управление Доступом", callback_data="menu_users")
    b.adjust(1); return b.as_markup()

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    conn = sqlite3.connect("bot_data.db")
    res = conn.execute("SELECT 1 FROM allowed_users WHERE user_id=?", (m.from_user.id,)).fetchone()
    conn.close()
    if not res: return
    await m.answer("👋 Панель управления Юзерботом!", reply_markup=main_menu(m.from_user.id))

# --- Внутренности веб-сервера для ввода кода ---
current_code = None

async def handle_web(request):
    global current_code
    if "code" in request.query:
        current_code = request.query["code"]
        return web.Response(text=f"Код {current_code} принят! Проверь логи Render.")
    return web.Response(text="Бот запущен. Чтобы ввести код подтверждения, допиши в ссылку: ?code=НАШ_КОД")

client = TelegramClient('session_iphone', API_ID, API_HASH)

async def code_callback():
    global current_code
    print("⚠️ ВНИМАНИЕ: Telegram отправил тебе код подтверждения!")
    print("Перейди по ссылке твоего приложения Render и допиши в конце URL: ?code=ТВОЙ_КОД")
    while current_code is None:
        await asyncio.sleep(1)
    res = current_code
    current_code = None
    return res

@client.on(events.NewMessage(incoming=True))
async def userbot_handler(e):
    if not e.text: return
    chat_id, text_lower = e.chat_id, e.text.lower()
    conn = sqlite3.connect("bot_data.db")
    is_allowed = conn.execute("SELECT 1 FROM allowed_chats WHERE chat_id=?", (chat_id,)).fetchone()
    if not is_allowed: conn.close(); return
    triggers = conn.execute("SELECT keyword, file_id, delay FROM triggers").fetchall(); conn.close()
    for keyword, file_id, delay in triggers:
        if keyword in text_lower:
            if delay > 0: await asyncio.sleep(delay)
            await e.reply(file=file_id); break

async def main():
    print("Запуск веб-сервера...")
    app = web.Application()
    app.router.add_get('/', handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()

    print("Запуск Юзербота...")
    await client.start(phone=PHONE, code_callback=code_callback)
    print("Юзербот успешно авторизован!")
    
    print("Запуск Админ-Панели...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
