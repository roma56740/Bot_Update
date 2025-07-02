from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from config import ADMIN_ID
import db

from datetime import datetime
import pytz
import asyncio


async def notify_user_later(bot, user_id, text):
    tg_id = db.get_telegram_id_by_user_id(user_id)
    if not tg_id:
        return

    now = datetime.now(pytz.timezone("Europe/Moscow"))
    if 21 <= now.hour or now.hour < 8:
        await bot.send_message(tg_id, text)
    else:
        target = 21
        delay_sec = ((target - now.hour) % 24) * 3600
        await asyncio.sleep(delay_sec)
        await bot.send_message(tg_id, text)


class DeleteUserState(StatesGroup):
    waiting_for_username = State()

class PlanSalesState(StatesGroup):
    waiting_for_plan = State()

class HeartGiveState(StatesGroup):
    waiting_for_username = State()
    waiting_for_reason = State()
    waiting_for_reduce_fine = State()

class AddOrderState(StatesGroup):
    waiting_for_username = State()
    waiting_for_price = State()
    waiting_for_description = State()

class HeartRemoveState(StatesGroup):
    waiting_for_username = State()
    waiting_for_fine_reason = State()
    waiting_for_fine_amount = State()


def register_admin_handlers(dp: Dispatcher):

    @dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text == "все пользователи", state="*")
    async def show_all_users(message: types.Message, state: FSMContext):
        await state.finish()
        users = db.get_all_users()
        if not users:
            await message.answer("Пользователей пока нет.")
            return
        text = "👥 Все пользователи:\n\n"
        for user in users:
            text += f"{user['name']} - @{user['username']} ({user['role']})\n"
        await message.answer(text)

    @dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text == "Удалить пользователя", state="*")
    async def delete_user_start(message: types.Message, state: FSMContext):
        await state.finish()
        await message.answer("Введите @username пользователя, которого нужно удалить:")
        await DeleteUserState.waiting_for_username.set()

    @dp.message_handler(state=DeleteUserState.waiting_for_username)
    async def delete_user_by_username(message: types.Message, state: FSMContext):
        username = message.text.strip().lstrip('@')
        success = db.delete_user_by_username(username)
        if success:
            await message.answer(f"Пользователь @{username} удалён.")
        else:
            await message.answer(f"Пользователь @{username} не найден.")
        await state.finish()

    @dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text == "План продаж", state="*")
    async def start_plan_sales(message: types.Message, state: FSMContext):
        await state.finish()
        await message.answer("Введите два числа через пробел: план на день и на месяц (в BYN)")
        await PlanSalesState.waiting_for_plan.set()

    @dp.message_handler(state=PlanSalesState.waiting_for_plan)
    async def set_plan_sales(message: types.Message, state: FSMContext):
        try:
            day, month = map(float, message.text.strip().split())
        except:
            await message.answer("Ошибка ввода. Введите два числа через пробел, например: 200 5000")
            return
        db.set_plan_for_all(day, month)
        await message.answer(f"✅ План установлен: {day} BYN в день, {month} BYN в месяц для всех менеджеров.")
        await state.finish()

    @dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text == "Все менеджеры", state="*")
    async def show_all_managers(message: types.Message, state: FSMContext):
        await state.finish()
        managers = db.get_all_managers_with_stats()
        if not managers:
            await message.answer("Менеджеров пока нет.")
            return
        text = "📊 Все менеджеры:\n\n"
        for m in managers:
            conversion = (m['day_sales'] / m['day_plan'] * 100) if m['day_plan'] else 0
            text += (
                f"👤 {m['name']} - @{m['username']}\n"
                f"📅 План: {m['day_plan']} / {m['month_plan']} BYN\n"
                f"💰 Продажи: {m['day_sales']} BYN\n"
                f"📦 Заказы: {m['orders_count']} шт\n"
                f"📈 Конверсия: {conversion:.1f}%\n\n"
            )
        await message.answer(text)

    @dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text == "добавить заказ", state="*")
    async def start_add_order(message: types.Message, state: FSMContext):
        await state.finish()
        await message.answer("Введите @username менеджера, которому хотите добавить заказ:")
        await AddOrderState.waiting_for_username.set()

    @dp.message_handler(state=AddOrderState.waiting_for_username)
    async def get_order_price(message: types.Message, state: FSMContext):
        username = message.text.strip().lstrip('@')
        user = db.get_user_by_username(username)
        if not user or user['role'] != 'менеджер':
            await message.answer("Пользователь не найден или не является менеджером.")
            return
        await state.update_data(user_id=user['id'], username=username)
        await message.answer("Введите сумму заказа (в BYN):")
        await AddOrderState.waiting_for_price.set()

    @dp.message_handler(state=AddOrderState.waiting_for_price)
    async def get_order_description(message: types.Message, state: FSMContext):
        try:
            price = float(message.text.strip())
        except:
            await message.answer("Введите сумму заказа числом.")
            return
        await state.update_data(price=price)
        await message.answer("Введите описание заказа:")
        await AddOrderState.waiting_for_description.set()

    @dp.message_handler(state=AddOrderState.waiting_for_description)
    async def finish_add_order(message: types.Message, state: FSMContext):
        data = await state.get_data()
        db.add_order(data['user_id'], data['price'], message.text.strip())
        db.update_sales_stats(data['user_id'], data['price'])
        await message.answer("✅ Заказ добавлен!")
        tg_id = db.get_telegram_id_by_user_id(data['user_id'])
        if tg_id:
            await message.bot.send_message(
                tg_id,
                f"📦 Вам добавлен заказ:\n💰 Сумма: {data['price']} BYN\n📝 Описание: {message.text.strip()}"
            )
        await state.finish()

    @dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text == "добавить сердце", state="*")
    async def start_add_heart(message: types.Message, state: FSMContext):
        await state.finish()
        await message.answer("Введите @username пользователя, которому хотите добавить сердце:")
        await HeartGiveState.waiting_for_username.set()

    @dp.message_handler(state=HeartGiveState.waiting_for_username)
    async def check_user_for_heart(message: types.Message, state: FSMContext):
        username = message.text.strip().lstrip('@')
        user = db.get_user_by_username(username)
        if not user:
            await message.answer("Пользователь не найден.")
            return
        await state.update_data(user_data=user)
        if user['fine'] > 0:
            await message.answer(f"У пользователя штраф: {user['fine']} BYN. Сколько списать?")
            await HeartGiveState.waiting_for_reduce_fine.set()
        elif user['hearts'] >= 3:
            await message.answer("У пользователя уже максимум 3 сердца. Добавить невозможно.")
            await state.finish()
        else:
            await message.answer("Введите причину, за что добавляется сердце:")
            await HeartGiveState.waiting_for_reason.set()

    @dp.message_handler(state=HeartGiveState.waiting_for_reduce_fine)
    async def reduce_fine(message: types.Message, state: FSMContext):
        try:
            amount = int(message.text.strip())
        except:
            await message.answer("Введите сумму списания штрафа числом.")
            return
        data = await state.get_data()
        user = data['user_data']
        new_fine = max(0, user['fine'] - amount)
        db.set_user_fine(user['id'], new_fine)
        if new_fine == 0 and user['hearts'] < 3:
            await message.answer("Штраф закрыт. Введите причину, за что добавляется сердце:")
            await HeartGiveState.waiting_for_reason.set()
        else:
            await message.answer("Штраф обновлён.")
            await state.finish()

    @dp.message_handler(state=HeartGiveState.waiting_for_reason)
    async def add_heart(message: types.Message, state: FSMContext):
        reason = message.text.strip()
        data = await state.get_data()
        user = data['user_data']
        db.add_heart(user['id'])
        await message.answer(f"Сердце добавлено пользователю @{user['username']} ❤️")
        now = datetime.now(pytz.timezone("Europe/Moscow"))
        if 21 <= now.hour or now.hour < 8:
            tg_id = db.get_telegram_id_by_user_id(user['id'])
            if tg_id:
                await message.bot.send_message(
                    tg_id,
                    f"💖 Вам добавлено сердце!\nПричина: {reason}"
                )
        else:
            await message.answer("⚠️ Сообщение пользователю будет отправлено ночью (21:00–08:00 по МСК).")
        await state.finish()

    @dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and m.text == "снять сердце", state="*")
    async def start_remove_heart(message: types.Message, state: FSMContext):
        await state.finish()
        await message.answer("Введите @username пользователя, у которого хотите снять сердце:")
        await HeartRemoveState.waiting_for_username.set()

    @dp.message_handler(state=HeartRemoveState.waiting_for_username)
    async def remove_heart_or_fine(message: types.Message, state: FSMContext):
        username = message.text.strip().lstrip('@')
        user = db.get_user_by_username(username)
        if not user:
            await message.answer("Пользователь не найден.")
            return
        await state.update_data(user_data=user)
        if user['hearts'] > 0:
            db.remove_heart(user['id'])
            await message.answer("Введите причину снятия сердца:")
            await HeartRemoveState.waiting_for_fine_reason.set()
        else:
            await message.answer("У пользователя нет сердец. Введите сумму штрафа в BYN:")
            await HeartRemoveState.waiting_for_fine_amount.set()

    @dp.message_handler(state=HeartRemoveState.waiting_for_fine_amount)
    async def fine_amount(message: types.Message, state: FSMContext):
        try:
            fine = int(message.text.strip())
        except:
            await message.answer("Введите сумму штрафа числом.")
            return
        await state.update_data(fine=fine)
        await message.answer("Введите причину штрафа:")
        await HeartRemoveState.waiting_for_fine_reason.set()

    @dp.message_handler(state=HeartRemoveState.waiting_for_fine_reason)
    async def handle_fine_or_remove_reason(message: types.Message, state: FSMContext):
        reason = message.text.strip()
        data = await state.get_data()
        user = data['user_data']
        if 'fine' in data:
            fine = data['fine']
            db.add_fine(user['id'], fine)
            await message.answer(f"Пользователю @{user['username']} добавлен штраф {fine} BYN.")
            await notify_user_later(
                message.bot,
                user['id'],
                f"🚫 Вам добавлен штраф: {fine} BYN\nПричина: {reason}"
            )
        else:
            await message.answer(f"❤️ Сердце снято у @{user['username']}.\nПричина сохранена.")
            await notify_user_later(
                message.bot,
                user['id'],
                f"💔 У вас снято сердце.\nПричина: {reason}"
            )
        await state.finish()

    @dp.callback_query_handler(lambda c: c.data.startswith("approve_"))
    async def approve_heart_request(call: types.CallbackQuery):
        _, from_id, to_id = call.data.split("_")
        from_id = int(from_id)
        to_id = int(to_id)
        db.add_heart_by_telegram_id(to_id)
        db.delete_help_request_by_user(from_id)
        await call.message.edit_text("✅ Заявка одобрена.")
        await notify_user_later(call.bot, to_id, "💖 Вам добавлено сердце за помощь от коллеги!")

    @dp.callback_query_handler(lambda c: c.data.startswith("reject_"))
    async def reject_heart_request(call: types.CallbackQuery):
        _, from_id = call.data.split("_")
        from_id = int(from_id)
        db.delete_help_request_by_user(from_id)
        await call.message.edit_text("❌ Заявка отклонена.")
        await call.bot.send_message(from_id, "🚫 Ваша заявка на добавление сердца отклонена.")
