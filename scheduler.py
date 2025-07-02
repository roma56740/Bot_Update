from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import pytz
import db
from config import ADMIN_ID

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

def setup_daily_report(bot):
    @scheduler.scheduled_job("cron", hour=8, minute=0)
    async def send_daily_report():
        try:
            # 📋 Отчёт по всем пользователям
            users = db.get_all_users_full()
            msg1 = "📋 Все пользователи:\n\n"
            for u in users:
                msg1 += (
                    f"{u['name']} - @{u['username']} ({u['role']})\n"
                    f"❤️ Сердец: {u['hearts']}, 💸 Штраф: {u['fine']} BYN\n\n"
                )

            # 📊 Отчёт по менеджерам
            managers = db.get_all_managers_with_stats()
            msg2 = "📊 Все менеджеры:\n\n"
            for m in managers:
                conversion = (m['day_sales'] / m['day_plan'] * 100) if m['day_plan'] else 0
                msg2 += (
                    f"{m['name']} - @{m['username']}\n"
                    f"📅 План: {m['day_plan']} / {m['month_plan']} BYN\n"
                    f"💰 Продажи: {m['day_sales']} BYN\n"
                    f"📦 Заказы: {m['orders_count']} шт\n"
                    f"📈 Конверсия: {conversion:.1f}%\n\n"
                )

            await bot.send_message(ADMIN_ID, msg1 + msg2)

        except Exception as e:
            await bot.send_message(ADMIN_ID, f"⚠️ Ошибка при формировании отчёта: {e}")

    # Старт планировщика (асинхронно, чтобы не упал event loop)
    import asyncio
    async def start_scheduler():
        scheduler.start()

    asyncio.get_event_loop().create_task(start_scheduler())
