"""
Модуль для обеспечения обратной совместимости с существующим кодом.
Перенаправляет импорты из config.database в app.db
"""

import logging
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker, get_session
from app.db.engine import init_db, close_db
from app.core.config import settings

# Для совместимости с существующим кодом
DB_HOST = settings.DB_HOST
DB_USER = settings.DB_USER
DB_PASS = settings.DB_PASS
DB_NAME = settings.DB_NAME
DB_PORT = settings.DB_PORT

# Класс для совместимости
class DatabaseConfig:
    def __init__(self):
        self.host = DB_HOST
        self.user = DB_USER
        self.password = DB_PASS
        self.database = DB_NAME
        self.port = DB_PORT
        
    def get_dsn(self):
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        
    def get_async_dsn(self):
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}" 