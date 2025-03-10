"""
Модуль для обеспечения обратной совместимости с существующим кодом.
Перенаправляет импорты из config.bot_config в app.core.config
"""

import os
from dotenv import load_dotenv
from app.core.config import settings

# Загружаем переменные окружения
load_dotenv()

# Получаем токен бота
API_TOKEN = settings.API_TOKEN
BOT_TOKEN = API_TOKEN  # Для совместимости

# Получаем ID администратора
ADMIN_ID = settings.admin_id_as_int
ADMIN_IDS = [ADMIN_ID]  # Для совместимости с множественными админами

# Получаем ID канала
CHANNEL_ID = settings.channel_id_as_int

# Настройки базы данных
DB_HOST = settings.DB_HOST
DB_USER = settings.DB_USER
DB_PASS = settings.DB_PASS
DB_NAME = settings.DB_NAME
DB_PORT = settings.DB_PORT

# Функция проверки является ли пользователь администратором
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS 