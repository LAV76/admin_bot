import asyncio
import os
import sys
from dotenv import load_dotenv
import logging
import asyncpg

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def create_admin_direct():
    """Создание администратора напрямую через SQL-запросы"""
    # Загружаем переменные окружения
    load_dotenv()
    
    # Получаем ID администратора из .env
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id:
        logger.error("ADMIN_ID не указан в .env файле")
        return False
    
    try:
        admin_id = int(admin_id)
    except ValueError:
        logger.error(f"Некорректный ADMIN_ID: {admin_id}")
        return False
    
    logger.info(f"Добавление администратора с ID: {admin_id}")
    
    # Получаем параметры подключения к БД
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASS", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "tgbot_admin")
    
    # Формируем строку подключения
    dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    try:
        # Подключаемся к базе данных
        conn = await asyncpg.connect(dsn)
        
        try:
            # Проверяем существование таблиц
            tables = await conn.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
            table_names = [t['tablename'] for t in tables]
            
            logger.info(f"Найдены таблицы: {table_names}")
            
            # Проверяем существование пользователя в таблице users
            if 'users' in table_names:
                user = await conn.fetchrow(
                    "SELECT * FROM users WHERE user_id = $1", 
                    admin_id
                )
                
                if user:
                    logger.info(f"Пользователь с ID {admin_id} уже существует")
                    # Обновляем роль пользователя
                    await conn.execute(
                        "UPDATE users SET user_role = 'admin' WHERE user_id = $1",
                        admin_id
                    )
                    logger.info(f"Обновлена роль пользователя с ID: {admin_id}")
                else:
                    # Создаем пользователя
                    await conn.execute(
                        """
                        INSERT INTO users (user_id, username, user_role) 
                        VALUES ($1, 'admin', 'admin')
                        """,
                        admin_id
                    )
                    logger.info(f"Создан новый пользователь с ID: {admin_id}")
            else:
                logger.error("Таблица 'users' не найдена в базе данных")
                return False
            
            # Проверяем существование роли в таблице user_roles
            if 'user_roles' in table_names:
                role = await conn.fetchrow(
                    "SELECT * FROM user_roles WHERE user_id = $1 AND role_type = 'admin'",
                    admin_id
                )
                
                if role:
                    logger.info(f"Роль 'admin' для пользователя {admin_id} уже существует")
                else:
                    # Добавляем роль администратора
                    await conn.execute(
                        """
                        INSERT INTO user_roles (user_id, role_type, created_by) 
                        VALUES ($1, 'admin', $1)
                        """,
                        admin_id
                    )
                    logger.info(f"Добавлена роль 'admin' для пользователя {admin_id}")
            else:
                logger.error("Таблица 'user_roles' не найдена в базе данных")
                return False
            
            logger.info("Администратор успешно добавлен в базу данных")
            return True
            
        finally:
            # Закрываем соединение
            await conn.close()
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении администратора: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = asyncio.run(create_admin_direct())
    if success:
        print("✅ Администратор успешно добавлен в базу данных")
    else:
        print("❌ Ошибка при добавлении администратора")
        sys.exit(1) 