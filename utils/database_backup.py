import os
import logging
import subprocess
import asyncpg
import glob
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)

# Получение параметров подключения к БД из переменных окружения
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tgbot_admin")

BACKUP_DIR = "backups"

# Убедимся, что директория для резервных копий существует
os.makedirs(BACKUP_DIR, exist_ok=True)

async def create_backup() -> str:
    """Создание резервной копии базы данных"""
    try:
        # Формируем имя файла резервной копии
        backup_file = os.path.join(BACKUP_DIR, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")
        
        # Формируем команду для создания резервной копии
        command = [
            "pg_dump",
            f"--host={DB_HOST}",
            f"--port={DB_PORT}",
            f"--username={DB_USER}",
            f"--file={backup_file}",
            DB_NAME
        ]
        
        # Устанавливаем переменную окружения для пароля
        env = os.environ.copy()
        env["PGPASSWORD"] = DB_PASS
        
        # Выполняем команду
        subprocess.run(command, check=True, env=env)
        
        logger.info(f"Резервная копия базы данных создана: {backup_file}")
        return backup_file
    except Exception as e:
        logger.error(f"Ошибка при создании резервной копии базы данных: {e}")
        return ""

async def restore_backup(backup_file: str) -> bool:
    """Восстановление базы данных из резервной копии"""
    try:
        # Формируем команду для восстановления из резервной копии
        command = [
            "psql",
            f"--host={DB_HOST}",
            f"--port={DB_PORT}",
            f"--username={DB_USER}",
            f"--dbname={DB_NAME}",
            f"--file={backup_file}"
        ]
        
        # Устанавливаем переменную окружения для пароля
        env = os.environ.copy()
        env["PGPASSWORD"] = DB_PASS
        
        # Выполняем команду
        subprocess.run(command, check=True, env=env)
        
        logger.info(f"База данных успешно восстановлена из резервной копии: {backup_file}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при восстановлении базы данных из резервной копии: {e}")
        return False

async def get_database_stats() -> dict:
    """
    Получение статистики базы данных
    
    Returns:
        dict: Словарь со статистикой базы данных
    """
    try:
        # Подключаемся к базе данных
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        
        # Получаем размер базы данных
        db_size_query = """
        SELECT pg_size_pretty(pg_database_size($1)) as db_size
        """
        db_size = await conn.fetchval(db_size_query, DB_NAME)
        
        # Получаем список таблиц
        tables_query = """
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public'
        """
        tables = await conn.fetch(tables_query)
        
        # Получаем количество записей в каждой таблице
        tables_data = {}
        for table in tables:
            table_name = table['tablename']
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            count = await conn.fetchval(count_query)
            tables_data[table_name] = count
        
        # Формируем результат
        result = {
            'db_size': db_size,
            'tables_count': len(tables),
            'tables_data': tables_data
        }
        
        await conn.close()
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении статистики базы данных: {e}")
        return {
            'db_size': 'Ошибка',
            'tables_count': 0,
            'tables_data': {}
        }

async def get_available_backups() -> list:
    """
    Получение списка доступных резервных копий
    
    Returns:
        list: Список путей к файлам резервных копий
    """
    try:
        # Получаем список файлов резервных копий
        backup_files = glob.glob(os.path.join(BACKUP_DIR, "backup_*.sql"))
        
        # Сортируем по дате создания (от старых к новым)
        backup_files.sort(key=os.path.getmtime)
        
        return backup_files
    except Exception as e:
        logger.error(f"Ошибка при получении списка резервных копий: {e}")
        return []

async def clear_role_history() -> bool:
    """
    Очистка истории изменений ролей
    
    Returns:
        bool: True если успешно, False в противном случае
    """
    try:
        # Подключаемся к базе данных
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        
        # Очищаем таблицу role_audit
        await conn.execute("DELETE FROM role_audit")
        
        await conn.close()
        logger.info("История изменений ролей успешно очищена")
        return True
    except Exception as e:
        logger.error(f"Ошибка при очистке истории изменений ролей: {e}")
        return False

async def export_user_data(file_path: str) -> bool:
    """
    Экспорт данных пользователей в CSV файл
    
    Args:
        file_path: Путь к файлу для экспорта
        
    Returns:
        bool: True если успешно, False в противном случае
    """
    try:
        # Формируем команду для экспорта данных
        command = [
            "psql",
            f"--host={DB_HOST}",
            f"--port={DB_PORT}",
            f"--username={DB_USER}",
            f"--dbname={DB_NAME}",
            "-c", f"\\COPY (SELECT * FROM users) TO '{file_path}' WITH CSV HEADER"
        ]
        
        # Устанавливаем переменную окружения для пароля
        env = os.environ.copy()
        env["PGPASSWORD"] = DB_PASS
        
        # Выполняем команду
        subprocess.run(command, check=True, env=env)
        
        logger.info(f"Данные пользователей успешно экспортированы в файл: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при экспорте данных пользователей: {e}")
        return False

async def import_user_data(file_path: str) -> bool:
    """
    Импорт данных пользователей из CSV файла
    
    Args:
        file_path: Путь к файлу для импорта
        
    Returns:
        bool: True если успешно, False в противном случае
    """
    try:
        # Проверяем существование файла
        if not os.path.exists(file_path):
            logger.error(f"Файл не найден: {file_path}")
            return False
        
        # Формируем команду для импорта данных
        command = [
            "psql",
            f"--host={DB_HOST}",
            f"--port={DB_PORT}",
            f"--username={DB_USER}",
            f"--dbname={DB_NAME}",
            "-c", f"\\COPY users FROM '{file_path}' WITH CSV HEADER"
        ]
        
        # Устанавливаем переменную окружения для пароля
        env = os.environ.copy()
        env["PGPASSWORD"] = DB_PASS
        
        # Выполняем команду
        subprocess.run(command, check=True, env=env)
        
        logger.info(f"Данные пользователей успешно импортированы из файла: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при импорте данных пользователей: {e}")
        return False 