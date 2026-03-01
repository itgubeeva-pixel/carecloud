import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

# Токен бота, полученный от @BotFather в Telegram
# Обязательная переменная, должна быть указана в .env файле
BOT_TOKEN = os.getenv('BOT_TOKEN')

# URL для подключения к PostgreSQL базе данных
# Используется по умолчанию, если не включен режим SQLite
# Формат: postgresql://username:password@host:port/database_name
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/carecloud')

# Флаг для использования SQLite вместо PostgreSQL
# Удобно для разработки и тестирования без настройки PostgreSQL
# Значение из .env преобразуется в булево: 'True' -> True, все остальное -> False
USE_SQLITE = os.getenv('USE_SQLITE', 'True').lower() == 'true'

# Путь к файлу SQLite базы данных
# Используется только когда USE_SQLITE = True
SQLITE_PATH = 'carecloud.db'