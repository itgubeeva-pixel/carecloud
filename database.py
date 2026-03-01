import aiosqlite
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

# Настройка логгера для текущего модуля
logger = logging.getLogger(__name__)


class Database:
    # Класс для работы с базой данных SQLite.
    # Отвечает за все операции с данными пользователей, их записями,
    # тегами, достижениями и настройками напоминаний.

    def __init__(self, db_path: str = "carecloud.db"):
        # Инициализация подключения к базе данных
        #
        # Args:
        #     db_path: Путь к файлу базы данных (по умолчанию carecloud.db)

        self.db_path = db_path

    async def init_db(self):
        # Инициализация структуры базы данных.
        # Создает все необходимые таблицы при первом запуске.

        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Создание таблицы пользователей
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER UNIQUE,
                        username TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        reminder_time TEXT,
                        reminder_note TEXT,
                        timezone INTEGER DEFAULT 3,
                        notification_enabled BOOLEAN DEFAULT 0
                    )
                ''')

                # Проверяем наличие колонки reminder_note (для совместимости со старыми базами)
                cursor = await db.execute("PRAGMA table_info(users)")
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]

                # Если колонки reminder_note нет, добавляем её
                if 'reminder_note' not in column_names:
                    try:
                        await db.execute('ALTER TABLE users ADD COLUMN reminder_note TEXT')
                        logger.info("Добавлена колонка reminder_note в таблицу users")
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении колонки reminder_note: {e}")

                # Создание таблицы записей о состоянии
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        date TEXT,
                        mood INTEGER,
                        energy INTEGER,
                        anxiety INTEGER,
                        sleep_hours REAL,
                        note TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')

                # Создание таблицы тегов
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE
                    )
                ''')

                # Создание таблицы связей между записями и тегами (многие ко многим)
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS entry_tags (
                        entry_id INTEGER,
                        tag_id INTEGER,
                        FOREIGN KEY (entry_id) REFERENCES entries (id),
                        FOREIGN KEY (tag_id) REFERENCES tags (id)
                    )
                ''')

                # Создание таблицы достижений пользователей
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS user_achievements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        achievement_type TEXT,
                        earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, achievement_type),
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')

                await db.commit()
                logger.info("База данных инициализирована")

        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")

    async def add_user(self, telegram_id: int, username: str = None):
        # Добавление нового пользователя в базу данных.
        # Если пользователь уже существует, операция игнорируется.
        #
        # Args:
        #     telegram_id: ID пользователя в Telegram
        #     username: Имя пользователя (опционально)

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)',
                    (telegram_id, username)
                )
                await db.commit()
                logger.info(f"Пользователь {telegram_id} добавлен")

        except Exception as e:
            logger.error(f"Ошибка добавления пользователя {telegram_id}: {e}")

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        # Получение информации о пользователе по его Telegram ID.
        #
        # Args:
        #     telegram_id: ID пользователя в Telegram
        #
        # Returns:
        #     Словарь с данными пользователя или None, если пользователь не найден

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    'SELECT * FROM users WHERE telegram_id = ?',
                    (telegram_id,)
                )
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"Ошибка получения пользователя {telegram_id}: {e}")
            return None

    async def has_today_entry(self, user_id: int) -> bool:
        # Проверка, есть ли у пользователя запись за текущий день.
        #
        # Args:
        #     user_id: Внутренний ID пользователя в системе
        #
        # Returns:
        #     True если запись за сегодня существует, иначе False

        try:
            async with aiosqlite.connect(self.db_path) as db:
                today = datetime.now().strftime('%Y-%m-%d')
                cursor = await db.execute(
                    'SELECT COUNT(*) FROM entries WHERE user_id = ? AND date = ?',
                    (user_id, today)
                )
                count = await cursor.fetchone()
                return count[0] > 0

        except Exception as e:
            logger.error(f"Ошибка проверки записи за сегодня: {e}")
            return False

    async def add_entry(self, user_id: int, data: Dict[str, Any]) -> int:
        # Добавление новой записи о состоянии пользователя.
        #
        # Args:
        #     user_id: Внутренний ID пользователя
        #     data: Словарь с данными записи (дата, настроение, энергия и т.д.)
        #
        # Returns:
        #     ID созданной записи или 0 в случае ошибки

        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    '''INSERT INTO entries 
                       (user_id, date, mood, energy, anxiety, sleep_hours, note)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (user_id, data['date'], data['mood'], data['energy'],
                     data['anxiety'], data['sleep_hours'], data.get('note', ''))
                )
                await db.commit()
                return cursor.lastrowid

        except Exception as e:
            logger.error(f"Ошибка добавления записи: {e}")
            return 0

    async def add_tags_to_entry(self, entry_id: int, tags: List[str]) -> None:
        # Привязка тегов к существующей записи.
        #
        # Args:
        #     entry_id: ID записи
        #     tags: Список тегов для привязки

        try:
            async with aiosqlite.connect(self.db_path) as db:
                for tag_name in tags:
                    # Добавляем тег в таблицу тегов, если его еще нет
                    await db.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag_name,))

                    # Получаем ID тега
                    cursor = await db.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
                    tag_row = await cursor.fetchone()

                    # Создаем связь между записью и тегом
                    if tag_row:
                        await db.execute(
                            'INSERT INTO entry_tags (entry_id, tag_id) VALUES (?, ?)',
                            (entry_id, tag_row[0])
                        )

                await db.commit()

        except Exception as e:
            logger.error(f"Ошибка добавления тегов: {e}")

    async def get_user_entries(self, user_id: int, days: int = 7) -> List[Dict[str, Any]]:
        # Получение последних записей пользователя (только последняя запись за каждый день).
        #
        # Args:
        #     user_id: Внутренний ID пользователя
        #     days: Количество дней для выборки (по умолчанию 7)
        #
        # Returns:
        #     Список словарей с записями пользователя

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    '''SELECT * FROM entries 
                       WHERE user_id = ? 
                       GROUP BY date
                       HAVING id = MAX(id)
                       ORDER BY date DESC LIMIT ?''',
                    (user_id, days)
                )
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Ошибка получения записей: {e}")
            return []

    async def get_entries_with_tags(self, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        # Получение записей пользователя с привязанными тегами.
        # Возвращает только последнюю запись за каждый день.
        #
        # Args:
        #     user_id: Внутренний ID пользователя
        #     days: Количество дней для выборки (по умолчанию 30)
        #
        # Returns:
        #     Список словарей с записями, где теги представлены в виде списка

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row

                # Получаем все записи с объединенными тегами
                cursor = await db.execute(
                    '''SELECT e.*, GROUP_CONCAT(t.name) as tags
                       FROM entries e
                       LEFT JOIN entry_tags et ON e.id = et.entry_id
                       LEFT JOIN tags t ON et.tag_id = t.id
                       WHERE e.user_id = ?
                       GROUP BY e.id
                       ORDER BY e.date DESC''',
                    (user_id,)
                )
                rows = await cursor.fetchall()

                if not rows:
                    return []

                # Группируем по датам, оставляя только последнюю запись за день
                unique_by_date = {}
                for row in rows:
                    row_dict = dict(row)
                    date = row_dict['date']

                    # Если даты еще нет в словаре, добавляем запись
                    if date not in unique_by_date:
                        # Преобразуем строку тегов в список
                        tags_value = row_dict.get('tags')
                        row_dict['tags'] = str(tags_value).split(',') if tags_value else []
                        unique_by_date[date] = row_dict

                # Преобразуем в список и сортируем по дате
                result = list(unique_by_date.values())
                result.sort(key=lambda x: x['date'], reverse=True)

                # Возвращаем только последние 'days' дней
                return result[:days]

        except Exception as e:
            logger.error(f"Ошибка получения записей с тегами: {e}")
            return []

    async def delete_user_data(self, telegram_id: int) -> bool:
        # Полное удаление всех данных пользователя по Telegram ID.
        # Удаляет пользователя, его записи, теги и достижения.
        #
        # Args:
        #     telegram_id: ID пользователя в Telegram
        #
        # Returns:
        #     True если удаление успешно, иначе False

        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Начинаем транзакцию для целостности данных
                await db.execute('BEGIN TRANSACTION')

                # Получаем внутренний ID пользователя
                cursor = await db.execute('SELECT user_id FROM users WHERE telegram_id = ?', (telegram_id,))
                row = await cursor.fetchone()

                if not row:
                    return False

                user_id = row[0]

                # Удаляем связи тегов с записями пользователя
                await db.execute(
                    'DELETE FROM entry_tags WHERE entry_id IN (SELECT id FROM entries WHERE user_id = ?)',
                    (user_id,)
                )

                # Удаляем записи пользователя
                await db.execute('DELETE FROM entries WHERE user_id = ?', (user_id,))

                # Удаляем достижения пользователя
                await db.execute('DELETE FROM user_achievements WHERE user_id = ?', (user_id,))

                # Удаляем самого пользователя
                await db.execute('DELETE FROM users WHERE user_id = ?', (user_id,))

                await db.commit()
                logger.info(f"Данные пользователя {telegram_id} удалены")
                return True

        except Exception as e:
            logger.error(f"Ошибка удаления данных: {e}")
            return False

    async def set_reminder_time(self, user_id: int, reminder_time: str) -> None:
        # Установка времени ежедневного напоминания для пользователя.
        # Автоматически включает уведомления.
        #
        # Args:
        #     user_id: Внутренний ID пользователя
        #     reminder_time: Время в формате ЧЧ:ММ

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE users SET reminder_time = ?, notification_enabled = 1 WHERE user_id = ?',
                    (reminder_time, user_id)
                )
                await db.commit()
                logger.info(f"Время напоминания установлено для пользователя {user_id}: {reminder_time}")

        except Exception as e:
            logger.error(f"Ошибка установки времени напоминания: {e}")

    async def set_reminder_note(self, user_id: int, note: str) -> None:
        # Установка текстовой заметки для напоминания.
        #
        # Args:
        #     user_id: Внутренний ID пользователя
        #     note: Текст заметки

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE users SET reminder_note = ? WHERE user_id = ?',
                    (note, user_id)
                )
                await db.commit()
                logger.info(f"Заметка напоминания установлена для пользователя {user_id}: {note}")

        except Exception as e:
            logger.error(f"Ошибка установки заметки напоминания: {e}")

    async def disable_reminders(self, user_id: int) -> None:
        # Отключение всех напоминаний для пользователя.
        #
        # Args:
        #     user_id: Внутренний ID пользователя

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE users SET notification_enabled = 0 WHERE user_id = ?',
                    (user_id,)
                )
                await db.commit()
                logger.info(f"Напоминания отключены для пользователя {user_id}")

        except Exception as e:
            logger.error(f"Ошибка отключения напоминаний: {e}")

    async def get_users_with_reminders(self) -> List[Dict[str, Any]]:
        # Получение списка всех пользователей с активными напоминаниями.
        # Используется при запуске бота для восстановления задач.
        #
        # Returns:
        #     Список словарей с данными пользователей

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    'SELECT user_id, telegram_id, reminder_time, reminder_note FROM users WHERE notification_enabled = 1 AND reminder_time IS NOT NULL'
                )
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Ошибка получения пользователей с напоминаниями: {e}")
            return []

    async def get_user_reminder(self, user_id: int) -> Optional[Dict[str, Any]]:
        # Получение настроек напоминания для конкретного пользователя.
        #
        # Args:
        #     user_id: Внутренний ID пользователя
        #
        # Returns:
        #     Словарь с временем и заметкой напоминания или None

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    'SELECT reminder_time, reminder_note FROM users WHERE user_id = ?',
                    (user_id,)
                )
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"Ошибка получения настроек напоминания: {e}")
            return None

    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С ДОСТИЖЕНИЯМИ ==========

    async def add_achievement(self, user_id: int, achievement_type: str) -> bool:
        # Добавление нового достижения пользователю.
        # Если достижение уже есть, операция игнорируется.
        #
        # Args:
        #     user_id: Внутренний ID пользователя
        #     achievement_type: Тип достижения
        #
        # Returns:
        #     True если добавление успешно, иначе False

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT OR IGNORE INTO user_achievements (user_id, achievement_type) VALUES (?, ?)',
                    (user_id, achievement_type)
                )
                await db.commit()
                return True

        except Exception as e:
            logger.error(f"Ошибка добавления ачивки: {e}")
            return False

    async def get_user_achievements(self, user_id: int) -> List[str]:
        # Получение списка всех достижений пользователя.
        #
        # Args:
        #     user_id: Внутренний ID пользователя
        #
        # Returns:
        #     Список типов достижений, отсортированный по дате получения

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    'SELECT achievement_type FROM user_achievements WHERE user_id = ? ORDER BY earned_at DESC',
                    (user_id,)
                )
                rows = await cursor.fetchall()
                return [row['achievement_type'] for row in rows]

        except Exception as e:
            logger.error(f"Ошибка получения ачивок: {e}")
            return []

    async def check_achievement_unlocked(self, user_id: int, achievement_type: str) -> bool:
        # Проверка, получено ли уже конкретное достижение пользователем.
        #
        # Args:
        #     user_id: Внутренний ID пользователя
        #     achievement_type: Тип достижения для проверки
        #
        # Returns:
        #     True если достижение уже получено, иначе False

        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'SELECT COUNT(*) FROM user_achievements WHERE user_id = ? AND achievement_type = ?',
                    (user_id, achievement_type)
                )
                count = await cursor.fetchone()
                return count[0] > 0

        except Exception as e:
            logger.error(f"Ошибка проверки ачивки: {e}")
            return False