import asyncio
import asyncpg
import os
import sys
from dotenv import load_dotenv

async def check_database():
    print("Начинаем проверку базы данных...")
    
    # Загружаем переменные окружения
    load_dotenv()
    print("Переменные окружения загружены")
    
    # Получаем параметры подключения к БД
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASS", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "tgbot_admin")
    
    print(f"Параметры подключения: user={db_user}, host={db_host}, port={db_port}, db={db_name}")
    
    # Формируем строку подключения
    dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    print(f"Строка подключения: {dsn}")
    
    try:
        print("Попытка подключения к базе данных...")
        # Подключаемся к базе данных
        conn = await asyncpg.connect(dsn)
        print(f"✅ Подключение к базе данных {db_name} успешно установлено")
        
        # Получаем список таблиц
        print("Получение списка таблиц...")
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        
        print("\nСписок таблиц в базе данных:")
        if tables:
            for table in tables:
                print(f"- {table['tablename']}")
        else:
            print("Таблицы не найдены")
        
        # Проверяем наличие таблицы alembic_version
        print("Проверка наличия таблицы alembic_version...")
        alembic_version = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'alembic_version')"
        )
        
        if alembic_version:
            print("\n✅ Таблица alembic_version существует")
            
            # Получаем версию миграции
            version = await conn.fetchval(
                "SELECT version_num FROM alembic_version"
            )
            print(f"Текущая версия миграции: {version}")
        else:
            print("\n❌ Таблица alembic_version не существует")
        
        # Проверяем структуру таблицы posts
        print("Проверка структуры таблицы posts...")
        posts_exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'posts')"
        )
        
        if posts_exists:
            posts_columns = await conn.fetch(
                """
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'posts' AND table_schema = 'public'
                ORDER BY ordinal_position
                """
            )
            
            print("\nСтруктура таблицы posts:")
            for column in posts_columns:
                print(f"- {column['column_name']}: {column['data_type']}")
        else:
            print("\n❌ Таблица posts не существует")
        
        # Закрываем соединение
        await conn.close()
        print("\nСоединение с базой данных закрыто")
        
    except asyncpg.InvalidCatalogNameError:
        print(f"❌ База данных {db_name} не существует")
    except Exception as e:
        print(f"❌ Ошибка при проверке базы данных: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Запуск скрипта проверки базы данных...")
    sys.stdout.flush()
    asyncio.run(check_database())
    print("Скрипт проверки базы данных завершен")
    sys.stdout.flush() 