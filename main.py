import os
import json
import logging
import base64

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiohttp import web

logging.basicConfig(level=logging.INFO)

BOT_TOKEN         = os.getenv("BOT_TOKEN")
GOOGLE_CREDS_B64  = os.getenv("GOOGLE_CREDS_B64")
SPREADSHEET_NAME  = os.getenv("SPREADSHEET_NAME")
WEBHOOK_URL       = os.getenv("WEBHOOK_URL")  # Добавь в Render переменную с URL
PORT              = int(os.environ.get("PORT", 8080))

bot     = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp      = Dispatcher(bot, storage=storage)

def init_gspread():
    if not GOOGLE_CREDS_B64:
        raise RuntimeError("GOOGLE_CREDS_B64 not set")
    raw_json = base64.b64decode(GOOGLE_CREDS_B64).decode("utf-8")
    creds_dict = json.loads(raw_json)
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open(SPREADSHEET_NAME).sheet1

sheet = init_gspread()

class Survey(StatesGroup):
    first_name = State()
    last_name  = State()
    email      = State()
    country    = State()
    city       = State()

@dp.message_handler(commands="start", state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Welcome! Let's endorse the Plant Based Treaty.\nFirst Name:")
    await Survey.first_name.set()

@dp.message_handler(state=Survey.first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("Last Name:")
    await Survey.last_name.set()

@dp.message_handler(state=Survey.last_name)
async def process_last_name(message: types.Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await message.answer("Email:")
    await Survey.email.set()

@dp.message_handler(state=Survey.email)
async def process_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer("Country:")
    await Survey.country.set()

@dp.message_handler(state=Survey.country)
async def process_country(message: types.Message, state: FSMContext):
    await state.update_data(country=message.text)
    await message.answer("City:")
    await Survey.city.set()

@dp.message_handler(state=Survey.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    data = await state.get_data()
    row = [data["first_name"], data["last_name"], data["email"], data["country"], data["city"]]
    sheet.append_row(row)
    await message.answer("Thank you for endorsing the Plant Based Treaty! ✅")
    await state.finish()

@dp.message_handler()
async def fallback(message: types.Message):
    await message.reply("Please send /start to begin.")

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()

async def handle_webhook(request):
    body = await request.read()
    update = types.Update.de_json(body.decode("utf-8"))
    await dp.process_update(update)
    return web.Response()

app = web.Application()
app.router.add_post("/", handle_webhook)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, port=PORT)
