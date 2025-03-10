import os
import sys
import shutil
from alembic import command
from alembic.config import Config
import logging
from pathlib import Path
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_migrations():
    """Инициализация и создание первой миграции"""
    try:
        # Загружаем переменные окружения
        load_dotenv()
        
        # Получаем путь к корневой директории проекта
        base_path = Path(__file__).parent.parent
        migrations_path = base_path / "migrations"
        versions_path = migrations_path / "versions"
        
        # Пересоздаем директорию versions
        if versions_path.exists():
            shutil.rmtree(versions_path)
        versions_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Создана директория для версий миграций: {versions_path}")
        
        # Проверяем наличие шаблона миграций
        template_file = migrations_path / "script.py.mako"
        if not template_file.exists():
            logger.error(f"Файл шаблона миграций не найден: {template_file}")
            sys.exit(1)
            
        # Проверяем наличие env.py
        env_file = migrations_path / "env.py"
        if not env_file.exists():
            logger.error(f"Файл окружения миграций не найден: {env_file}")
            sys.exit(1)
            
        # Инициализируем конфигурацию Alembic
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("script_location", str(migrations_path))
        
        # Устанавливаем параметры подключения из переменных окружения
        alembic_cfg.set_section_option(alembic_cfg.config_ini_section, "DB_USER", os.getenv("DB_USER", "postgres"))
        alembic_cfg.set_section_option(alembic_cfg.config_ini_section, "DB_PASS", os.getenv("DB_PASS", ""))
        alembic_cfg.set_section_option(alembic_cfg.config_ini_section, "DB_HOST", os.getenv("DB_HOST", "localhost"))
        alembic_cfg.set_section_option(alembic_cfg.config_ini_section, "DB_PORT", os.getenv("DB_PORT", "5432"))
        alembic_cfg.set_section_option(alembic_cfg.config_ini_section, "DB_NAME", os.getenv("DB_NAME", "tgbot_admin"))
        
        # Создаем новую миграцию
        logger.info("Создание новой миграции...")
        command.revision(
            alembic_cfg,
            autogenerate=True,
            message="Create users table",
            sql=False
        )
        logger.info("Миграция успешно создана")
        
        # Проверяем, что файл миграции создан
        migration_files = list(versions_path.glob("*.py"))
        if not migration_files:
            logger.error("Файл миграции не был создан")
            sys.exit(1)
        logger.info(f"Создан файл миграции: {migration_files[0].name}")
        
        # Применяем миграцию
        logger.info("Применение миграции...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Миграция успешно применена")
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации миграций: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    init_migrations() 