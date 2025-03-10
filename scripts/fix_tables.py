import asyncio
import asyncpg
import os
import logging
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("table_fixer")

# Загрузка переменных окружения
load_dotenv()

async def fix_tables_structure():
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
        
        # Начинаем транзакцию
        async with connection.transaction():
            # 1. Добавляем колонку user_role в таблицу users, если она не существует
            # Сначала проверяем, существует ли колонка
            column_exists = await connection.fetchval("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'user_role'
                )
            """)
            
            if not column_exists:
                logger.info("Добавляем колонку user_role в таблицу users...")
                await connection.execute("""
                    ALTER TABLE users
                    ADD COLUMN user_role VARCHAR(50)
                """)
                logger.info("Колонка user_role успешно добавлена")
            else:
                logger.info("Колонка user_role уже существует в таблице users")
            
            # 2. Переименовываем колонки в таблице user_roles
            # Сначала проверяем, существуют ли колонки granted_at и granted_by
            granted_at_exists = await connection.fetchval("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'user_roles' AND column_name = 'granted_at'
                )
            """)
            
            granted_by_exists = await connection.fetchval("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'user_roles' AND column_name = 'granted_by'
                )
            """)
            
            created_at_exists = await connection.fetchval("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'user_roles' AND column_name = 'created_at'
                )
            """)
            
            created_by_exists = await connection.fetchval("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'user_roles' AND column_name = 'created_by'
                )
            """)
            
            # Переименовываем колонки, если это необходимо
            if granted_at_exists and not created_at_exists:
                logger.info("Переименовываем колонку granted_at в created_at...")
                await connection.execute("""
                    ALTER TABLE user_roles
                    RENAME COLUMN granted_at TO created_at
                """)
                logger.info("Колонка granted_at успешно переименована в created_at")
            elif granted_at_exists and created_at_exists:
                logger.info("Обе колонки granted_at и created_at существуют. Переносим данные и удаляем granted_at...")
                await connection.execute("""
                    UPDATE user_roles SET created_at = granted_at WHERE created_at IS NULL;
                    ALTER TABLE user_roles DROP COLUMN granted_at;
                """)
                logger.info("Данные перенесены, колонка granted_at удалена")
            
            if granted_by_exists and not created_by_exists:
                logger.info("Переименовываем колонку granted_by в created_by...")
                await connection.execute("""
                    ALTER TABLE user_roles
                    RENAME COLUMN granted_by TO created_by
                """)
                logger.info("Колонка granted_by успешно переименована в created_by")
            elif granted_by_exists and created_by_exists:
                logger.info("Обе колонки granted_by и created_by существуют. Переносим данные и удаляем granted_by...")
                await connection.execute("""
                    UPDATE user_roles SET created_by = granted_by WHERE created_by IS NULL;
                    ALTER TABLE user_roles DROP COLUMN granted_by;
                """)
                logger.info("Данные перенесены, колонка granted_by удалена")
        
        logger.info("Проверяем обновленную структуру таблиц:")
        
        # Проверяем таблицу users
        logger.info("Структура таблицы users после изменений:")
        users_columns = await connection.fetch("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        for column in users_columns:
            column_type = f"{column['data_type']}"
            if column['character_maximum_length']:
                column_type += f"({column['character_maximum_length']})"
            logger.info(f"  - {column['column_name']}: {column_type}")
        
        # Проверяем таблицу user_roles
        logger.info("\nСтруктура таблицы user_roles после изменений:")
        user_roles_columns = await connection.fetch("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'user_roles'
            ORDER BY ordinal_position
        """)
        
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
    asyncio.run(fix_tables_structure()) 