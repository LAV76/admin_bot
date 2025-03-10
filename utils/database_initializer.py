import asyncio
import os
import logging
from dotenv import load_dotenv
import asyncpg
from typing import List, Tuple, Optional

# Настройка логирования
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    """Класс для инициализации базы данных и создания необходимых таблиц"""
    
    def __init__(self):
        # Загружаем переменные окружения
        load_dotenv()
        
        # Получаем параметры подключения к БД
        self.db_user = os.getenv("DB_USER", "postgres")
        self.db_pass = os.getenv("DB_PASS", "")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = os.getenv("DB_PORT", "5432")
        self.db_name = os.getenv("DB_NAME", "tgbot_admin")
        
        # Получаем ID администратора из .env
        self.admin_id = os.getenv("ADMIN_ID")
        
        # Формируем строки подключения
        self.system_dsn = f"postgresql://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/postgres"
        self.db_dsn = f"postgresql://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    async def check_database_exists(self) -> bool:
        """Проверка существования базы данных"""
        try:
            # Подключаемся к системной БД postgres
            conn = await asyncpg.connect(self.system_dsn)
            
            try:
                # Проверяем существование нашей БД
                result = await conn.fetchrow(
                    "SELECT 1 FROM pg_database WHERE datname = $1",
                    self.db_name
                )
                
                return result is not None
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Ошибка при проверке существования базы данных: {e}")
            return False
    
    async def create_database(self) -> bool:
        """Создание базы данных"""
        try:
            # Подключаемся к системной БД postgres
            conn = await asyncpg.connect(self.system_dsn)
            
            try:
                # Создаем нашу БД
                await conn.execute(f"CREATE DATABASE {self.db_name}")
                logger.info(f"База данных {self.db_name} успешно создана")
                return True
                
            finally:
                await conn.close()
                
        except asyncpg.DuplicateDatabaseError:
            logger.info(f"База данных {self.db_name} уже существует")
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании базы данных: {e}")
            return False
    
    async def check_tables(self) -> Tuple[bool, List[str]]:
        """Проверка существования необходимых таблиц"""
        required_tables = ['users', 'user_roles', 'role_audit', 'alembic_version']
        missing_tables = []
        
        try:
            # Подключаемся к нашей БД
            conn = await asyncpg.connect(self.db_dsn)
            
            try:
                # Получаем список существующих таблиц
                tables = await conn.fetch(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                )
                existing_tables = [t['tablename'] for t in tables]
                
                logger.info(f"Существующие таблицы: {existing_tables}")
                
                # Проверяем наличие всех необходимых таблиц
                for table in required_tables:
                    if table not in existing_tables:
                        missing_tables.append(table)
                
                return len(missing_tables) == 0, missing_tables
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Ошибка при проверке таблиц: {e}")
            return False, required_tables
    
    async def create_tables(self) -> bool:
        """Создание необходимых таблиц"""
        try:
            # Проверяем ID администратора
            if not self.admin_id:
                logger.error("ADMIN_ID не указан в .env файле")
                return False
            
            try:
                admin_id = int(self.admin_id)
                logger.info(f"ID администратора: {admin_id}")
            except ValueError:
                logger.error(f"Некорректный ADMIN_ID: {self.admin_id}")
                return False
            
            # Подключаемся к нашей БД
            conn = await asyncpg.connect(self.db_dsn)
            
            try:
                # Проверяем существование таблиц
                tables = await conn.fetch(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                )
                table_names = [t['tablename'] for t in tables]
                
                # Создаем таблицу users, если она не существует
                if 'users' not in table_names:
                    logger.info("Создание таблицы users...")
                    await conn.execute('''
                        CREATE TABLE users (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT NOT NULL UNIQUE,
                            username VARCHAR,
                            role VARCHAR,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        )
                    ''')
                    
                    # Создаем индекс для user_id
                    await conn.execute('''
                        CREATE INDEX ix_users_user_id ON users(user_id)
                    ''')
                    logger.info("Таблица users успешно создана")
                
                # Создаем таблицу user_roles, если она не существует
                if 'user_roles' not in table_names:
                    logger.info("Создание таблицы user_roles...")
                    await conn.execute('''
                        CREATE TABLE user_roles (
                            user_id BIGINT NOT NULL,
                            role_type VARCHAR(50) NOT NULL,
                            created_at TIMESTAMP DEFAULT NOW(),
                            created_by BIGINT NOT NULL,
                            PRIMARY KEY (user_id, role_type),
                            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                        )
                    ''')
                    
                    # Создаем индексы для user_roles
                    await conn.execute('''
                        CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
                        CREATE INDEX idx_user_roles_role_type ON user_roles(role_type)
                    ''')
                    logger.info("Таблица user_roles успешно создана")
                
                # Создаем таблицу role_audit, если она не существует
                if 'role_audit' not in table_names:
                    logger.info("Создание таблицы role_audit...")
                    await conn.execute('''
                        CREATE TABLE role_audit (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT NOT NULL,
                            role_type VARCHAR(50) NOT NULL,
                            action VARCHAR(20) NOT NULL,
                            performed_by BIGINT NOT NULL,
                            performed_at TIMESTAMP DEFAULT NOW(),
                            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
                        )
                    ''')
                    
                    # Создаем индексы для role_audit
                    await conn.execute('''
                        CREATE INDEX idx_role_audit_user_id ON role_audit(user_id);
                        CREATE INDEX idx_role_audit_performed_at ON role_audit(performed_at)
                    ''')
                    logger.info("Таблица role_audit успешно создана")
                
                # Создаем таблицу alembic_version, если она не существует
                if 'alembic_version' not in table_names:
                    logger.info("Создание таблицы alembic_version...")
                    await conn.execute('''
                        CREATE TABLE alembic_version (
                            version_num VARCHAR(32) NOT NULL,
                            PRIMARY KEY (version_num)
                        )
                    ''')
                    
                    # Добавляем текущую версию миграции
                    await conn.execute('''
                        INSERT INTO alembic_version (version_num) VALUES ('1a2b3c4d5e6f')
                    ''')
                    logger.info("Таблица alembic_version успешно создана")
                
                # Добавляем администратора в таблицу users
                user = await conn.fetchrow(
                    "SELECT * FROM users WHERE user_id = $1", 
                    admin_id
                )
                
                if not user:
                    logger.info(f"Добавление администратора с ID {admin_id}...")
                    await conn.execute(
                        "INSERT INTO users (user_id, username, role) VALUES ($1, 'admin', 'admin')",
                        admin_id
                    )
                    logger.info(f"Администратор с ID {admin_id} добавлен в таблицу users")
                else:
                    logger.info(f"Администратор с ID {admin_id} уже существует в таблице users")
                
                # Добавляем роль администратора в таблицу user_roles
                if 'user_roles' in table_names:
                    role = await conn.fetchrow(
                        "SELECT * FROM user_roles WHERE user_id = $1 AND role_type = 'admin'",
                        admin_id
                    )
                    
                    if not role:
                        logger.info(f"Добавление роли администратора для пользователя {admin_id}...")
                        try:
                            await conn.execute(
                                "INSERT INTO user_roles (user_id, role_type, created_by) VALUES ($1, 'admin', $1)",
                                admin_id
                            )
                            logger.info(f"Роль администратора для пользователя {admin_id} добавлена")
                        except Exception as e:
                            logger.error(f"Ошибка при добавлении роли администратора: {e}")
                    else:
                        logger.info(f"Роль администратора для пользователя {admin_id} уже существует")
                
                logger.info("Все таблицы успешно созданы и настроены")
                return True
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц: {e}")
            return False
    
    async def initialize(self) -> bool:
        """Инициализация базы данных и таблиц"""
        try:
            # Проверяем существование базы данных
            db_exists = await self.check_database_exists()
            
            if not db_exists:
                logger.info(f"База данных {self.db_name} не существует, создаем...")
                if not await self.create_database():
                    logger.error("Не удалось создать базу данных")
                    return False
            
            # Проверяем существование таблиц
            tables_ok, missing_tables = await self.check_tables()
            
            if not tables_ok:
                logger.info(f"Отсутствуют таблицы: {missing_tables}, создаем...")
                if not await self.create_tables():
                    logger.error("Не удалось создать таблицы")
                    return False
            
            logger.info("База данных и таблицы успешно инициализированы")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            return False

async def initialize_database() -> bool:
    """
    Инициализация базы данных.
    Проверяет наличие необходимых таблиц и создает их при необходимости.
    Также добавляет администратора из переменной окружения ADMIN_ID.
    
    Returns:
        bool: True если инициализация прошла успешно, иначе False
    """
    try:
        # Создаем экземпляр инициализатора базы данных
        initializer = DatabaseInitializer()
        
        # Проверяем существование базы данных
        db_exists = await initializer.check_database_exists()
        if not db_exists:
            # Создаем базу данных, если она не существует
            db_created = await initializer.create_database()
            if not db_created:
                logger.error("Не удалось создать базу данных")
                return False
            logger.info("База данных успешно создана")
        
        # Импортируем функцию создания таблиц из create_tables.py
        from create_tables import create_tables
        
        # Создаем таблицы
        tables_created = await create_tables()
        if not tables_created:
            logger.error("Не удалось создать таблицы")
            return False
        
        # Получаем параметры подключения к БД
        db_user = os.getenv("DB_USER", "postgres")
        db_pass = os.getenv("DB_PASS", "")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "tgbot_admin")
        
        # Формируем строку подключения
        dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        
        # Подключаемся к базе данных
        conn = await asyncpg.connect(dsn)
        
        try:
            # Добавляем администратора, если указан ADMIN_ID
            admin_id = os.getenv("ADMIN_ID")
            if admin_id:
                # Проверяем существование пользователя
                user_exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM users WHERE user_id = $1)",
                    int(admin_id)
                )
                
                if not user_exists:
                    # Создаем пользователя
                    await conn.execute(
                        """
                        INSERT INTO users (user_id, username, role) 
                        VALUES ($1, 'admin', 'admin')
                        """,
                        int(admin_id)
                    )
                    logger.info(f"Создан пользователь-администратор с ID: {admin_id}")
                
                # Проверяем наличие роли администратора
                admin_role_exists = await conn.fetchval(
                    """
                    SELECT EXISTS(
                        SELECT 1 FROM user_roles 
                        WHERE user_id = $1 AND role_type = 'admin'
                    )
                    """,
                    int(admin_id)
                )
                
                if not admin_role_exists:
                    # Добавляем роль администратора
                    await conn.execute(
                        """
                        INSERT INTO user_roles (user_id, role_type, created_by) 
                        VALUES ($1, 'admin', $1)
                        """,
                        int(admin_id)
                    )
                    logger.info(f"Добавлена роль 'admin' для пользователя {admin_id}")
                    
                    # Логируем добавление роли в таблицу role_audit
                    await conn.execute(
                        """
                        INSERT INTO role_audit (user_id, role_type, action, performed_by) 
                        VALUES ($1, 'admin', 'add', $1)
                        """,
                        int(admin_id)
                    )
            
            logger.info("Инициализация базы данных успешно завершена")
            return True
            
        finally:
            # Закрываем соединение
            await conn.close()
            
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}", exc_info=True)
        return False

# Алиас для обратной совместимости
init_database = initialize_database

if __name__ == "__main__":
    # Настройка логирования для запуска скрипта напрямую
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    success = asyncio.run(initialize_database())
    
    if success:
        print("✅ База данных и таблицы успешно инициализированы")
    else:
        print("❌ Ошибка при инициализации базы данных")
        exit(1) 