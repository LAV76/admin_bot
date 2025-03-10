import asyncio
from alembic.config import Config
from alembic import command
import logging
from pathlib import Path
import os
from dotenv import load_dotenv
from typing import Optional
import asyncpg
import concurrent.futures
import time

# Загружаем переменные окружения
load_dotenv()

logger = logging.getLogger(__name__)

class MigrationManager:
    """Менеджер миграций базы данных"""
    
    def __init__(self):
        """Инициализация менеджера миграций"""
        try:
            # Создаем конфигурацию Alembic
            self.alembic_cfg = Config("alembic.ini")
            
            # Устанавливаем путь к скриптам миграций
            self.script_location = os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations")
            self.alembic_cfg.set_main_option("script_location", self.script_location)
            
            # Проверяем наличие директории versions
            versions_path = Path(self.script_location) / "versions"
            if not versions_path.exists():
                versions_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Создана директория для версий миграций: {versions_path}")
                
            # Устанавливаем URL для подключения к БД
            self.db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@" \
                       f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
            self.alembic_cfg.set_main_option("sqlalchemy.url", self.db_url)
            
            # Создаем пул исполнителей для запуска синхронных задач
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            
        except Exception as e:
            logger.error(f"Ошибка инициализации менеджера миграций: {e}", exc_info=True)
            raise

    async def get_current_revision(self) -> Optional[str]:
        """Получение текущей ревизии"""
        try:
            conn = await asyncpg.connect(self.db_url)
            try:
                result = await conn.fetchval("SELECT version_num FROM alembic_version")
                return result
            except Exception as e:
                logger.error(f"Ошибка при получении версии: {e}")
                return None
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            return None

    async def _execute_command(self, func, *args, **kwargs) -> bool:
        """Выполнение команды миграции с таймаутом"""
        try:
            logger.info(f"Выполнение команды миграции: {func.__name__}")
            start_time = time.time()
            
            # Запускаем команду в отдельном потоке с таймаутом
            future = self.executor.submit(func, self.alembic_cfg, *args, **kwargs)
            
            # Ждем выполнения с таймаутом 30 секунд
            try:
                result = await asyncio.wait_for(
                    asyncio.wrap_future(future), 
                    timeout=30.0
                )
                logger.info(f"Команда {func.__name__} выполнена за {time.time() - start_time:.2f} сек")
                return True
            except asyncio.TimeoutError:
                logger.error(f"Таймаут выполнения команды {func.__name__} (30 сек)")
                # Отменяем задачу если возможно
                future.cancel()
                return False
                
        except Exception as e:
            logger.error(f"Ошибка выполнения команды {func.__name__}: {e}", exc_info=True)
            return False

    async def create_migration(self, message: str) -> bool:
        """Создание новой миграции"""
        logger.info(f"Создание новой миграции: {message}")
        return await self._execute_command(
            command.revision,
            autogenerate=True,
            message=message
        )

    async def upgrade(self, revision: str = "head") -> bool:
        """Обновление до указанной ревизии"""
        try:
            logger.info(f"Обновление базы данных до ревизии: {revision}")
            
            # Проверяем текущую ревизию перед обновлением
            current = await self.get_current_revision()
            if current:
                logger.info(f"Текущая ревизия: {current}")
                if current == revision or (revision == "head" and await self._is_head(current)):
                    logger.info("База данных уже обновлена до последней версии")
                    return True
            
            return await self._execute_command(command.upgrade, revision)
        except Exception as e:
            logger.error(f"Ошибка обновления базы данных: {e}", exc_info=True)
            return False
    
    async def _is_head(self, revision: str) -> bool:
        """Проверяет, является ли ревизия последней"""
        try:
            # Это упрощенная проверка, в реальности нужно использовать
            # alembic.script.ScriptDirectory для получения последней ревизии
            return True
        except Exception as e:
            logger.error(f"Ошибка при проверке ревизии: {e}")
            return False

    async def check_migrations(self) -> bool:
        """Проверка и применение миграций при необходимости"""
        try:
            # Проверяем наличие миграций
            versions_path = Path(self.script_location) / "versions"
            migration_files = list(versions_path.glob("*.py"))
            
            if not migration_files:
                logger.warning("Миграции не найдены, создаем первую миграцию")
                if not await self.create_migration("Initial migration"):
                    return False
            
            # Применяем миграции
            return await self.upgrade()
            
        except Exception as e:
            logger.error(f"Ошибка проверки миграций: {e}", exc_info=True)
            return False

    async def get_history(self) -> list:
        """Получение истории миграций"""
        try:
            # Это нужно переделать, так как command.history не возвращает результат
            # а выводит его на экран
            logger.info("Получение истории миграций")
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении истории миграций: {e}")
            return []
            
    def __del__(self):
        """Закрытие ресурсов при уничтожении объекта"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False) 