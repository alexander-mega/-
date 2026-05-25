import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telethon import TelegramClient, events

logging.basicConfig(level=logging.INFO)

# =================!!! ТВОИ ДАННЫЕ НА МЕСТЕ !!!=================
API_ID = 23451898
API_HASH = "f0e79c505bbcc7728505df9108cc3d22"
BOT_TOKEN = "8888017127:AAFywfUncgftwMA_f4JztHnf4L2fiIdtFWE"
ADMIN_ID = 7653039412
# =======================================================================

# Инициализация Базы Данных (создается сама)
def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS triggers 
                      (keyword TEXT PRIMARY KEY, file_id TEXT, delay INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS allowed_chats (chat_id INTEGER PRIMARY KEY)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS allowed_users (user_id INTEGER PRIMARY KEY)''')
    cursor.execute("INSERT OR IGNORE INTO allowed_users (user_id) VALUES (?)", (ADMIN_ID,))
    conn.commit()
    conn.close()

init_db()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
storage = {} 

def main_menu(user_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="🎵 Триггеры и Аудио", callback_data="menu_triggers")
    builder.button(text="💬 Разрешенные Чаты", callback_data="menu_chats")
    if user_id == ADMIN_ID:
        builder.button(text="👥 Управление Доступом (Суперправа)", callback_data="menu_users")
    builder.adjust(1)
    return builder.as_markup()

# --- ЛОГИКА МЕНЮ БОТА ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    conn = sqlite3.connect("bot_data.db")
    res = conn.execute("SELECT 1 FROM allowed_users WHERE user_id = ?", (message.from_user.id,)).fetchone()
    conn.close()
    if not res:
        await message.answer("❌ У вас нет доступа к этой панели управления.")
        return
    await message.answer("👋 Добро пожаловать в панель управления Юзерботом!", reply_markup=main_menu(message.from_user.id))

@dp.callback_query(F.data == "menu_users")
async def view_users(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect("bot_data.db")
    users = conn.execute("SELECT user_id FROM allowed_users").fetchall()
    conn.close()
    builder = InlineKeyboardBuilder()
    for u in users:
        if u[0] != ADMIN_ID:
            builder.button(text=f"❌ Забанить {u[0]}", callback_data=f"del_user_{u[0]}")
    builder.button(text="➕ Добавить пользователя", callback_data="add_user")
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    builder.adjust(1)
    await call.message.edit_text("👥 Управление пользователями БД:", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "add_user")
async def action_add_user(call: types.CallbackQuery):
    storage[call.from_user.id] = {"state": "wait_user_id"}
    await call.message.answer("Введите Telegram ID человека, чтобы дать ему доступ:")
    await call.answer()

@dp.callback_query(F.data.startswith("del_user_"))
async def action_del_user(call: types.CallbackQuery):
    uid = int(call.data.split("_")[2])
    conn = sqlite3.connect("bot_data.db")
    conn.execute("DELETE FROM allowed_users WHERE user_id = ?", (uid,))
    conn.commit()
    conn.close()
    await call.answer("Пользователь удален из БД!")
    await view_users(call)

@dp.callback_query(F.data == "menu_chats")
async def view_chats(call: types.CallbackQuery):
    conn = sqlite3.connect("bot_data.db")
    chats = conn.execute("SELECT chat_id FROM allowed_chats").fetchall()
    conn.close()
    builder = InlineKeyboardBuilder()
    for c in chats:
        builder.button(text=f"❌ Удалить чат {c[0]}", callback_data=f"del_chat_{c[0]}")
    builder.button(text="➕ Добавить чат (Перешлите сообщение)", callback_data="add_chat")
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    builder.adjust(1)
    await call.message.edit_text("💬 Белый список чатов:", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "add_chat")
async def action_add_chat(call: types.CallbackQuery):
    storage[call.from_user.id] = {"state": "wait_chat_msg"}
    await call.message.answer("Перешлите в этот диалог любое сообщение из нужного чата:")
    await call.answer()

@dp.callback_query(F.data.startswith("del_chat_"))
async def action_del_chat(call: types.CallbackQuery):
    cid = int(call.data.split("_")[2])
    conn = sqlite3.connect("bot_data.db")
    conn.execute("DELETE FROM allowed_chats WHERE chat_id = ?", (cid,))
    conn.commit()
    conn.close()
    await call.answer("Чат удален!")
    await view_chats(call)

@dp.callback_query(F.data == "menu_triggers")
async def view_triggers(call: types.CallbackQuery):
    conn = sqlite3.connect("bot_data.db")
    triggers = conn.execute("SELECT keyword, delay FROM triggers").fetchall()
    conn.close()
    builder = InlineKeyboardBuilder()
    for t in triggers:
        builder.button(text=f"❌ {t[0]} ({t[1]} сек)", callback_data=f"del_trig_{t[0]}")
    builder.button(text="➕ Добавить триггер", callback_data="add_trig")
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    builder.adjust(1)
    await call.message.edit_text("🎵 Ваши активные триггеры:", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "add_trig")
async def action_add_trig(call: types.CallbackQuery):
    storage[call.from_user.id] = {"state": "wait_trig_word"}
    await call.message.answer("Введите слово-триггер:")
    await call.answer()

@dp.callback_query(F.data.startswith("del_trig_"))
async def action_del_trig(call: types.CallbackQuery):
    keyword = call.data.split("_")[2]
    conn = sqlite3.connect("bot_data.db")
    conn.execute("DELETE FROM triggers WHERE keyword = ?", (keyword,))
    conn.commit()
    conn.close()
    await call.answer("Триггер удален!")
    await view_triggers(call)

@dp.callback_query(F.data == "main_menu")
async def go_to_main_menu(call: types.CallbackQuery):
    await call.message.edit_text("👋 Добро пожаловать в▮панель управления Юзерботом!", reply_markup=main_menu(call.from_user.id))

@dp.message()
async def handle_inputs(message: types.Message):
    uid = message.from_user.id
    if uid not in storage: return
    state = storage[uid].get("state")
    
    if state == "wait_user_id":
        try:
            new_uid = int(message.text)
            conn = sqlite3.connect("bot_data.db")
            conn.execute("INSERT OR IGNORE INTO allowed_users (user_id) VALUES (?)", (new_uid,))
            conn.commit()
            conn.close()
            del storage[uid]
            await message.answer(f"✅ Пользователь {new_uid} добавлен в базу!", reply_markup=main_menu(uid))
        except ValueError:
            await message.answer("❌ Введите числовой ID.")
            
    elif state == "wait_chat_msg":
        chat_id = None
        if message.forward_from_chat: chat_id = message.forward_from_chat.id
        elif message.forward_from: chat_id = message.forward_from.id
        
        if chat_id:
            conn = sqlite3.connect("bot_data.db")
            conn.execute("INSERT OR IGNORE INTO allowed_chats (chat_id) VALUES (?)", (chat_id,))
            conn.commit()
            conn.close()
            del storage[uid]
            await message.answer(f"✅ Чат {chat_id} добавлен в белый список!", reply_markup=main_menu(uid))
        else:
            await message.answer("❌ Сообщение должно быть переслано из нужной группы/канала!")

    elif state == "wait_trig_word":
        storage[uid]["word"] = message.text.lower()
        storage[uid]["state"] = "wait_trig_audio"
        await message.answer("Теперь отправьте или перешлите аудиозапись/голосовое сообщение:")

    elif state == "wait_trig_audio":
        if message.audio or message.voice:
            storage[uid]["file_id"] = message.audio.file_id if message.audio else message.voice.file_id
            storage[uid]["state"] = "wait_trig_delay"
            await message.answer("Введите задержку ответа в секундах (цифрой, например: 0 или 3):")
        else:
            await message.answer("❌ Отправьте именно аудио или голосовое сообщение.")

    elif state == "wait_trig_delay":
        try:
            delay = int(message.text)
            word = storage[uid]["word"]
            file_id = storage[uid]["file_id"]
            conn = sqlite3.connect("bot_data.db")
            conn.execute("INSERT OR REPLACE INTO triggers (keyword, file_id, delay) VALUES (?, ?, ?)", (word, file_id, delay))
            conn.commit()
            conn.close()
            del storage[uid]
            await message.answer(f"✅ Триггер «{word}» успешно сохранен в БД!", reply_markup=main_menu(uid))
        except ValueError:
            await message.answer("❌ Введите целое число.")

# --- ЛОГИКА ЮЗЕРБОТА ---
client = TelegramClient('session_iphone', API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True))
async def userbot_handler(event):
    if not event.text: return
    chat_id = event.chat_id
    text_lower = event.text.lower()
    
    conn = sqlite3.connect("bot_data.db")
    is_allowed_chat = conn.execute("SELECT 1 FROM allowed_chats WHERE chat_id = ?", (chat_id,)).fetchone()
    if not is_allowed_chat:
        conn.close()
        return
        
    triggers = conn.execute("SELECT keyword, file_id, delay FROM triggers").fetchall()
    conn.close()
    
    for keyword, file_id, delay in triggers:
        if keyword in text_lower:
            if delay > 0:
                await asyncio.sleep(delay)
            await event.reply(file=file_id)
            break

async def main():
    print("Запуск Юзербота...")
    await client.start()
    print("Запуск Админ-Бот панели...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())