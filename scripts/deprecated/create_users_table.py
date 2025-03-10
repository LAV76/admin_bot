import asyncio
import asyncpg
import os
import logging
from dotenv import load_dotenv

# Настраиваем логгер
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('create_users_table')

# Загружаем переменные окружения
load_dotenv()

# Получаем параметры подключения из переменных окружения
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tgbot_admin")

async def create_users_table():
    # Формируем DSN для подключения
    dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # SQL для создания таблицы пользователей
    create_users_table_sql = """
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
    );
    """
    
    # SQL для создания таблицы ролей пользователей
    create_user_roles_table_sql = """
    CREATE TABLE IF NOT EXISTS user_roles (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        role_type VARCHAR(50) NOT NULL,
        created_by BIGINT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        display_name VARCHAR(100),
        notes TEXT,
        CONSTRAINT user_role_unique UNIQUE (user_id, role_type)
    );
    """
    
    # SQL для создания таблицы истории ролей
    create_role_history_table_sql = """
    CREATE TABLE IF NOT EXISTS role_history (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        role_type VARCHAR(50) NOT NULL,
        action VARCHAR(20) NOT NULL, -- 'add' or 'remove'
        admin_id BIGINT NOT NULL,
        action_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        notes TEXT
    );
    """
    
    try:
        # Подключаемся к базе данных
        logger.info(f"Подключение к базе данных {DB_NAME}...")
        conn = await asyncpg.connect(dsn)
        
        # Создаем таблицу пользователей
        logger.info("Создание таблицы users...")
        await conn.execute(create_users_table_sql)
        logger.info("Таблица users успешно создана")
        
        # Создаем таблицу ролей пользователей
        logger.info("Создание таблицы user_roles...")
        await conn.execute(create_user_roles_table_sql)
        logger.info("Таблица user_roles успешно создана")
        
        # Создаем таблицу истории ролей
        logger.info("Создание таблицы role_history...")
        await conn.execute(create_role_history_table_sql)
        logger.info("Таблица role_history успешно создана")
        
        # Добавляем администратора из .env
        admin_id = os.getenv("ADMIN_ID")
        if admin_id:
            try:
                admin_id = int(admin_id)
                # Проверяем, существует ли уже пользователь
                user_exists = await conn.fetchval(
                    "SELECT COUNT(*) FROM users WHERE user_id = $1", admin_id
                )
                
                if not user_exists:
                    logger.info(f"Добавление администратора (ID: {admin_id})...")
                    await conn.execute(
                        "INSERT INTO users (user_id, username, user_role) VALUES ($1, $2, $3)",
                        admin_id, f"admin_{admin_id}", "admin"
                    )
                    logger.info(f"Администратор (ID: {admin_id}) успешно добавлен")
                else:
                    logger.info(f"Администратор (ID: {admin_id}) уже существует")
                
                # Проверяем, есть ли у пользователя роль admin
                role_exists = await conn.fetchval(
                    "SELECT COUNT(*) FROM user_roles WHERE user_id = $1 AND role_type = $2",
                    admin_id, "admin"
                )
                
                if not role_exists:
                    logger.info(f"Добавление роли администратора для пользователя (ID: {admin_id})...")
                    await conn.execute(
                        "INSERT INTO user_roles (user_id, role_type, created_by, display_name) VALUES ($1, $2, $3, $4)",
                        admin_id, "admin", admin_id, "Администратор"
                    )
                    logger.info(f"Роль администратора успешно добавлена пользователю (ID: {admin_id})")
                else:
                    logger.info(f"Пользователь (ID: {admin_id}) уже имеет роль администратора")
            except ValueError:
                logger.error(f"Некорректный ADMIN_ID: {admin_id}")
        
        # Закрываем соединение
        await conn.close()
        logger.info("Соединение с базой данных закрыто")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(create_users_table()) 