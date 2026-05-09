import asyncio
import sqlite3
from datetime import datetime
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    FSInputFile,
)

from dotenv import load_dotenv
from openpyxl import Workbook

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MANAGER_CHAT = 6600140962

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# =========================
# DATABASE
# =========================

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    full_name TEXT,
    action TEXT,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    full_name TEXT,
    phone TEXT,
    city TEXT,
    contact TEXT,
    comment TEXT,
    source TEXT,
    created_at TEXT
)
""")

conn.commit()

# =========================
# STATES
# =========================

class Office(StatesGroup):
    name = State()
    phone = State()
    city = State()
    comment = State()

class Online(StatesGroup):
    name = State()
    phone = State()
    contact = State()
    time = State()

# =========================
# KEYBOARDS
# =========================

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📄 Презентація")],
        [KeyboardButton(text="🏢 Офіс консультація")],
        [KeyboardButton(text="💻 Онлайн консультація")],
    ],
    resize_keyboard=True,
)

admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="📁 Експорт CRM")],
    ],
    resize_keyboard=True,
)

# =========================
# HELPERS
# =========================

def save_event(user, action):
    cursor.execute("""
        INSERT INTO analytics (username, full_name, action, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        user.username,
        user.full_name,
        action,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))
    conn.commit()

def save_lead(data, user, source):
    cursor.execute("""
        INSERT INTO leads (
            username, full_name, phone, city, contact, comment, source, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user.username,
        user.full_name,
        data.get("phone"),
        data.get("city"),
        data.get("contact"),
        data.get("comment"),
        source,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))
    conn.commit()

async def send_manager(text):
    await bot.send_message(MANAGER_CHAT, text)

# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message):

    if message.chat.id == MANAGER_CHAT:
        await message.answer("🔐 CRM ADMIN PANEL", reply_markup=admin_keyboard)
        return

    try:
        await message.answer_photo(FSInputFile("suprema.jpg"), caption="🔥 Suprema")
        await message.answer_photo(FSInputFile("accure.jpg"), caption="❄️ Accure")
    except:
        pass

    await message.answer(
        "📍 DUSO BOT\n📞 044 506 77 77",
        reply_markup=main_keyboard
    )

# =========================
# PDF
# =========================

@dp.message(F.text == "📄 Презентація")
async def pdf(message: Message):

    await message.answer_document(FSInputFile("catalog.pdf"))

    save_event(message.from_user, "pdf")

# =========================
# OFFICE LEAD
# =========================

@dp.message(F.text == "🏢 Офіс консультація")
async def office_start(message: Message, state: FSMContext):
    await state.set_state(Office.name)
    await message.answer("Ім'я:")

@dp.message(Office.name)
async def office_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Office.phone)
    await message.answer("Телефон:")

@dp.message(Office.phone)
async def office_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(Office.city)
    await message.answer("Місто:")

@dp.message(Office.city)
async def office_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(Office.comment)
    await message.answer("Коментар:")

@dp.message(Office.comment)
async def office_finish(message: Message, state: FSMContext):

    data = await state.get_data()

    save_lead(data, message.from_user, "office")

    await send_manager(f"""
🏢 ОФЛАЙН ЛІД

👤 {data['name']}
📱 {data['phone']}
🏙 {data['city']}
💬 {message.text}
""")

    save_event(message.from_user, "office")

    await message.answer("✔️ Дякуємо!")
    await state.clear()

# =========================
# ONLINE LEAD
# =========================

@dp.message(F.text == "💻 Онлайн консультація")
async def online_start(message: Message, state: FSMContext):
    await state.set_state(Online.name)
    await message.answer("Ім'я:")

@dp.message(Online.name)
async def online_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Online.phone)
    await message.answer("Телефон:")

@dp.message(Online.phone)
async def online_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(Online.contact)
    await message.answer("Контакт:")

@dp.message(Online.contact)
async def online_contact(message: Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await state.set_state(Online.time)
    await message.answer("Час:")

@dp.message(Online.time)
async def online_finish(message: Message, state: FSMContext):

    data = await state.get_data()

    save_lead(data, message.from_user, "online")

    await send_manager(f"""
💻 ОНЛАЙН ЛІД

👤 {data['name']}
📱 {data['phone']}
📧 {data['contact']}
⏰ {message.text}
""")

    save_event(message.from_user, "online")

    await message.answer("✔️ Дякуємо!")
    await state.clear()

# =========================
# ADMIN STATS BUTTON
# =========================

@dp.message(F.text == "📊 Статистика")
async def stats(message: Message):

    if message.chat.id != MANAGER_CHAT:
        return

    cursor.execute("SELECT COUNT(*) FROM analytics WHERE action='pdf'")
    pdf = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM analytics WHERE action='office'")
    office = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM analytics WHERE action='online'")
    online = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads")
    leads = cursor.fetchone()[0]

    await message.answer(f"""
📊 CRM STAT

📄 PDF: {pdf}
🏢 Офіс: {office}
💻 Онлайн: {online}
📦 Ліди: {leads}
""")

# =========================
# EXPORT CRM
# =========================

@dp.message(F.text == "📁 Експорт CRM")
async def export(message: Message):

    if message.chat.id != MANAGER_CHAT:
        return

    cursor.execute("SELECT * FROM leads")
    rows = cursor.fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "CRM"

    ws.append([
        "ID", "Username", "Full Name",
        "Phone", "City", "Contact",
        "Comment", "Source", "Date"
    ])

    for r in rows:
        ws.append(r)

    file = "crm.xlsx"
    wb.save(file)

    await message.answer_document(FSInputFile(file))

# =========================
# RUN
# =========================

async def main():
    print("BOT STARTED")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
