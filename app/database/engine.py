"""
Модуль для работы с подключением к базе данных.
Этот файл является заглушкой для обратной совместимости.
Фактическая реализация находится в app.db.engine.
"""

from app.db.engine import *

# Для обратной совместимости
__all__ = [
    'get_pool',
    'close_pool',
    'init_db',
    'create_async_engine',
    'get_session_maker',
    'get_session',
    'proceed_schemas',
] 