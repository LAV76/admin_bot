import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
import asyncpg

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def remove_admin(user_id: int):
    """Удаление администратора из базы данных"""
    # Загружаем переменные окружения
    load_dotenv()
    
    # Получаем параметры подключения к БД
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASS", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "tgbot_admin")
    
    # Получаем ID администратора из .env для проверки
    env_admin_id = os.getenv("ADMIN_ID")
    if not env_admin_id:
        logger.error("ADMIN_ID не указан в .env файле")
        return False
    
    try:
        env_admin_id = int(env_admin_id)
        logger.info(f"Основной ID администратора из .env: {env_admin_id}")
        
        # Не позволяем удалить основного администратора
        if user_id == env_admin_id:
            logger.error(f"Нельзя удалить основного администратора ({env_admin_id})")
            return False
            
    except ValueError:
        logger.error(f"Некорректный ADMIN_ID в .env: {env_admin_id}")
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
                user_id
            )
            
            if not user:
                logger.info(f"Пользователь с ID {user_id} не найден в базе данных")
                return False
            
            # Удаляем роль администратора из таблицы user_roles
            logger.info(f"Удаляем роль администратора у пользователя {user_id}...")
            await conn.execute(
                "DELETE FROM user_roles WHERE user_id = $1 AND role_type = 'admin'",
                user_id
            )
            
            # Обновляем роль в таблице users
            logger.info(f"Обновляем роль пользователя {user_id} в таблице users...")
            await conn.execute(
                "UPDATE users SET user_role = NULL WHERE user_id = $1",
                user_id
            )
            
            logger.info(f"Роль администратора успешно удалена у пользователя {user_id}")
            return True
            
        finally:
            # Закрываем соединение
            await conn.close()
            logger.info("Соединение с базой данных закрыто")
            
    except Exception as e:
        logger.error(f"Ошибка при удалении роли администратора: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            admin_id = int(sys.argv[1])
            print(f"Удаление администратора с ID {admin_id}...")
            success = asyncio.run(remove_admin(admin_id))
            
            if success:
                print(f"✅ Роль администратора успешно удалена у пользователя с ID {admin_id}")
            else:
                print(f"❌ Ошибка при удалении роли администратора у пользователя с ID {admin_id}")
                sys.exit(1)
        except ValueError:
            print("❌ Ошибка: ID пользователя должен быть числом")
            sys.exit(1)
    else:
        print("❌ Ошибка: Необходимо указать ID пользователя")
        print("Использование: python remove_admin.py <USER_ID>")
        sys.exit(1) 