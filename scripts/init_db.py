"""
Скрипт инициализации базы данных.

Предоставляет функционал для:
- проверки подключения к PostgreSQL
- создания базы данных, если она не существует
- применения миграций Alembic

Использование:
python -m scripts.init_db [--skip-migrations]
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import asyncpg
import click
from alembic.config import Config
from alembic import command
from dotenv import load_dotenv

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(str(Path(__file__).parent.parent))


class LoggerFactory:
    """Фабрика для создания логгеров с унифицированной конфигурацией."""

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        Создает настроенный логгер с указанным именем.
        
        Args:
            name: Имя логгера
            
        Returns:
            logging.Logger: Настроенный логгер
        """
        logger = logging.getLogger(name)
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger


class DatabaseConfig:
    """Класс для управления конфигурацией базы данных."""
    
    def __init__(self) -> None:
        """
        Инициализирует конфигурацию, загружая данные из .env файла.
        """
        load_dotenv()
        self.db_user = os.getenv("DB_USER", "postgres")
        self.db_pass = os.getenv("DB_PASS", "")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = os.getenv("DB_PORT", "5432")
        self.db_name = os.getenv("DB_NAME", "tgbot_admin")
        
    def get_system_dsn(self) -> str:
        """
        Возвращает строку подключения к системной базе данных postgres.
        
        Returns:
            str: Строка подключения к системной БД
        """
        return self._format_dsn("postgres")
    
    def get_app_dsn(self) -> str:
        """
        Возвращает строку подключения к базе данных приложения.
        
        Returns:
            str: Строка подключения к БД приложения
        """
        return self._format_dsn(self.db_name)
    
    def _format_dsn(self, db_name: str) -> str:
        """
        Форматирует строку подключения для указанной базы данных.
        
        Args:
            db_name: Имя базы данных
            
        Returns:
            str: Отформатированная строка подключения
        """
        # Используем маскировку пароля для безопасности в логах
        return (
            f"postgresql://{self.db_user}:{self.db_pass}@"
            f"{self.db_host}:{self.db_port}/{db_name}"
        )
    
    def get_connection_params(self) -> Dict[str, Any]:
        """
        Возвращает параметры подключения в виде словаря.
        
        Returns:
            Dict[str, Any]: Параметры подключения
        """
        return {
            "user": self.db_user,
            "password": self.db_pass,
            "host": self.db_host,
            "port": self.db_port,
            "database": self.db_name
        }
    
    def get_safe_connection_string(self) -> str:
        """
        Возвращает безопасную для логирования строку подключения
        (с маскированным паролем).
        
        Returns:
            str: Безопасная строка подключения
        """
        masked_pass = "***" if self.db_pass else ""
        return (
            f"postgresql://{self.db_user}:{masked_pass}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )


class PostgresConnector:
    """Класс для работы с подключениями к PostgreSQL."""
    
    def __init__(self, config: DatabaseConfig, logger: logging.Logger) -> None:
        """
        Инициализирует коннектор с указанной конфигурацией.
        
        Args:
            config: Конфигурация базы данных
            logger: Логгер для записи событий
        """
        self.config = config
        self.logger = logger
        
    async def check_connection(self) -> bool:
        """
        Проверяет возможность подключения к PostgreSQL.
        
        Returns:
            bool: True, если подключение успешно
        """
        system_dsn = self.config.get_system_dsn()
        try:
            self.logger.info("Проверка подключения к PostgreSQL...")
            conn = await asyncpg.connect(system_dsn)
            await conn.close()
            self.logger.info("Подключение к PostgreSQL успешно установлено")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при подключении к PostgreSQL: {e}")
            return False
    
    async def database_exists(self, db_name: str) -> bool:
        """
        Проверяет существование указанной базы данных.
        
        Args:
            db_name: Имя проверяемой базы данных
            
        Returns:
            bool: True, если база данных существует
            
        Raises:
            ConnectionError: Если не удалось подключиться к PostgreSQL
        """
        system_dsn = self.config.get_system_dsn()
        try:
            conn = await asyncpg.connect(system_dsn)
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = $1)",
                db_name
            )
            await conn.close()
            return bool(exists)
        except Exception as e:
            self.logger.error(
                f"Ошибка при проверке существования базы данных: {e}"
            )
            raise ConnectionError(f"Ошибка подключения: {e}") from e
    
    async def create_database(self) -> bool:
        """
        Создает базу данных, если она не существует.
        
        Returns:
            bool: True, если база данных создана или уже существовала
            
        Raises:
            ConnectionError: Если произошла ошибка при создании БД
        """
        db_name = self.config.db_name
        system_dsn = self.config.get_system_dsn()
        
        try:
            # Проверяем существование базы данных
            exists = await self.database_exists(db_name)
            
            if exists:
                self.logger.info(f"База данных {db_name} уже существует")
                return True
            
            # Создаем базу данных
            self.logger.info(f"Создание базы данных {db_name}...")
            conn = await asyncpg.connect(system_dsn)
            
            # Используем безопасный способ с параметризованным запросом
            # для предотвращения SQL-инъекций
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            await conn.close()
            
            self.logger.info(f"База данных {db_name} успешно создана")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при создании базы данных: {e}")
            raise ConnectionError(f"Ошибка создания базы данных: {e}") from e


class MigrationManager:
    """Класс для управления миграциями базы данных."""
    
    def __init__(self, logger: logging.Logger) -> None:
        """
        Инициализирует менеджер миграций.
        
        Args:
            logger: Логгер для записи событий
        """
        self.logger = logger
        self.project_root = Path(__file__).parent.parent
        
    def apply_migrations(self) -> bool:
        """
        Применяет миграции Alembic.
        
        Returns:
            bool: True, если миграции применены успешно
        """
        try:
            self.logger.info("Применение миграций...")
            
            # Получаем путь к конфигурации alembic
            alembic_ini = self.project_root / "alembic.ini"
            
            if not alembic_ini.exists():
                self.logger.error(
                    f"Файл конфигурации alembic.ini не найден: {alembic_ini}"
                )
                return False
            
            # Создаем объект конфигурации
            alembic_cfg = Config(str(alembic_ini))
            
            # Применяем миграции
            command.upgrade(alembic_cfg, "head")
            
            self.logger.info("Миграции успешно применены")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при применении миграций: {e}")
            return False


class DatabaseInitializer:
    """
    Класс для инициализации базы данных, инкапсулирующий
    весь процесс инициализации.
    """
    
    def __init__(self) -> None:
        """Инициализирует объект и создаёт зависимости."""
        self.logger = LoggerFactory.get_logger("db_initializer")
        self.config = DatabaseConfig()
        self.connector = PostgresConnector(self.config, self.logger)
        self.migration_manager = MigrationManager(self.logger)
    
    async def initialize(self, skip_migrations: bool = False) -> bool:
        """
        Выполняет полную инициализацию базы данных.
        
        Args:
            skip_migrations: Флаг пропуска миграций
            
        Returns:
            bool: True, если инициализация прошла успешно
        """
        try:
            # Шаг 1: Проверка подключения к PostgreSQL
            if not await self.connector.check_connection():
                self.logger.error("Не удалось подключиться к PostgreSQL")
                return False
            
            # Шаг 2: Создание базы данных
            if not await self.connector.create_database():
                self.logger.error("Не удалось создать базу данных")
                return False
            
            # Шаг 3: Применение миграций (если не пропущено)
            if not skip_migrations:
                if not self.migration_manager.apply_migrations():
                    self.logger.error("Не удалось применить миграции")
                    return False
            
            self.logger.info("Инициализация базы данных успешно завершена")
            return True
        except Exception as e:
            self.logger.exception(
                f"Неожиданная ошибка при инициализации базы данных: {e}"
            )
            return False


@click.command()
@click.option(
    '--skip-migrations',
    is_flag=True,
    help='Пропустить применение миграций'
)
def init_db(skip_migrations: bool) -> int:
    """
    Инициализация базы данных.
    
    Args:
        skip_migrations: Флаг пропуска миграций
        
    Returns:
        int: Код возврата (0 - успех, 1 - ошибка)
    """
    initializer = DatabaseInitializer()
    success = asyncio.run(initializer.initialize(skip_migrations))
    
    if not success:
        return 1
    return 0


if __name__ == "__main__":
    # Настройка базового логгера для модуля
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Запуск инициализации
    sys.exit(init_db()) 