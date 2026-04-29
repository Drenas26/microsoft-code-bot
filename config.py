import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FIRSTMAIL_API_KEY = os.getenv("FIRSTMAIL_API_KEY")

# Настройки проверки
CHECK_ATTEMPTS = 2          # количество попыток
CHECK_INTERVAL_FIRST = 7    # первая проверка через 7 секунд
CHECK_INTERVAL_SECOND = 8   # интервал между первой и второй = 8 секунд (всего 15)