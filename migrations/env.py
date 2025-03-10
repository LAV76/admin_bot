import os
import sys
import logging
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from sqlalchemy.engine import Connection
from alembic import context
from dotenv import load_dotenv

# Настройка логирования
logger = logging.getLogger("alembic.env")

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Загружаем переменные окружения
load_dotenv()

# Импортируем модели для автоматического обнаружения
from app.db.base import Base
from app.db.models.posts import Post
from models.users import User

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Настройка логирования
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Получаем URL для подключения
db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
logger.info(f"Using database URL: {db_url}")

# Настраиваем URL для подключения
config.set_main_option("sqlalchemy.url", db_url)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Запуск миграций в оффлайн режиме"""
    logger.info("Running offline migrations")
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Запуск миграций в онлайн режиме"""
    logger.info("Running online migrations")
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online() 