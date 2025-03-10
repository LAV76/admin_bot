import asyncio
import asyncpg
import os
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_admin_role():
    # Загружаем переменные окружения
    load_dotenv()
    
    # Получаем значение ADMIN_ID
    admin_id_str = os.getenv("ADMIN_ID")
    if not admin_id_str:
        logger.error("ADMIN_ID не указан в .env файле")
        return False
    
    try:
        admin_id = int(admin_id_str)
        logger.info(f"ID администратора: {admin_id}")
    except ValueError:
        logger.error(f"Некорректный ADMIN_ID: {admin_id_str}")
        return False
    
    # Получаем параметры подключения к базе данных
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASS", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "tgbot_admin")
    
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
                logger.error(f"Пользователь с ID {admin_id} не найден в таблице users")
                return False
            else:
                logger.info(f"Пользователь с ID {admin_id} найден в таблице users: {user}")
            
            # Проверяем существование роли в таблице user_roles
            role = await conn.fetchrow(
                "SELECT * FROM user_roles WHERE user_id = $1 AND role_type = 'admin'",
                admin_id
            )
            
            if not role:
                logger.error(f"Роль администратора для пользователя {admin_id} не найдена в таблице user_roles")
                return False
            else:
                logger.info(f"Роль администратора для пользователя {admin_id} найдена в таблице user_roles: {role}")
                return True
            
        finally:
            # Закрываем соединение
            await conn.close()
            logger.info("Соединение с базой данных закрыто")
            
    except Exception as e:
        logger.error(f"Ошибка при работе с базой данных: {e}")
        return False

if __name__ == "__main__":
    print("Проверка роли администратора в базе данных...")
    result = asyncio.run(check_admin_role())
    if result:
        print("✅ Роль администратора найдена в базе данных")
    else:
        print("❌ Роль администратора не найдена в базе данных") 