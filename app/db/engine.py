"""
Модуль для управления движком базы данных.
"""

import asyncio
import logging
import os
import asyncpg
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logging import setup_logger

# Импортируем необходимые объекты из session для обратной совместимости
from app.db.session import async_session_maker, get_session

# Настройка логирования
logger = setup_logger("db.engine")

# Создаем алиас get_db_session для обратной совместимости
get_db_session = get_session

# Глобальная переменная для хранения движка
engine: Optional[AsyncEngine] = None

# Экспортируем для обратной совместимости
__all__ = ["init_db", "close_db", "get_engine", "check_db_connection", 
           "async_session_maker", "get_session", "get_db_session"]

async def create_database() -> bool:
    """
    Создает базу данных, если она не существует
    
    Returns:
        bool: True, если база данных существует или была успешно создана
    """
    try:
        # Получаем параметры подключения к БД
        db_user = os.getenv("DB_USER", "postgres")
        db_pass = os.getenv("DB_PASS", "")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "tgbot_admin")
        
        # Подключаемся к системной БД postgres
        system_dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/postgres"
        
        # Проверяем существование базы данных
        conn = await asyncpg.connect(system_dsn)
        try:
            # Проверяем существование нашей БД
            result = await conn.fetchrow(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                db_name
            )
            
            if result is None:
                logger.info(f"База данных {db_name} не существует, создаем...")
                # Создаем базу данных
                await conn.execute(f"CREATE DATABASE {db_name}")
                logger.info(f"База данных {db_name} успешно создана")
            else:
                logger.info(f"База данных {db_name} уже существует")
                
            return True
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Ошибка при создании базы данных: {e}")
        return False

async def init_db() -> bool:
    """
    Инициализирует подключение к базе данных
    
    Returns:
        bool: True, если инициализация прошла успешно
    """
    global engine
    
    try:
        # Проверка наличия настроек БД
        if not hasattr(settings, "DATABASE_URL") or not settings.DATABASE_URL:
            logger.error("Не указан URL подключения к базе данных в настройках (DATABASE_URL)")
            return False
        
        # Создаем базу данных, если она не существует
        db_created = await create_database()
        if not db_created:
            logger.error("Не удалось создать базу данных")
            return False
            
        # Создаем асинхронный движок SQLAlchemy
        connection_args = {}
        
        if hasattr(settings, "db_connect_timeout") and settings.db_connect_timeout:
            connection_args["connect_timeout"] = settings.db_connect_timeout
            
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.db_echo if hasattr(settings, "db_echo") else False,
            pool_size=settings.db_pool_size if hasattr(settings, "db_pool_size") else 5,
            max_overflow=settings.db_max_overflow if hasattr(settings, "db_max_overflow") else 10,
            pool_timeout=settings.db_pool_timeout if hasattr(settings, "db_pool_timeout") else 30,
            pool_recycle=settings.db_pool_recycle if hasattr(settings, "db_pool_recycle") else 1800,
            pool_pre_ping=True,
            connect_args=connection_args
        )
        
        # Проверяем соединение
        async with engine.begin() as conn:
            await conn.run_sync(lambda _: None)
            
        logger.info("Подключение к базе данных успешно инициализировано")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при инициализации подключения к базе данных: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при инициализации подключения к базе данных: {e}", exc_info=True)
        return False

async def close_db() -> bool:
    """
    Закрывает соединение с базой данных
    
    Returns:
        bool: True, если закрытие прошло успешно
    """
    global engine
    
    if engine is not None:
        try:
            await engine.dispose()
            engine = None
            logger.info("Соединение с базой данных успешно закрыто")
            return True
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединения с базой данных: {e}", exc_info=True)
            return False
    else:
        logger.warning("Попытка закрыть несуществующее соединение с базой данных")
        return False

def get_engine() -> Optional[AsyncEngine]:
    """
    Возвращает текущий движок базы данных
    
    Returns:
        Optional[AsyncEngine]: Текущий движок или None, если он не инициализирован
    """
    global engine
    return engine

async def check_db_connection() -> Dict[str, Any]:
    """
    Проверяет соединение с базой данных
    
    Returns:
        Dict[str, Any]: Результат проверки в формате:
        {
            "success": bool,  # Успешность проверки
            "ping": float,    # Время отклика в миллисекундах
            "error": str,     # Текст ошибки (если success=False)
        }
    """
    global engine
    
    if engine is None:
        return {
            "success": False,
            "error": "Движок базы данных не инициализирован"
        }
    
    try:
        # Замеряем время отклика
        start_time = asyncio.get_event_loop().time()
        
        async with engine.begin() as conn:
            # Выполняем простой запрос для проверки соединения
            await conn.execute(engine.text("SELECT 1"))
        
        end_time = asyncio.get_event_loop().time()
        ping_ms = (end_time - start_time) * 1000  # Переводим в миллисекунды
        
        logger.debug(f"Успешная проверка соединения с базой данных (ping: {ping_ms:.2f} мс)")
        
        return {
            "success": True,
            "ping": round(ping_ms, 2),
        }
    
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при проверке соединения с базой данных: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Ошибка SQL: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Неожиданная ошибка при проверке соединения с базой данных: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Неожиданная ошибка: {str(e)}"
        } 