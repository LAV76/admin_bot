import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def check_channels_table():
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
    
    # Подключаемся к базе данных
    conn = await asyncpg.connect(dsn)
    
    try:
        # Получаем информацию о колонках таблицы channels
        result = await conn.fetch(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'channels'"
        )
        
        print("\nКолонки таблицы channels:")
        for row in result:
            print(f"{row['column_name']} - {row['data_type']}")
            
    finally:
        # Закрываем соединение
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_channels_table()) 