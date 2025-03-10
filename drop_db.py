import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def drop_database():
    # Загружаем переменные окружения
    load_dotenv()
    
    # Получаем параметры подключения к БД
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASS", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "tgbot_admin")
    
    # Подключаемся к системной БД postgres
    system_dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/postgres"
    
    try:
        # Подключаемся к системной БД postgres
        conn = await asyncpg.connect(system_dsn)
        
        # Удаляем базу данных, если она существует
        await conn.execute(f"DROP DATABASE IF EXISTS {db_name}")
        print(f"База данных {db_name} успешно удалена (если существовала)")
        
        # Закрываем соединение
        await conn.close()
    except Exception as e:
        print(f"Ошибка при удалении базы данных: {e}")

if __name__ == "__main__":
    asyncio.run(drop_database()) 