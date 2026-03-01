from enum import Enum
from typing import Dict
from dataclasses import dataclass


class AchievementType(Enum):
    # Перечисление всех типов достижений, доступных в системе.
    # Каждое достижение имеет уникальный строковый идентификатор.

    FIRST_ENTRY = "first_entry"  # Первая запись
    STREAK_3 = "streak_3"  # 3 дня подряд
    STREAK_7 = "streak_7"  # 7 дней подряд
    STREAK_30 = "streak_30"  # 30 дней подряд
    TOTAL_10 = "total_10"  # 10 записей всего
    TOTAL_50 = "total_50"  # 50 записей всего
    MOOD_MASTER = "mood_master"  # Высокое настроение
    SLEEP_KING = "sleep_king"  # Хороший сон
    ENERGY_BOOST = "energy_boost"  # Высокая энергия
    CALM_MIND = "calm_mind"  # Низкая тревожность


@dataclass
class Achievement:
    # Дата-класс, представляющий одно достижение.
    # Содержит всю информацию для отображения достижения пользователю.

    type: AchievementType  # Тип достижения из перечисления
    name: str  # Название для отображения
    description: str  # Описание условия получения
    emoji: str  # Эмодзи для визуального представления
    image_file: str  # Имя файла с изображением (в папке images)


# Словарь, сопоставляющий каждый тип достижения с его полным описанием.
# Используется для быстрого доступа к информации о достижении по его типу.
ACHIEVEMENTS: Dict[AchievementType, Achievement] = {

    AchievementType.FIRST_ENTRY: Achievement(
        type=AchievementType.FIRST_ENTRY,
        name="Первая запись",
        description="Сделайте свою первую запись состояния",
        emoji="🌟",
        image_file="first_entry.png"
    ),

    AchievementType.STREAK_3: Achievement(
        type=AchievementType.STREAK_3,
        name="На пути к балансу",
        description="Записывайте состояние 3 дня подряд",
        emoji="🔥",
        image_file="streak_3.png"
    ),

    AchievementType.STREAK_7: Achievement(
        type=AchievementType.STREAK_7,
        name="Неделя осознанности",
        description="7 дней подряд без пропусков",
        emoji="⚡",
        image_file="streak_7.png"
    ),

    AchievementType.STREAK_30: Achievement(
        type=AchievementType.STREAK_30,
        name="Месяц гармонии",
        description="30 дней подряд без пропусков",
        emoji="🌙",
        image_file="streak_30.png"
    ),

    AchievementType.TOTAL_10: Achievement(
        type=AchievementType.TOTAL_10,
        name="Исследователь",
        description="10 записей всего",
        emoji="📊",
        image_file="total_10.png"
    ),

    AchievementType.TOTAL_50: Achievement(
        type=AchievementType.TOTAL_50,
        name="Мастер самоанализа",
        description="50 записей всего",
        emoji="📈",
        image_file="total_50.png"
    ),

    AchievementType.MOOD_MASTER: Achievement(
        type=AchievementType.MOOD_MASTER,
        name="Мастер настроения",
        description="Среднее настроение выше 8 за месяц",
        emoji="😊",
        image_file="mood_master.png"
    ),

    AchievementType.SLEEP_KING: Achievement(
        type=AchievementType.SLEEP_KING,
        name="Король сна",
        description="Средняя продолжительность сна 7-9 часов",
        emoji="😴",
        image_file="sleep_king.png"
    ),

    AchievementType.ENERGY_BOOST: Achievement(
        type=AchievementType.ENERGY_BOOST,
        name="Энерджайзер",
        description="Средняя энергия выше 8 за месяц",
        emoji="⚡",
        image_file="energy_boost.png"
    ),

    AchievementType.CALM_MIND: Achievement(
        type=AchievementType.CALM_MIND,
        name="Спокойствие",
        description="Средняя тревожность ниже 4 за месяц",
        emoji="😌",
        image_file="calm_mind.png"
    ),
}