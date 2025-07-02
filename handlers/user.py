from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import ADMIN_ID
import db
from aiogram.dispatcher import FSMContext


from aiogram.dispatcher.filters.state import State, StatesGroup

class HelpRequestState(StatesGroup):
    waiting_for_target = State()
    waiting_for_reason = State()

def register_user_handlers(dp: Dispatcher):

    @dp.message_handler(lambda m: m.text in ["склад", "менеджер", "бухгалтер"])
    async def register_role(message: types.Message):
        user_id = message.from_user.id
        username = message.from_user.username or "нет username"
        full_name = message.from_user.full_name
        role = message.text

        db.register_user(user_id, full_name, username, role)
        await message.answer(f"Вы зарегистрированы как {role}.", reply_markup=user_keyboard(role))


    @dp.message_handler(lambda m: m.text == "Мой статус")
    async def show_my_status(message: types.Message):
        user = db.get_user_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("Вы ещё не зарегистрированы. Нажмите /start.")
            return

        text = (
            f"👤 Имя: {user['name']}\n"
            f"🧑‍💼 Должность: {user['role']}\n"
            f"❤️ Сердец: {user['hearts']}\n"
            f"💸 Штраф: {user['fine']} BYN"
        )
        await message.answer(text)

    @dp.message_handler(lambda m: m.text == "Моя статистика")
    async def show_my_stats(message: types.Message):
        user = db.get_user_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("Вы ещё не зарегистрированы.")
            return

        if user['role'] != 'менеджер':
            await message.answer("Эта функция доступна только менеджерам.")
            return

        stats = db.get_user_stats(user['id'])
        if not stats:
            await message.answer("Статистика не найдена.")
            return

        conversion = 0
        if stats['day_plan'] > 0:
            conversion = (stats['day_sales'] / stats['day_plan']) * 100

        text = (
            f"👤 {user['name']}\n"
            f"📅 План: {stats['day_plan']} / {stats['month_plan']} BYN\n"
            f"💰 Продажи: {stats['day_sales']} BYN\n"
            f"📦 Заказы: {stats['orders_count']} шт\n"
            f"📈 Конверсия: {conversion:.1f}%"
        )
        await message.answer(text)

    @dp.message_handler(lambda m: m.text == "Помог коллеге")
    async def start_help_request(message: types.Message):
        await message.answer("Кому хотите добавить сердце? Напишите `себе` или @username:")
        await HelpRequestState.waiting_for_target.set()
    
    @dp.message_handler(state=HelpRequestState.waiting_for_target)
    async def help_request_target(message: types.Message, state: FSMContext):
        raw = message.text.strip()
        if raw.lower() == "себе":
            await state.update_data(target_id=message.from_user.id)
        else:
            username = raw.lstrip('@')
            user = db.get_user_by_username(username)
            if not user:
                await message.answer("Пользователь не найден.")
                return
            await state.update_data(target_id=user['telegram_id'])

        await state.update_data(from_user_id=message.from_user.id)
        await message.answer("Опишите, как вы помогли:")
        await HelpRequestState.waiting_for_reason.set()


    @dp.message_handler(state=HelpRequestState.waiting_for_reason)
    async def help_request_reason(message: types.Message, state: FSMContext):
        reason = message.text.strip()
        data = await state.get_data()

        db.create_help_request(data['from_user_id'], data['target_id'], reason)

        await message.answer("✅ Заявка отправлена на рассмотрение администратору.")
        await state.finish()

        # Уведомим админа
        from_user = db.get_user_by_telegram_id(data['from_user_id'])
        target_user = db.get_user_by_telegram_id(data['target_id'])

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("✅ Принять", callback_data=f"approve_{data['from_user_id']}_{data['target_id']}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{data['from_user_id']}")
        )

        await message.bot.send_message(
            int(ADMIN_ID),
            f"🆘 Заявка на добавление сердца:\n"
            f"От: {from_user['name']} (@{from_user['username']})\n"
            f"Кому: {target_user['name']} (@{target_user['username']})\n"
            f"Описание: {reason}",
            reply_markup=keyboard
        )



def user_keyboard(role):
    buttons = ["Мой статус", "Помог коллеге"]
    if role == "менеджер":
        buttons.append("Моя статистика")
    return ReplyKeyboardMarkup(resize_keyboard=True).add(*[KeyboardButton(text=b) for b in buttons])
