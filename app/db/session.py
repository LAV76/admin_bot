from typing import AsyncGenerator, Optional, Callable, Any, TypeVar, Generic
from contextlib import asynccontextmanager
import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logging import setup_logger

logger = logging.getLogger("db.session")

# Создаем асинхронный движок SQLAlchemy
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.db_echo if hasattr(settings, "db_echo") else False,
    pool_size=settings.db_pool_size if hasattr(settings, "db_pool_size") else 5,
    max_overflow=settings.db_max_overflow if hasattr(settings, "db_max_overflow") else 10,
    pool_timeout=settings.db_pool_timeout if hasattr(settings, "db_pool_timeout") else 30,
    pool_recycle=settings.db_pool_recycle if hasattr(settings, "db_pool_recycle") else 1800,
    pool_pre_ping=True
)

# Создаем фабрику сессий
async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

# Экспортируем необходимые объекты для использования в других модулях
__all__ = ["get_session", "UnitOfWork", "async_session_maker", "unit_of_work"]

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный контекстный менеджер для работы с сессией базы данных
    
    Yields:
        AsyncSession: Асинхронная сессия SQLAlchemy
    """
    session = async_session_maker()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Ошибка сессии БД: {e}", exc_info=True)
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Неожиданная ошибка при работе с БД: {e}", exc_info=True)
        raise
    finally:
        await session.close()
        logger.debug("Сессия БД закрыта")


# Создаем тип для репозитория
T = TypeVar('T')

class UnitOfWork:
    """
    Класс для управления транзакциями с базой данных.
    Реализует паттерн Unit of Work.
    
    Attributes:
        _session_factory: Фабрика для создания сессий БД
        _session: Текущая сессия БД
        _repositories: Словарь с репозиториями
    """
    
    def __init__(self):
        """
        Инициализирует Unit of Work
        """
        self._session_factory = async_session_maker
        self._session: Optional[AsyncSession] = None
        self._repositories = {}
        self.logger = setup_logger("unit_of_work")
    
    async def __aenter__(self) -> 'UnitOfWork':
        """
        Входит в контекст Unit of Work, создает сессию БД
        
        Returns:
            UnitOfWork: Экземпляр Unit of Work
        """
        self._session = self._session_factory()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Выходит из контекста Unit of Work, завершает транзакцию и закрывает сессию
        
        Args:
            exc_type: Тип исключения, если оно возникло
            exc_val: Значение исключения, если оно возникло
            exc_tb: Трассировка исключения, если оно возникло
        """
        if exc_type is not None:
            # Если произошла ошибка, откатываем транзакцию
            await self._session.rollback()
            self.logger.error(f"Транзакция откачена из-за ошибки: {exc_val}")
        else:
            # Если ошибок не было, фиксируем транзакцию
            await self._session.commit()
            self.logger.debug("Транзакция успешно зафиксирована")
        
        # В любом случае закрываем сессию
        await self._session.close()
        self._session = None
        self.logger.debug("Сессия БД закрыта")
    
    async def commit(self) -> None:
        """
        Фиксирует текущую транзакцию
        """
        if self._session is not None:
            await self._session.commit()
            self.logger.debug("Транзакция зафиксирована")
    
    async def rollback(self) -> None:
        """
        Откатывает текущую транзакцию
        """
        if self._session is not None:
            await self._session.rollback()
            self.logger.debug("Транзакция откачена")
    
    def get_repository(self, repository_class: Callable[[AsyncSession], T]) -> T:
        """
        Получает репозиторий по его классу, создавая его при необходимости
        
        Args:
            repository_class: Класс репозитория
            
        Returns:
            T: Экземпляр репозитория
        """
        if self._session is None:
            raise ValueError("Сессия БД не создана. Используйте контекстный менеджер.")
        
        # Получаем имя класса репозитория
        repository_name = repository_class.__name__
        
        # Если репозиторий уже создан, возвращаем его
        if repository_name in self._repositories:
            return self._repositories[repository_name]
        
        # Создаем новый экземпляр репозитория
        repository = repository_class(self._session)
        self._repositories[repository_name] = repository
        
        return repository
    
    @property
    def session(self) -> AsyncSession:
        """
        Возвращает текущую сессию БД
        
        Returns:
            AsyncSession: Текущая сессия БД
        """
        if self._session is None:
            raise ValueError("Сессия БД не создана. Используйте контекстный менеджер.")
        return self._session


# Создаем глобальный экземпляр UnitOfWork для использования в приложении
unit_of_work = UnitOfWork() 