import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class Analytics:
    # Класс для аналитики и визуализации данных о состоянии пользователя.
    # Генерирует графики и предоставляет умные инсайты на основе записей.

    @staticmethod
    async def generate_chart(entries: List[Dict], period: str) -> Optional[BytesIO]:
        # Генерация графика с динамикой показателей за указанный период.
        #
        # Args:
        #     entries: Список записей пользователя
        #     period: Период ('week', 'month', 'year')
        #
        # Returns:
        #     BytesIO с изображением графика или None, если данных недостаточно

        if not entries:
            return None

        # Создаем словарь данных по датам сразу из записей
        data_by_date = {}
        for entry in entries:
            entry_date = datetime.strptime(entry['date'], '%Y-%m-%d').date()
            # Если есть несколько записей за один день, оставляем последнюю
            data_by_date[entry_date] = {
                'mood': entry['mood'],
                'energy': entry['energy'],
                'anxiety': entry['anxiety'],
                'sleep_hours': entry['sleep_hours']
            }

        # Определяем период и формируем диапазон дат
        now = datetime.now()
        if period == 'week':
            start_date = now - timedelta(days=7)
            end_date = now
            title = 'Динамика за последние 7 дней'
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        elif period == 'month':
            start_date = now - timedelta(days=30)
            end_date = now
            title = 'Динамика за последние 30 дней'
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        elif period == 'year':
            start_date = now - timedelta(days=365)
            end_date = now
            title = 'Динамика за последние 12 месяцев'
            date_range = pd.date_range(start=start_date, end=end_date, freq='MS')
        else:
            return None

        # Создаем DataFrame со всеми датами периода
        plot_df = pd.DataFrame({'date': date_range})
        plot_df['date_str'] = plot_df['date'].dt.strftime('%d.%m')

        # Для года добавляем названия месяцев
        if period == 'year':
            plot_df['date_str'] = plot_df['date'].dt.strftime('%b %Y')

        # Заполняем данные для каждой даты в периоде
        moods = []
        energies = []
        anxieties = []
        sleeps = []

        for date in plot_df['date'].dt.date:
            if date in data_by_date:
                moods.append(data_by_date[date]['mood'])
                energies.append(data_by_date[date]['energy'])
                anxieties.append(data_by_date[date]['anxiety'])
                sleeps.append(data_by_date[date]['sleep_hours'])
            else:
                moods.append(np.nan)
                energies.append(np.nan)
                anxieties.append(np.nan)
                sleeps.append(np.nan)

        plot_df['mood'] = moods
        plot_df['energy'] = energies
        plot_df['anxiety'] = anxieties
        plot_df['sleep_hours'] = sleeps

        if plot_df.empty:
            return None

        # Создаем фигуру с тремя подграфиками
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))

        x_values = range(len(plot_df))
        date_labels = plot_df['date_str'].tolist()

        # График 1: Динамика настроения
        ax1 = axes[0]
        mask = ~np.isnan(plot_df['mood'])
        x_masked = [i for i, m in zip(x_values, mask) if m]
        y_masked = [plot_df['mood'].iloc[i] for i in x_masked]

        if x_masked:
            ax1.plot(x_masked, y_masked, 'o-', color='#27AE60', linewidth=2.5, markersize=8, label='Настроение')
            ax1.fill_between(x_masked, y_masked, alpha=0.2, color='#27AE60')

        ax1.set_ylabel('Настроение (1-10)', fontsize=11)
        ax1.set_title('Динамика настроения', fontsize=12, fontweight='bold')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 11)
        ax1.set_xticks(x_values)
        ax1.set_xticklabels(date_labels, rotation=45, ha='right')

        # График 2: Энергия и тревожность
        ax2 = axes[1]

        mask_energy = ~np.isnan(plot_df['energy'])
        x_energy = [i for i, m in zip(x_values, mask_energy) if m]
        y_energy = [plot_df['energy'].iloc[i] for i in x_energy]

        mask_anxiety = ~np.isnan(plot_df['anxiety'])
        x_anxiety = [i for i, m in zip(x_values, mask_anxiety) if m]
        y_anxiety = [plot_df['anxiety'].iloc[i] for i in x_anxiety]

        if x_energy:
            ax2.plot(x_energy, y_energy, 's-', color='#F39C12', linewidth=2, markersize=8, label='Энергия')
        if x_anxiety:
            ax2.plot(x_anxiety, y_anxiety, '^-', color='#E74C3C', linewidth=2, markersize=8, label='Тревожность')

        ax2.set_ylabel('Оценка (1-10)', fontsize=11)
        ax2.set_title('Энергия и тревожность', fontsize=12, fontweight='bold')
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(0, 11)
        ax2.set_xticks(x_values)
        ax2.set_xticklabels(date_labels, rotation=45, ha='right')

        # График 3: Сон
        ax3 = axes[2]

        mask_sleep = ~np.isnan(plot_df['sleep_hours'])
        x_sleep = [i for i, m in zip(x_values, mask_sleep) if m]
        y_sleep = [plot_df['sleep_hours'].iloc[i] for i in x_sleep]

        if x_sleep:
            ax3.bar(x_sleep, y_sleep, color='#3498DB', alpha=0.7, width=0.6, label='Сон')

        ax3.axhline(y=7, color='#27AE60', linestyle='--', linewidth=1, alpha=0.7, label='Оптимум сна (7-8 ч)')
        ax3.axhline(y=8, color='#27AE60', linestyle='--', linewidth=1, alpha=0.7)
        ax3.set_ylabel('Часы сна', fontsize=11)
        ax3.set_title('Продолжительность сна', fontsize=12, fontweight='bold')
        ax3.legend(loc='upper right')
        ax3.grid(True, alpha=0.3)
        ax3.set_ylim(0, 12)
        ax3.set_xticks(x_values)
        ax3.set_xticklabels(date_labels, rotation=45, ha='right')

        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close(fig)

        return buf

    @staticmethod
    async def generate_weekly_chart(entries: List[Dict]) -> Optional[BytesIO]:
        # Генерация графика за последнюю неделю.
        # Обертка над generate_chart с периодом 'week'.

        return await Analytics.generate_chart(entries, 'week')

    @staticmethod
    async def generate_monthly_chart(entries: List[Dict]) -> Optional[BytesIO]:
        # Генерация графика за последний месяц.
        # Обертка над generate_chart с периодом 'month'.

        return await Analytics.generate_chart(entries, 'month')

    @staticmethod
    async def generate_yearly_chart(entries: List[Dict]) -> Optional[BytesIO]:
        # Генерация графика за последний год.
        # Обертка над generate_chart с периодом 'year'.

        return await Analytics.generate_chart(entries, 'year')

    @staticmethod
    async def get_smart_insights(entries: List[Dict]) -> str:
        # Глубокий анализ записей с генерацией персонализированных инсайтов и рекомендаций.
        # Учитывает количество записей и предоставляет разный уровень детализации.
        #
        # Args:
        #     entries: Список записей пользователя
        #
        # Returns:
        #     Отформатированная строка с анализом и рекомендациями

        total_entries = len(entries)

        # Если записей нет совсем
        if total_entries == 0:
            return "📊 <b>Данных пока нет</b>\n\nНачните отслеживать своё состояние через меню <b>'📝 Записать состояние'</b>. Чем больше записей, тем точнее будет исследование Вашего состояния! 🌱"

        # Если только одна запись
        if total_entries == 1:
            entry = entries[0]
            insights = []

            mood = entry['mood']
            if mood >= 8:
                insights.append(
                    "🌟 У вас отличное настроение! Постарайтесь запомнить этот день и повторить его условия.")
            elif mood >= 5:
                insights.append(
                    "😊 Настроение хорошее. Чтобы сделать его ещё лучше, добавьте любимое занятие в свой день.")
            else:
                insights.append(
                    "😔 Настроение ниже среднего. Возможно, сегодня просто тяжёлый день. Завтра всё наладится!")

            energy = entry['energy']
            if energy >= 8:
                insights.append("⚡ Вы полны энергии! Отличное время для важных дел.")
            elif energy >= 5:
                insights.append(
                    "⚡ Энергии достаточно для повседневных задач. Для подъёма сил попробуйте небольшую прогулку.")
            else:
                insights.append("⚡ Энергии мало. Возможно, стоит отдохнуть и набраться сил.")

            anxiety = entry['anxiety']
            if anxiety >= 7:
                insights.append("😰 Уровень тревоги высокий. Попробуйте глубокое дыхание: вдох на 4 счёта, выдох на 6.")
            elif anxiety >= 4:
                insights.append("😐 Тревожность средняя. Чашка травяного чая и спокойная музыка помогут расслабиться.")
            else:
                insights.append("😌 Уровень тревоги низкий. Вы отлично справляетесь со стрессом!")

            sleep = entry['sleep_hours']
            if sleep >= 8:
                insights.append("😴 Вы отлично выспались! Сон больше 8 часов помогает восстановиться.")
            elif sleep >= 6:
                insights.append("😴 Сна достаточно. Для лучшего восстановления старайтесь спать 7-8 часов.")
            else:
                insights.append("😴 Мало сна. Постарайтесь сегодня лечь пораньше.")

            return f"""
    📊 <b>Ваша статистика (всего записей: 1)</b>

    📅 Запись за {entry['date'][:10]}:
    😊 Настроение: {mood}/10
    ⚡ Энергия: {energy}/10
    😰 Тревожность: {anxiety}/10
    😴 Сон: {sleep} ч

    💡 <b>Исследование состояния на сегодня:</b>
    • {insights[0]}
    • {insights[1]}
    • {insights[2]}
    • {insights[3]}

    🌟 Продолжайте отслеживать состояние! Через несколько дней появится ещё больше полезной аналитики.
            """

        # Если 2 записи
        if total_entries == 2:
            entry1, entry2 = entries[0], entries[1]

            avg_mood = (entry1['mood'] + entry2['mood']) / 2
            avg_energy = (entry1['energy'] + entry2['energy']) / 2
            avg_anxiety = (entry1['anxiety'] + entry2['anxiety']) / 2
            avg_sleep = (entry1['sleep_hours'] + entry2['sleep_hours']) / 2

            mood_diff = entry2['mood'] - entry1['mood']
            energy_diff = entry2['energy'] - entry1['energy']

            diff_text = []
            if mood_diff > 0:
                diff_text.append(f"настроение улучшилось на {mood_diff} балла")
            elif mood_diff < 0:
                diff_text.append(f"настроение снизилось на {abs(mood_diff)} балла")

            if energy_diff > 0:
                diff_text.append(f"энергия выросла на {energy_diff} балла")
            elif energy_diff < 0:
                diff_text.append(f"энергия упала на {abs(energy_diff)} балла")

            comparison = " и ".join(diff_text) if diff_text else "показатели остались на том же уровне"

            return f"""
    📊 <b>Ваша статистика (всего записей: 2)</b>

    😊 Настроение: {avg_mood:.1f}/10
    ⚡ Энергия: {avg_energy:.1f}/10
    😰 Тревожность: {avg_anxiety:.1f}/10
    😴 Сон: {avg_sleep:.1f} часов

    📈 <b>Динамика:</b> {comparison}

    💡 <b>Первые наблюдения:</b>
    • Сравнивайте свои ощущения - это помогает лучше понимать себя
    • Обратите внимание на то, что влияет на ваше состояние
    • Чем больше записей, тем точнее будут рекомендации

    🌟 Добавьте ещё несколько записей для полноценного анализа!
            """

        # Основной анализ для 3+ записей
        df_insights = pd.DataFrame(entries)
        df_insights['date'] = pd.to_datetime(df_insights['date'])
        # Добавляем день недели для анализа
        df_insights['day_of_week'] = df_insights['date'].dt.strftime('%A')

        # Словарь для перевода дней недели на русский
        days_ru = {
            'Monday': 'Понедельник', 'Tuesday': 'Вторник', 'Wednesday': 'Среда',
            'Thursday': 'Четверг', 'Friday': 'Пятница', 'Saturday': 'Суббота',
            'Sunday': 'Воскресенье'
        }

        # Вычисляем средние показатели
        avg_mood = df_insights['mood'].mean()
        avg_energy = df_insights['energy'].mean()
        avg_anxiety = df_insights['anxiety'].mean()
        avg_sleep = df_insights['sleep_hours'].mean()

        # Находим лучший и худший дни по настроению
        best_day = df_insights.loc[df_insights['mood'].idxmax()]
        worst_day = df_insights.loc[df_insights['mood'].idxmin()]

        best_date = best_day['date'].strftime('%Y-%m-%d') if hasattr(best_day['date'], 'strftime') else str(
            best_day['date'])[:10]
        worst_date = worst_day['date'].strftime('%Y-%m-%d') if hasattr(worst_day['date'], 'strftime') else str(
            worst_day['date'])[:10]

        # Формируем базовую статистику
        result = [
            f"🔍 <b>Исследование Вашего состояния:</b>\n",
            f"📊 <b>Ваша статистика (всего записей: {total_entries})</b>\n",
            f"😊 Настроение: {avg_mood:.1f}/10",
            f"⚡ Энергия: {avg_energy:.1f}/10",
            f"😰 Тревожность: {avg_anxiety:.1f}/10",
            f"😴 Сон: {avg_sleep:.1f} часов\n",
            f"🌟 <b>Лучший день:</b> {best_date} (настроение: {best_day['mood']}/10)",
            f"😔 <b>Худший день:</b> {worst_date} (настроение: {worst_day['mood']}/10)\n"
        ]

        # Анализ по дням недели (если достаточно данных)
        if len(df_insights) >= 5:
            day_stats = df_insights.groupby('day_of_week')['mood'].mean().sort_values(ascending=False)
            best_day_name = days_ru[day_stats.index[0]]
            worst_day_name = days_ru[day_stats.index[-1]]

            result.append("📅 <b>По дням недели</b>")
            result.append(f"   • Лучший день: {best_day_name}")
            result.append(f"   • Тяжёлый день: {worst_day_name}")

            # Добавляем советы в зависимости от самого тяжелого дня
            if worst_day_name == 'Понедельник':
                result.append("   💡 <b>Совет:</b> Воскресным вечером планируйте что-то приятное на утро понедельника")
            elif worst_day_name == 'Вторник':
                result.append("   💡 <b>Совет:</b> Вторник часто бывает напряженным. Делайте короткие перерывы")
            elif worst_day_name == 'Среда':
                result.append("   💡 <b>Совет:</b> Среда — экватор недели. Устройте небольшой перерыв в середине дня")
            elif worst_day_name == 'Четверг':
                result.append("   💡 <b>Совет:</b> Четверг — предпятничный день. Постарайтесь не перегружать себя")
            elif worst_day_name == 'Пятница':
                result.append("   💡 <b>Совет:</b> Усталость накапливается к пятнице. Запланируйте что-то расслабляющее")
            elif worst_day_name == 'Суббота':
                result.append("   💡 <b>Совет:</b> Суббота — время отдыха. Не забывайте про активный отдых")
            elif worst_day_name == 'Воскресенье':
                result.append("   💡 <b>Совет:</b> Воскресная тоска? Запланируйте интересное занятие на вечер")

            result.append("")

        # Анализ сна
        result.append("😴 <b>Анализ сна</b>")

        if avg_sleep < 6:
            result.append("   • Вы спите меньше 6 часов - это мало")
            result.append("   💡 <b>Совет:</b> Старайтесь ложиться спать на 30-40 минут раньше")
            result.append("   💡 <b>Совет:</b> Уберите телефон за час до сна")
            result.append("   💡 <b>Совет:</b> Проветривайте комнату перед сном")
        elif avg_sleep < 7:
            result.append("   • Сон около 6 часов - неплохо, но можно улучшить")
            result.append("   💡 <b>Совет:</b> Добавьте ещё 30 минут сна для лучшего восстановления")
            result.append("   💡 <b>Совет:</b> Попробуйте ложиться в одно и то же время")
        elif avg_sleep <= 8:
            result.append("   • Отличная продолжительность сна!")
        elif avg_sleep <= 9:
            result.append("   • Хороший сон! 8-9 часов — отличный показатель")
        else:
            result.append("   • Вы спите больше 9 часов")
            result.append("   💡 <b>Совет:</b> Возможно, качество сна низкое")
            result.append("   💡 <b>Совет:</b> Попробуйте просыпаться без будильника")

        result.append("")

        # Анализ тревожности
        result.append("😰 <b>Анализ тревожности</b>")

        if avg_anxiety > 7:
            result.append("   • Высокий уровень тревоги")
            result.append("   💡 <b>Совет:</b> Попробуйте дыхательные упражнения: вдох на 4 счёта, выдох на 6")
            result.append("   💡 <b>Совет:</b> Медитация 5-10 минут в день помогает снизить тревожность")
            result.append("   💡 <b>Совет:</b> Прогулки на свежем воздухе творят чудеса")
        elif avg_anxiety > 5:
            result.append("   • Средний уровень тревоги")
            result.append("   💡 <b>Совет:</b> Прогулки на свежем воздухе помогают снизить тревожность")
            result.append("   💡 <b>Совет:</b> Попробуйте вести дневник благодарности")
        else:
            result.append("   • Низкий уровень тревоги - вы хорошо справляетесь со стрессом")

        result.append("")

        # Дополнительный анализ стабильности и трендов
        result.append("📊 <b>Дополнительное исследование состояния</b>")

        mood_std = df_insights['mood'].std()
        if mood_std < 1.5:
            result.append("   • Ваше настроение стабильно — вы отлично держите баланс!")
        elif mood_std < 2.5:
            result.append("   • Небольшие перепады настроения — это нормально")
        else:
            result.append("   • Заметны сильные перепады настроения")
            result.append("   💡 <b>Совет:</b> Попробуйте отслеживать, что вызывает перепады")

        # Анализ тренда за последнее время (если достаточно данных)
        if len(df_insights) >= 7:
            recent_mood = df_insights.tail(3)['mood'].mean()
            old_mood = df_insights.head(3)['mood'].mean()
            if recent_mood > old_mood + 1:
                result.append("   📈 В последнее время настроение улучшается! Так держать!")
            elif recent_mood < old_mood - 1:
                result.append("   📉 В последнее время настроение снижается")
                result.append("   💡 <b>Совет:</b> Уделите себе время и отдохните")

        result.append("")

        # Персонализированные рекомендации
        result.append("💡 <b>Рекомендации для вас</b>")

        recommendations = []

        if avg_mood < 5:
            recommendations.append("• Добавьте в день больше приятных мелочей: любимый кофе, прогулка, музыка")
        if avg_energy < 5:
            recommendations.append("• Короткие прогулки и разминка каждый час помогут поднять энергию")
        if avg_anxiety > 6:
            recommendations.append("• Перед сном откладывайте телефон и проветривайте комнату")
            recommendations.append("• Попробуйте дыхательную гимнастику: 4-7-8 (вдох 4с, задержка 7с, выдох 8с)")
        if avg_sleep < 6:
            recommendations.append("• Старайтесь ложиться спать в одно и то же время, даже в выходные")
            recommendations.append("• Создайте ритуал перед сном: тёплый душ, книга, спокойная музыка")
        if avg_sleep > 9:
            recommendations.append("• Попробуйте просыпаться без будильника и следить за самочувствием")

        # Если все показатели в норме
        if not recommendations and avg_mood >= 6 and avg_energy >= 6 and avg_anxiety <= 5 and 6 <= avg_sleep <= 9:
            recommendations.append("• У вас хорошие показатели! Продолжайте в том же духе")

        # Добавляем общие рекомендации
        recommendations.append("• Пейте достаточно воды в течение дня")

        # Выводим рекомендации (не более 5)
        if recommendations:
            for rec in recommendations[:5]:
                result.append(rec)

        return "\n".join(result)