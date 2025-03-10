import asyncio
import sys
import logging
import signal
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from app.db.engine import init_db, close_db
from handlers import register_all_handlers
from app.middlewares import setup_middlewares
from utils.logger import setup_logger
from utils.database_initializer import initialize_database
from utils.migration_manager import MigrationManager
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from app.core.config import settings
from aiogram.types import ChatMemberAdministrator

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logger = setup_logger()

# Глобальные переменные для отслеживания задач
background_tasks = set()

class BotApplication:
    """Класс приложения бота"""
    
    def __init__(self):
        """Инициализация приложения"""
        self.bot_token = os.getenv("API_TOKEN")
        if not self.bot_token:
            logger.error("Не указан токен бота в переменных окружения")
            sys.exit(1)
            
        # Инициализация бота и диспетчера
        self.bot = Bot(token=self.bot_token)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        
        # Регистрация обработчиков сигналов для корректного завершения
        self._handle_signal()
        
        # Регистрация обработчиков
        register_all_handlers(self.dp)
        
        # Регистрация middleware
        setup_middlewares(self.dp)
        
        # Зарегистрированные задачи в фоне
        self.background_tasks = set()
        
        logger.info("Бот инициализирован")
        
    async def check_channel_access(self) -> bool:
        """
        Проверка доступа бота к каналу из .env файла
        
        Returns:
            bool: True, если бот имеет доступ к каналу и права администратора
        """
        try:
            logger.info("Проверка доступа к каналу...")
            
            # Проверяем, указан ли ID канала в настройках
            if settings.channel_id_as_int is None:
                logger.warning("ID канала не указан в настройках (.env файл, CHANNEL_ID)")
                return False
                
            channel_id = settings.channel_id_as_int
            
            try:
                # Получаем информацию о канале
                chat = await self.bot.get_chat(channel_id)
                logger.info(f"Канал найден: {chat.title} (ID: {chat.id})")
                
                # Проверяем права бота в канале
                bot_member = await self.bot.get_chat_member(channel_id, self.bot.id)
                
                is_admin = False
                if isinstance(bot_member, ChatMemberAdministrator):
                    is_admin = True
                    admin_rights = []
                    
                    if bot_member.can_post_messages:
                        admin_rights.append("публикация сообщений")
                    if bot_member.can_edit_messages:
                        admin_rights.append("редактирование сообщений")
                    if bot_member.can_delete_messages:
                        admin_rights.append("удаление сообщений")
                    if bot_member.can_restrict_members:
                        admin_rights.append("ограничение пользователей")
                    
                    rights_str = ", ".join(admin_rights)
                    logger.info(f"Бот имеет права администратора в канале ({rights_str})")
                else:
                    logger.warning(f"Бот не имеет прав администратора в канале {chat.title} (ID: {chat.id})")
                
                return is_admin
                
            except Exception as e:
                logger.error(f"Ошибка при проверке доступа к каналу {channel_id}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при проверке доступа к каналу: {e}")
            return False

    async def init_services(self) -> bool:
        """Инициализация сервисов бота."""
        try:
            logger.info("Инициализация базы данных...")
            # Сначала инициализируем подключение к БД и создаем базу, если её нет
            db_initialized = await init_db()
            if not db_initialized:
                logger.error("Не удалось инициализировать подключение к базе данных")
                return False
            logger.info("Подключение к базе данных успешно инициализировано")
            
            # Затем инициализируем саму структуру базы данных (таблицы)
            tables_initialized = await initialize_database()
            if not tables_initialized:
                logger.error("Не удалось инициализировать таблицы базы данных")
                return False
            logger.info("Инициализация таблиц базы данных успешно завершена")
            
            # Проверяем доступ к каналу публикации
            has_channel_access = await self.check_channel_access()
            if has_channel_access:
                logger.info("Доступ к каналу публикации успешно проверен")
            else:
                logger.warning("Бот не имеет доступа к каналу публикации или канал не настроен. "
                              "Публикация постов в канал может быть недоступна.")
            
            # Инициализируем сервис управления доступом
            try:
                from app.services.access_control import get_access_control
                access_control = await get_access_control()
                logger.info("Сервис управления доступом успешно инициализирован")
            except Exception as e:
                logger.error(f"Ошибка при инициализации сервиса управления доступом: {e}")
                # Продолжаем работу, так как инициализация может происходить во время первого использования
            
            # Явно добавляем роль администратора после создания таблиц
            try:
                from scripts.admin_role_manager import add_admin_role
                admin_role_added = await add_admin_role()
                if admin_role_added:
                    logger.info("Роль администратора успешно добавлена/проверена")
                else:
                    logger.warning("Не удалось добавить роль администратора, но продолжаем работу")
            except Exception as e:
                logger.error(f"Ошибка при добавлении роли администратора: {e}")
                # Продолжаем работу даже если не удалось добавить роль администратора

            logger.info("Применение миграций...")
            try:
                # Получаем текущую версию миграций
                version = await self._get_current_migration_version()
                if version:
                    logger.info(f"Текущая версия миграций: {version}")
                    # Проверяем, является ли текущая версия последней
                    is_head = await self._is_migration_head(version)
                    if is_head:
                        logger.info("Миграции уже применены до последней версии")
                    else:
                        # Применяем миграции
                        await self._apply_migrations()
                else:
                    # Если не удалось определить текущую версию
                    logger.warning("Не удалось определить текущую версию миграций")
                    # Запускаем скрипт исправления миграций
                    await self._fix_migrations()
            except Exception as e:
                logger.error(f"Ошибка при применении миграций: {e}")
                # Продолжаем работу бота даже при ошибке миграций
            
            # Запускаем планировщик уведомлений в фоновом режиме
            try:
                from utils.notifications import start_notification_scheduler
                # Запускаем планировщик в фоновом режиме
                asyncio.create_task(start_notification_scheduler(self.bot))
                logger.info("Планировщик уведомлений запущен")
            except Exception as e:
                logger.error(f"Ошибка при запуске планировщика уведомлений: {e}")
                # Продолжаем работу бота даже при ошибке планировщика

            return True
        except Exception as e:
            logger.error(f"Ошибка при инициализации сервисов: {e}")
            return False
            
    async def _get_current_migration_version(self) -> Optional[str]:
        """Получение текущей версии миграций"""
        try:
            migration_manager = MigrationManager()
            return await migration_manager.get_current_revision()
        except Exception as e:
            logger.error(f"Ошибка при получении текущей версии миграций: {e}")
            return None
            
    async def _is_migration_head(self, version: str) -> bool:
        """Проверка, является ли текущая версия миграций последней"""
        try:
            migration_manager = MigrationManager()
            return await migration_manager._is_head(version)
        except Exception as e:
            logger.error(f"Ошибка при проверке версии миграций: {e}")
            return False
            
    async def _apply_migrations(self) -> bool:
        """Применение миграций"""
        try:
            migration_manager = MigrationManager()
            result = await migration_manager.upgrade()
            if result:
                logger.info("Миграции успешно применены")
            else:
                logger.error("Не удалось применить миграции")
            return result
        except Exception as e:
            logger.error(f"Ошибка при применении миграций: {e}")
            return False
            
    async def _fix_migrations(self) -> bool:
        """Исправление миграций"""
        try:
            # Проверяем наличие таблицы alembic_version и создаем ее при необходимости
            migration_manager = MigrationManager()
            result = await migration_manager.check_migrations()
            if result:
                logger.info("Таблица миграций проверена и исправлена")
            else:
                logger.error("Не удалось исправить таблицу миграций")
            return result
        except Exception as e:
            logger.error(f"Ошибка при исправлении миграций: {e}")
            return False
            
    def _handle_signal(self, signals: List[signal.Signals] = None):
        """
        Устанавливает обработчики сигналов системы.
        
        Args:
            signals: Список сигналов для обработки
        """
        if signals is None:
            # По умолчанию обрабатываем SIGINT и SIGTERM
            signals = [signal.SIGINT, signal.SIGTERM]
            
        async def shutdown_callback(signal_type):
            """
            Callback для корректного завершения работы при получении сигнала.
            
            Args:
                signal_type: Тип сигнала
            """
            logger.info(f"Получен сигнал {signal_type}, начинаем завершение работы...")
            await self.shutdown()
            
            # Используем sys.exit() только если есть loop и он запущен
            if asyncio.get_event_loop().is_running():
                # Не используем sys.exit внутри корутины, чтобы избежать рекурсивных вызовов
                # при обработке исключения SystemExit
                loop = asyncio.get_event_loop()
                loop.stop()
            
        # Регистрируем обработчики сигналов
        for sig in signals:
            # Добавляем обработчик сигнала в цикл событий
            try:
                if sys.platform == 'win32':
                    # На Windows добавляем обработчик сигнала немного по-другому
                    asyncio.get_event_loop().add_signal_handler(
                        sig.value, lambda s=sig.value: asyncio.create_task(shutdown_callback(s))
                    )
                else:
                    # На Unix системах
                    asyncio.get_event_loop().add_signal_handler(
                        sig, lambda s=sig: asyncio.create_task(shutdown_callback(s))
                    )
                logger.debug(f"Обработчик сигнала {sig} зарегистрирован")
            except NotImplementedError:
                # Если платформа не поддерживает add_signal_handler (например, Windows)
                logger.warning(f"Не удалось зарегистрировать обработчик сигнала {sig} через add_signal_handler")
                
                # Используем стандартный signal.signal
                signal.signal(sig, lambda s, f: asyncio.create_task(shutdown_callback(s)))
                logger.debug(f"Обработчик сигнала {sig} зарегистрирован через signal.signal")

    async def start(self) -> int:
        """
        Запуск бота
        
        Returns:
            int: Код возврата (0 - успешно, 1 - ошибка)
        """
        try:
            logger.info("Запуск приложения...")
            
            # Инициализация сервисов
            services_initialized = await self.init_services()
            if not services_initialized:
                logger.error("Ошибка при инициализации сервисов")
                return 1
                
            # Запуск бота
            logger.info("Запуск бота...")
            await self.dp.start_polling(self.bot)
            
            return 0
            
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)
            return 1
        finally:
            await self.shutdown()
            
    async def shutdown(self):
        """Корректное завершение работы приложения"""
        logger.info("Завершение работы бота...")
        
        # Останавливаем поллинг
        try:
            # Используем await вместо прямого вызова
            await self.dp.stop_polling()
            logger.info("Остановлен поллинг")
        except Exception as e:
            logger.error(f"Ошибка при остановке поллинга: {e}")
        
        # Закрываем соединение с базой данных
        try:
            from app.db.engine import close_db
            success = await close_db()
            if success:
                logger.info("Соединение с базой данных закрыто")
            else:
                logger.warning("Проблемы при закрытии соединения с базой данных")
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединения с базой данных: {e}")
            
        # Закрываем все ожидающие задачи (хендлеры, middleware)
        try:
            # Получаем все активные задачи, кроме текущей
            tasks = [t for t in asyncio.all_tasks() 
                    if t is not asyncio.current_task() and not t.done()]
            
            if tasks:
                logger.debug(f"Отменяем {len(tasks)} задач...")
                
                # Отменяем задачи и ждем их завершения с таймаутом
                for task in tasks:
                    task.cancel()
                
                # Ждем завершения задач
                done, pending = await asyncio.wait(tasks, timeout=5)
                
                if pending:
                    logger.warning(f"{len(pending)} задач не удалось завершить корректно")
        except Exception as e:
            logger.error(f"Ошибка при завершении работы: {e}")
            
        # Дополнительные действия при завершении работы
        try:
            await self._on_shutdown()
        except Exception as e:
            logger.critical(f"Критическая ошибка: {e}", exc_info=True)

    async def _on_shutdown(self):
        """
        Дополнительные действия при завершении работы бота.
        Этот метод вызывается в конце процесса shutdown.
        """
        # Здесь можно добавить дополнительные действия при завершении работы
        logger.info("Бот успешно завершил работу")

async def main() -> int:
    """
    Основная функция запуска бота
    
    Returns:
        int: Код возврата (0 - успешно, 1 - ошибка)
    """
    app = BotApplication()
    return await app.start()

if __name__ == "__main__":
    try:
        # Запуск бота
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Программа остановлена пользователем")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)




