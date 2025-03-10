import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
import asyncpg

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_migrations():
    """
    Исправление проблемы с миграциями.
    Создает таблицу alembic_version и добавляет в неё информацию о текущей версии миграции.
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
    dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    try:
        # Подключаемся к базе данных
        logger.info(f"Подключение к базе данных {db_name}...")
        conn = await asyncpg.connect(dsn)
        
        # Проверяем существование таблицы alembic_version
        logger.info("Проверка существования таблицы alembic_version...")
        alembic_exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'alembic_version')"
        )
        
        if alembic_exists:
            logger.info("Таблица alembic_version уже существует")
            
            # Проверяем наличие записей в таблице
            version = await conn.fetchval("SELECT version_num FROM alembic_version")
            if version:
                logger.info(f"Текущая версия миграции: {version}")
            else:
                # Если таблица пуста, добавляем версию миграции
                logger.info("Добавление версии миграции в таблицу alembic_version...")
                await conn.execute(
                    "INSERT INTO alembic_version (version_num) VALUES ('1a2b3c4d5e6f')"
                )
                logger.info("Версия миграции успешно добавлена")
        else:
            # Создаем таблицу alembic_version
            logger.info("Создание таблицы alembic_version...")
            await conn.execute(
                """
                CREATE TABLE alembic_version (
                    version_num VARCHAR(32) NOT NULL, 
                    PRIMARY KEY (version_num)
                )
                """
            )
            
            # Добавляем версию миграции
            logger.info("Добавление версии миграции в таблицу alembic_version...")
            await conn.execute(
                "INSERT INTO alembic_version (version_num) VALUES ('1a2b3c4d5e6f')"
            )
            
            logger.info("Таблица alembic_version успешно создана и заполнена")
        
        # Проверяем существование таблиц
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        table_names = [t['tablename'] for t in tables]
        logger.info(f"Существующие таблицы: {table_names}")
        
        logger.info("Миграции успешно исправлены")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при исправлении миграций: {e}", exc_info=True)
        return False
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    success = asyncio.run(fix_migrations())
    if success:
        print("✅ Миграции успешно исправлены")
    else:
        print("❌ Ошибка при исправлении миграций")
        sys.exit(1) 