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

def test_psycopg2_connection():
    """Тестирование подключения с использованием psycopg2"""
    print("\nТестирование подключения с использованием psycopg2...")
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        print("Подключение к базе данных...")
        # Подключаемся к базе данных
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        
        # Настраиваем уровень изоляции
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Создаем курсор
        cursor = conn.cursor()
        
        # Выполняем тестовый запрос
        print("Выполнение тестового запроса...")
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"Версия PostgreSQL: {version}")
        
        # Проверяем наличие таблиц
        print("\nПроверка наличия таблиц:")
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        tables = cursor.fetchall()
        
        if tables:
            print("Найдены следующие таблицы:")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("Таблицы в схеме 'public' не найдены")
        
        # Закрываем соединение
        cursor.close()
        conn.close()
        print("\nПодключение к базе данных через psycopg2 успешно!")
        return True
        
    except ImportError as e:
        print(f"Ошибка импорта: {e}")
        print("Установите psycopg2: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        return False

def main():
    """Основная функция"""
    # Тестирование подключения с использованием psycopg2
    psycopg2_success = test_psycopg2_connection()
    
    # Итоговый результат
    print("\nРезультаты тестирования:")
    print(f"  - psycopg2: {'Успешно' if psycopg2_success else 'Ошибка'}")
    
    if psycopg2_success:
        print("\nТест подключения к базе данных успешен!")
        return 0
    else:
        print("\nТест подключения к базе данных не пройден.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 