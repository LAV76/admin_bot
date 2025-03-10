import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
import asyncpg

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def add_new_admin(user_id: int):
    """Добавление еще одного администратора в базу данных"""
    # Загружаем переменные окружения
    load_dotenv()
    
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
        logger.info(f"Подключение к базе данных {db_name}...")
        conn = await asyncpg.connect(dsn)
        
        try:
            # Проверяем существование пользователя в таблице users
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1", 
                user_id
            )
            
            if not user:
                logger.info(f"Пользователь с ID {user_id} не найден, добавляем...")
                await conn.execute(
                    "INSERT INTO users (user_id, username, user_role) VALUES ($1, 'admin', 'admin')",
                    user_id
                )
                logger.info(f"Пользователь с ID {user_id} добавлен в таблицу users")
            else:
                logger.info(f"Пользователь с ID {user_id} уже существует в таблице users")
                # Обновляем роль пользователя
                await conn.execute(
                    "UPDATE users SET user_role = 'admin' WHERE user_id = $1",
                    user_id
                )
                logger.info(f"Роль пользователя с ID {user_id} обновлена на 'admin'")
            
            # Проверяем существование роли в таблице user_roles
            role = await conn.fetchrow(
                "SELECT * FROM user_roles WHERE user_id = $1 AND role_type = 'admin'",
                user_id
            )
            
            if not role:
                logger.info(f"Добавляем роль администратора для пользователя {user_id}...")
                # Получаем ADMIN_ID для created_by
                admin_id = int(os.getenv("ADMIN_ID", user_id))
                await conn.execute(
                    "INSERT INTO user_roles (user_id, role_type, created_by) VALUES ($1, 'admin', $2)",
                    user_id, admin_id
                )
                logger.info(f"Роль администратора для пользователя {user_id} добавлена")
                return True
            else:
                logger.info(f"Роль администратора для пользователя {user_id} уже существует")
                return True
            
        finally:
            # Закрываем соединение
            await conn.close()
            logger.info("Соединение с базой данных закрыто")
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении роли администратора: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            new_admin_id = int(sys.argv[1])
            print(f"Добавление нового администратора с ID {new_admin_id}...")
            success = asyncio.run(add_new_admin(new_admin_id))
            
            if success:
                print(f"✅ Роль администратора успешно добавлена для ID {new_admin_id}")
            else:
                print(f"❌ Ошибка при добавлении роли администратора для ID {new_admin_id}")
                sys.exit(1)
        except ValueError:
            print("❌ Ошибка: ID пользователя должен быть числом")
            sys.exit(1)
    else:
        print("❌ Ошибка: Необходимо указать ID пользователя")
        print("Использование: python add_new_admin.py <USER_ID>")
        sys.exit(1) 