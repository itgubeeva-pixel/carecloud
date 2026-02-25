from flask import Flask, jsonify
from flask_cors import CORS
import sqlite3
import logging
from datetime import datetime
import json
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Разрешаем запросы с любого домена

# Путь к базе данных (относительно этого файла)
DB_PATH = os.path.join(os.path.dirname(__file__), 'carecloud.db')


def dict_factory(cursor, row):
    """Преобразует строку SQLite в словарь"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_db():
    """Получить соединение с БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    return conn


def calculate_streak(entries):
    """Рассчитать текущую серию дней"""
    if not entries:
        return 0

    # Сортируем по дате
    dates = sorted([datetime.strptime(e['date'], '%Y-%m-%d').date() for e in entries], reverse=True)

    # Если последняя запись не сегодня и не вчера, серия 0
    today = datetime.now().date()
    if (today - dates[0]).days > 1:
        return 0

    streak = 1
    for i in range(len(dates) - 1):
        if (dates[i] - dates[i + 1]).days == 1:
            streak += 1
        else:
            break

    return streak


def get_smart_insights(entries):
    """Получить инсайты на основе записей"""
    if len(entries) < 3:
        return "📊 Недостаточно данных для анализа. Добавьте ещё несколько записей!"

    # Средние показатели
    avg_mood = sum(e['mood'] for e in entries) / len(entries)
    avg_energy = sum(e['energy'] for e in entries) / len(entries)
    avg_anxiety = sum(e['anxiety'] for e in entries) / len(entries)
    avg_sleep = sum(e['sleep_hours'] for e in entries) / len(entries)

    # Лучший и худший день
    best_day = max(entries, key=lambda x: x['mood'])
    worst_day = min(entries, key=lambda x: x['mood'])

    insights = []

    # Анализ настроения
    if avg_mood >= 8:
        insights.append("🌟 У вас отличное настроение! Так держать!")
    elif avg_mood >= 6:
        insights.append("😊 У вас хорошее настроение. Есть потенциал стать ещё лучше!")
    elif avg_mood >= 4:
        insights.append("😐 Настроение среднее. Давайте подумаем, что может его улучшить?")
    else:
        insights.append("😔 Настроение низкое. Возможно, стоит обратиться к специалисту.")

    # Анализ энергии
    if avg_energy < 5:
        insights.append("⚡️ Низкая энергия. Попробуйте добавить физическую активность.")
    elif avg_energy < 7:
        insights.append("⚡️ Энергии достаточно, но можно и больше.")

    # Анализ тревожности
    if avg_anxiety > 7:
        insights.append("😰 Высокий уровень тревоги. Попробуйте дыхательные упражнения.")
    elif avg_anxiety > 5:
        insights.append("😟 Тревожность выше среднего.")

    # Анализ сна
    if avg_sleep < 6:
        insights.append("😴 Мало сна. Старайтесь спать не меньше 7-8 часов.")
    elif avg_sleep > 9:
        insights.append("💤 Много сна. Возможно, качество сна низкое.")

    result = f"""📊 **Ваша статистика**

😊 Настроение: {avg_mood:.1f}/10
⚡ Энергия: {avg_energy:.1f}/10
😰 Тревожность: {avg_anxiety:.1f}/10
😴 Сон: {avg_sleep:.1f} часов

🌟 Лучший день: {best_day['date']} (настроение: {best_day['mood']}/10)
😔 Худший день: {worst_day['date']} (настроение: {worst_day['mood']}/10)

💡 **Инсайты:**
"""
    for insight in insights:
        result += f"• {insight}\n"

    return result


@app.route('/api/stats/<int:telegram_id>', methods=['GET'])
def get_stats(telegram_id):
    """Получить статистику пользователя"""
    try:
        conn = get_db()

        # Получаем пользователя
        user = conn.execute(
            'SELECT * FROM users WHERE telegram_id = ?',
            (telegram_id,)
        ).fetchone()

        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404

        # Получаем записи пользователя
        entries = conn.execute('''
            SELECT e.*, GROUP_CONCAT(t.name) as tags
            FROM entries e
            LEFT JOIN entry_tags et ON e.id = et.entry_id
            LEFT JOIN tags t ON et.tag_id = t.id
            WHERE e.user_id = ?
            GROUP BY e.id
            ORDER BY e.date DESC
            LIMIT 90
        ''', (user['user_id'],)).fetchall()

        # Обрабатываем теги
        for entry in entries:
            if entry['tags']:
                entry['tags'] = entry['tags'].split(',')
            else:
                entry['tags'] = []

        if not entries:
            return jsonify({
                'totalEntries': 0,
                'avgMood': 0,
                'avgEnergy': 0,
                'avgAnxiety': 0,
                'avgSleep': 0,
                'streak': 0,
                'entries': []
            })

        # Рассчитываем статистику
        total = len(entries)
        avg_mood = sum(e['mood'] for e in entries) / total
        avg_energy = sum(e['energy'] for e in entries) / total
        avg_anxiety = sum(e['anxiety'] for e in entries) / total
        avg_sleep = sum(e['sleep_hours'] for e in entries) / total

        # Рассчитываем серию
        streak = calculate_streak(entries)

        # Получаем инсайты
        insights = get_smart_insights(entries)

        conn.close()

        return jsonify({
            'totalEntries': total,
            'avgMood': round(avg_mood, 1),
            'avgEnergy': round(avg_energy, 1),
            'avgAnxiety': round(avg_anxiety, 1),
            'avgSleep': round(avg_sleep, 1),
            'streak': streak,
            'insights': insights,
            'entries': entries[:10]  # Последние 10 записей
        })

    except Exception as e:
        logger.error(f"Ошибка API: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/insights/<int:telegram_id>', methods=['GET'])
def get_insights(telegram_id):
    """Получить инсайты для пользователя"""
    try:
        conn = get_db()

        user = conn.execute(
            'SELECT * FROM users WHERE telegram_id = ?',
            (telegram_id,)
        ).fetchone()

        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404

        entries = conn.execute('''
            SELECT * FROM entries 
            WHERE user_id = ? 
            ORDER BY date DESC 
            LIMIT 90
        ''', (user['user_id'],)).fetchall()

        conn.close()

        insights = get_smart_insights(entries)

        return jsonify({'insights': insights})

    except Exception as e:
        logger.error(f"Ошибка получения инсайтов: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/articles', methods=['GET'])
def get_articles():
    """Получить все статьи"""
    try:
        articles_path = os.path.join(os.path.dirname(__file__), 'web', 'articles', 'data.json')
        with open(articles_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data.get('articles', []))
    except Exception as e:
        logger.error(f"Ошибка загрузки статей: {e}")
        return jsonify([])


@app.route('/api/videos', methods=['GET'])
def get_videos():
    """Получить все видео"""
    try:
        videos_path = os.path.join(os.path.dirname(__file__), 'web', 'articles', 'data.json')
        with open(videos_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data.get('videos', []))
    except Exception as e:
        logger.error(f"Ошибка загрузки видео: {e}")
        return jsonify([])


@app.route('/health', methods=['GET'])
def health_check():
    """Проверка работоспособности"""
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()})


if __name__ == '__main__':
    logger.info(f"Запуск API на порту 5000")
    logger.info(f"Путь к БД: {DB_PATH}")
    app.run(host='0.0.0.0', port=5000, debug=True)