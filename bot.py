import asyncio
import logging
import aiosqlite
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup

from config import BOT_TOKEN
from database import Database
from analytics import Analytics
from keyboards import *
from states import EntryStates, SettingsStates, DeleteStates
from reminders import ReminderService
from exporter import DataExporter
from achievement_service import AchievementService
from achievements import ACHIEVEMENTS, AchievementType

# НАСТРОЙКА ЛОГИРОВАНИЯ
# Отключаем подробные логи от библиотек, чтобы не засорять консоль
logging.getLogger("pydantic").setLevel(logging.ERROR)
logging.getLogger("aiogram").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)

# Настраиваем основной логгер для нашего приложения
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)

# ИНИЦИАЛИЗАЦИЯ КОМПОНЕНТОВ
bot = Bot(token=BOT_TOKEN)                          # Экземпляр бота для отправки сообщений
dp = Dispatcher(storage=MemoryStorage())            # Диспетчер с хранилищем состояний в памяти
db = Database()                                      # Работа с базой данных
analytics = Analytics()                              # Генерация графиков и аналитики
exporter = DataExporter()                            # Экспорт данных в Excel/PDF
reminder_service: ReminderService = None             # Сервис напоминаний (инициализируется позже)
achievement_service: AchievementService = None       # Сервис достижений (инициализируется позже)


@dp.message(F.text == "◀️ Назад в главное меню")
async def go_back(message: types.Message, state: FSMContext):
    # Возврат в главное меню
    await state.clear()                               # Очищаем состояние бота
    await message.answer(
        " ",                                           # Отправляем пустое сообщение с пробелом
        reply_markup=get_main_keyboard()               # Показываем главную клавиатуру
    )
    await message.delete()                             # Удаляем пробел (пользователь его не видит)


@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    # Возврат в главное меню из инлайн меню
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        " ",
        reply_markup=get_main_keyboard()
    )
    await callback.message.delete()


@dp.callback_query(F.data == "reminder_back")
async def reminder_back(callback: types.CallbackQuery):
    # Возврат в главное меню из настроек напоминаний
    await callback.message.delete()
    await callback.message.answer(
        " ",
        reply_markup=get_main_keyboard()
    )
    await callback.message.delete()


# КОМАНДА /START
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Регистрируем пользователя в базе данных при первом запуске
    await db.add_user(message.from_user.id, message.from_user.username)
    logger.info(f"Пользователь {message.from_user.id} запустил бота")

    # Приветственное сообщение с описанием возможностей
    welcome_text = """
☁️ <b>Добро пожаловать в CareCloud Bot!</b>

Я помогу вам отслеживать ваше эмоциональное состояние и находить закономерности.

<b>Что я умею:</b>
• 📝 Записывать ваше настроение, энергию и тревожность
• 😴 Отслеживать качество сна
• 🏷 Добавлять теги для контекста
• 📊 Строить графики динамики состояния
• 🔍 Исследовать состояние и давать рекомендации
• 🏆 Получать достижения за регулярность
• ⏰ Напоминать о записи состояния
• 📤 Экспортировать данные в Excel и PDF

<b>Важно:</b> Я не заменяю профессиональную психологическую помощь. Если вам тяжело, обратитесь к специалисту.

Начнём? Нажмите <b>"📝 Записать состояние"</b> или выберите команду в меню.
    """

    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")


# НАЧАЛО ЗАПИСИ СОСТОЯНИЯ
@dp.message(F.text == "📝 Записать состояние")
async def start_entry(message: types.Message, state: FSMContext):
    # Получаем пользователя из базы данных
    user = await db.get_user_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    # Проверяем, есть ли уже запись за сегодня
    has_entry = await db.has_today_entry(user['user_id'])

    if has_entry:
        # Если запись уже есть, спрашиваем о перезаписи
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да, перезаписать", callback_data="override_entry")],
                [InlineKeyboardButton(text="❌ Нет, оставить", callback_data="cancel_entry")]
            ]
        )
        await message.answer(
            "⚠️ <b>Вы уже делали запись сегодня.</b>\n"
            "Хотите перезаписать её?",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    # Если записи нет, начинаем опрос
    await state.set_state(EntryStates.mood)
    await message.answer(
        "Оцените ваше настроение сегодня от 1 до 10:\n"
        "1 — очень плохое, 10 — отличное",
        reply_markup=get_rating_with_back_keyboard()
    )


@dp.callback_query(F.data == "override_entry")
async def override_entry(callback: types.CallbackQuery, state: FSMContext):
    # Перезапись существующей записи
    await callback.message.delete()
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.answer("❌ Ошибка: пользователь не найден")
        return

    await state.set_state(EntryStates.mood)
    await callback.message.answer(
        "Оцените ваше настроение сегодня от 1 до 10:",
        reply_markup=get_rating_with_back_keyboard()
    )


@dp.callback_query(F.data == "cancel_entry")
async def cancel_entry(callback: types.CallbackQuery):
    # Отмена перезаписи
    await callback.message.delete()
    await callback.message.answer(
        "🌟 <b>Хорошо, сохраняем предыдущую запись!</b>\n"
        "Возвращайтесь завтра для новой записи.",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )


# ОБРАБОТЧИКИ ВОЗВРАТА НА ПРЕДЫДУЩИЕ ШАГИ
@dp.callback_query(F.data == "rating_back")
async def rating_back(callback: types.CallbackQuery, state: FSMContext):
    # Возврат из оценки настроения
    await callback.message.delete()
    current_state = await state.get_state()

    if current_state == EntryStates.mood:
        # Если мы на первом шаге, отменяем запись полностью
        await state.clear()
        await callback.message.answer(
            "Запись отменена. Вы можете начать заново когда захотите.",
            reply_markup=get_main_keyboard()
        )
    elif current_state == EntryStates.energy:
        # Возврат на шаг настроения
        await state.set_state(EntryStates.mood)
        await callback.message.answer(
            "Оцените ваше настроение сегодня от 1 до 10:",
            reply_markup=get_rating_with_back_keyboard()
        )
    elif current_state == EntryStates.anxiety:
        # Возврат на шаг энергии
        await state.set_state(EntryStates.energy)
        await callback.message.answer(
            "Оцените уровень вашей энергии сегодня:",
            reply_markup=get_rating_with_back_keyboard()
        )
    elif current_state == EntryStates.sleep:
        # Возврат на шаг тревожности
        await state.set_state(EntryStates.anxiety)
        await callback.message.answer(
            "Оцените уровень тревожности сегодня:",
            reply_markup=get_rating_with_back_keyboard()
        )


@dp.callback_query(F.data == "sleep_back")
async def sleep_back(callback: types.CallbackQuery, state: FSMContext):
    # Возврат из выбора часов сна
    await callback.message.delete()
    await state.set_state(EntryStates.anxiety)
    await callback.message.answer(
        "Оцените уровень тревожности сегодня:",
        reply_markup=get_rating_with_back_keyboard()
    )


@dp.callback_query(F.data == "tags_back")
async def tags_back(callback: types.CallbackQuery, state: FSMContext):
    # Возврат из выбора тегов
    await callback.message.delete()
    await state.set_state(EntryStates.sleep)
    await callback.message.answer(
        "Сколько часов вы спали?",
        reply_markup=get_sleep_with_back_keyboard()
    )


@dp.message(F.text == "◀️ Назад")
async def note_back(message: types.Message, state: FSMContext):
    # Возврат из ввода заметки
    await state.set_state(EntryStates.tags)
    await message.answer(
        "Добавьте теги, чтобы описать контекст сегодняшнего дня.",
        reply_markup=get_tags_with_back_keyboard()
    )


# ОБРАБОТЧИКИ ОЦЕНОК
@dp.callback_query(lambda c: c.data.startswith('rating_'))
async def process_rating(callback: types.CallbackQuery, state: FSMContext):
    # Обработка оценки (настроение, энергия, тревожность)
    rating = int(callback.data.split('_')[1])
    current_state = await state.get_state()
    await callback.message.delete()

    if current_state == EntryStates.mood:
        # Сохраняем настроение и переходим к энергии
        await state.update_data(mood=rating)
        await state.set_state(EntryStates.energy)
        await callback.message.answer(
            "Оцените уровень вашей энергии сегодня:",
            reply_markup=get_rating_with_back_keyboard()
        )
    elif current_state == EntryStates.energy:
        # Сохраняем энергию и переходим к тревожности
        await state.update_data(energy=rating)
        await state.set_state(EntryStates.anxiety)
        await callback.message.answer(
            "Оцените уровень тревожности сегодня:",
            reply_markup=get_rating_with_back_keyboard()
        )
    elif current_state == EntryStates.anxiety:
        # Сохраняем тревожность и переходим ко сну
        await state.update_data(anxiety=rating)
        await state.set_state(EntryStates.sleep)
        await callback.message.answer(
            "Сколько часов вы спали?",
            reply_markup=get_sleep_with_back_keyboard()
        )


@dp.callback_query(lambda c: c.data.startswith('sleep_'))
async def process_sleep(callback: types.CallbackQuery, state: FSMContext):
    # Обработка выбора часов сна
    sleep_hours = float(callback.data.split('_')[1])

    # Проверяем текущее состояние
    current_state = await state.get_state()
    if current_state != EntryStates.sleep:
        await callback.answer("❌ Ошибка состояния")
        return

    await state.update_data(sleep_hours=sleep_hours)
    await state.set_state(EntryStates.tags)
    await callback.message.delete()
    await callback.message.answer(
        "Добавьте теги, чтобы описать контекст сегодняшнего дня.\n"
        "Выбирайте из предложенных или напишите свои (например, #работа, #спорт)",
        reply_markup=get_tags_with_back_keyboard()
    )


@dp.callback_query(lambda c: c.data.startswith('tag_'))
async def process_tag(callback: types.CallbackQuery, state: FSMContext):
    # Обработка выбора тега из предложенных
    tag = callback.data.split('_')[1]
    data = await state.get_data()
    tags = data.get('tags', [])
    if tag not in tags:
        tags.append(tag)
        await state.update_data(tags=tags)
        await callback.answer(f"✅ Тег {tag} добавлен!")
    else:
        await callback.answer(f"⚠️ Тег {tag} уже есть!")


# ОБРАБОТКА ПОЛЬЗОВАТЕЛЬСКИХ ТЕГОВ
@dp.message(EntryStates.tags)
async def process_custom_tag(message: types.Message, state: FSMContext):
    # Обработка пользовательских тегов, введенных вручную
    tag = message.text.strip()

    # Проверяем, что тег начинается с #
    if not tag.startswith('#'):
        tag = '#' + tag

    data = await state.get_data()
    tags = data.get('tags', [])

    if tag not in tags:
        tags.append(tag)
        await state.update_data(tags=tags)
        await message.answer(
            f"✅ <b>Тег {tag} добавлен!</b>\n"
            f"Можете добавить еще или нажмите '✅ Готово'",
            reply_markup=get_tags_with_back_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"⚠️ <b>Тег {tag} уже есть!</b>\n"
            f"Добавьте другой тег или нажмите '✅ Готово'",
            reply_markup=get_tags_with_back_keyboard(),
            parse_mode="HTML"
        )


@dp.callback_query(F.data == "tags_done")
async def tags_done(callback: types.CallbackQuery, state: FSMContext):
    # Завершение выбора тегов и переход к заметке
    current_state = await state.get_state()
    if current_state != EntryStates.tags:
        await callback.answer("❌ Ошибка состояния")
        return

    # Получаем данные для проверки (но не используем)
    await state.get_data()

    await state.set_state(EntryStates.note)
    await callback.message.delete()
    await callback.message.answer(
        "Хотите добавить текстовую заметку? Если да, напишите её сейчас.\n"
        "Если нет, отправьте '-'",
        reply_markup=get_note_with_back_keyboard()
    )


@dp.message(EntryStates.note)
async def process_note(message: types.Message, state: FSMContext):
    # Обработка текстовой заметки
    current_state = await state.get_state()
    if current_state != EntryStates.note:
        return

    data = await state.get_data()

    # Проверяем, что все необходимые данные есть
    required_fields = ['mood', 'energy', 'anxiety', 'sleep_hours']
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        logger.error(f"Отсутствуют поля в состоянии: {missing_fields}")
        await message.answer(
            "❌ <b>Произошла ошибка.</b> Пожалуйста, начните запись заново.",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
        await state.clear()
        return

    note = message.text if message.text != '-' else ''
    await state.update_data(note=note)

    # Получаем обновленные данные
    data = await state.get_data()
    user = await db.get_user_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        await state.clear()
        return

    # ПРОВЕРКА НА НАЛИЧИЕ СЕГОДНЯШНЕЙ ЗАПИСИ
    today = datetime.now().strftime('%Y-%m-%d')
    entries = await db.get_user_entries(user['user_id'], days=1)

    today_entry = None
    for entry in entries:
        if entry['date'] == today:
            today_entry = entry
            break

    # Если есть сегодняшняя запись, удаляем её (это перезапись)
    if today_entry:
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute('DELETE FROM entry_tags WHERE entry_id = ?', (today_entry['id'],))
            await conn.execute('DELETE FROM entries WHERE id = ?', (today_entry['id'],))
            await conn.commit()
        logger.info(f"Удалена старая запись за {today} перед сохранением новой")

    # Сохраняем новую запись
    entry_data = {
        'date': today,
        'mood': data['mood'],
        'energy': data['energy'],
        'anxiety': data['anxiety'],
        'sleep_hours': data['sleep_hours'],
        'note': note
    }

    entry_id = await db.add_entry(user['user_id'], entry_data)

    if data.get('tags'):
        await db.add_tags_to_entry(entry_id, data['tags'])

    await state.clear()

    # Проверяем и выдаем ачивки
    if achievement_service:
        await achievement_service.check_and_award(user['user_id'], message.from_user.id)

    tags_text = ', '.join(data.get('tags', [])) or 'нет'
    summary = f"""
✅ <b>Запись сохранена!</b>

📊 <b>Сегодняшние показатели:</b>
• Настроение: {data['mood']}/10
• Энергия: {data['energy']}/10
• Тревожность: {data['anxiety']}/10
• Сон: {data['sleep_hours']} ч
• Теги: {tags_text}

📝 Заметка: {note if note else 'нет'}

Спасибо, что заботитесь о себе! 🌟
    """
    await message.answer(summary, reply_markup=get_main_keyboard(), parse_mode="HTML")


# ГРАФИКИ И АНАЛИТИКА
@dp.message(F.text == "📈 Аналитика")
async def charts_menu(message: types.Message):
    # Меню выбора графиков
    await message.answer(
        "Выберите период для графика:",
        reply_markup=get_charts_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith('chart_'))
async def show_chart(callback: types.CallbackQuery):
    # Показать график за выбранный период
    await callback.message.delete()

    period = callback.data.split('_')[1]

    user = await db.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.answer("❌ Ошибка: пользователь не найден")
        return

    # Выбор периода и получение данных
    if period == 'week':
        entries = await db.get_entries_with_tags(user['user_id'], days=7)
        chart = await analytics.generate_weekly_chart(entries)
        period_text = "неделю:"
        period_preposition = "за последнюю"
    elif period == 'month':
        entries = await db.get_entries_with_tags(user['user_id'], days=30)
        chart = await analytics.generate_monthly_chart(entries)
        period_text = "месяц:"
        period_preposition = "за последний"
    elif period == 'year':
        entries = await db.get_entries_with_tags(user['user_id'], days=365)
        chart = await analytics.generate_yearly_chart(entries)
        period_text = "год:"
        period_preposition = "за последний"
    else:
        await callback.message.answer("❌ Неизвестный период")
        return

    if not entries:
        await callback.message.answer(
            f"❌ За последний {period_text} нет записей",
            parse_mode="HTML"
        )
        return

    if chart:
        await callback.message.answer_photo(
            types.BufferedInputFile(chart.getvalue(), filename=f"chart_{period}.png"),
            caption=f"📊 Аналитика {period_preposition} {period_text}",
            parse_mode="HTML"
        )


# ДОСТИЖЕНИЯ
@dp.message(F.text == "🏆 Достижения")
async def achievements_menu(message: types.Message):
    # Меню достижений
    await cmd_achievements(message)


@dp.message(Command("achievements"))
async def cmd_achievements(message: types.Message):
    # Показать все полученные достижения
    user = await db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    unlocked = await db.get_user_achievements(user['user_id'])

    if not unlocked:
        await message.answer(
            "📭 <b>У вас пока нет достижений</b>\n\n"
            "Делайте записи, чтобы получать награды!\n"
            "Чем больше записей, тем больше достижений вы откроете.\n\n"
            "🌟 Все достижения можно посмотреть на нашем сайте — кнопка <b>\"🌐 CareCloud Сайт\"</b> в главном меню!",
            parse_mode="HTML"
        )
        return

    # Группируем достижения по категориям для удобного отображения
    text = "🏆 <b>Ваши достижения:</b>\n\n"

    # ОСНОВНЫЕ ДОСТИЖЕНИЯ
    text += "<b>📝 Основные:</b>\n"
    for ach_type in unlocked:
        ach = ACHIEVEMENTS[AchievementType(ach_type)]
        if ach.type in [AchievementType.FIRST_ENTRY, AchievementType.TOTAL_10, AchievementType.TOTAL_50]:
            text += f"  {ach.emoji} {ach.name} - {ach.description}\n"

    # СЕРИИ
    text += "\n<b>🔥 Серии:</b>\n"
    for ach_type in unlocked:
        ach = ACHIEVEMENTS[AchievementType(ach_type)]
        if ach.type in [AchievementType.STREAK_3, AchievementType.STREAK_7, AchievementType.STREAK_30]:
            text += f"  {ach.emoji} {ach.name} - {ach.description}\n"

    # ПОКАЗАТЕЛИ
    text += "\n<b>📊 Показатели:</b>\n"
    for ach_type in unlocked:
        ach = ACHIEVEMENTS[AchievementType(ach_type)]
        if ach.type in [AchievementType.MOOD_MASTER, AchievementType.SLEEP_KING,
                        AchievementType.ENERGY_BOOST, AchievementType.CALM_MIND]:
            text += f"  {ach.emoji} {ach.name} - {ach.description}\n"

    text += f"\n<b>✨ Всего достижений: {len(unlocked)}</b>"
    text += "\n\n🌟 <b>Все твои победы в одном месте</b>"
    text += "\nЗаходи на сайт <b>CareCloud</b> — там каждая награда сияет ярче!"
    text += "\n\n🔮 <b>А ещё там можно увидеть:</b>"
    text += "\n• Какие награды ты ещё не получил"
    text += "\n• Что нужно сделать для каждой награды"
    text += "\n• Как продвигаешься к новым достижениям"
    text += "\n\n🌐 Кнопка <b>\"CareCloud Сайт\"</b> в главном меню ждёт тебя ✨"

    await message.answer(text, parse_mode="HTML")


# ИССЛЕДОВАНИЕ СОСТОЯНИЯ
@dp.message(F.text == "🔍 Исследование")
async def show_insights(message: types.Message):
    # Показать исследование состояния с рекомендациями
    user = await db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    entries = await db.get_entries_with_tags(user['user_id'], days=30)
    insights = await analytics.get_smart_insights(entries)

    await message.answer(insights, parse_mode="HTML")


# УПРАВЛЕНИЕ НАПОМИНАНИЯМИ
@dp.message(F.text == "⏰ Напоминания")
async def reminders_menu(message: types.Message):
    # Меню управления напоминаниями
    user = await db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    reminder = await db.get_user_reminder(user['user_id'])

    if reminder and reminder.get('reminder_time'):
        # Если напоминание уже установлено, показываем текущие настройки
        time_str = reminder['reminder_time']
        note = reminder.get('reminder_note')

        if note:
            note_text = f"\n📝 Заметка: {note}"
            note_button_text = "📝 Редактировать заметку"
        else:
            note_text = "\n📝 Заметка: не добавлена"
            note_button_text = "📝 Добавить заметку"

        inline_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⏰ Изменить время", callback_data="reminder_change_time")],
                [InlineKeyboardButton(text=note_button_text, callback_data="reminder_change_note")],
                [InlineKeyboardButton(text="🔕 Отключить", callback_data="reminder_disable")]
            ]
        )

        await message.answer(
            f"⏰ <b>Текущее напоминание:</b> {time_str}{note_text}\n\n"
            f"<b>Что хотите изменить?</b>",
            reply_markup=inline_keyboard,
            parse_mode="HTML"
        )
    else:
        # Если напоминания нет, предлагаем установить
        await message.answer(
            "У вас нет активных напоминаний.\n"
            "Хотите установить?",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Установить", callback_data="reminder_setup")]
                ]
            )
        )


@dp.callback_query(F.data == "reminder_setup")
async def reminder_setup(callback: types.CallbackQuery, state: FSMContext):
    # Начало установки напоминания
    await callback.message.delete()
    await state.set_state(SettingsStates.reminder_time)
    await callback.message.answer(
        "В какое время вы хотите получать напоминания?\n"
        "Отправьте время в формате ЧЧ:ММ (например, 09:00)"
    )


@dp.callback_query(F.data == "reminder_change_time")
async def reminder_change_time(callback: types.CallbackQuery, state: FSMContext):
    # Изменение времени напоминания
    await callback.message.delete()
    await state.set_state(SettingsStates.reminder_time)
    await callback.message.answer(
        "Введите новое время для напоминаний в формате ЧЧ:ММ (например, 09:00)"
    )


@dp.callback_query(F.data == "reminder_change_note")
async def reminder_change_note(callback: types.CallbackQuery, state: FSMContext):
    # Изменение заметки к напоминанию
    await callback.message.delete()
    await state.set_state(SettingsStates.reminder_note)

    user = await db.get_user_by_telegram_id(callback.from_user.id)
    if user:
        reminder = await db.get_user_reminder(user['user_id'])
        current_note = reminder.get('reminder_note') if reminder else None

        if current_note:
            await callback.message.answer(
                f"📝 <b>Текущая заметка:</b> {current_note}\n\n"
                f"Введите новый текст заметки для напоминания.\n"
                f"Отправьте '-' чтобы удалить заметку.",
                parse_mode="HTML"
            )
        else:
            await callback.message.answer(
                f"Введите текст заметки для напоминания.\n"
                f"Эта заметка будет приходить вместе с напоминанием.\n"
                f"Отправьте '-' чтобы пропустить."
            )


@dp.callback_query(F.data == "reminder_disable")
async def reminder_disable(callback: types.CallbackQuery):
    # Отключение напоминаний
    await callback.message.delete()
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    if user and reminder_service:
        await reminder_service.stop_reminder(user['user_id'])
        await callback.message.answer(
            "✅ Напоминания отключены",
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            "❌ Ошибка при отключении напоминаний"
        )


@dp.message(SettingsStates.reminder_time)
async def process_reminder_time(message: types.Message, state: FSMContext):
    # Обработка введенного времени напоминания
    global reminder_service
    user = await db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Пользователь не найден. Напишите /start")
        await state.clear()
        return

    if message.text == '0':
        # Отключение напоминаний
        if reminder_service:
            await reminder_service.stop_reminder(user['user_id'])
        await state.clear()
        await message.answer("✅ Напоминания отключены", parse_mode="HTML")
        logger.info(f"Reminders disabled for user {user['user_id']}")
        return

    try:
        # Парсим время из строки
        parsed_time = datetime.strptime(message.text, '%H:%M').time()

        # Получаем текущую заметку
        reminder = await db.get_user_reminder(user['user_id'])
        current_note = reminder.get('reminder_note') if reminder else None

        # Устанавливаем напоминание
        success = await reminder_service.set_reminder(
            user['user_id'],
            message.from_user.id,
            parsed_time,
            current_note
        )

        if success:
            # Предлагаем добавить заметку
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📝 Добавить/Редактировать заметку", callback_data="reminder_change_note")],
                    [InlineKeyboardButton(text="✅ Завершить", callback_data="reminder_back")]
                ]
            )

            await message.answer(
                f"✅ <b>Время напоминания установлено на {message.text}!</b>\n\n"
                f"Теперь вы можете настроить заметку для напоминания.",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            logger.info(f"Reminders set for user {user['user_id']} at {message.text}")
        else:
            await message.answer("❌ Ошибка при настройке напоминаний")

        await state.clear()

    except ValueError:
        await message.answer("❌ Неправильный формат. Используйте ЧЧ:ММ (например, 09:00)")


@dp.message(SettingsStates.reminder_note)
async def process_reminder_note(message: types.Message, state: FSMContext):
    # Обработка введенной заметки для напоминания
    user = await db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Пользователь не найден")
        await state.clear()
        return

    note = None if message.text == '-' else message.text

    if reminder_service:
        # Обновляем заметку
        success = await reminder_service.update_reminder_note(
            user['user_id'],
            message.from_user.id,
            note
        )

        if success:
            if note:
                await message.answer(
                    f"✅ Заметка для напоминания сохранена:\n\n{note}",
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    "✅ Заметка удалена",
                    parse_mode="HTML"
                )
            await return_to_reminders_menu(message, user['user_id'])
        else:
            await message.answer(
                "❌ Ошибка при сохранении заметки"
            )
    else:
        await message.answer(
            "❌ Сервис напоминаний недоступен"
        )

    await state.clear()


async def return_to_reminders_menu(message: types.Message, user_id: int):
    # Вспомогательная функция для возврата в меню напоминаний
    reminder = await db.get_user_reminder(user_id)

    if reminder and reminder.get('reminder_time'):
        time_str = reminder['reminder_time']
        note = reminder.get('reminder_note')

        if note:
            note_text = f"\n📝 Заметка: {note}"
            note_button_text = "📝 Изменить заметку"
        else:
            note_text = "\n📝 Заметка: не добавлена"
            note_button_text = "📝 Добавить заметку"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⏰ Изменить время", callback_data="reminder_change_time")],
                [InlineKeyboardButton(text=note_button_text, callback_data="reminder_change_note")],
                [InlineKeyboardButton(text="🔕 Отключить", callback_data="reminder_disable")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="reminder_back")]
            ]
        )

        await message.answer(
            f"⏰ <b>Текущее напоминание:</b> {time_str}{note_text}\n\n"
            f"<b>Что хотите изменить?</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )


# ЭКСПОРТ ДАННЫХ
@dp.message(F.text == "📤 Экспорт данных")
async def export_data(message: types.Message):
    # Меню выбора формата экспорта
    await message.answer(
        "<b>Выберите формат экспорта:</b>",
        reply_markup=get_export_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query(lambda c: c.data.startswith('export_'))
async def process_export(callback: types.CallbackQuery):
    # Обработка экспорта данных
    await callback.message.delete()
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.answer("❌ Ошибка: пользователь не найден")
        return

    entries = await db.get_entries_with_tags(user['user_id'], days=90)
    if not entries:
        await callback.message.answer("Нет данных для экспорта")
        return

    format_type = callback.data.split('_')[1]
    try:
        if format_type == "excel":
            # Экспорт в Excel
            data = await exporter.export_to_excel(entries)
            filename = f"carecloud_export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            caption = "📊 Ваш Excel файл готов!"
        else:
            # Экспорт в PDF
            username = callback.from_user.full_name or "User"
            data = await exporter.generate_pdf_report(entries, username)
            filename = f"carecloud_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            caption = "📑 Ваш PDF отчет готов!"

        await callback.message.answer_document(
            types.BufferedInputFile(data.getvalue(), filename=filename),
            caption=caption,
            parse_mode="HTML"
        )
        logger.info(f"Экспорт {format_type} для пользователя {user['user_id']}")
    except Exception as e:
        logger.error(f"Export error: {e}")
        await callback.message.answer(f"❌ Ошибка при экспорте данных: {str(e)}")


@dp.callback_query(F.data == "quick_track")
async def quick_track(callback: types.CallbackQuery, state: FSMContext):
    # Быстрый старт записи (из уведомления)
    await callback.message.delete()
    await start_entry(callback.message, state)


# НАСТРОЙКИ
@dp.message(F.text == "⚙️ Настройки")
async def settings(message: types.Message):
    # Меню настроек
    await message.answer(
        "⚙️ <b>Настройки</b>\n\nЧто вы хотите сделать?",
        reply_markup=get_settings_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "settings_reminder_time")
async def settings_reminder_time(callback: types.CallbackQuery, state: FSMContext):
    # Настройка времени напоминания из меню настроек
    await callback.message.delete()
    await state.set_state(SettingsStates.reminder_time)
    await callback.message.answer(
        "В какое время вы хотите получать напоминания?\n"
        "Отправьте время в формате ЧЧ:ММ (например, 09:00)\n"
        "Или отправьте '0' чтобы отключить напоминания."
    )


@dp.callback_query(F.data == "settings_reminder_note")
async def settings_reminder_note(callback: types.CallbackQuery, state: FSMContext):
    # Настройка заметки напоминания из меню настроек
    await callback.message.delete()
    await state.set_state(SettingsStates.reminder_note)
    await callback.message.answer(
        "Введите текст заметки для напоминания.\n"
        "Отправьте '-' чтобы удалить заметку."
    )


@dp.callback_query(F.data == "settings_delete")
async def settings_delete(callback: types.CallbackQuery, state: FSMContext):
    # Удаление данных из меню настроек
    await callback.message.delete()
    await cmd_delete_data(callback.message, state)


@dp.callback_query(F.data == "about")
async def about(callback: types.CallbackQuery):
    # Информация о боте
    about_text = """
🤖 <b>CareCloud Bot v1.0</b>

<b>Бот для отслеживания ментального состояния</b>

📅 Дата релиза: Январь 2026
👨‍💻 Разработчик: @itgubeeva

<b>✨ Возможности:</b>
• 📝 Ежедневный трекинг настроения, энергии, тревожности
• 😴 Отслеживание качества сна
• 🏷 Добавление тегов для контекста
• 📊 Красивые графики и статистика
• 🔍 Исследование состояния и рекомендации
• 🏆 Достижения за регулярность
• ⏰ Ежедневные напоминания
• 📤 Экспорт в Excel и PDF

<b>🛠 Используемые технологии:</b>
• Python + aiogram
• SQLite
• Pandas + Matplotlib
• ReportLab

💡 Идеи и предложения: @itgubeeva
    """
    await callback.message.answer(about_text, parse_mode="HTML")
    await callback.message.delete()


@dp.message(Command("delete_my_data"))
async def cmd_delete_data(message: types.Message, state: FSMContext):
    # Команда для полного удаления данных
    user = await db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    await state.update_data(telegram_id=message.from_user.id)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚠️ ДА, УДАЛИТЬ ВСЁ", callback_data="delete_confirm")],
            [InlineKeyboardButton(text="❌ Нет, отмена", callback_data="delete_cancel")]
        ]
    )
    await message.answer(
        "⚠️ <b>ВНИМАНИЕ!</b> ⚠️\n\n"
        "Вы собираетесь удалить <b>ВСЕ свои данные</b>:\n"
        "• Всю историю записей\n"
        "• Все теги и заметки\n"
        "• Настройки напоминаний\n"
        "• Все полученные достижения\n\n"
        "<b>Данное действие необратимо!</b>\n\n"
        "Вы уверены?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(DeleteStates.confirm)


@dp.callback_query(DeleteStates.confirm, F.data == "delete_confirm")
async def delete_confirm(callback: types.CallbackQuery, state: FSMContext):
    # Подтверждение удаления данных
    telegram_id = callback.from_user.id
    await state.clear()

    logger.info(f"Удаление данных для пользователя {telegram_id}")
    await callback.message.edit_text("🔄 Удаляю ваши данные...")

    # Останавливаем напоминания
    if reminder_service:
        user = await db.get_user_by_telegram_id(telegram_id)
        if user:
            await reminder_service.stop_reminder(user['user_id'])
            logger.info(f"Reminders stopped for user {user['user_id']}")

    success = await db.delete_user_data(telegram_id)

    if success:
        # Создаем новую чистую запись пользователя
        await db.add_user(telegram_id, callback.from_user.username)
        await callback.message.edit_text(
            "✅ <b>Все ваши данные успешно удалены!</b>\n\n"
            "Я создал для вас новую чистую запись.\n"
            "Можете начать всё сначала с команды /start",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
        logger.info(f"Данные пользователя {telegram_id} удалены")
    else:
        await callback.message.edit_text(
            "✅ <b>Операция завершена!</b>\n\nВаши данные были очищены.",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )


@dp.callback_query(DeleteStates.confirm, F.data == "delete_cancel")
async def delete_cancel(callback: types.CallbackQuery, state: FSMContext):
    # Отмена удаления данных
    await callback.message.edit_text(
        "✅ Удаление отменено. Ваши данные в сохранности!",
        reply_markup=get_main_keyboard()
    )
    await state.clear()


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    # Справка по командам
    help_text = """
🆘 <b>Помощь</b>

<b>Основные команды:</b>
• /start - Начать работу
• /help - Эта справка
• /achievements - Мои достижения
• /delete_my_data - Удалить все данные

<b>Кнопки меню:</b>
• 📝 Записать состояние - ежедневный трекинг
• 📈 Аналитика - графики за неделю, месяц, год
• 🔍 Исследование - анализ состояния и рекомендации
• 🏆 Достижения - полученные награды
• 🌐 CareCloud Сайт - наш сайт с полезными материалами
• ⏰ Напоминания - настроить уведомления
• 📤 Экспорт данных - выгрузка в Excel или PDF
• ⚙️ Настройки - настройки бота

<b>Важные ресурсы:</b>
• 📞 Горячая линия психологической помощи: 8-800-555-35-35
• 💬 Онлайн-чат поддержки: https://pomosch.ru

Помните: забота о ментальном здоровье — это важно! 💙
    """
    await message.answer(help_text, parse_mode="HTML")


@dp.message(F.text == "🌐 CareCloud Сайт")
async def web_menu(message: types.Message):
    # Меню с ссылкой на сайт
    site_url = f"https://itgubeeva-pixel.github.io/carecloud/?user_id={message.from_user.id}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Открыть сайт", url=site_url)],
        ]
    )

    await message.answer(
        "🌐 <b>CareCloud Сайт</b>\n\n"
        "На сайте вы найдете:\n"
        "• 📊 Вашу статистику в реальном времени\n"
        "• 📚 Полезные статьи по саморазвитию\n"
        "• 🎥 Видео с практиками и медитациями\n"
        "• 😊 Советы для улучшения настроения\n\n"
        "Переходите по ссылке и изучайте материалы!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ОБРАБОТКА НЕИЗВЕСТНЫХ СООБЩЕНИЙ
@dp.message()
async def handle_unknown_message(message: types.Message, state: FSMContext):
    # Обработка любых сообщений, не попавших в другие хендлеры
    current_state = await state.get_state()

    if current_state is not None:
        return

    # Список допустимых команд из меню
    menu_commands = [
        "📝 Записать состояние",
        "📈 Аналитика",
        "🔍 Исследование",
        "🏆 Достижения",
        "🌐 CareCloud Сайт",
        "⏰ Напоминания",
        "📤 Экспорт данных",
        "⚙️ Настройки",
        "◀️ Назад в главное меню"
    ]

    if message.text in menu_commands:
        return

    # Системные команды
    system_commands = ['/start', '/help', '/delete_my_data', '/achievements']

    if message.text and message.text.startswith('/'):
        if message.text in system_commands:
            return
        else:
            await message.answer(
                "❌ Неизвестная команда. Используйте /help для списка доступных команд."
            )
            return

    # Проверка на числа (оценки и часы сна)
    if message.text and message.text.replace('.', '').replace(' ', '').isdigit():
        num = float(message.text)
        if 1 <= num <= 10:  # Оценки от 1 до 10
            return
        if 1 <= num <= 12:  # Часы сна от 1 до 12
            return

    # Проверка на теги
    if message.text and message.text.startswith('#'):
        allowed_tags = [
            "#работа", "#учеба", "#спорт", "#отдых", "#общение", "#семья",
            "#стресс", "#радость", "#болезнь", "#путешествие", "#кофе", "#еда"
        ]
        if message.text in allowed_tags:
            return

    # Проверка на формат времени
    if message.text and ':' in message.text:
        try:
            datetime.strptime(message.text, '%H:%M')
            return
        except ValueError:
            pass

    # Проверка на callback-команды
    callback_commands = [
        "rating_", "sleep_", "tag_", "tags_done",
        "override_entry", "cancel_entry",
        "export_excel", "export_pdf", "quick_track",
        "reminder_setup", "reminder_change_time", "reminder_change_note",
        "reminder_disable", "reminder_back",
        "settings_reminder_time", "settings_reminder_note",
        "settings_delete", "about",
        "delete_confirm", "delete_cancel",
        "chart_", "back_to_main"
    ]

    if message.text and any(message.text.startswith(cmd) for cmd in callback_commands):
        return

    # Если ничего не подошло, отправляем подсказку
    await message.answer(
        "Пожалуйста, используйте кнопки на клавиатуре для навигации и выбора команд.\n"
        "Если клавиатура не отображается, нажмите на кнопку с квадратиком в поле ввода.",
        reply_markup=get_main_keyboard()
    )

    # ВРЕМЕННАЯ ДИАГНОСТИКА
    @dp.message()
    async def debug_all_messages(msg: types.Message):
        # Временный обработчик для отладки - логирует все сообщения
        print(f"📨 Получено сообщение: '{msg.text}' от {msg.from_user.id}")


async def main():
    # Главная функция запуска бота
    global reminder_service, achievement_service

    # Инициализация базы данных
    await db.init_db()
    logger.info("База данных инициализирована")

    # Инициализация сервисов
    reminder_service = ReminderService(bot, db)
    logger.info("Сервис напоминаний инициализирован")

    achievement_service = AchievementService(bot, db)
    logger.info("Сервис достижений инициализирован")

    # Восстановление напоминаний после перезапуска
    restored = await reminder_service.check_and_restore_reminders()
    logger.info(f"Восстановлено напоминаний: {restored}")

    # Запуск бота
    logger.info("Запуск бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())