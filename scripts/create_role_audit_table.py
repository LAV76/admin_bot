import asyncio
import asyncpg
import os
import logging
from dotenv import load_dotenv
from datetime import datetime

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("create_role_audit_table")

async def create_role_audit_table():
    # Загружаем переменные окружения
    load_dotenv()
    
    # Получаем параметры подключения
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    
    # Формируем DSN для подключения
    dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    logger.info(f"Подключение к базе данных {db_name}...")
    conn = await asyncpg.connect(dsn)
    
    try:
        # Проверяем существование таблицы
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'role_audit'
            )
        """)
        
        if table_exists:
            logger.info("Таблица role_audit уже существует")
            return
        
        # Создаем таблицу
        logger.info("Создание таблицы role_audit...")
        await conn.execute("""
            CREATE TABLE role_audit (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                role_type VARCHAR(50) NOT NULL,
                action VARCHAR(20) NOT NULL CHECK (action IN ('add', 'remove', 'update')),
                performed_by BIGINT NOT NULL,
                performed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                notes TEXT,
                CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Создаем индексы для оптимизации запросов
        logger.info("Создание индексов для таблицы role_audit...")
        await conn.execute("""
            CREATE INDEX idx_role_audit_user_id ON role_audit(user_id);
            CREATE INDEX idx_role_audit_performed_at ON role_audit(performed_at DESC);
        """)
        
        logger.info("Таблица role_audit успешно создана")
        
    except Exception as e:
        logger.error(f"Ошибка при создании таблицы role_audit: {e}")
    finally:
        logger.info("Соединение с базой данных закрыто")
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_role_audit_table()) 