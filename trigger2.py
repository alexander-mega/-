import asyncio, sqlite3, logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telethon import TelegramClient

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

# Состояние для ожидания кода авторизации
user_auth_state = {}

def main_menu(uid):
    b = InlineKeyboardBuilder()
    b.button(text="🎵 Триггеры и Аудио", callback_data="menu_triggers")
    b.button(text="💬 Разрешенные Чаты", callback_data="menu_chats")
    b.adjust(1); return b.as_markup()

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    await m.answer("👋 Панель управления Юзерботом!\n\nЕсли запускаешь первый раз, нажми /auth чтобы войти в аккаунт.", reply_markup=main_menu(m.from_user.id))

# Авторизация через обычного Бота
@dp.message(Command("auth"))
async def cmd_auth(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    await m.answer("⏳ Подключаюсь к Telegram API... Подожди пару секунд.")
    await client.connect()
    
    if await client.is_user_authorized():
        await m.answer("✅ Юзербот уже успешно авторизован и работает!")
        return
        
    # Отправляем запрос кода на твой номер
    res = await client.send_code_request(PHONE)
    user_auth_state["phone_code_hash"] = res.phone_code_hash
    await m.answer("📩 Telegram отправил тебе код подтверждения в приложение. \n\n**Пришли мне этот код обычным сообщением в ответ.**")

@dp.message()
async def handle_auth_code(m: types.Message):
    if m.from_user.id != ADMIN_ID or "phone_code_hash" not in user_auth_state:
        # Обычная обработка сообщений, если это не ввод кода
        return

    code = m.text.strip()
    await m.answer(f"⚙️ Пробую войти с кодом {code}...")
    
    try:
        await client.connect()
        await client.sign_in(phone=PHONE, code=code, phone_code_hash=user_auth_state["phone_code_hash"])
        await m.answer("🎉 УРА! Юзербот успешно залогинился и запущен!")
        user_auth_state.clear()
    except Exception as e:
        await m.answer(f"❌ Ошибка входа: {e}\nПопробуй заново через /auth")

# Работа триггеров юзербота
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
    print("Запуск панели управления через бота...")
    # Запускаем только бота aiogram, он не требует открытых портов
    await dp.start_polling(bot)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
