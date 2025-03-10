import sys
import psycopg2

print(f"Python версия: {sys.version}")
print(f"Операционная система: {sys.platform}")

def test_postgres_exists():
    """Тестирование подключения к системной базе postgres"""
    try:
        # Пробуем подключиться к базе данных postgres
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="BifNhtGkt",  # Пароль из .env
            host="localhost",
            port="5432"
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        
        print(f"Версия PostgreSQL: {version}")
        print("Подключение к базе данных postgres успешно!")
        
        # Проверяем существование базы данных tgbot_admin
        cursor.execute("SELECT datname FROM pg_database WHERE datname = 'tgbot_admin'")
        exists = cursor.fetchone()
        
        if exists:
            print("База данных tgbot_admin существует!")
        else:
            print("База данных tgbot_admin не существует!")
            print("Создаем базу данных tgbot_admin...")
            # Сначала закрываем текущее соединение и открываем новое с autocommit
            cursor.close()
            conn.close()
            
            conn = psycopg2.connect(
                dbname="postgres",
                user="postgres",
                password="BifNhtGkt",
                host="localhost",
                port="5432"
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            cursor.execute("CREATE DATABASE tgbot_admin")
            print("База данных tgbot_admin успешно создана!")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Ошибка подключения к postgres: {e}")
        return False

if __name__ == "__main__":
    result = test_postgres_exists()
    sys.exit(0 if result else 1) 