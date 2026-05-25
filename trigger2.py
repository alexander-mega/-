import asyncio, sqlite3, logging, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telethon import TelegramClient, events
from aiohttp import web

logging.basicConfig(level=logging.INFO)

API_ID, API_HASH = 23451898, "f0e79c505bbcc7728505df9108cc3d22"
BOT_TOKEN, ADMIN_ID = "8888017127:AAFywfUncgftwMA_f4JztHnf4L2fiIdtFWE", 7653039412
PHONE = "+380680434161"

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

user_auth_state = {}

async def handle_web(request):
    return web.Response(text="Бот онлайн!")

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    b = InlineKeyboardBuilder()
    b.button(text="🔐 Авторизовать Юзербота", callback_data="start_auth")
    await m.answer("👋 Панель управления!", reply_markup=b.as_markup())

@dp.callback_query(F.data == "start_auth")
async def auth_callback(call: types.CallbackQuery):
    await call.message.answer("⏳ Запрашиваю код у Telegram API...")
    try:
        await client.connect()
        if await client.is_user_authorized():
            await call.message.answer("✅ Юзербот уже успешно авторизован!")
            return
        
        res = await client.send_code_request(PHONE)
        user_auth_state["phone_code_hash"] = res.phone_code_hash
        
        # Делаем хитрый ForceReply, чтобы скрыть ввод от алгоритмов
        await call.message.answer(
            "📩 Код отправлен!\n\nСделай **ОТВЕТ (Reply)** на ЭТО сообщение и напиши код через пробелы (например: `1 2 3 4 5`), чтобы Телеграм не заблокировал его!",
            reply_markup=types.ForceReply(selective=True)
        )
    except Exception as e:
        await call.message.answer(f"Ошибка: {e}")

@dp.message(F.reply_to_message)
async def handle_reply_code(m: types.Message):
    if m.from_user.id != ADMIN_ID or "phone_code_hash" not in user_auth_state: return
    
    # Убираем пробелы, которые мы ввели для маскировки кода
    code = m.text.replace(" ", "").strip()
    await m.answer(f"⚙️ Пробую войти с кодом {code}...")
    
    try:
        await client.connect()
        await client.sign_in(phone=PHONE, code=code, phone_code_hash=user_auth_state["phone_code_hash"])
        await m.answer("🎉 УРА! Юзербот успешно залогинился и работает!")
        user_auth_state.clear()
    except Exception as e:
        await m.answer(f"❌ Ошибка входа: {e}\nНажми кнопку авторизации заново.")

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
    app = web.Application()
    app.router.add_get('/', handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
