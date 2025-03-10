import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
import asyncpg

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_role_audit_table():
    """Проверка и создание таблицы role_audit, если она не существует"""
    try:
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
        
        # Подключаемся к базе данных
        logger.info(f"Подключение к базе данных {db_name}...")
        conn = await asyncpg.connect(dsn)
        
        try:
            # Проверяем существование таблицы role_audit
            tables = await conn.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
            table_names = [t['tablename'] for t in tables]
            
            if 'role_audit' in table_names:
                logger.info("Таблица role_audit уже существует")
                
                # Проверяем структуру таблицы
                columns = await conn.fetch(
                    """
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'role_audit'
                    """
                )
                
                column_names = [c['column_name'] for c in columns]
                logger.info(f"Столбцы таблицы role_audit: {column_names}")
                
                # Проверяем наличие индексов
                indexes = await conn.fetch(
                    """
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = 'role_audit'
                    """
                )
                
                index_names = [i['indexname'] for i in indexes]
                logger.info(f"Индексы таблицы role_audit: {index_names}")
                
                # Проверяем количество записей
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM role_audit"
                )
                
                logger.info(f"Количество записей в таблице role_audit: {count}")
                
                return True
            
            # Создаем таблицу role_audit
            logger.info("Таблица role_audit не существует, создаем...")
            await conn.execute("""
                CREATE TABLE role_audit (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    role_type VARCHAR(50) NOT NULL,
                    action VARCHAR(20) NOT NULL,
                    performed_by BIGINT NOT NULL,
                    performed_at TIMESTAMP DEFAULT NOW(),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
                )
            """)
            
            # Создаем индексы для таблицы role_audit
            await conn.execute("""
                CREATE INDEX idx_role_audit_user_id ON role_audit(user_id);
                CREATE INDEX idx_role_audit_performed_at ON role_audit(performed_at);
            """)
            
            logger.info("Таблица role_audit успешно создана")
            
            # Добавляем тестовую запись
            admin_id = os.getenv("ADMIN_ID")
            if admin_id:
                try:
                    admin_id = int(admin_id)
                    # Проверяем существование пользователя
                    user = await conn.fetchrow(
                        "SELECT * FROM users WHERE user_id = $1",
                        admin_id
                    )
                    
                    if user:
                        await conn.execute(
                            """
                            INSERT INTO role_audit (user_id, role_type, action, performed_by)
                            VALUES ($1, 'admin', 'add', $1)
                            """,
                            admin_id
                        )
                        logger.info(f"Добавлена тестовая запись в role_audit для пользователя {admin_id}")
                except Exception as e:
                    logger.error(f"Ошибка при добавлении тестовой записи: {e}")
            
            return True
            
        finally:
            # Закрываем соединение
            await conn.close()
            
    except Exception as e:
        logger.error(f"Ошибка при проверке таблицы role_audit: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = asyncio.run(check_role_audit_table())
    
    if success:
        print("✅ Таблица role_audit успешно проверена/создана")
    else:
        print("❌ Ошибка при проверке/создании таблицы role_audit")
        sys.exit(1) 