import asyncio
import asyncpg
import os
import logging
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Получение параметров подключения к базе данных
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_ID = os.getenv("ADMIN_ID")

async def create_channels_table():
    """Создание таблицы каналов в базе данных"""
    # Формирование DSN для подключения к PostgreSQL
    dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # SQL-запрос для создания таблицы каналов
    create_channels_table_sql = """
    CREATE TABLE IF NOT EXISTS channels (
        id SERIAL PRIMARY KEY,
        chat_id BIGINT NOT NULL UNIQUE,
        title VARCHAR(255) NOT NULL,
        chat_type VARCHAR(50) NOT NULL,
        username VARCHAR(100),
        is_default BOOLEAN DEFAULT FALSE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        added_by BIGINT NOT NULL,
        last_used_at TIMESTAMP WITH TIME ZONE
    );
    """
    
    # Подключение к базе данных
    conn = None
    try:
        logger.info(f"Подключение к базе данных {DB_NAME}...")
        conn = await asyncpg.connect(dsn)
        
        # Создание таблицы каналов
        logger.info("Создание таблицы channels...")
        await conn.execute(create_channels_table_sql)
        logger.info("Таблица channels успешно создана")
        
        # Проверка наличия канала по умолчанию
        if CHANNEL_ID:
            channel_id = int(CHANNEL_ID)
            admin_id = int(ADMIN_ID) if ADMIN_ID else None
            
            # Проверяем, существует ли уже канал с таким chat_id
            existing_channel = await conn.fetchrow(
                "SELECT id FROM channels WHERE chat_id = $1", channel_id
            )
            
            if not existing_channel:
                # Добавляем канал по умолчанию из .env
                logger.info(f"Добавление канала по умолчанию с ID {channel_id}...")
                await conn.execute(
                    """
                    INSERT INTO channels (chat_id, title, chat_type, is_default, added_by)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    channel_id, f"Канал {channel_id}", "channel", True, admin_id
                )
                logger.info(f"Канал по умолчанию с ID {channel_id} успешно добавлен")
            else:
                logger.info(f"Канал с ID {channel_id} уже существует в базе данных")
        
    except Exception as e:
        logger.error(f"Ошибка при создании таблицы channels: {e}")
    finally:
        # Закрытие соединения с базой данных
        if conn:
            await conn.close()
            logger.info("Соединение с базой данных закрыто")

if __name__ == "__main__":
    asyncio.run(create_channels_table()) 