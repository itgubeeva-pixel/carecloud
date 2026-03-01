import asyncio
from datetime import datetime, time, timedelta
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

# Настройка логгера для текущего модуля
logger = logging.getLogger(__name__)


class ReminderService:
    # Сервис для управления напоминаниями пользователей.
    # Отвечает за создание, отправку и остановку периодических уведомлений.

    def __init__(self, bot: Bot, db):
        # Инициализация сервиса напоминаний.
        #
        # Args:
        #     bot: Экземпляр бота для отправки сообщений
        #     db: Объект базы данных для работы с пользователями

        self.bot = bot
        self.db = db
        # Словарь для хранения активных задач напоминаний {user_id: task}
        self.reminder_tasks = {}

    async def send_reminder(self, user_id: int, telegram_id: int, note: str = None):
        # Отправка напоминания пользователю с возможной заметкой.
        #
        # Args:
        #     user_id: Внутренний ID пользователя в системе
        #     telegram_id: Telegram ID пользователя для отправки
        #     note: Дополнительная заметка к напоминанию (опционально)

        try:
            logger.info(f"🔔 Отправка напоминания пользователю {telegram_id}")

            # Проверяем, есть ли уже запись за сегодня
            entries = await self.db.get_user_entries(user_id, days=1)
            today = datetime.now().strftime('%Y-%m-%d')
            already_recorded = any(e['date'] == today for e in entries)

            if already_recorded:
                logger.info(
                    f"📝 У пользователя {user_id} уже есть запись за сегодня, но напоминание всё равно отправлено"
                )

            # Выбор приветствия в зависимости от времени суток
            current_hour = datetime.now().hour
            if 5 <= current_hour < 12:
                greeting = "🌅 Доброе утро"
            elif 12 <= current_hour < 18:
                greeting = "☀️ Добрый день"
            elif 18 <= current_hour < 23:
                greeting = "🌆 Добрый вечер"
            else:
                greeting = "🌙 Доброй ночи"

            # Формируем текст сообщения
            message_text = f"{greeting}!"

            # Добавляем заметку, если она есть
            if note:
                message_text += f"\n\n📝 Заметка: {note}"

            message_text += "\n\nНе забудьте записать своё состояние — это займёт всего минуту!"

            # Создаем клавиатуру с действиями
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📝 Записать состояние", callback_data="quick_track")],
                    [InlineKeyboardButton(text="⚙️ Настройки напоминания", callback_data="reminder_settings")]
                ]
            )

            # Отправляем сообщение
            await self.bot.send_message(
                telegram_id,
                message_text,
                reply_markup=keyboard
            )
            logger.info(f"✅ Напоминание отправлено пользователю {user_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка при отправке напоминания: {e}")

    async def reminder_worker(
            self,
            user_id: int,
            telegram_id: int,
            reminder_hour: int,
            reminder_minute: int,
            note: str = None
    ):
        # Фоновая задача, которая работает бесконечно и отправляет напоминания
        # каждый день в заданное время.
        #
        # Args:
        #     user_id: Внутренний ID пользователя
        #     telegram_id: Telegram ID пользователя
        #     reminder_hour: Час отправки (0-23)
        #     reminder_minute: Минута отправки (0-59)
        #     note: Текст заметки к напоминанию

        try:
            while True:
                now = datetime.now()

                # Вычисляем целевое время на сегодня
                target = datetime(
                    now.year, now.month, now.day,
                    reminder_hour, reminder_minute, 0
                )

                # Если время уже прошло сегодня, переносим на завтра
                if target <= now:
                    target = target + timedelta(days=1)
                    logger.info(
                        f"📅 Время уже прошло, переносим на завтра "
                        f"{target.strftime('%d.%m %H:%M')}"
                    )

                # Рассчитываем время ожидания до следующей отправки
                wait_seconds = (target - now).total_seconds()
                wait_hours = int(wait_seconds // 3600)
                wait_minutes = int((wait_seconds % 3600) // 60)

                logger.info(f"😴 До следующего напоминания: {wait_hours}ч {wait_minutes}м")

                # Ждем до нужного времени
                await asyncio.sleep(wait_seconds)

                # Отправляем напоминание
                logger.info(f"🔔 ОТПРАВЛЯЕМ НАПОМИНАНИЕ!")
                await self.send_reminder(user_id, telegram_id, note)

                # Небольшая пауза перед следующим циклом
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            # Задача была отменена - это нормальное поведение
            logger.info(f"Задача напоминания для пользователя {user_id} отменена")
        except Exception as e:
            logger.error(f"Ошибка в задаче напоминания для пользователя {user_id}: {e}")

    async def set_reminder(
            self,
            user_id: int,
            telegram_id: int,
            reminder_time: time,
            note: str = None
    ):
        # Установка нового напоминания для пользователя.
        #
        # Args:
        #     user_id: Внутренний ID пользователя
        #     telegram_id: Telegram ID пользователя
        #     reminder_time: Время отправки напоминания
        #     note: Текст заметки
        #
        # Returns:
        #     bool: True если напоминание успешно установлено

        try:
            # Останавливаем старое напоминание, если оно существует
            if user_id in self.reminder_tasks:
                self.reminder_tasks[user_id].cancel()
                logger.info(f"Старое напоминание для пользователя {user_id} отменено")

            # Сохраняем настройки в базу данных
            await self.db.set_reminder_time(user_id, reminder_time.strftime('%H:%M'))
            if note is not None:
                await self.db.set_reminder_note(user_id, note)

            # Создаем новую фоновую задачу с бесконечным циклом
            task = asyncio.create_task(
                self.reminder_worker(
                    user_id,
                    telegram_id,
                    reminder_time.hour,
                    reminder_time.minute,
                    note
                )
            )
            self.reminder_tasks[user_id] = task

            logger.info(
                f"✅ Напоминание установлено для пользователя {user_id} "
                f"на {reminder_time} с заметкой: {note}"
            )
            return True

        except Exception as e:
            logger.error(f"Ошибка установки напоминания для пользователя {user_id}: {e}")
            return False

    async def update_reminder_note(self, user_id: int, telegram_id: int, new_note: str):
        # Обновление только заметки напоминания без изменения времени.
        #
        # Args:
        #     user_id: Внутренний ID пользователя
        #     telegram_id: Telegram ID пользователя
        #     new_note: Новый текст заметки
        #
        # Returns:
        #     bool: True если заметка успешно обновлена

        try:
            if user_id in self.reminder_tasks:
                # Останавливаем старую задачу
                self.reminder_tasks[user_id].cancel()
                logger.info(f"Старая задача для пользователя {user_id} отменена для обновления заметки")

                # Получаем текущее время напоминания из базы данных
                user = await self.db.get_user_by_telegram_id(telegram_id)
                if user and user.get('reminder_time'):
                    reminder_time = datetime.strptime(user['reminder_time'], '%H:%M').time()

                    # Создаем новую задачу с обновленной заметкой
                    task = asyncio.create_task(
                        self.reminder_worker(
                            user_id,
                            telegram_id,
                            reminder_time.hour,
                            reminder_time.minute,
                            new_note
                        )
                    )
                    self.reminder_tasks[user_id] = task

                    # Обновляем заметку в базе данных
                    await self.db.set_reminder_note(user_id, new_note)

                    logger.info(f"✅ Заметка напоминания обновлена для пользователя {user_id}")
                    return True
            return False

        except Exception as e:
            logger.error(f"Ошибка обновления заметки для пользователя {user_id}: {e}")
            return False

    async def stop_reminder(self, user_id: int):
        # Полная остановка напоминаний для пользователя и очистка настроек.
        #
        # Args:
        #     user_id: Внутренний ID пользователя
        #
        # Returns:
        #     bool: True если напоминания успешно остановлены

        try:
            # Отменяем активную задачу, если есть
            if user_id in self.reminder_tasks:
                self.reminder_tasks[user_id].cancel()
                del self.reminder_tasks[user_id]
                logger.info(f"Напоминание для пользователя {user_id} остановлено")

            # Очищаем все настройки напоминаний в базе данных
            await self.db.disable_reminders(user_id)
            await self.db.set_reminder_time(user_id, None)  # Очищаем время
            await self.db.set_reminder_note(user_id, None)  # Очищаем заметку
            return True

        except Exception as e:
            logger.error(f"Ошибка остановки напоминания для пользователя {user_id}: {e}")
            return False

    async def check_and_restore_reminders(self):
        # Восстановление всех активных напоминаний при запуске бота.
        # Используется после перезагрузки, чтобы продолжить отправку уведомлений.
        #
        # Returns:
        #     int: Количество восстановленных напоминаний

        try:
            # Получаем всех пользователей с активными напоминаниями
            users = await self.db.get_users_with_reminders()
            restored = 0

            for user in users:
                if user.get('reminder_time'):
                    try:
                        reminder_time = datetime.strptime(user['reminder_time'], '%H:%M').time()
                        note = user.get('reminder_note')

                        logger.info(
                            f"Восстановление напоминания для пользователя {user['user_id']} "
                            f"на {reminder_time}"
                        )

                        # Создаем новую задачу для каждого пользователя
                        task = asyncio.create_task(
                            self.reminder_worker(
                                user['user_id'],
                                user['telegram_id'],
                                reminder_time.hour,
                                reminder_time.minute,
                                note
                            )
                        )
                        self.reminder_tasks[user['user_id']] = task
                        restored += 1

                    except Exception as e:
                        logger.error(f"Ошибка восстановления для пользователя {user['user_id']}: {e}")

            logger.info(f"✅ Восстановлено напоминаний: {restored}")
            return restored

        except Exception as e:
            logger.error(f"Ошибка восстановления напоминаний: {e}")
            return 0