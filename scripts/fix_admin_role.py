import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
import asyncpg

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_admin_role():
    """Принудительное добавление роли администратора через прямой SQL-запрос"""
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
            # Выводим информацию о таблицах
            tables = await conn.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
            table_names = [t['tablename'] for t in tables]
            logger.info(f"Найдены таблицы: {table_names}")
            
            # Проверяем структуру таблицы user_roles
            if 'user_roles' in table_names:
                columns = await conn.fetch(
                    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'user_roles'"
                )
                logger.info(f"Структура таблицы user_roles: {columns}")
            
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
                logger.info(f"Пользователь с ID {admin_id} уже существует в таблице users: {user}")
            
            # Удаляем существующую роль, если она есть (для очистки)
            await conn.execute(
                "DELETE FROM user_roles WHERE user_id = $1",
                admin_id
            )
            logger.info(f"Удалены существующие роли для пользователя {admin_id}")
            
            # Принудительно добавляем роль администратора
            try:
                await conn.execute(
                    "INSERT INTO user_roles (user_id, role_type, created_by) VALUES ($1, 'admin', $1)",
                    admin_id
                )
                logger.info(f"Роль администратора для пользователя {admin_id} добавлена")
                
                # Проверяем, что роль добавлена
                role = await conn.fetchrow(
                    "SELECT * FROM user_roles WHERE user_id = $1 AND role_type = 'admin'",
                    admin_id
                )
                
                if role:
                    logger.info(f"Проверка успешна: роль администратора добавлена: {role}")
                    return True
                else:
                    logger.error("Роль не была добавлена, несмотря на успешное выполнение запроса")
                    return False
                
            except Exception as e:
                logger.error(f"Ошибка при добавлении роли администратора: {e}")
                
                # Пробуем альтернативный способ добавления
                logger.info("Пробуем альтернативный способ добавления роли...")
                await conn.execute("""
                    DO $$
                    BEGIN
                        INSERT INTO user_roles (user_id, role_type, created_by)
                        VALUES (%s, 'admin', %s);
                        EXCEPTION WHEN OTHERS THEN
                            RAISE NOTICE '%%', SQLERRM;
                    END $$;
                """ % (admin_id, admin_id))
                
                # Проверяем, что роль добавлена
                role = await conn.fetchrow(
                    "SELECT * FROM user_roles WHERE user_id = $1 AND role_type = 'admin'",
                    admin_id
                )
                
                if role:
                    logger.info(f"Альтернативный способ сработал: роль администратора добавлена: {role}")
                    return True
                else:
                    logger.error("Роль не была добавлена даже альтернативным способом")
                    return False
            
        finally:
            # Закрываем соединение
            await conn.close()
            logger.info("Соединение с базой данных закрыто")
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении роли администратора: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    print("Принудительное добавление роли администратора...")
    success = asyncio.run(fix_admin_role())
    
    if success:
        print("✅ Роль администратора успешно добавлена")
    else:
        print("❌ Ошибка при добавлении роли администратора")
        sys.exit(1) 