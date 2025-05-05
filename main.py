import os
import json
import logging

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# Логи
logging.basicConfig(level=logging.INFO)

# Переменные окружения
BOT_TOKEN         = os.getenv("BOT_TOKEN")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
SPREADSHEET_NAME  = os.getenv("SPREADSHEET_NAME")

if not BOT_TOKEN or not GOOGLE_CREDS_JSON or not SPREADSHEET_NAME:
    raise RuntimeError("Env vars BOT_TOKEN, GOOGLE_CREDENTIALS_JSON, SPREADSHEET_NAME required")

# Инициализация бота и диспетчера
bot     = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp      = Dispatcher(bot, storage=storage)

# Функция для инициализации Google Sheets
def init_gspread():
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open(SPREADSHEET_NAME).sheet1

sheet = init_gspread()

# Описание состояний
class Survey(StatesGroup):
    first_name = State()
    last_name  = State()
    email      = State()
    country    = State()
    city       = State()

# Команда /start
@dp.message_handler(commands="start", state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Welcome! Let's endorse the Plant Based Treaty.\nFirst Name:")
    await Survey.first_name.set()

# Первый вопрос
@dp.message_handler(state=Survey.first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("Last Name:")
    await Survey.last_name.set()

# Второй вопрос
@dp.message_handler(state=Survey.last_name)
async def process_last_name(message: types.Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await message.answer("Email:")
    await Survey.email.set()

# Третий вопрос
@dp.message_handler(state=Survey.email)
async def process_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer("Country:")
    await Survey.country.set()

# Четвёртый вопрос
@dp.message_handler(state=Survey.country)
async def process_country(message: types.Message, state: FSMContext):
    await state.update_data(country=message.text)
    await message.answer("City:")
    await Survey.city.set()

# Финальный вопрос и запись в таблицу
@dp.message_handler(state=Survey.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    data = await state.get_data()

    # Добавляем строку в Google Sheet
    sheet.append_row([
        data["first_name"],
        data["last_name"],
        data["email"],
        data["country"],
        data["city"]
    ])

    await message.answer("Thank you for endorsing the Plant Based Treaty! ✅")
    await state.finish()

# Фолбэк
@dp.message_handler()
async def fallback(message: types.Message):
    await message.reply("Please send /start to begin.")

# Запуск polling
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
