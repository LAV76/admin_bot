import asyncio
import os
import sys
import logging
from sqlalchemy import text
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(str(Path(__file__).parent.parent))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('migration_marker')

# Загрузка переменных окружения
load_dotenv()

# Получение параметров подключения к базе данных
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tgbot_admin")

async def mark_migration_as_applied(revision_id: str, description: str = "") -> bool:
    """
    Помечает миграцию как примененную в таблице alembic_version
    
    Args:
        revision_id: Идентификатор ревизии миграции
        description: Описание миграции (опционально)
        
    Returns:
        bool: True если успешно, False в случае ошибки
    """
    # Формирование DSN для подключения к PostgreSQL
    dsn = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    try:
        # Создаем асинхронный движок SQLAlchemy
        engine = create_async_engine(dsn)
        
        async with engine.begin() as conn:
            # Проверяем существование таблицы alembic_version
            result = await conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'alembic_version')"
            ))
            exists = result.scalar()
            
            if not exists:
                # Создаем таблицу alembic_version, если она не существует
                logger.info("Создание таблицы alembic_version...")
                await conn.execute(text("""
                    CREATE TABLE alembic_version (
                        version_num VARCHAR(32) NOT NULL,
                        PRIMARY KEY (version_num)
                    )
                """))
                logger.info("Таблица alembic_version успешно создана")
            
            # Проверяем, существует ли уже запись для данной ревизии
            result = await conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM alembic_version WHERE version_num = :revision_id)"
            ), {"revision_id": revision_id})
            exists = result.scalar()
            
            if exists:
                logger.info(f"Ревизия {revision_id} уже помечена как примененная")
                return True
            
            # Удаляем любые существующие записи (должна быть только одна текущая версия)
            await conn.execute(text("DELETE FROM alembic_version"))
            
            # Добавляем новую ревизию
            await conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision_id)"),
                {"revision_id": revision_id}
            )
            
            logger.info(f"Ревизия {revision_id} успешно помечена как примененная")
            
            # Логируем операцию, если есть описание
            if description:
                logger.info(f"Описание миграции: {description}")
                
            return True
            
    except Exception as e:
        logger.error(f"Ошибка при пометке миграции {revision_id} как примененной: {e}")
        return False
    finally:
        # Закрываем движок
        try:
            await engine.dispose()
        except:
            pass


async def main():
    """Основная функция для запуска из командной строки"""
    if len(sys.argv) < 2:
        logger.error("Не указан идентификатор ревизии")
        print(f"Использование: python -m scripts.{Path(__file__).stem} <revision_id> [description]")
        return 1
    
    revision_id = sys.argv[1]
    description = sys.argv[2] if len(sys.argv) > 2 else ""
    
    success = await mark_migration_as_applied(revision_id, description)
    return 0 if success else 1


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result) 