import logging
import os
import json
from io import StringIO
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

API_TOKEN = os.getenv('TELEGRAM_TOKEN')
GOOGLE_CREDS_JSON = os.getenv('GOOGLE_CREDS_JSON')  # JSON-строка с ключами сервисного аккаунта
SPREADSHEET_NAME = 'PBTEndorsements'

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Google Sheets setup
def init_gspread():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    json_creds = json.loads(GOOGLE_CREDS_JSON)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json_creds, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).sheet1
    return sheet

sheet = init_gspread()

# Define survey states
class Survey(StatesGroup):
    first_name = State()
    last_name = State()
    email = State()
    country = State()
    city = State()
    subscribe = State()

# Start command handler
@dp.message_handler(commands='start', state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Welcome! Let's endorse the Plant Based Treaty.\nFirst Name:")
    await Survey.first_name.set()

# First Name
@dp.message_handler(state=Survey.first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer('Last Name:')
    await Survey.next()

# Last Name
@dp.message_handler(state=Survey.last_name)
async def process_last_name(message: types.Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await message.answer('Email:')
    await Survey.next()

# Email
@dp.message_handler(state=Survey.email)
async def process_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer('Country:')
    await Survey.next()

# Country
@dp.message_handler(state=Survey.country)
async def process_country(message: types.Message, state: FSMContext):
    await state.update_data(country=message.text)
    await message.answer('City:')
    await Survey.next()

# City
@dp.message_handler(state=Survey.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    # Subscription question with buttons
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('Yes', callback_data='subscribe_yes'))
    keyboard.add(types.InlineKeyboardButton('No', callback_data='subscribe_no'))
    await message.answer('Would you like to receive occasional updates via email?', reply_markup=keyboard)
    await Survey.subscribe.set()

# Subscription callback
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('subscribe_'), state=Survey.subscribe)
async def process_subscribe(callback_query: types.CallbackQuery, state: FSMContext):
    subscribe_choice = 'yes' if callback_query.data == 'subscribe_yes' else 'no'
    await state.update_data(subscribe=subscribe_choice)

    # Gather all data and write to sheet
    user_data = await state.get_data()
    row = [
        user_data['first_name'],
        user_data['last_name'],
        user_data['email'],
        user_data['country'],
        user_data['city'],
        user_data['subscribe']
    ]
    sheet.append_row(row)

    # Thank you message
    await bot.send_message(callback_query.from_user.id, 'Thank you for endorsing the Plant Based Treaty! ✅')
    await state.finish()

# Fallback
@dp.message_handler()
async def fallback(message: types.Message):
    await message.reply('Please use /start to begin the endorsement.')

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
