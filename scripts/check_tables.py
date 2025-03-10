import asyncio
import asyncpg
import os
import logging
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("table_checker")

# Загрузка переменных окружения
load_dotenv()

async def check_tables_structure():
    # Получаем параметры подключения из переменных окружения
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASS", "")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME", "tgbot_admin")
    
    # Формируем DSN для подключения
    dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    logger.info(f"Подключение к базе данных {database}...")
    
    # Подключаемся к базе данных
    connection = None
    try:
        connection = await asyncpg.connect(dsn)
        logger.info("Соединение установлено успешно")
        
        # Проверяем таблицу users
        logger.info("Проверяем структуру таблицы users:")
        users_columns = await connection.fetch("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        if not users_columns:
            logger.error("Таблица users не существует или не содержит колонок")
        else:
            for column in users_columns:
                column_type = f"{column['data_type']}"
                if column['character_maximum_length']:
                    column_type += f"({column['character_maximum_length']})"
                logger.info(f"  - {column['column_name']}: {column_type}")
        
        # Проверяем таблицу user_roles
        logger.info("\nПроверяем структуру таблицы user_roles:")
        user_roles_columns = await connection.fetch("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'user_roles'
            ORDER BY ordinal_position
        """)
        
        if not user_roles_columns:
            logger.error("Таблица user_roles не существует или не содержит колонок")
        else:
            for column in user_roles_columns:
                column_type = f"{column['data_type']}"
                if column['character_maximum_length']:
                    column_type += f"({column['character_maximum_length']})"
                logger.info(f"  - {column['column_name']}: {column_type}")
                
    except Exception as e:
        logger.error(f"Ошибка при работе с базой данных: {e}")
    finally:
        if connection:
            await connection.close()
            logger.info("Соединение с базой данных закрыто")

# Запускаем асинхронную функцию
if __name__ == "__main__":
    asyncio.run(check_tables_structure()) 