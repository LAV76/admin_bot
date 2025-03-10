import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
import asyncpg

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def execute_sql():
    """Выполнение прямых SQL-запросов для диагностики и исправления проблемы"""
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
            # 1. Проверяем список таблиц
            logger.info("1. Проверка списка таблиц:")
            tables = await conn.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
            for table in tables:
                logger.info(f"  - {table['tablename']}")
            
            # 2. Проверяем структуру таблицы users
            logger.info("\n2. Структура таблицы users:")
            users_columns = await conn.fetch(
                "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users'"
            )
            for column in users_columns:
                logger.info(f"  - {column['column_name']}: {column['data_type']}")
            
            # 3. Проверяем структуру таблицы user_roles
            logger.info("\n3. Структура таблицы user_roles:")
            roles_columns = await conn.fetch(
                "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'user_roles'"
            )
            for column in roles_columns:
                logger.info(f"  - {column['column_name']}: {column['data_type']}")
            
            # 4. Проверяем ограничения таблицы user_roles
            logger.info("\n4. Ограничения таблицы user_roles:")
            constraints = await conn.fetch("""
                SELECT conname, pg_get_constraintdef(c.oid) 
                FROM pg_constraint c 
                JOIN pg_namespace n ON n.oid = c.connamespace 
                WHERE conrelid = 'user_roles'::regclass
            """)
            for constraint in constraints:
                logger.info(f"  - {constraint['conname']}: {constraint['pg_get_constraintdef']}")
            
            # 5. Проверяем данные в таблице users
            logger.info("\n5. Данные в таблице users:")
            users = await conn.fetch("SELECT * FROM users")
            for user in users:
                logger.info(f"  - {user}")
            
            # 6. Проверяем данные в таблице user_roles
            logger.info("\n6. Данные в таблице user_roles:")
            roles = await conn.fetch("SELECT * FROM user_roles")
            for role in roles:
                logger.info(f"  - {role}")
            
            # 7. Проверяем наличие пользователя с ID администратора
            logger.info(f"\n7. Проверка пользователя с ID {admin_id}:")
            user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", admin_id)
            if user:
                logger.info(f"  - Пользователь найден: {user}")
            else:
                logger.info(f"  - Пользователь не найден")
            
            # 8. Проверяем наличие роли администратора
            logger.info(f"\n8. Проверка роли администратора для пользователя {admin_id}:")
            role = await conn.fetchrow(
                "SELECT * FROM user_roles WHERE user_id = $1 AND role_type = 'admin'", 
                admin_id
            )
            if role:
                logger.info(f"  - Роль найдена: {role}")
            else:
                logger.info(f"  - Роль не найдена")
            
            # 9. Пробуем добавить роль администратора
            logger.info(f"\n9. Добавление роли администратора для пользователя {admin_id}:")
            try:
                # Сначала удаляем существующую роль, если она есть
                await conn.execute(
                    "DELETE FROM user_roles WHERE user_id = $1 AND role_type = 'admin'",
                    admin_id
                )
                logger.info("  - Существующая роль удалена (если была)")
                
                # Добавляем роль администратора
                await conn.execute("""
                    INSERT INTO user_roles (user_id, role_type, created_by) 
                    VALUES ($1, 'admin', $1)
                """, admin_id)
                logger.info("  - Роль администратора добавлена")
                
                # Проверяем, что роль добавлена
                role = await conn.fetchrow(
                    "SELECT * FROM user_roles WHERE user_id = $1 AND role_type = 'admin'", 
                    admin_id
                )
                if role:
                    logger.info(f"  - Проверка успешна: роль найдена: {role}")
                else:
                    logger.error("  - Ошибка: роль не найдена после добавления")
            except Exception as e:
                logger.error(f"  - Ошибка при добавлении роли: {e}")
            
            return True
            
        finally:
            # Закрываем соединение
            await conn.close()
            logger.info("Соединение с базой данных закрыто")
            
    except Exception as e:
        logger.error(f"Ошибка при выполнении SQL-запросов: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    print("Выполнение SQL-запросов для диагностики...")
    success = asyncio.run(execute_sql())
    
    if success:
        print("✅ SQL-запросы выполнены успешно")
    else:
        print("❌ Ошибка при выполнении SQL-запросов")
        sys.exit(1) 