import asyncio
import sqlite3
from datetime import datetime

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
import os

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

conn.commit()

# =========================
# STATES
# =========================

class OfficeConsultation(StatesGroup):
    name = State()
    phone = State()
    city = State()
    comment = State()


class OnlineConsultation(StatesGroup):
    name = State()
    phone = State()
    contact = State()
    time = State()

# =========================
# KEYBOARD
# =========================

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📄 Отримати презентацію")],
        [KeyboardButton(text="🏢 Замовити консультацію в офісі ДЮСО")],
        [KeyboardButton(text="💻 Замовити консультацію онлайн")],
    ],
    resize_keyboard=True,
)

# =========================
# HELPERS
# =========================

def save_analytics(user, action):
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


async def send_lead_to_manager(text):
    await bot.send_message(MANAGER_CHAT, text)

# =========================
# START
# =========================

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "🔥 DUSO BOT",
        reply_markup=main_keyboard
    )

# =========================
# PDF
# =========================

@dp.message(F.text == "📄 Отримати презентацію")
async def send_presentation(message: Message):

    pdf = FSInputFile("catalog.pdf")

    await message.answer_document(
        document=pdf,
        caption="Каталог DUSO"
    )

    save_analytics(message.from_user, "download_pdf")

# =========================
# OFFICE
# =========================

@dp.message(F.text == "🏢 Замовити консультацію в офісі ДЮСО")
async def office_start(message: Message, state: FSMContext):
    await state.set_state(OfficeConsultation.name)
    await message.answer("Ім'я:")

@dp.message(OfficeConsultation.name)
async def office_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OfficeConsultation.phone)
    await message.answer("Телефон:")

@dp.message(OfficeConsultation.phone)
async def office_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(OfficeConsultation.city)
    await message.answer("Місто:")

@dp.message(OfficeConsultation.city)
async def office_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(OfficeConsultation.comment)
    await message.answer("Коментар:")

@dp.message(OfficeConsultation.comment)
async def office_finish(message: Message, state: FSMContext):
    data = await state.get_data()

    text = f"""
🏢 ОФЛАЙН ЗАЯВКА

👤 {data['name']}
📱 {data['phone']}
🏙 {data['city']}
💬 {message.text}
"""

    await send_lead_to_manager(text)
    save_analytics(message.from_user, "office_consultation")

    await message.answer("Дякуємо!", reply_markup=main_keyboard)
    await state.clear()

# =========================
# ONLINE
# =========================

@dp.message(F.text == "💻 Замовити консультацію онлайн")
async def online_start(message: Message, state: FSMContext):
    await state.set_state(OnlineConsultation.name)
    await message.answer("Ім'я:")

@dp.message(OnlineConsultation.name)
async def online_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OnlineConsultation.phone)
    await message.answer("Телефон:")

@dp.message(OnlineConsultation.phone)
async def online_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(OnlineConsultation.contact)
    await message.answer("Контакт:")

@dp.message(OnlineConsultation.contact)
async def online_contact(message: Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await state.set_state(OnlineConsultation.time)
    await message.answer("Час:")

@dp.message(OnlineConsultation.time)
async def online_finish(message: Message, state: FSMContext):
    data = await state.get_data()

    text = f"""
💻 ОНЛАЙН ЗАЯВКА

👤 {data['name']}
📱 {data['phone']}
📧 {data['contact']}
⏰ {message.text}
"""

    await send_lead_to_manager(text)
    save_analytics(message.from_user, "online_consultation")

    await message.answer("Дякуємо!", reply_markup=main_keyboard)
    await state.clear()

# =========================
# STATS (ONLY MANAGER)
# =========================

@dp.message(F.text == "/analytics")
async def analytics(message: Message):

    if message.chat.id != MANAGER_CHAT:
        return

    cursor.execute("SELECT COUNT(*) FROM analytics WHERE action='download_pdf'")
    pdf = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM analytics WHERE action='office_consultation'")
    office = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM analytics WHERE action='online_consultation'")
    online = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM analytics")
    total = cursor.fetchone()[0]

    text = f"""
📊 СТАТИСТИКА

📄 PDF: {pdf}
🏢 Офлайн: {office}
💻 Онлайн: {online}

📦 Всього: {total}
"""

    await message.answer(text)

# =========================
# EXPORT EXCEL
# =========================

@dp.message(F.text == "/export")
async def export_excel(message: Message):

    if message.chat.id != MANAGER_CHAT:
        return

    cursor.execute("SELECT * FROM analytics")
    rows = cursor.fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"

    ws.append(["ID", "Username", "Full Name", "Action", "Date"])

    for row in rows:
        ws.append(row)

    file_path = "leads.xlsx"
    wb.save(file_path)

    await message.answer_document(
        FSInputFile(file_path),
        caption="📁 Експорт лідів"
    )

# =========================
# MAIN
# =========================

async def main():
    print("BOT STARTED")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
