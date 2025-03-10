"""
Модуль для внедрения зависимостей (Dependency Injection).
"""

from typing import Dict, Any, Optional, Callable, Awaitable, TypeVar, Generic, Union, Type
import inspect
from functools import wraps

from app.core.logging import setup_logger
from app.db.session import get_session


class DependencyProvider:
    """
    Провайдер зависимостей для внедрения сервисов и репозиториев.
    Реализует паттерн Singleton.
    
    Attributes:
        _instance: Единственный экземпляр класса
        _services: Словарь для хранения сервисов
        _repositories: Словарь для хранения репозиториев
        _session_factory: Фабрика для создания сессий базы данных
        logger: Логгер для записи информации
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """
        Создает единственный экземпляр класса (Singleton)
        """
        if cls._instance is None:
            cls._instance = super(DependencyProvider, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        Инициализация провайдера зависимостей
        """
        if not getattr(self, '_initialized', False):
            self._services = {}
            self._repositories = {}
            self._session_factory = get_session
            self.logger = setup_logger("dependency_provider")
            self._initialized = True
    
    async def get_service(self, service_class: Type) -> Any:
        """
        Получает экземпляр сервиса по его классу
        
        Args:
            service_class: Класс сервиса
            
        Returns:
            Any: Экземпляр сервиса
        """
        service_name = service_class.__name__
        
        # Если сервис уже создан, возвращаем его
        if service_name in self._services:
            return self._services[service_name]
        
        # Создаем новый экземпляр сервиса
        service = service_class()
        self._services[service_name] = service
        
        self.logger.debug(f"Создан новый экземпляр сервиса: {service_name}")
        return service
    
    async def get_repository(self, repository_class: Type) -> Any:
        """
        Получает экземпляр репозитория по его классу
        
        Args:
            repository_class: Класс репозитория
            
        Returns:
            Any: Экземпляр репозитория
        """
        # Для репозиториев всегда создаем новый экземпляр с новой сессией
        async with self._session_factory() as session:
            repository = repository_class(session)
            self.logger.debug(f"Создан новый экземпляр репозитория: {repository_class.__name__}")
            return repository
    
    async def get_post_service(self) -> Any:
        """
        Получает экземпляр сервиса постов
        
        Returns:
            PostService: Экземпляр сервиса постов
        """
        # Импортируем сервис внутри метода для избежания циклических импортов
        from app.services.post_service import PostService
        return await self.get_service(PostService)
    
    async def get_channel_service(self) -> Any:
        """
        Получает экземпляр сервиса каналов
        
        Returns:
            ChannelService: Экземпляр сервиса каналов
        """
        # Импортируем сервис внутри метода для избежания циклических импортов
        from app.services.channel_service import ChannelService
        return await self.get_service(ChannelService)
    
    async def get_role_service(self) -> Any:
        """
        Получает экземпляр сервиса ролей
        
        Returns:
            RoleService: Экземпляр сервиса ролей
        """
        # Импортируем сервис внутри метода для избежания циклических импортов
        from app.services.role_service import RoleService
        return await self.get_service(RoleService)
    
    async def get_access_control_service(self) -> Any:
        """
        Получает экземпляр сервиса контроля доступа
        
        Returns:
            AccessControlService: Экземпляр сервиса контроля доступа
        """
        # Импортируем сервис внутри метода для избежания циклических импортов
        from app.services.access_control import AccessControlService
        return await self.get_service(AccessControlService)
    
    async def get_cache_service(self) -> Any:
        """
        Получает экземпляр сервиса кэширования
        
        Returns:
            CacheService: Экземпляр сервиса кэширования
        """
        # Импортируем сервис внутри метода для избежания циклических импортов
        from app.services.cache_service import CacheService
        return await self.get_service(CacheService)
    
    async def get_post_repository(self) -> Any:
        """
        Получает экземпляр репозитория постов
        
        Returns:
            PostRepository: Экземпляр репозитория постов
        """
        # Импортируем репозиторий внутри метода для избежания циклических импортов
        from app.db.repositories.post_repository import PostRepository
        return await self.get_repository(PostRepository)
    
    async def get_user_repository(self) -> Any:
        """
        Получает экземпляр репозитория пользователей
        
        Returns:
            UserRepository: Экземпляр репозитория пользователей
        """
        # Импортируем репозиторий внутри метода для избежания циклических импортов
        from app.db.repositories.user_repository import UserRepository
        return await self.get_repository(UserRepository)


# Создаем глобальный экземпляр провайдера зависимостей
dependency_provider = DependencyProvider()


def inject(
    post_service: bool = False,
    channel_service: bool = False,
    role_service: bool = False,
    access_control_service: bool = False,
    cache_service: bool = False,
    post_repository: bool = False,
    user_repository: bool = False
):
    """
    Декоратор для внедрения зависимостей в функцию
    
    Args:
        post_service: Внедрять ли сервис постов
        channel_service: Внедрять ли сервис каналов
        role_service: Внедрять ли сервис ролей
        access_control_service: Внедрять ли сервис контроля доступа
        cache_service: Внедрять ли сервис кэширования
        post_repository: Внедрять ли репозиторий постов
        user_repository: Внедрять ли репозиторий пользователей
        
    Returns:
        Callable: Декоратор для функции
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Внедряем зависимости в kwargs
            if post_service:
                kwargs['post_service'] = await dependency_provider.get_post_service()
            if channel_service:
                kwargs['channel_service'] = await dependency_provider.get_channel_service()
            if role_service:
                kwargs['role_service'] = await dependency_provider.get_role_service()
            if access_control_service:
                kwargs['access_control_service'] = await dependency_provider.get_access_control_service()
            if cache_service:
                kwargs['cache_service'] = await dependency_provider.get_cache_service()
            if post_repository:
                kwargs['post_repository'] = await dependency_provider.get_post_repository()
            if user_repository:
                kwargs['user_repository'] = await dependency_provider.get_user_repository()
            
            # Вызываем оригинальную функцию с внедренными зависимостями
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator 