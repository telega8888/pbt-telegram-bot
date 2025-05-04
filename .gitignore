from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiohttp import web
import asyncio
import logging
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Настройки
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Настройка Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = os.getenv("GOOGLE_CREDS_JSON")
creds = ServiceAccountCredentials.from_json_keyfile_dict(eval(creds_json), scope)
client = gspread.authorize(creds)
spreadsheet = client.open("PBTEndorsements")
sheet = spreadsheet.sheet1

# Состояния
class Form(StatesGroup):
    first_name = State()
    last_name = State()
    email = State()
    country = State()
    city = State()

# Хендлер на /start
@dp.message(commands="start")
async def cmd_start(message: Message, state: FSMContext):
    await message.answer("👋 Привет! Давайте поддержим инициативу Plant Based Treaty.\nКак вас зовут?")
    await state.set_state(Form.first_name)

@dp.message(Form.first_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("А фамилия?")
    await state.set_state(Form.last_name)

@dp.message(Form.last_name)
async def process_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await message.answer("Ваш email:")
    await state.set_state(Form.email)

@dp.message(Form.email)
async def process_email(message: Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer("Из какой вы страны?")
    await state.set_state(Form.country)

@dp.message(Form.country)
async def process_country(message: Message, state: FSMContext):
    await state.update_data(country=message.text)
    await message.answer("А город?")
    await state.set_state(Form.city)

@dp.message(Form.city)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    data = await state.get_data()
    row = [data["first_name"], data["last_name"], data["email"], data["country"], data["city"]]
    sheet.append_row(row)
    await message.answer("✅ Спасибо! Ваш отклик сохранён.")
    await state.clear()

# Обработка необработанных сообщений
@dp.message()
async def fallback(message: Message):
    await message.answer("Пожалуйста, используйте команду /start, чтобы начать анкету.")

# Веб-сервер
async def on_startup(app):
    logging.info("Устанавливаю webhook...")
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=False)
    logging.info("Webhook установлен")

async def on_shutdown(app):
    logging.warning("Отключение...")

async def handle_webhook(request):
    body = await request.json()
    update = types.Update(**body)
    await dp.feed_update(bot, update)
    return web.Response()

app = web.Application()
app.router.add_post('/webhook', handle_webhook)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
