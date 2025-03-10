import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(str(Path(__file__).parent.parent))

# Загружаем переменные окружения
load_dotenv()

# Вывод информации о версии Python и ОС
print(f"Python версия: {sys.version}")
print(f"Операционная система: {sys.platform}")

# Получаем параметры подключения из переменных окружения
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tgbot_admin")

# Вывод параметров подключения (без пароля)
print(f"Параметры подключения:")
print(f"  DB_USER: {DB_USER}")
print(f"  DB_HOST: {DB_HOST}")
print(f"  DB_PORT: {DB_PORT}")
print(f"  DB_NAME: {DB_NAME}")

async def test_asyncpg_connection():
    """Тестирование подключения с использованием asyncpg"""
    print("\nТестирование подключения с использованием asyncpg...")
    try:
        import asyncpg
        
        # Формируем DSN для подключения
        dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        
        # Подключаемся к базе данных
        print("Подключение к базе данных...")
        conn = await asyncpg.connect(dsn)
        
        # Выполняем тестовый запрос
        print("Выполнение тестового запроса...")
        version = await conn.fetchval("SELECT version()")
        print(f"Версия PostgreSQL: {version}")
        
        # Проверяем наличие таблиц
        print("\nПроверка наличия таблиц:")
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        
        if tables:
            print("Найдены следующие таблицы:")
            for table in tables:
                print(f"  - {table['tablename']}")
        else:
            print("Таблицы в схеме 'public' не найдены")
        
        # Закрываем соединение
        await conn.close()
        print("\nПодключение к базе данных через asyncpg успешно!")
        return True
        
    except ImportError as e:
        print(f"Ошибка импорта: {e}")
        print("Установите asyncpg: pip install asyncpg")
        return False
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        return False

async def test_sqlalchemy_connection():
    """Тестирование подключения с использованием SQLAlchemy"""
    print("\nТестирование подключения с использованием SQLAlchemy...")
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        # Формируем DSN для подключения
        dsn = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        
        # Создаем движок
        print("Создание движка SQLAlchemy...")
        engine = create_async_engine(dsn, echo=False)
        
        # Выполняем тестовый запрос
        print("Выполнение тестового запроса...")
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"Версия PostgreSQL: {version}")
        
        # Закрываем движок
        await engine.dispose()
        print("\nПодключение к базе данных через SQLAlchemy успешно!")
        return True
        
    except ImportError as e:
        print(f"Ошибка импорта: {e}")
        print("Установите необходимые пакеты: pip install sqlalchemy[asyncio] asyncpg")
        return False
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        return False

async def main():
    """Основная функция"""
    # Тестирование подключения с использованием asyncpg
    asyncpg_success = await test_asyncpg_connection()
    
    # Тестирование подключения с использованием SQLAlchemy
    sqlalchemy_success = await test_sqlalchemy_connection()
    
    # Итоговый результат
    print("\nРезультаты тестирования:")
    print(f"  - asyncpg: {'Успешно' if asyncpg_success else 'Ошибка'}")
    print(f"  - SQLAlchemy: {'Успешно' if sqlalchemy_success else 'Ошибка'}")
    
    if asyncpg_success and sqlalchemy_success:
        print("\nВсе тесты подключения к базе данных успешны!")
        return 0
    else:
        print("\nНекоторые тесты подключения к базе данных не пройдены.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 