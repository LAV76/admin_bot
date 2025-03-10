"""
Скрипт для настройки и применения миграций в правильном порядке.

Этот скрипт:
1. Копирует файлы миграций в папку versions
2. Помечает миграции как выполненные в таблице alembic_version
"""

import os
import sys
import asyncio
import logging
import shutil
from pathlib import Path

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(str(Path(__file__).parent.parent))

# Импорт собственного модуля для пометки миграций
from scripts.mark_migration_as_applied import mark_migration_as_applied

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('setup_migrations')

# Путь к директории versions
VERSIONS_DIR = Path(__file__).parent.parent / "migrations" / "versions"

# Список файлов миграций и их ревизий
MIGRATIONS = [
    {
        "source": Path(__file__).parent.parent / "migrations" / "users_migration.py",
        "revision": "20250309001",
        "description": "create_users_table"
    },
    {
        "source": Path(__file__).parent.parent / "migrations" / "channels_migration.py",
        "revision": "20250309002",
        "description": "create_channels_table"
    },
    {
        "source": Path(__file__).parent.parent / "migrations" / "posts_migration.py",
        "revision": "20250309003",
        "description": "create_posts_table"
    }
]


async def copy_migration_files():
    """
    Копирует файлы миграций в папку versions
    """
    try:
        # Создаем директорию versions, если она не существует
        VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
        
        for migration in MIGRATIONS:
            source = migration["source"]
            revision = migration["revision"]
            description = migration["description"]
            
            # Формируем имя файла в формате Alembic
            target_filename = f"{revision}_{description}.py"
            target_path = VERSIONS_DIR / target_filename
            
            # Копируем файл
            if source.exists():
                logger.info(f"Копирование {source} в {target_path}")
                
                # Читаем содержимое файла и адаптируем его
                with open(source, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Записываем адаптированный файл в директорию versions
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"Файл {target_filename} успешно скопирован в {VERSIONS_DIR}")
            else:
                logger.error(f"Файл {source} не существует")
                return False
        
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при копировании файлов миграций: {e}")
        return False


async def mark_migrations_as_applied():
    """
    Помечает миграции как выполненные в таблице alembic_version
    """
    try:
        # Берем последнюю миграцию как текущую
        if MIGRATIONS:
            latest_migration = MIGRATIONS[-1]
            revision = latest_migration["revision"]
            description = latest_migration["description"]
            
            # Помечаем эту миграцию как выполненную
            success = await mark_migration_as_applied(revision, description)
            
            if success:
                logger.info(f"Миграция {revision} ({description}) помечена как выполненная")
            else:
                logger.error(f"Не удалось пометить миграцию {revision} как выполненную")
                return False
        
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при пометке миграций как выполненных: {e}")
        return False


async def main():
    """
    Основная функция для выполнения всего процесса
    """
    logger.info("Начало настройки миграций...")
    
    # Копируем файлы миграций
    success = await copy_migration_files()
    if not success:
        logger.error("Не удалось скопировать файлы миграций")
        return 1
    
    # Помечаем миграции как выполненные
    success = await mark_migrations_as_applied()
    if not success:
        logger.error("Не удалось пометить миграции как выполненные")
        return 1
    
    logger.info("Настройка миграций успешно завершена")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 