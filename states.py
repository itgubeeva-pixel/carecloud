from aiogram.fsm.state import State, StatesGroup


class EntryStates(StatesGroup):

    #Группа состояний для процесса создания новой записи состояния пользователя.
    #Каждое состояние соответствует определенному шагу заполнения дневника.

    # Шаг 1: Ввод текущего настроения
    mood = State()

    # Шаг 2: Ввод уровня энергии
    energy = State()

    # Шаг 3: Ввод уровня тревожности
    anxiety = State()

    # Шаг 4: Ввод качества сна
    sleep = State()

    # Шаг 5: Ввод тегов (пометок) для записи
    tags = State()

    # Шаг 6: Добавление текстовой заметки
    note = State()

    # Шаг 7: Подтверждение всех введенных данных перед сохранением
    confirm = State()


class SettingsStates(StatesGroup):

    # Состояние для установки времени ежедневного напоминания
    reminder_time = State()

    # Состояние для добавления заметки к напоминанию
    reminder_note = State()


class DeleteStates(StatesGroup):

    # Состояние ожидания подтверждения от пользователя
    confirm = State()