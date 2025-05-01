import logging
import json
import os
import gspread
from aiogram import Bot, Dispatcher, types, executor
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from oauth2client.service_account import ServiceAccountCredentials

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Настройки
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

# Проверка переменных окружения
if not BOT_TOKEN or not GOOGLE_CREDS_JSON:
    raise ValueError("Переменные окружения BOT_TOKEN и GOOGLE_CREDS_JSON обязательны.")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Настройка доступа к Google Sheets
def init_gspread():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("PBTEndorsements").sheet1  # Используем ваше название таблицы
    return sheet

sheet = init_gspread()

# Определение состояний
class Form(StatesGroup):
    name = State()
    surname = State()
    email = State()
    country = State()
    message = State()

# Старт
@dp.message_handler(commands="start")
async def start_form(message: types.Message):
    await message.answer("Привет! Давай начнем. Как тебя зовут?")
    await Form.name.set()

@dp.message_handler(state=Form.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("А фамилия?")
    await Form.surname.set()

@dp.message_handler(state=Form.surname)
async def process_surname(message: types.Message, state: FSMContext):
    await state.update_data(surname=message.text)
    await message.answer("Укажи свой email:")
    await Form.email.set()

@dp.message_handler(state=Form.email)
async def process_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer("Из какой ты страны?")
    await Form.country.set()

@dp.message_handler(state=Form.country)
async def process_country(message: types.Message, state: FSMContext):
    await state.update_data(country=message.text)
    await message.answer("Из какого ты города?")
    await Form.message.set()

@dp.message_handler(state=Form.message)
async def process_message(message: types.Message, state: FSMContext):
    await state.update_data(message=message.text)
    data = await state.get_data()

    # Сохраняем в таблицу
    sheet.append_row([
        data["name"],
        data["surname"],
        data["email"],
        data["country"],
        data["message"]
    ])

    await message.answer("Спасибо! Ты поддержал инициативу Plant Based Treaty!")
    await state.finish()

# Запуск
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
