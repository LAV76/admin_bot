import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    try:
        # Получаем данные для подключения из переменных окружения
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASS")
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT")
        database = os.getenv("DB_NAME")
        
        # Выводим информацию о подключении
        print(f"Подключаемся к базе данных: {user}@{host}:{port}/{database}")
        
        # Пробуем подключиться
        conn = await asyncpg.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database
        )
        
        # Проверяем подключение запросом
        version = await conn.fetchval("SELECT version()")
        print(f"Успешное подключение!")
        print(f"Версия PostgreSQL: {version}")
        
        # Закрываем соединение
        await conn.close()
        
    except Exception as e:
        print(f"Ошибка при подключении: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection()) 