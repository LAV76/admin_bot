import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
import asyncpg

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def add_admin_role():
    """Добавление роли администратора напрямую в базу данных"""
    # Загружаем переменные окружения
    load_dotenv()
    
    # Получаем параметры подключения к БД
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASS", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "tgbot_admin")
    
    # Получаем ID администратора из .env
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id:
        logger.error("ADMIN_ID не указан в .env файле")
        return False
    
    try:
        admin_id = int(admin_id)
        logger.info(f"ID администратора: {admin_id}")
    except ValueError:
        logger.error(f"Некорректный ADMIN_ID: {admin_id}")
        return False
    
    # Формируем строку подключения
    dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    try:
        # Подключаемся к базе данных
        logger.info(f"Подключение к базе данных {db_name}...")
        conn = await asyncpg.connect(dsn)
        
        try:
            # Проверяем существование пользователя в таблице users
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1", 
                admin_id
            )
            
            if not user:
                logger.info(f"Пользователь с ID {admin_id} не найден, добавляем...")
                await conn.execute(
                    "INSERT INTO users (user_id, username, user_role) VALUES ($1, 'admin', 'admin')",
                    admin_id
                )
                logger.info(f"Пользователь с ID {admin_id} добавлен в таблицу users")
            else:
                logger.info(f"Пользователь с ID {admin_id} уже существует в таблице users")
            
            # Проверяем существование роли в таблице user_roles
            role = await conn.fetchrow(
                "SELECT * FROM user_roles WHERE user_id = $1 AND role_type = 'admin'",
                admin_id
            )
            
            if not role:
                logger.info(f"Добавляем роль администратора для пользователя {admin_id}...")
                await conn.execute(
                    "INSERT INTO user_roles (user_id, role_type, created_by) VALUES ($1, 'admin', $1)",
                    admin_id
                )
                logger.info(f"Роль администратора для пользователя {admin_id} добавлена")
                return True
            else:
                logger.info(f"Роль администратора для пользователя {admin_id} уже существует")
                return True
            
        finally:
            # Закрываем соединение
            await conn.close()
            logger.info("Соединение с базой данных закрыто")
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении роли администратора: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    print("Добавление роли администратора...")
    success = asyncio.run(add_admin_role())
    
    if success:
        print("✅ Роль администратора успешно добавлена")
    else:
        print("❌ Ошибка при добавлении роли администратора")
        sys.exit(1) 