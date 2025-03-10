"""
Скрипт для создания таблиц в базе данных на основе моделей SQLAlchemy.
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Импортируем все модели
from app.db.base import Base
from app.db.models import User, UserRole, RoleAudit, Post, Channel

async def create_tables():
    """
    Создает таблицы в базе данных на основе моделей SQLAlchemy.
    """
    # Загружаем переменные окружения
    load_dotenv()
    
    # Получаем параметры подключения к БД
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASS", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "tgbot_admin")
    
    # Формируем строку подключения
    database_url = f"postgresql+asyncpg://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    try:
        # Создаем асинхронный движок SQLAlchemy
        engine = create_async_engine(database_url, echo=True)
        
        # Создаем таблицы
        async with engine.begin() as conn:
            # Удаляем существующие таблицы (опционально)
            # await conn.run_sync(Base.metadata.drop_all)
            
            # Создаем таблицы
            await conn.run_sync(Base.metadata.create_all)
            
            # Создаем таблицу alembic_version, если она не существует
            create_alembic_query = text("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL, 
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """)
            await conn.execute(create_alembic_query)
            
            # Проверяем, есть ли записи в таблице alembic_version
            try:
                # Проверяем существование записей в таблице alembic_version
                check_query = text("SELECT COUNT(*) FROM alembic_version")
                result = await conn.execute(check_query)
                row = await result.first()
                count = 0 if row is None else row[0]
                
                # Если записей нет, добавляем текущую версию
                if count == 0:
                    insert_query = text("INSERT INTO alembic_version (version_num) VALUES ('1a2b3c4d5e6f')")
                    await conn.execute(insert_query)
                    logger.info("Добавлена начальная версия миграции в таблицу alembic_version")
            except Exception as e:
                logger.error(f"Ошибка при проверке таблицы alembic_version: {e}")
        
        logger.info("Таблицы успешно созданы")
        
        # Закрываем соединение
        await engine.dispose()
        
        return True
    except SQLAlchemyError as e:
        logger.error(f"Ошибка SQLAlchemy при создании таблиц: {e}")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при создании таблиц: {e}")
        return False

async def main():
    """
    Основная функция скрипта.
    """
    success = await create_tables()
    
    if success:
        logger.info("✅ Таблицы успешно созданы")
    else:
        logger.error("❌ Ошибка при создании таблиц")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 