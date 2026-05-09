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
    InputMediaPhoto,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
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
        [KeyboardButton(text="📄 Отримати презентацію")],
        [KeyboardButton(text="🏢 Консультація в офісі")],
        [KeyboardButton(text="💻 Онлайн консультація")],
    ],
    resize_keyboard=True,
)

admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="📁 Експорт CRM")],
        [KeyboardButton(text="🧹 Reset (TEST)")],
    ],
    resize_keyboard=True,
)

def call_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Зателефонувати", url="tel:+380445067777")]
    ])

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

async def send_lead_to_manager(text):
    await bot.send_message(MANAGER_CHAT, text)

# =========================
# START + CAROUSEL
# =========================

@dp.message(CommandStart())
async def start(message: Message):

    if message.chat.id == MANAGER_CHAT:
        await message.answer("🔐 ADMIN PANEL", reply_markup=admin_keyboard)
        return

    try:
        media = [
            InputMediaPhoto(FSInputFile("suprema.jpg"),
                caption="🔥 Suprema — флагманська платформа Quanta System"),
            InputMediaPhoto(FSInputFile("accure.jpg"),
                caption="❄️ Accure — Єдина в світі система апаратного лікування акне"),
        ]
        await message.answer_media_group(media)
    except:
        pass

    await message.answer(
        """
🔥 ЛІДЕРИ ДЛЯ ЛІДЕРІВ - DUSO since 2006

📍 Київ, вул. Садово-Ботанічна, 64
📞 +380445067777
🌐 duso.ua
📸 Instagram: <a href="https://www.instagram.com/duso.ua?igsh=ZmNmZGVzcHJuNGM5">@duso.ua</a>

Цікавить індивідуальна консультація або презентація 👇
        """,
        reply_markup=main_keyboard,
        parse_mode="HTML"
    )

# =========================
# PDF
# =========================

@dp.message(F.text == "📄 Отримати презентацію")
async def pdf(message: Message):

    await message.answer_document(FSInputFile("catalog.pdf"))

    save_event(message.from_user, "pdf_download")

# =========================
# OFFICE LEAD
# =========================

@dp.message(F.text == "🏢 Консультація в офісі")
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
    await message.answer("Додатковий коментар:")

@dp.message(Office.comment)
async def office_finish(message: Message, state: FSMContext):

    data = await state.get_data()

    save_lead(data, message.from_user, "office")
    save_event(message.from_user, "office")

    await send_lead_to_manager(f"""
🏢 ОФІС ЛІД

👤 {data['name']}
📱 {data['phone']}
🏙 {data['city']}
💬 {message.text}

TG: @{message.from_user.username}
""")

    await message.answer(
        "🙏 Дякуємо! Найближчим часом з Вами зв’яжеться наш менеджер."
    )

    await message.answer(
        "📞 Ми завжди на зв'язку!",
        reply_markup=call_keyboard()
    )

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
    await message.answer("Додатковий контакт/e-mail:")

@dp.message(Online.contact)
async def online_contact(message: Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await state.set_state(Online.time)
    await message.answer("Бажана дата:")

@dp.message(Online.time)
async def online_finish(message: Message, state: FSMContext):

    data = await state.get_data()

    save_lead(data, message.from_user, "online")
    save_event(message.from_user, "online")

    await send_lead_to_manager(f"""
💻 ОНЛАЙН ЛІД

👤 {data['name']}
📱 {data['phone']}
📧 {data['contact']}
⏰ {message.text}

TG: @{message.from_user.username}
""")

    await message.answer(
        "🙏 Дякуємо! Найближчим часом з Вами зв’яжеться наш менеджер."
    )

    await message.answer(
        "📞 Ми завжди на зв'язку!",
        reply_markup=call_keyboard()
    )

    await state.clear()

# =========================
# STATISTICS
# =========================

@dp.message(F.text == "📊 Статистика")
async def stats(message: Message):

    if message.chat.id != MANAGER_CHAT:
        return

    cursor.execute("SELECT COUNT(*) FROM leads")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE source='office'")
    office = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE source='online'")
    online = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM analytics WHERE action='pdf_download'")
    pdf = cursor.fetchone()[0]

    await message.answer(f"""
📊 CRM

📦 Всього: {total}
🏢 Офіс: {office}
💻 Онлайн: {online}
📄 PDF: {pdf}
""")

# =========================
# EXPORT CRM
# =========================

@dp.message(F.text == "📁 Експорт CRM")
async def export(message: Message):

    if message.chat.id != MANAGER_CHAT:
        return

    wb = Workbook()

    ws1 = wb.active
    ws1.title = "LEADS"

    ws1.append(["ID","Username","Full Name","Phone","City","Contact","Comment","Source","Date"])

    cursor.execute("SELECT * FROM leads")
    for r in cursor.fetchall():
        ws1.append(r)

    ws2 = wb.create_sheet("PDF")

    ws2.append(["Username","Full Name","Date"])

    cursor.execute("""
        SELECT username, full_name, created_at
        FROM analytics
        WHERE action='pdf_download'
    """)

    for r in cursor.fetchall():
        ws2.append(r)

    wb.save("crm.xlsx")

    await message.answer_document(FSInputFile("crm.xlsx"))

# =========================
# RESET
# =========================

@dp.message(F.text == "🧹 Reset ")
async def reset(message: Message):

    if message.chat.id != MANAGER_CHAT:
        return

    cursor.execute("DELETE FROM leads")
    cursor.execute("DELETE FROM analytics")
    conn.commit()

    await message.answer("♻️ RESET DONE")

# =========================
# RUN
# =========================

async def main():
    print("BOT STARTED")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
