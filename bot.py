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

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MANAGER_CHAT = 6600140962
SUPREMA_IMAGE = "suprema.jpg"
ACCURE_IMAGE = "accure.jpg"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# =========================
# DATABASE
# =========================

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    full_name TEXT,
    action TEXT,
    created_at TEXT
)
"""
)

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
    cursor.execute(
        """
        INSERT INTO analytics (username, full_name, action, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            user.username,
            user.full_name,
            action,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()


async def send_lead_to_manager(text):
    await bot.send_message(MANAGER_CHAT, text)


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start_handler(message: Message):

    print("USER ID:", message.chat.id)

    # Фото Suprema
    try:
        suprema = FSInputFile(SUPREMA_IMAGE)

        await message.answer_photo(
            photo=suprema,
            caption="🔥 Suprema — флагманська платформа Quanta System"
        )

    except Exception as e:
        print("SUPREMA ERROR:", e)

    # Фото Accure
    try:
        accure = FSInputFile(ACCURE_IMAGE)

        await message.answer_photo(
            photo=accure,
            caption="❄️ Accure — Єдина в світі система апаратного лікування акне"
        )

    except Exception as e:
        print("ACCURE ERROR:", e)

    await message.answer(
        """
🔥 Chat Лідери для лідерів DUSO

Оберіть потрібний пункт меню:

📍 Звязатись з нами:
Київ, вул. Садово-Ботанічна, 64
📞 044 506 77 77
duso.ua
        """,
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
        caption="Каталог Quanta System"
    )

    save_analytics(message.from_user, "download_pdf")


# =========================
# OFFICE CONSULTATION
# =========================

@dp.message(F.text == "🏢 Замовити консультацію в офісі ДЮСО")
async def office_consultation(message: Message, state: FSMContext):
    await state.set_state(OfficeConsultation.name)
    await message.answer("Вкажіть ваше ім'я:")


@dp.message(OfficeConsultation.name)
async def office_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OfficeConsultation.phone)
    await message.answer("Вкажіть номер телефону:")


@dp.message(OfficeConsultation.phone)
async def office_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(OfficeConsultation.city)
    await message.answer("Ваше місто:")


@dp.message(OfficeConsultation.city)
async def office_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(OfficeConsultation.comment)
    await message.answer("Коментар або побажання:")


@dp.message(OfficeConsultation.comment)
async def office_comment(message: Message, state: FSMContext):
    await state.update_data(comment=message.text)

    data = await state.get_data()

    text = f"""
🏢 НОВА ЗАЯВКА — КОНСУЛЬТАЦІЯ В ОФІСІ

👤 Ім'я: {data['name']}
📱 Телефон: {data['phone']}
🏙 Місто: {data['city']}
💬 Коментар: {data['comment']}

Telegram: @{message.from_user.username}
    """

    await send_lead_to_manager(text)

    save_analytics(message.from_user, "office_consultation")

    await message.answer(
        "✅ Дякуємо! Менеджер DUSO зв'яжеться з вами найближчим часом. 📞 044 506 77 77",
        reply_markup=main_keyboard,
    )

    await state.clear()


# =========================
# ONLINE CONSULTATION
# =========================

@dp.message(F.text == "💻 Замовити консультацію онлайн")
async def online_consultation(message: Message, state: FSMContext):
    await state.set_state(OnlineConsultation.name)
    await message.answer("Вкажіть ваше ім'я:")


@dp.message(OnlineConsultation.name)
async def online_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OnlineConsultation.phone)
    await message.answer("Вкажіть номер телефону:")


@dp.message(OnlineConsultation.phone)
async def online_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(OnlineConsultation.contact)
    await message.answer("Ваш Telegram або email:")


@dp.message(OnlineConsultation.contact)
async def online_contact(message: Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await state.set_state(OnlineConsultation.time)
    await message.answer("Зручний час для консультації:")


@dp.message(OnlineConsultation.time)
async def online_time(message: Message, state: FSMContext):
    await state.update_data(time=message.text)

    data = await state.get_data()

    text = f"""
💻 НОВА ЗАЯВКА — ОНЛАЙН КОНСУЛЬТАЦІЯ

👤 Ім'я: {data['name']}
📱 Телефон: {data['phone']}
📧 Контакт: {data['contact']}
⏰ Зручний час: {data['time']}

Telegram: @{message.from_user.username}
    """

    await send_lead_to_manager(text)

    save_analytics(message.from_user, "online_consultation")

    await message.answer(
        "✅ Дякуємо! Менеджер DUSO зв'яжеться з вами найближчим часом. 📞 044 506 77 77",
        reply_markup=main_keyboard,
    )

    await state.clear()


# =========================
# ANALYTICS
# =========================

@dp.message(F.text == "/analytics")
async def analytics(message: Message):
    cursor.execute("SELECT COUNT(*) FROM analytics WHERE action='download_pdf'")
    downloads = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM analytics WHERE action='office_consultation'")
    office = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM analytics WHERE action='online_consultation'")
    online = cursor.fetchone()[0]

    text = f"""
📊 АНАЛІТИКА DUSO BOT

📄 Завантажень PDF: {downloads}
🏢 Консультацій в офісі: {office}
💻 Онлайн консультацій: {online}
    """

    await message.answer(text)


# =========================
# MAIN
# =========================

async def main():
    print("BOT STARTED")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())