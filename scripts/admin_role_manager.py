import asyncio
import os
import sys
import logging
import argparse
from dotenv import load_dotenv
import asyncpg
from typing import Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def get_db_connection():
    """Создаёт подключение к базе данных из параметров в .env"""
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
        return await asyncpg.connect(dsn)
    except Exception as e:
        logger.error(f"Ошибка при подключении к базе данных: {e}", exc_info=True)
        return None

async def add_admin_role() -> bool:
    """
    Добавление роли администратора из ADMIN_ID в .env файле
    
    Returns:
        bool: True если операция выполнена успешно
    """
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
    
    return await add_new_admin(admin_id)
    
async def add_new_admin(user_id: int) -> bool:
    """
    Добавление роли администратора для указанного пользователя
    
    Args:
        user_id: ID пользователя в Telegram
        
    Returns:
        bool: True если операция выполнена успешно
    """
    conn = await get_db_connection()
    if not conn:
        return False
    
    try:
        # Проверяем существование пользователя в таблице users
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE user_id = $1", 
            user_id
        )
        
        if not user:
            logger.info(f"Пользователь с ID {user_id} не найден, добавляем...")
            await conn.execute(
                "INSERT INTO users (user_id, username, role) VALUES ($1, 'admin', 'admin')",
                user_id
            )
            logger.info(f"Пользователь с ID {user_id} добавлен в таблицу users")
        else:
            logger.info(f"Пользователь с ID {user_id} уже существует в таблице users")
            # Обновляем роль пользователя
            await conn.execute(
                "UPDATE users SET role = 'admin' WHERE user_id = $1",
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
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении роли администратора: {e}", exc_info=True)
        return False
    finally:
        # Закрываем соединение
        await conn.close()
        logger.info("Соединение с базой данных закрыто")

async def remove_admin(user_id: int) -> bool:
    """
    Удаление роли администратора у указанного пользователя
    
    Args:
        user_id: ID пользователя в Telegram
        
    Returns:
        bool: True если операция выполнена успешно
    """
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
    
    conn = await get_db_connection()
    if not conn:
        return False
    
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
            "UPDATE users SET role = NULL WHERE user_id = $1",
            user_id
        )
        
        logger.info(f"Роль администратора успешно удалена у пользователя {user_id}")
        return True
            
    except Exception as e:
        logger.error(f"Ошибка при удалении роли администратора: {e}", exc_info=True)
        return False
    finally:
        # Закрываем соединение
        await conn.close()
        logger.info("Соединение с базой данных закрыто")

async def list_admins() -> bool:
    """
    Выводит список всех администраторов
    
    Returns:
        bool: True если операция выполнена успешно
    """
    conn = await get_db_connection()
    if not conn:
        return False
    
    try:
        # Получаем всех пользователей с ролью админа
        admins = await conn.fetch("""
            SELECT u.user_id, u.username, ur.created_at, ur.created_by 
            FROM users u
            JOIN user_roles ur ON u.user_id = ur.user_id
            WHERE ur.role_type = 'admin'
            ORDER BY ur.created_at
        """)
        
        if not admins:
            logger.info("Администраторы не найдены в базе данных")
            return True
        
        logger.info(f"Найдено администраторов: {len(admins)}")
        print(f"\nСписок администраторов ({len(admins)}):")
        print("-" * 50)
        
        for admin in admins:
            env_admin = "✅" if str(admin['user_id']) == os.getenv("ADMIN_ID", "") else " "
            created_by = "самостоятельно" if admin['user_id'] == admin['created_by'] else f"админом {admin['created_by']}"
            print(f"{env_admin} ID: {admin['user_id']:<15} Имя: {admin['username'] or 'не задано':<20} Добавлен: {created_by}")
        
        print("-" * 50)
        return True
            
    except Exception as e:
        logger.error(f"Ошибка при получении списка администраторов: {e}", exc_info=True)
        return False
    finally:
        # Закрываем соединение
        await conn.close()
        logger.info("Соединение с базой данных закрыто")

def main():
    """Основная функция для CLI-интерфейса"""
    parser = argparse.ArgumentParser(description='Управление ролями администраторов')
    subparsers = parser.add_subparsers(dest='command', help='Команды')
    
    # Команда инициализации основного администратора
    init_parser = subparsers.add_parser('init', help='Добавить основного администратора из .env')
    
    # Команда добавления администратора
    add_parser = subparsers.add_parser('add', help='Добавить нового администратора')
    add_parser.add_argument('user_id', type=int, help='ID пользователя в Telegram')
    
    # Команда удаления администратора
    remove_parser = subparsers.add_parser('remove', help='Удалить администратора')
    remove_parser.add_argument('user_id', type=int, help='ID пользователя в Telegram')
    
    # Команда вывода списка администраторов
    list_parser = subparsers.add_parser('list', help='Список всех администраторов')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        print("Инициализация основного администратора...")
        success = asyncio.run(add_admin_role())
        if success:
            print("✅ Роль администратора успешно добавлена")
        else:
            print("❌ Ошибка при добавлении роли администратора")
            sys.exit(1)
            
    elif args.command == 'add':
        print(f"Добавление нового администратора с ID {args.user_id}...")
        success = asyncio.run(add_new_admin(args.user_id))
        if success:
            print(f"✅ Роль администратора успешно добавлена для ID {args.user_id}")
        else:
            print(f"❌ Ошибка при добавлении роли администратора для ID {args.user_id}")
            sys.exit(1)
            
    elif args.command == 'remove':
        print(f"Удаление администратора с ID {args.user_id}...")
        success = asyncio.run(remove_admin(args.user_id))
        if success:
            print(f"✅ Роль администратора успешно удалена у пользователя с ID {args.user_id}")
        else:
            print(f"❌ Ошибка при удалении роли администратора у пользователя с ID {args.user_id}")
            sys.exit(1)
            
    elif args.command == 'list':
        asyncio.run(list_admins())
        
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main() 