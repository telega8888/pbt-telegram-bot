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

# Получаем переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

# Проверка наличия переменных окружения
if not BOT_TOKEN or not GOOGLE_CREDS_JSON:
    raise ValueError("Переменные окружения BOT_TOKEN и GOOGLE_CREDS_JSON обязательны.")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Настройка доступа к Google Таблице
def init_gspread():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("PBTEndorsements").sheet1
    return sheet

sheet = init_gspread()

# Состояния анкеты
class Form(StatesGroup):
    name = State()
    surname = State()
    email = State()
    country = State()
    city = State()

# Старт команды
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
    await message.answer("Из какого города?")
    await Form.city.set()

@dp.message_handler(state=Form.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    data = await state.get_data()

    # Добавляем строку в таблицу
    sheet.append_row([
        data["name"],
        data["surname"],
        data["email"],
        data["country"],
        data["city"]
    ])

    await message.answer("Спасибо! Ты поддержал инициативу Plant Based Treaty 🌱")
    await state.finish()

# Запуск бота
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
