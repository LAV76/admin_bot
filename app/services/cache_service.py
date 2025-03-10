"""
Сервис для кэширования часто запрашиваемых данных.
"""

import asyncio
from typing import Dict, Any, Optional, Callable, Awaitable, TypeVar, Generic, Union
from datetime import datetime, timedelta
import json
import pickle
import hashlib
import functools

from app.core.logging import setup_logger

# Тип для возвращаемого значения кэшируемой функции
T = TypeVar('T')


class CacheService:
    """
    Сервис для кэширования часто запрашиваемых данных.
    Реализует паттерн Singleton.
    
    Attributes:
        _instance: Единственный экземпляр класса
        _cache: Словарь для хранения кэшированных данных
        _ttl: Время жизни кэша в секундах
        logger: Логгер для записи информации
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """
        Создает единственный экземпляр класса (Singleton)
        """
        if cls._instance is None:
            cls._instance = super(CacheService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, ttl: int = 300):
        """
        Инициализация сервиса кэширования
        
        Args:
            ttl: Время жизни кэша в секундах (по умолчанию 5 минут)
        """
        if not self._initialized:
            self._cache = {}
            self._ttl = ttl
            self.logger = setup_logger("cache_service")
            self._initialized = True
            
            # Запускаем задачу очистки устаревшего кэша
            asyncio.create_task(self._cleanup_expired_cache())
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Получает данные из кэша по ключу
        
        Args:
            key: Ключ для поиска в кэше
            
        Returns:
            Optional[Any]: Данные из кэша или None, если ключ не найден или данные устарели
        """
        if key not in self._cache:
            return None
        
        cache_entry = self._cache[key]
        
        # Проверяем, не устарели ли данные
        if datetime.now() > cache_entry['expires_at']:
            # Удаляем устаревшие данные
            del self._cache[key]
            return None
        
        self.logger.debug(f"Получены данные из кэша по ключу: {key}")
        return cache_entry['data']
    
    async def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """
        Сохраняет данные в кэш
        
        Args:
            key: Ключ для сохранения в кэше
            data: Данные для сохранения
            ttl: Время жизни кэша в секундах (если None, используется значение по умолчанию)
        """
        # Если ttl не указан, используем значение по умолчанию
        ttl = ttl or self._ttl
        
        # Вычисляем время истечения кэша
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        # Сохраняем данные в кэш
        self._cache[key] = {
            'data': data,
            'expires_at': expires_at
        }
        
        self.logger.debug(f"Данные сохранены в кэш по ключу: {key} (TTL: {ttl}с)")
    
    async def delete(self, key: str) -> bool:
        """
        Удаляет данные из кэша по ключу
        
        Args:
            key: Ключ для удаления из кэша
            
        Returns:
            bool: True, если данные были удалены, False, если ключ не найден
        """
        if key in self._cache:
            del self._cache[key]
            self.logger.debug(f"Данные удалены из кэша по ключу: {key}")
            return True
        
        return False
    
    async def clear(self) -> None:
        """
        Очищает весь кэш
        """
        self._cache.clear()
        self.logger.debug("Кэш полностью очищен")
    
    async def _cleanup_expired_cache(self) -> None:
        """
        Периодически очищает устаревший кэш
        """
        while True:
            try:
                # Ждем половину времени жизни кэша перед очисткой
                await asyncio.sleep(self._ttl / 2)
                
                current_time = datetime.now()
                keys_to_delete = []
                
                # Находим все устаревшие ключи
                for key, cache_entry in self._cache.items():
                    if current_time > cache_entry['expires_at']:
                        keys_to_delete.append(key)
                
                # Удаляем устаревшие ключи
                for key in keys_to_delete:
                    del self._cache[key]
                
                if keys_to_delete:
                    self.logger.debug(f"Очищено {len(keys_to_delete)} устаревших записей кэша")
            except Exception as e:
                self.logger.error(f"Ошибка при очистке устаревшего кэша: {e}")
    
    def cached(self, ttl: Optional[int] = None):
        """
        Декоратор для кэширования результатов функций
        
        Args:
            ttl: Время жизни кэша в секундах (если None, используется значение по умолчанию)
            
        Returns:
            Callable: Декоратор для функции
        """
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Создаем ключ на основе имени функции и аргументов
                key_parts = [func.__name__]
                
                # Добавляем позиционные аргументы
                for arg in args:
                    key_parts.append(str(arg))
                
                # Добавляем именованные аргументы (отсортированные по имени)
                for k in sorted(kwargs.keys()):
                    key_parts.append(f"{k}={kwargs[k]}")
                
                # Создаем хеш из всех частей ключа
                key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
                
                # Пытаемся получить данные из кэша
                cached_data = await self.get(key)
                if cached_data is not None:
                    return cached_data
                
                # Если данных нет в кэше, вызываем оригинальную функцию
                result = await func(*args, **kwargs)
                
                # Сохраняем результат в кэш
                await self.set(key, result, ttl)
                
                return result
            
            return wrapper
        
        return decorator


# Создаем глобальный экземпляр сервиса кэширования
cache_service = CacheService()


def cached(ttl: Optional[int] = None):
    """
    Декоратор для кэширования результатов функций
    
    Args:
        ttl: Время жизни кэша в секундах (если None, используется значение по умолчанию)
        
    Returns:
        Callable: Декоратор для функции
    """
    return cache_service.cached(ttl) 