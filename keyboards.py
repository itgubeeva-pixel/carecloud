from aiogram.types import KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_main_keyboard():
    # Основная клавиатура бота с главным меню
    # Кнопки расположены по 2 в ряд для компактности

    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📝 Записать состояние"))
    builder.add(KeyboardButton(text="📈 Аналитика"))
    builder.add(KeyboardButton(text="🔍 Исследование"))
    builder.add(KeyboardButton(text="🏆 Достижения"))
    builder.add(KeyboardButton(text="🌐 CareCloud Сайт"))
    builder.add(KeyboardButton(text="⏰ Напоминания"))
    builder.add(KeyboardButton(text="📤 Экспорт данных"))
    builder.add(KeyboardButton(text="⚙️ Настройки"))

    # Располагаем кнопки в 4 ряда по 2 кнопки
    builder.adjust(2, 2, 2, 2)
    return builder.as_markup(resize_keyboard=True)


def get_charts_keyboard():
    # Клавиатура для выбора периода отображения графиков в аналитике
    # Позволяет пользователю выбрать глубину анализа данных

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📈 За неделю", callback_data="chart_week"))
    builder.add(InlineKeyboardButton(text="📊 За месяц", callback_data="chart_month"))
    builder.add(InlineKeyboardButton(text="📉 За год", callback_data="chart_year"))

    # Первые две кнопки в ряд, третья отдельно
    builder.adjust(2, 1)
    return builder.as_markup()


def get_reminder_keyboard():
    # Клавиатура для управления существующим напоминанием
    # Позволяет изменить время, отредактировать заметку или отключить уведомления

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⏰ Изменить время", callback_data="reminder_change_time"))
    builder.add(InlineKeyboardButton(text="📝 Добавить/Редактировать заметку", callback_data="reminder_change_note"))
    builder.add(InlineKeyboardButton(text="🔕 Отключить", callback_data="reminder_disable"))

    # Две кнопки в первом ряду, одна отдельно
    builder.adjust(2, 1)
    return builder.as_markup()


def get_reminder_setup_keyboard():
    # Клавиатура для первого шага установки нового напоминания
    # Просто кнопка подтверждения после выбора времени

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Установить", callback_data="reminder_setup"))
    builder.adjust(1)
    return builder.as_markup()


def get_rating_keyboard():
    # Клавиатура для оценки состояния по шкале от 1 до 10
    # Используется для ввода настроения, энергии, тревожности

    builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        builder.add(InlineKeyboardButton(text=str(i), callback_data=f"rating_{i}"))

    # Разбиваем на два ряда по 5 кнопок для удобства
    builder.adjust(5, 5)
    return builder.as_markup()


def get_rating_with_back_keyboard():
    # Клавиатура для оценки состояния с дополнительной кнопкой "Назад"
    # Используется в процессе создания записи для возврата к предыдущему шагу

    builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        builder.add(InlineKeyboardButton(text=str(i), callback_data=f"rating_{i}"))
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="rating_back"))

    # Два ряда по 5 кнопок и отдельно кнопка возврата
    builder.adjust(5, 5, 1)
    return builder.as_markup()


def get_sleep_keyboard():
    # Клавиатура для выбора количества сна (от 1 до 12 часов)

    builder = InlineKeyboardBuilder()
    for i in range(1, 13):
        builder.add(InlineKeyboardButton(text=f"{i} ч", callback_data=f"sleep_{i}"))

    # Три ряда по 4 кнопки для равномерного распределения
    builder.adjust(4, 4, 4)
    return builder.as_markup()


def get_sleep_with_back_keyboard():
    # Клавиатура для выбора часов сна с кнопкой "Назад"
    # Используется в процессе создания записи для возврата к предыдущему шагу

    builder = InlineKeyboardBuilder()
    for i in range(1, 13):
        builder.add(InlineKeyboardButton(text=f"{i} ч", callback_data=f"sleep_{i}"))
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="sleep_back"))

    # Три ряда по 4 кнопки и отдельно кнопка возврата
    builder.adjust(4, 4, 4, 1)
    return builder.as_markup()


def get_common_tags_keyboard():
    # Клавиатура с популярными тегами для быстрой маркировки записей
    # Позволяет выбрать несколько тегов, а затем нажать "Готово"

    builder = InlineKeyboardBuilder()
    tags = ["#работа", "#учеба", "#спорт", "#отдых", "#общение", "#семья",
            "#стресс", "#радость", "#болезнь", "#путешествие", "#кофе", "#еда"]

    for tag in tags:
        builder.add(InlineKeyboardButton(text=tag, callback_data=f"tag_{tag}"))

    # Добавляем кнопку завершения выбора тегов
    builder.add(InlineKeyboardButton(text="✅ Готово", callback_data="tags_done"))

    # 4 ряда по 3 тега и отдельно кнопка подтверждения
    builder.adjust(3, 3, 3, 3, 1)
    return builder.as_markup()


def get_tags_with_back_keyboard():
    # Клавиатура для выбора тегов с кнопкой "Назад"
    # Используется в процессе создания записи для возврата к предыдущему шагу

    builder = InlineKeyboardBuilder()
    tags = ["#работа", "#учеба", "#спорт", "#отдых", "#общение", "#семья",
            "#стресс", "#радость", "#болезнь", "#путешествие", "#кофе", "#еда"]

    for tag in tags:
        builder.add(InlineKeyboardButton(text=tag, callback_data=f"tag_{tag}"))

    # Кнопки управления
    builder.add(InlineKeyboardButton(text="✅ Готово", callback_data="tags_done"))
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="tags_back"))

    # 4 ряда по 3 тега и ряд с двумя кнопками управления
    builder.adjust(3, 3, 3, 3, 2)
    return builder.as_markup()


def get_note_with_back_keyboard():
    # Reply-клавиатура для шага ввода заметки
    # Содержит только кнопку "Назад", так как основной ввод идет с обычной клавиатуры

    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="◀️ Назад"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_export_keyboard():
    # Клавиатура для выбора формата экспорта данных
    # Позволяет пользователю скачать данные в Excel или PDF

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📊 Excel", callback_data="export_excel"))
    builder.add(InlineKeyboardButton(text="📑 PDF отчет", callback_data="export_pdf"))

    # Две кнопки в одном ряду
    builder.adjust(2)
    return builder.as_markup()


def get_settings_keyboard():
    # Клавиатура меню настроек
    # Содержит все доступные опции конфигурации бота

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⏰ Время напоминаний", callback_data="settings_reminder_time"))
    builder.add(InlineKeyboardButton(text="📝 Заметка напоминания", callback_data="settings_reminder_note"))
    builder.add(InlineKeyboardButton(text="🗑 Удалить все данные", callback_data="settings_delete"))
    builder.add(InlineKeyboardButton(text="ℹ️ О боте", callback_data="about"))

    # Каждая кнопка на отдельной строке для читаемости
    builder.adjust(1)
    return builder.as_markup()


def get_web_keyboard():
    # Клавиатура с ссылками на веб-версию и сайт CareCloud
    # Содержит URL-кнопки, открывающиеся при нажатии

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🌐 Открыть сайт", url="https://ваш-сайт.ru"))
    builder.add(InlineKeyboardButton(text="📱 Веб-версия", url="https://ваш-сайт.ru"))

    # Две кнопки вертикально
    builder.adjust(1)
    return builder.as_markup()