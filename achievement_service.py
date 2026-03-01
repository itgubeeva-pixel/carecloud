from datetime import datetime
from typing import List, Dict
from aiogram import Bot
from aiogram.types import FSInputFile
import os
import logging

from database import Database
from achievements import ACHIEVEMENTS, AchievementType

# Настройка логгера для текущего модуля
logger = logging.getLogger(__name__)


class AchievementService:
    # Сервис для проверки и выдачи достижений пользователям.
    # Отслеживает прогресс пользователя и награждает за выполнение условий.

    def __init__(self, bot: Bot, db: Database):
        # Инициализация сервиса достижений.
        #
        # Args:
        #     bot: Экземпляр бота для отправки уведомлений
        #     db: Объект базы данных для работы с достижениями

        self.bot = bot
        self.db = db
        self.images_path = "images/"

        # Создаем папку для изображений, если её нет
        os.makedirs(self.images_path, exist_ok=True)

    async def check_and_award(self, user_id: int, telegram_id: int):
        # Проверка всех условий для выдачи новых достижений.
        # Анализирует записи пользователя и награждает за выполненные условия.
        #
        # Args:
        #     user_id: Внутренний ID пользователя в системе
        #     telegram_id: Telegram ID пользователя для отправки уведомлений

        try:
            # Получаем записи пользователя за последние 365 дней
            entries = await self.db.get_entries_with_tags(user_id, days=365)

            if not entries:
                return

            # Получаем уже полученные достижения
            unlocked = await self.db.get_user_achievements(user_id)

            # Список для новых достижений, которые нужно выдать
            new_achievements = []

            # ОСНОВНЫЕ ДОСТИЖЕНИЯ

            # 🌟 Первая запись - 1 запись
            if len(entries) >= 1 and AchievementType.FIRST_ENTRY.value not in unlocked:
                new_achievements.append(AchievementType.FIRST_ENTRY)

            # 📊 Исследователь - 10 записей всего
            if len(entries) >= 10 and AchievementType.TOTAL_10.value not in unlocked:
                new_achievements.append(AchievementType.TOTAL_10)

            # 📈 Мастер самоанализа - 50 записей всего
            if len(entries) >= 50 and AchievementType.TOTAL_50.value not in unlocked:
                new_achievements.append(AchievementType.TOTAL_50)

            # ДОСТИЖЕНИЯ ЗА СЕРИИ

            # Рассчитываем текущую серию дней
            streak = self._calculate_streak(entries)

            # 🔥 На пути к балансу - 3 дня подряд
            if streak >= 3 and AchievementType.STREAK_3.value not in unlocked:
                new_achievements.append(AchievementType.STREAK_3)

            # ⚡ Неделя осознанности - 7 дней подряд
            if streak >= 7 and AchievementType.STREAK_7.value not in unlocked:
                new_achievements.append(AchievementType.STREAK_7)

            # 🌙 Месяц гармонии - 30 дней подряд
            if streak >= 30 and AchievementType.STREAK_30.value not in unlocked:
                new_achievements.append(AchievementType.STREAK_30)

            # ДОСТИЖЕНИЯ ЗА ПОКАЗАТЕЛИ

            # Берем записи за последние 30 дней
            recent = [e for e in entries if self._is_last_30_days(e['date'])]

            # Нужно минимум 7 записей за месяц для достоверной статистики
            if recent and len(recent) >= 7:
                # Рассчитываем средние показатели
                avg_mood = sum(e['mood'] for e in recent) / len(recent)
                avg_energy = sum(e['energy'] for e in recent) / len(recent)
                avg_anxiety = sum(e['anxiety'] for e in recent) / len(recent)
                avg_sleep = sum(e['sleep_hours'] for e in recent) / len(recent)

                # 😊 Мастер настроения - среднее настроение ≥ 8
                if avg_mood >= 8 and AchievementType.MOOD_MASTER.value not in unlocked:
                    new_achievements.append(AchievementType.MOOD_MASTER)

                # 😴 Король сна - средний сон 7-9 часов
                if 7 <= avg_sleep <= 9 and AchievementType.SLEEP_KING.value not in unlocked:
                    new_achievements.append(AchievementType.SLEEP_KING)

                # ⚡ Энерджайзер - средняя энергия ≥ 8
                if avg_energy >= 8 and AchievementType.ENERGY_BOOST.value not in unlocked:
                    new_achievements.append(AchievementType.ENERGY_BOOST)

                # 😌 Спокойствие - средняя тревожность ≤ 4
                if avg_anxiety <= 4 and AchievementType.CALM_MIND.value not in unlocked:
                    new_achievements.append(AchievementType.CALM_MIND)

            # Отправляем все новые достижения пользователю
            for ach_type in new_achievements:
                await self._send_achievement(telegram_id, ach_type)
                await self.db.add_achievement(user_id, ach_type.value)
                logger.info(f"✅ Достижение '{ach_type.value}' выдано пользователю {user_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка при проверке достижений: {e}")

    @staticmethod
    def _calculate_streak(entries: List[Dict]) -> int:
        # Расчет текущей серии дней подряд.
        # Серия обрывается, если пропущен хотя бы один день.
        #
        # Args:
        #     entries: Список записей пользователя
        #
        # Returns:
        #     Количество дней подряд с записями

        if not entries:
            return 0

        try:
            # Сортируем даты записей от новых к старым
            dates = sorted([datetime.strptime(e['date'], '%Y-%m-%d').date() for e in entries], reverse=True)

            # Если последняя запись не сегодня и не вчера, серия равна 0
            today = datetime.now().date()
            if (today - dates[0]).days > 1:
                return 0

            # Считаем последовательные дни
            streak = 1
            for i in range(len(dates) - 1):
                if (dates[i] - dates[i + 1]).days == 1:
                    streak += 1
                else:
                    break

            return streak

        except Exception as e:
            logger.error(f"❌ Ошибка расчета серии: {e}")
            return 0

    @staticmethod
    def _is_last_30_days(date_str: str) -> bool:
        # Проверка, входит ли указанная дата в последние 30 дней.
        #
        # Args:
        #     date_str: Дата в формате 'YYYY-MM-DD'
        #
        # Returns:
        #     True если дата в пределах 30 дней, иначе False

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            return (datetime.now() - date).days <= 30

        except Exception as e:
            logger.error(f"❌ Ошибка проверки даты: {e}")
            return False

    async def _send_achievement(self, telegram_id: int, achievement_type: AchievementType):
        # Отправка уведомления о получении достижения с изображением.
        # Если изображение не найдено, отправляет текстовую версию.
        #
        # Args:
        #     telegram_id: Telegram ID пользователя
        #     achievement_type: Тип полученного достижения

        ach = ACHIEVEMENTS[achievement_type]

        # Формируем путь к файлу изображения
        image_path = os.path.join(self.images_path, ach.image_file)

        try:
            # Проверяем существование и размер файла
            if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
                photo = FSInputFile(image_path)
                await self.bot.send_photo(
                    chat_id=telegram_id,
                    photo=photo,
                    caption=f"🎉 <b>Достижение разблокировано!</b>\n\n"
                            f"{ach.emoji} <b>{ach.name}</b>\n"
                            f"{ach.description}\n\n"
                            f"✨ Поздравляю! Продолжайте в том же духе!",
                    parse_mode="HTML"
                )
                logger.info(f"✅ Отправлено достижение {ach.name} пользователю {telegram_id}")
            else:
                # Если файла нет, отправляем только текст
                logger.warning(f"⚠️ Файл {image_path} не найден, отправляю текстом")
                await self._send_achievement_text(telegram_id, achievement_type)

        except Exception as e:
            logger.error(f"❌ Ошибка отправки достижения с фото: {e}")
            # Отправляем текстом как запасной вариант
            await self._send_achievement_text(telegram_id, achievement_type)

    async def _send_achievement_text(self, telegram_id: int, achievement_type: AchievementType):
        # Запасной метод отправки достижения только текстом.
        # Используется, если изображение недоступно или произошла ошибка.
        #
        # Args:
        #     telegram_id: Telegram ID пользователя
        #     achievement_type: Тип полученного достижения

        ach = ACHIEVEMENTS[achievement_type]

        # Формируем текстовое сообщение
        text = f"🎉 <b>Достижение разблокировано!</b>\n\n"
        text += f"{ach.emoji} <b>{ach.name}</b>\n"
        text += f"{ach.description}\n\n"
        text += f"✨ Поздравляю! Продолжайте в том же духе!"

        await self.bot.send_message(
            chat_id=telegram_id,
            text=text,
            parse_mode="HTML"
        )
        logger.info(f"✅ Отправлено текстовое достижение {ach.name} пользователю {telegram_id}")