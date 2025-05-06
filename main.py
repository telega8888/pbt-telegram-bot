import os
import json
import logging
import base64
# ——— рабочий код ———————————————————————————
import gspread
from aiohttp import web
from oauth2client.service_account import ServiceAccountCredentials
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import Dispatcher as AiogramDispatcher

# ——— Логирование ——————————————————————————————————————————
logging.basicConfig(level=logging.INFO)

# ——— Переменные окружения ———————————————————————————————
BOT_TOKEN        = os.getenv("BOT_TOKEN")
GOOGLE_CREDS_B64 = os.getenv("GOOGLE_CREDS_B64")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")
WEBHOOK_URL      = os.getenv("WEBHOOK_URL")   # https://<your-app>.onrender.com/webhook
PORT             = int(os.getenv("PORT", 8080))

if not all([BOT_TOKEN, GOOGLE_CREDS_B64, SPREADSHEET_NAME, WEBHOOK_URL]):
    raise RuntimeError("Missing one or more required environment variables")

# ——— Инициализация бота и FSM-хранилища ———————————————
bot = Bot(token=BOT_TOKEN)
Bot.set_current(bot)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ——— Google Sheets —————————————————————————————————————
def init_gspread():
    creds_json  = base64.b64decode(GOOGLE_CREDS_B64).decode("utf-8")
    creds_dict  = json.loads(creds_json)
    scope       = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds       = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client      = gspread.authorize(creds)
    return client.open(SPREADSHEET_NAME).sheet1

sheet = init_gspread()

# ——— FSM: состояния анкеты —————————————————————————————
class Survey(StatesGroup):
    first_name = State()
    last_name  = State()
    email      = State()
    country    = State()
    city       = State()

# ——— Обработчики FSM —————————————————————————————————————
@dp.message_handler(commands=["start"], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    logging.info("CMD_START")
    await state.finish()
    await message.answer("Welcome! Let's endorse the Plant Based Treaty.\n\nFirst Name:")
    await Survey.first_name.set()

@dp.message_handler(state=Survey.first_name)
async def step_first_name(message: types.Message, state: FSMContext):
    logging.info("STEP first_name: %s", message.text)
    await state.update_data(first_name=message.text.strip())
    await message.answer("Last Name:")
    await Survey.last_name.set()

@dp.message_handler(state=Survey.last_name)
async def step_last_name(message: types.Message, state: FSMContext):
    logging.info("STEP last_name: %s", message.text)
    await state.update_data(last_name=message.text.strip())
    await message.answer("Email:")
    await Survey.email.set()

@dp.message_handler(state=Survey.email)
async def step_email(message: types.Message, state: FSMContext):
    logging.info("STEP email: %s", message.text)
    await state.update_data(email=message.text.strip())
    await message.answer("Country:")
    await Survey.country.set()

@dp.message_handler(state=Survey.country)
async def step_country(message: types.Message, state: FSMContext):
    logging.info("STEP country: %s", message.text)
    await state.update_data(country=message.text.strip())
    await message.answer("City:")
    await Survey.city.set()

@dp.message_handler(state=Survey.city)
async def step_city(message: types.Message, state: FSMContext):
    logging.info("STEP city: %s", message.text)
    await state.update_data(city=message.text.strip())
    data = await state.get_data()
    try:
        sheet.append_row([
            data.get("first_name", ""),
            data.get("last_name", ""),
            data.get("email", ""),
            data.get("country", ""),
            data.get("city", "")
        ])
        await message.answer("✅ Thank you for endorsing the Plant Based Treaty!")
    except Exception:
        logging.exception("Error writing to Google Sheet")
        await message.answer("⚠️ Error saving your response. Please try again later.")
    await state.finish()

@dp.message_handler()
async def unknown_message(message: types.Message):
    logging.info("UNKNOWN MESSAGE in state %s", await dp.current_state(chat=message.chat.id).get_state())
    await message.reply("To start a new survey, send /start")

# ——— Webhook endpoint ———————————————————————————————————
async def handle_webhook(request: web.Request):
    data = await request.json()
    Bot.set_current(bot)
    AiogramDispatcher.set_current(dp)
    update = types.Update(**data)
    await dp.process_update(update)
    return web.Response()

# ——— Healthcheck endpoints —————————————————————————————
async def ping(request: web.Request):
    return web.Response(text="pong")

async def root(request: web.Request):
    return web.Response(text="Bot is alive!")

# ——— Сборка приложения ———————————————————————————————————
app = web.Application()
app.router.add_post("/webhook", handle_webhook)
app.router.add_get("/ping", ping)  # GET /ping и HEAD /ping по умолчанию
app.router.add_get("/", root)

# ——— Синхронная установка webhook перед запуском ——————————
if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    logging.info("Main: deleting old webhook...")
    loop.run_until_complete(bot.delete_webhook(drop_pending_updates=True))
    logging.info("Main: setting new webhook to %s", WEBHOOK_URL)
    loop.run_until_complete(bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True))

    print(f"🚀 Server is running on port {PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)
