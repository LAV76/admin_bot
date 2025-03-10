import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_database_and_tables():
    """Создание базы данных и таблиц"""
    try:
        print("Подключение к базе данных postgres...")
        # Подключаемся к базе данных postgres
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="BifNhtGkt",
            host="localhost",
            port="5432"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Проверяем существование базы данных tgbot_admin
        cursor.execute("SELECT datname FROM pg_database WHERE datname = 'tgbot_admin'")
        exists = cursor.fetchone()
        
        if exists:
            print("База данных tgbot_admin уже существует")
        else:
            print("Создаем базу данных tgbot_admin...")
            cursor.execute("CREATE DATABASE tgbot_admin")
            print("База данных tgbot_admin успешно создана")
        
        cursor.close()
        conn.close()
        
        # Подключаемся к созданной базе данных
        print("Подключение к базе данных tgbot_admin...")
        conn = psycopg2.connect(
            dbname="tgbot_admin",
            user="postgres",
            password="BifNhtGkt",
            host="localhost",
            port="5432"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Создаем таблицу users, если она не существует
        print("Создание таблицы users...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL UNIQUE,
            username VARCHAR(100),
            user_role VARCHAR(50),
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            is_bot BOOLEAN DEFAULT FALSE,
            language_code VARCHAR(10),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("Таблица users успешно создана")
        
        # Создаем таблицу user_roles, если она не существует
        print("Создание таблицы user_roles...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            role_type VARCHAR(50) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_by BIGINT NOT NULL,
            display_name VARCHAR(100),
            notes TEXT,
            CONSTRAINT user_role_unique UNIQUE (user_id, role_type)
        )
        """)
        print("Таблица user_roles успешно создана")
        
        # Создаем таблицу channels, если она не существует
        print("Создание таблицы channels...")
        cursor.execute("""
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
        )
        """)
        print("Таблица channels успешно создана")
        
        # Создаем таблицу posts, если она не существует
        print("Создание таблицы posts...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            post_name VARCHAR(255) NOT NULL,
            post_description TEXT NOT NULL,
            post_image VARCHAR(255),
            post_tag VARCHAR(100),
            username VARCHAR(100) NOT NULL,
            user_id BIGINT NOT NULL,
            created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            is_published INTEGER NOT NULL DEFAULT 0,
            published_at TIMESTAMP WITH TIME ZONE,
            target_chat_id BIGINT,
            target_chat_title VARCHAR(255),
            change_username VARCHAR(100),
            change_date TIMESTAMP WITH TIME ZONE,
            is_archived BOOLEAN DEFAULT FALSE NOT NULL,
            archived_at TIMESTAMP WITH TIME ZONE,
            archived_by BIGINT,
            message_id BIGINT
        )
        """)
        print("Таблица posts успешно создана")
        
        # Создаем таблицу role_history, если она не существует
        print("Создание таблицы role_history...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS role_history (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            role_type VARCHAR(50) NOT NULL,
            action VARCHAR(20) NOT NULL,
            admin_id BIGINT NOT NULL,
            action_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
        """)
        print("Таблица role_history успешно создана")
        
        # Создаем таблицу alembic_version, если она не существует
        print("Создание таблицы alembic_version...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR(32) NOT NULL,
            PRIMARY KEY (version_num)
        )
        """)
        
        # Проверяем, существуют ли записи в таблице alembic_version
        cursor.execute("SELECT COUNT(*) FROM alembic_version")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Добавляем последнюю версию миграции
            cursor.execute("""
            INSERT INTO alembic_version (version_num) VALUES ('20250309003')
            """)
            print("Запись о миграции добавлена в таблицу alembic_version")
        else:
            print("Таблица alembic_version уже содержит записи")
        
        print("Таблица alembic_version успешно создана")
        
        # Проверяем созданные таблицы
        print("\nПроверка созданных таблиц:")
        cursor.execute("""
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
        """)
        
        tables = cursor.fetchall()
        for table in tables:
            print(f"  - {table[0]}")
        
        cursor.close()
        conn.close()
        
        print("\nБаза данных и таблицы успешно созданы")
        return True
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

if __name__ == "__main__":
    result = create_database_and_tables()
    sys.exit(0 if result else 1) 