import os
import json
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# ——— Logging ——————————————————————————————————————
logging.basicConfig(level=logging.INFO)

# ——— Environment ——————————————————————————————————
BOT_TOKEN          = os.getenv("BOT_TOKEN")
GOOGLE_CREDS_JSON  = os.getenv("GOOGLE_CREDS_JSON")
SPREADSHEET_NAME   = os.getenv("SPREADSHEET_NAME")

if not BOT_TOKEN or not GOOGLE_CREDS_JSON or not SPREADSHEET_NAME:
    raise RuntimeError("Required env vars: BOT_TOKEN, GOOGLE_CREDS_JSON, SPREADSHEET_NAME")

# ——— Telegram bot setup ————————————————————————————
bot     = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp      = Dispatcher(bot, storage=storage)

# ——— Google Sheets setup ——————————————————————————
def init_gspread():
    # 1. Считаем экранированный JSON из переменной окружения
    raw = os.getenv("GOOGLE_CREDS_JSON")
    if not raw:
        raise RuntimeError("GOOGLE_CREDS_JSON not set")

    # 2. Заменяем в нём все двойные слэши-n (\\n) на реальные переводы строк (\n)
    fixed = raw.replace("\\n", "\n")

    # 3. Парсим строку в Python-словарь
    creds_dict = json.loads(fixed)

    # 4. Авторизуемся в Google Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    # 5. Открываем твой лист по имени
    return client.open(SPREADSHEET_NAME).sheet1


sheet = init_gspread()

# ——— Survey states —————————————————————————————
class Survey(StatesGroup):
    first_name = State()
    last_name  = State()
    email      = State()
    country    = State()
    city       = State()

# ——— /start ——————————————————————————————————————
@dp.message_handler(commands="start", state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Welcome! Let's endorse the Plant Based Treaty.\n\nFirst Name:")
    await Survey.first_name.set()

# ——— First Name ——————————————————————————————————
@dp.message_handler(state=Survey.first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("Last Name:")
    await Survey.last_name.set()

# ——— Last Name ———————————————————————————————————
@dp.message_handler(state=Survey.last_name)
async def process_last_name(message: types.Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await message.answer("Email:")
    await Survey.email.set()

# ——— Email —————————————————————————————————————
@dp.message_handler(state=Survey.email)
async def process_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer("Country:")
    await Survey.country.set()

# ——— Country ————————————————————————————————————
@dp.message_handler(state=Survey.country)
async def process_country(message: types.Message, state: FSMContext):
    await state.update_data(country=message.text)
    await message.answer("City:")
    await Survey.city.set()

# ——— City & Submit —————————————————————————————
@dp.message_handler(state=Survey.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    data = await state.get_data()

    row = [
        data["first_name"],
        data["last_name"],
        data["email"],
        data["country"],
        data["city"]
    ]
    sheet.append_row(row)

    await message.answer("Thank you for endorsing the Plant Based Treaty! ✅")
    await state.finish()

# ——— Fallback ————————————————————————————————————
@dp.message_handler()
async def fallback(message: types.Message):
    await message.reply("Please send /start to begin.")

# ——— Entrypoint ———————————————————————————————————
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
