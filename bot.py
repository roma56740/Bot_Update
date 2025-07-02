from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_ID
from db import init_db
from handlers.user import register_user_handlers
from handlers.admin import register_admin_handlers
from scheduler import setup_daily_report


# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    if user_id == ADMIN_ID:
        await message.answer("Вы вошли как администратор", reply_markup=admin_keyboard())
    else:
        await message.answer("Добро пожаловать! Пожалуйста, выберите свою профессию:",
                             reply_markup=role_keyboard())


def admin_keyboard():
    buttons = [
        "все пользователи", "Удалить пользователя", "План продаж",
        "Все менеджеры", "добавить заказ", "добавить сердце", "снять сердце"
    ]
    return ReplyKeyboardMarkup(resize_keyboard=True).add(*[KeyboardButton(text=b) for b in buttons])


def role_keyboard():
    buttons = ["склад", "менеджер", "бухгалтер"]
    return ReplyKeyboardMarkup(resize_keyboard=True).add(*[KeyboardButton(text=b) for b in buttons])


def user_keyboard(role):
    buttons = ["Мой статус", "Помог коллеге"]
    if role == "менеджер":
        buttons.append("Моя статистика")
    return ReplyKeyboardMarkup(resize_keyboard=True).add(*[KeyboardButton(text=b) for b in buttons])


# Асинхронный запуск при старте
async def on_startup(dispatcher):
    setup_daily_report(bot)  # запуск планировщика внутри asyncio

if __name__ == '__main__':
    init_db()
    register_user_handlers(dp)
    register_admin_handlers(dp)
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
