from io import BytesIO
from datetime import datetime
from typing import List, Dict
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import traceback
import logging

# Настройка логгера для текущего модуля
logger = logging.getLogger(__name__)


class DataExporter:
    # Класс для экспорта данных пользователя в различные форматы.
    # Поддерживает экспорт в Excel и PDF.

    @staticmethod
    async def export_to_excel(entries: List[Dict]) -> BytesIO:
        # Экспорт записей пользователя в Excel файл.
        # Создает два листа: "Все записи" с детальными данными и "Статистика" с аналитикой.
        #
        # Args:
        #     entries: Список словарей с записями пользователя
        #
        # Returns:
        #     BytesIO: Буфер с Excel файлом для отправки пользователю

        output = BytesIO()

        try:
            # Создаем Excel файл с использованием xlsxwriter для лучшего форматирования
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Проверка на пустой список записей
                if not entries:
                    pd.DataFrame({'Сообщение': ['Нет данных']}).to_excel(writer, sheet_name='Данные', index=False)
                    output.seek(0)
                    return output

                df = pd.DataFrame(entries)

                # Дополнительная проверка на пустой DataFrame
                if df.empty:
                    pd.DataFrame({'Сообщение': ['Нет данных для экспорта']}).to_excel(
                        writer, sheet_name='Данные', index=False
                    )
                    output.seek(0)
                    return output

                # Преобразуем записи в формат для читаемого отображения
                data = []
                for entry in entries:
                    # Объединяем теги в строку через запятую, если они есть
                    tags = ', '.join(entry.get('tags', [])) if entry.get('tags') else ''
                    data.append({
                        'Дата': entry['date'],
                        'Настроение': entry['mood'],
                        'Энергия': entry['energy'],
                        'Тревожность': entry['anxiety'],
                        'Сон (часы)': entry['sleep_hours'],
                        'Теги': tags,
                        'Заметка': entry.get('note', '')
                    })

                # Создаем DataFrame для отображения и сортируем по дате (свежие сверху)
                df_display = pd.DataFrame(data)
                df_display = df_display.sort_values('Дата', ascending=False)
                df_display.to_excel(writer, sheet_name='Все записи', index=False)

                # Создание листа со статистикой
                try:
                    # Безопасно получаем минимальную и максимальную даты
                    min_date = df['date'].min() if not df.empty else 'Нет данных'
                    max_date = df['date'].max() if not df.empty else 'Нет данных'

                    # Вычисляем средние значения по всем показателям
                    avg_mood = df['mood'].mean() if not df.empty else 0
                    avg_energy = df['energy'].mean() if not df.empty else 0
                    avg_anxiety = df['anxiety'].mean() if not df.empty else 0
                    avg_sleep = df['sleep_hours'].mean() if not df.empty else 0

                    # Находим максимальное и минимальное настроение
                    max_mood = df['mood'].max() if not df.empty else 0
                    min_mood = df['mood'].min() if not df.empty else 0

                    # Определяем даты лучшего и худшего дня
                    if not df.empty and len(df) > 0:
                        best_date = df.loc[df['mood'].idxmax(), 'date'] if not df['mood'].isna().all() else 'Нет данных'
                        worst_date = df.loc[df['mood'].idxmin(), 'date'] if not df[
                            'mood'].isna().all() else 'Нет данных'
                    else:
                        best_date = 'Нет данных'
                        worst_date = 'Нет данных'

                    # Формируем таблицу статистики
                    stats = pd.DataFrame({
                        'Показатель': [
                            'Всего записей',
                            'Период',
                            'Среднее настроение',
                            'Средняя энергия',
                            'Средняя тревожность',
                            'Средний сон',
                            'Максимальное настроение',
                            'Минимальное настроение'
                        ],
                        'Значение': [
                            str(len(df)),
                            f"{min_date} - {max_date}",
                            f"{avg_mood:.1f}/10",
                            f"{avg_energy:.1f}/10",
                            f"{avg_anxiety:.1f}/10",
                            f"{avg_sleep:.1f} ч",
                            f"{max_mood}/10 ({best_date})",
                            f"{min_mood}/10 ({worst_date})"
                        ]
                    })
                    stats.to_excel(writer, sheet_name='Статистика', index=False)

                except (KeyError, ValueError, TypeError, AttributeError) as stats_error:
                    # Логируем ошибку и создаем упрощенную версию статистики
                    logger.error(f"Ошибка при создании статистики: {stats_error}")
                    stats = pd.DataFrame({
                        'Показатель': ['Всего записей', 'Ошибка'],
                        'Значение': [str(len(df)), str(stats_error)]
                    })
                    stats.to_excel(writer, sheet_name='Статистика', index=False)

            # Возвращаем указатель в начало буфера для чтения
            output.seek(0)
            logger.info(f"Excel файл успешно создан, записей: {len(entries)}")
            return output

        except (pd.errors.EmptyDataError, pd.errors.ParserError, PermissionError, OSError, ValueError) as e:
            # Обработка ошибок при создании Excel файла
            logger.error(f"Ошибка при создании Excel файла: {e}")
            logger.error(traceback.format_exc())

            # Создаем простой Excel файл с сообщением об ошибке
            error_output = BytesIO()
            try:
                # Используем openpyxl как запасной движок
                with pd.ExcelWriter(error_output, engine='openpyxl') as writer:
                    error_df = pd.DataFrame({'Ошибка': [str(e)]})
                    error_df.to_excel(writer, sheet_name='Ошибка', index=False)
                error_output.seek(0)
            except (pd.errors.EmptyDataError, PermissionError, OSError):
                # Если даже это не работает, возвращаем пустой буфер
                pass
            return error_output

    @staticmethod
    async def generate_pdf_report(entries: List[Dict], username: str) -> BytesIO:
        # Генерация подробного PDF отчета с аналитикой и рекомендациями.
        # Отчет включает статистику, графики, инсайты и персонализированные рекомендации.
        #
        # Args:
        #     entries: Список записей пользователя
        #     username: Имя пользователя для персонализации отчета
        #
        # Returns:
        #     BytesIO: Буфер с PDF файлом для отправки пользователю

        # Создаем буфер для PDF файла
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Настройка шрифтов для поддержки кириллицы
        font_path = None
        # Список возможных путей к шрифтам в разных ОС
        possible_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux
            "C:/Windows/Fonts/arial.ttf",  # Windows
            "C:/Windows/Fonts/times.ttf",  # Windows
            "/System/Library/Fonts/Arial.ttf",  # macOS
        ]

        # Ищем существующий шрифт
        for path in possible_paths:
            if os.path.exists(path):
                font_path = path
                break

        # Регистрируем найденный шрифт
        if font_path:
            pdfmetrics.registerFont(TTFont('RussianFont', font_path))
            # Пытаемся найти жирную версию шрифта
            bold_path = font_path.replace('.ttf', 'bd.ttf').replace('Sans', 'Sans-Bold')
            if os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont('RussianFont-Bold', bold_path))
            else:
                # Если нет жирной версии, используем обычный шрифт
                pdfmetrics.registerFont(TTFont('RussianFont-Bold', font_path))
        else:
            print("Warning: Russian font not found, using standard font")

        # Определяем цветовую палитру для отчета
        dark_blue = HexColor('#2C3E50')
        light_blue = HexColor('#3498DB')
        green = HexColor('#27AE60')
        red = HexColor('#E74C3C')
        purple = HexColor('#9B59B6')
        orange = HexColor('#F39C12')
        grey = HexColor('#ECF0F1')
        white = HexColor('#FFFFFF')

        # Заголовок отчета
        if font_path:
            c.setFont("RussianFont-Bold", 24)
        else:
            c.setFont("Helvetica-Bold", 24)
        c.setFillColor(dark_blue)
        c.drawString(50, height - 50, "Отчет о состоянии")

        # Информация о пользователе и дате формирования
        if font_path:
            c.setFont("RussianFont", 12)
        else:
            c.setFont("Helvetica", 12)
        c.setFillColor(black)
        c.drawString(50, height - 75, f"Пользователь: {username}")
        c.drawString(50, height - 92, f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

        # Разделительная линия
        c.setStrokeColor(HexColor('#BDC3C7'))
        c.setLineWidth(1)
        c.line(50, height - 105, width - 50, height - 105)

        # Проверка на наличие данных
        if not entries:
            # Если данных нет, показываем сообщение об ошибке
            c.setFillColor(red)
            if font_path:
                c.setFont("RussianFont", 14)
            else:
                c.setFont("Helvetica", 14)
            c.drawString(50, height - 140, "Нет данных")
        else:
            # Основная часть отчета с данными
            df = pd.DataFrame(entries)
            y = height - 140

            # ОБЩАЯ СТАТИСТИКА
            if font_path:
                c.setFont("RussianFont-Bold", 16)
            else:
                c.setFont("Helvetica-Bold", 16)
            c.setFillColor(dark_blue)
            c.drawString(50, y, "Общая статистика")
            y -= 25

            # Карточки с основной статистикой
            stats_cards = [
                ("Всего записей", str(len(df)), light_blue),
                ("Период", f"{df['date'].min()} - {df['date'].max()}", light_blue),
            ]

            stats_x = 50
            for title, value, color in stats_cards:
                # Рисуем карточку
                c.setFillColor(color)
                c.rect(stats_x, y - 40, 150, 45, fill=1, stroke=0)

                # Добавляем текст в карточку
                c.setFillColor(white)
                if font_path:
                    c.setFont("RussianFont", 9)
                else:
                    c.setFont("Helvetica", 9)
                c.drawString(stats_x + 10, y - 15, title)
                if font_path:
                    c.setFont("RussianFont-Bold", 12)
                else:
                    c.setFont("Helvetica-Bold", 12)
                c.drawString(stats_x + 10, y - 30, value)
                stats_x += 170

            y -= 70

            # СРЕДНИЕ ПОКАЗАТЕЛИ
            if font_path:
                c.setFont("RussianFont-Bold", 14)
            else:
                c.setFont("Helvetica-Bold", 14)
            c.setFillColor(dark_blue)
            c.drawString(50, y, "Средние показатели")
            y -= 20

            # Карточки со средними значениями
            avg_data = [
                ("Настроение", f"{df['mood'].mean():.1f}/10", green),
                ("Энергия", f"{df['energy'].mean():.1f}/10", orange),
                ("Тревожность", f"{df['anxiety'].mean():.1f}/10", red),
                ("Сон", f"{df['sleep_hours'].mean():.1f} ч", purple)
            ]

            avg_x = 50
            for title, value, color in avg_data:
                c.setFillColor(color)
                c.rect(avg_x, y - 35, 120, 40, fill=1, stroke=0)

                c.setFillColor(white)
                if font_path:
                    c.setFont("RussianFont", 8)
                else:
                    c.setFont("Helvetica", 8)
                c.drawString(avg_x + 10, y - 15, title)
                if font_path:
                    c.setFont("RussianFont-Bold", 11)
                else:
                    c.setFont("Helvetica-Bold", 11)
                c.drawString(avg_x + 10, y - 28, value)
                avg_x += 140

            y -= 70

            # ЛУЧШИЙ И ХУДШИЙ ДНИ
            if font_path:
                c.setFont("RussianFont-Bold", 16)
            else:
                c.setFont("Helvetica-Bold", 16)
            c.setFillColor(dark_blue)
            c.drawString(50, y, "Лучший и худший дни")
            y -= 25

            # Находим индексы лучшего и худшего дня по настроению
            best_idx = df['mood'].idxmax()
            worst_idx = df['mood'].idxmin()

            # Карточка лучшего дня
            c.setFillColor(green)
            c.rect(50, y - 105, 230, 110, fill=1, stroke=0)

            c.setFillColor(white)
            if font_path:
                c.setFont("RussianFont-Bold", 14)
            else:
                c.setFont("Helvetica-Bold", 14)
            c.drawString(60, y - 15, "Лучший день")
            if font_path:
                c.setFont("RussianFont", 10)
            else:
                c.setFont("Helvetica", 10)
            c.drawString(60, y - 35, f"Дата: {df.loc[best_idx, 'date']}")
            c.drawString(60, y - 52, f"Настроение: {df.loc[best_idx, 'mood']}/10")
            c.drawString(60, y - 69, f"Энергия: {df.loc[best_idx, 'energy']}/10")
            c.drawString(60, y - 86, f"Сон: {df.loc[best_idx, 'sleep_hours']} ч")

            # Карточка худшего дня
            c.setFillColor(red)
            c.rect(320, y - 105, 230, 110, fill=1, stroke=0)

            c.setFillColor(white)
            if font_path:
                c.setFont("RussianFont-Bold", 14)
            else:
                c.setFont("Helvetica-Bold", 14)
            c.drawString(330, y - 15, "Худший день")
            if font_path:
                c.setFont("RussianFont", 10)
            else:
                c.setFont("Helvetica", 10)
            c.drawString(330, y - 35, f"Дата: {df.loc[worst_idx, 'date']}")
            c.drawString(330, y - 52, f"Настроение: {df.loc[worst_idx, 'mood']}/10")
            c.drawString(330, y - 69, f"Энергия: {df.loc[worst_idx, 'energy']}/10")
            c.drawString(330, y - 86, f"Сон: {df.loc[worst_idx, 'sleep_hours']} ч")

            y -= 135

            # ПОСЛЕДНИЕ ЗАПИСИ
            if font_path:
                c.setFont("RussianFont-Bold", 16)
            else:
                c.setFont("Helvetica-Bold", 16)
            c.setFillColor(dark_blue)
            c.drawString(50, y, "Последние записи")
            y -= 25

            # Заголовки таблицы последних записей
            c.setFillColor(grey)
            c.rect(50, y - 20, 500, 20, fill=1, stroke=0)

            c.setFillColor(black)
            if font_path:
                c.setFont("RussianFont-Bold", 10)
            else:
                c.setFont("Helvetica-Bold", 10)
            c.drawString(60, y - 14, "Дата")
            c.drawString(130, y - 14, "Настр.")
            c.drawString(190, y - 14, "Энерг.")
            c.drawString(250, y - 14, "Трев.")
            c.drawString(310, y - 14, "Сон")
            c.drawString(370, y - 14, "Заметка")

            y -= 25

            # Заполняем таблицу данными (максимум 10 последних записей)
            if font_path:
                c.setFont("RussianFont", 9)
            else:
                c.setFont("Helvetica", 9)

            for i, entry in enumerate(entries[:10]):
                # Проверка на конец страницы
                if y < 50:
                    c.showPage()
                    y = height - 50
                    if font_path:
                        c.setFont("RussianFont", 9)
                    else:
                        c.setFont("Helvetica", 9)

                # Чередование цвета строк для лучшей читаемости
                if i % 2 == 0:
                    c.setFillColor(HexColor('#F8F9F9'))
                    c.rect(50, y - 15, 500, 15, fill=1, stroke=0)

                c.setFillColor(black)
                c.drawString(60, y - 10, entry['date'][5:])  # Только день и месяц
                c.drawString(130, y - 10, str(entry['mood']))
                c.drawString(190, y - 10, str(entry['energy']))
                c.drawString(250, y - 10, str(entry['anxiety']))
                c.drawString(310, y - 10, f"{entry['sleep_hours']}ч")

                # Обрезаем длинные заметки
                note = entry.get('note', '')
                if len(note) > 25:
                    note = note[:22] + '...'
                c.drawString(370, y - 10, note)

                y -= 18

            # ИССЛЕДОВАНИЕ СОСТОЯНИЯ
            # Проверка на необходимость новой страницы
            if y < 100:
                c.showPage()
                y = height - 50

            y -= 20

            # Заголовок раздела
            if font_path:
                c.setFont("RussianFont-Bold", 16)
            else:
                c.setFont("Helvetica-Bold", 16)
            c.setFillColor(dark_blue)
            c.drawString(50, y, "Исследование состояния")
            y -= 25

            c.setFillColor(black)
            if font_path:
                c.setFont("RussianFont", 11)
            else:
                c.setFont("Helvetica", 11)

            # Генерация инсайтов на основе анализа данных
            insights = []

            # Анализ тренда настроения
            if len(df) >= 3:
                recent_avg = df.tail(3)['mood'].mean()
                overall_avg = df['mood'].mean()
                if recent_avg > overall_avg + 0.5:
                    insights.append("• В последние дни настроение выше обычного")
                elif recent_avg < overall_avg - 0.5:
                    insights.append("• В последние дни настроение ниже обычного")

            # Анализ качества сна
            if df['sleep_hours'].mean() < 6:
                insights.append("• Вы спите меньше 6 часов (рекомендуется 7-9 часов)")
            elif df['sleep_hours'].mean() > 9:
                insights.append("• Вы спите больше 9 часов")
            else:
                insights.append("• У вас хороший сон (7-9 часов)")

            # Анализ уровня тревожности
            if df['anxiety'].mean() > 7:
                insights.append("• Повышенная тревожность (рекомендуется обратиться к специалисту)")
            elif df['anxiety'].mean() < 4:
                insights.append("• Низкая тревожность - отлично!")

            # Анализ уровня энергии
            if df['energy'].mean() < 4:
                insights.append("• Низкий уровень энергии")
            elif df['energy'].mean() > 8:
                insights.append("• Высокий уровень энергии")

            # Вывод инсайтов
            for insight in insights:
                # Проверка на конец страницы
                if y < 50:
                    c.showPage()
                    y = height - 50
                    if font_path:
                        c.setFont("RussianFont", 11)
                    else:
                        c.setFont("Helvetica", 11)

                c.drawString(60, y, insight)
                y -= 18

            # РЕКОМЕНДАЦИИ
            # Проверка на необходимость новой страницы
            if y < 100:
                c.showPage()
                y = height - 50

            y -= 20

            # Заголовок раздела
            if font_path:
                c.setFont("RussianFont-Bold", 16)
            else:
                c.setFont("Helvetica-Bold", 16)
            c.setFillColor(dark_blue)
            c.drawString(50, y, "Рекомендации")
            y -= 25

            c.setFillColor(black)
            if font_path:
                c.setFont("RussianFont", 11)
            else:
                c.setFont("Helvetica", 11)

            # Генерация персонализированных рекомендаций
            recommendations = []

            # Рекомендации по сну
            if df['sleep_hours'].mean() < 7:
                recommendations.append("• Старайтесь спать не менее 7-8 часов в сутки")

            # Рекомендации по тревожности
            if df['anxiety'].mean() > 7:
                recommendations.append(
                    "• Попробуйте медитацию или дыхательные упражнения для снижения тревожности"
                )

            # Рекомендации по настроению
            if df['mood'].mean() < 5:
                recommendations.append(
                    "• Больше времени на свежем воздухе и физическая активность помогут улучшить настроение"
                )

            # Рекомендации по энергии
            if df['energy'].mean() < 5:
                recommendations.append(
                    "• Для повышения энергии рекомендуется регулярное питание и спорт"
                )

            # Если все показатели в норме
            if not recommendations:
                recommendations.append("• Продолжайте в том же духе! У вас всё отлично.")

            # Вывод рекомендаций
            for rec in recommendations:
                # Проверка на конец страницы
                if y < 50:
                    c.showPage()
                    y = height - 50
                    if font_path:
                        c.setFont("RussianFont", 11)
                    else:
                        c.setFont("Helvetica", 11)

                c.drawString(60, y, rec)
                y -= 18

        # Завершаем создание PDF и возвращаем буфер
        c.save()
        buffer.seek(0)
        return buffer