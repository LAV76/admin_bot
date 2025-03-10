import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def create_table():
    # Загружаем переменные окружения
    load_dotenv()
    
    # Получаем параметры подключения
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    
    # Формируем строку подключения
    conn_str = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    try:
        # Подключаемся к базе данных
        print(f"Connecting to {db_host}:{db_port}/{db_name}...")
        conn = await asyncpg.connect(conn_str)
        
        # SQL для создания таблицы posts
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            post_name VARCHAR(255) NOT NULL,
            post_description TEXT NOT NULL,
            post_image VARCHAR(255),
            post_tag VARCHAR(100),
            username VARCHAR(100) NOT NULL,
            user_id BIGINT NOT NULL,
            created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            is_published INTEGER DEFAULT 0 NOT NULL,
            published_at TIMESTAMP WITH TIME ZONE,
            target_chat_id BIGINT,
            target_chat_title VARCHAR(255)
        )
        """
        
        # Выполняем SQL
        print("Creating table posts...")
        await conn.execute(create_table_sql)
        
        # Закрываем соединение
        await conn.close()
        
        print("Table posts created successfully")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(create_table()) 