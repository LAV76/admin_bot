"""
Модуль с middleware для защиты от спама (троттлинг)
"""

import asyncio
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.event.handler import HandlerObject
from aiogram.dispatcher.flags import get_flag
from aiogram.exceptions import TelegramBadRequest
from cachetools import TTLCache

from app.core.logging import setup_logger

# Настройка логирования
logger = setup_logger("middleware.throttling")

# Кеш для хранения данных о троттлинге
throttle_cache = TTLCache(maxsize=10000, ttl=3600)


def rate_limit(limit: int, key=None):
    """
    Декоратор для ограничения частоты вызовов хендлера.
    
    Args:
        limit: Лимит в секундах между вызовами
        key: Ключ для идентификации (по умолчанию None)
    """
    def decorator(func):
        setattr(func, 'throttling_rate_limit', limit)
        if key:
            setattr(func, 'throttling_key', key)
        return func
    return decorator


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware для ограничения частоты запросов к боту (антиспам)
    """
    
    def __init__(self, default_rate_limit: float = 1.0, prefix: str = "antiflood"):
        """
        Инициализация middleware
        
        Args:
            default_rate_limit: Лимит по умолчанию в секундах
            prefix: Префикс для ключей хранилища
        """
        self.default_rate_limit = default_rate_limit
        self.prefix = prefix
        
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Any],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработка события перед вызовом хендлера
        
        Args:
            handler: Хендлер для обработки события
            event: Событие (сообщение или callback)
            data: Данные события
            
        Returns:
            Any: Результат выполнения хендлера
        """
        # Получаем текущий хендлер
        handler_obj = data.get('handler', None)
        
        # Если хендлер не найден, пропускаем
        if not isinstance(handler_obj, HandlerObject):
            return await handler(event, data)
        
        # Получаем лимит из флагов или атрибутов хендлера
        limit = get_flag(data, 'throttling_rate_limit')
        if not limit:
            limit = getattr(handler_obj.callback, 'throttling_rate_limit', self.default_rate_limit)
            
        # Получаем ключ из флагов или атрибутов хендлера
        key = get_flag(data, 'throttling_key')
        if not key:
            key = getattr(handler_obj.callback, 'throttling_key', f"{self.prefix}_{handler_obj.callback.__name__}")
            
        # Если пользователь авторизован, добавляем его ID к ключу
        if hasattr(event, 'from_user') and event.from_user:
            key = f"{key}_{event.from_user.id}"
        
        # Проверяем, не превышен ли лимит
        if not await self._throttle(key, limit):
            # Уведомляем пользователя о лимите
            message_text = f"⚠️ Слишком много запросов! Пожалуйста, подождите {limit} секунд."
            try:
                if isinstance(event, Message):
                    await event.answer(message_text)
                elif isinstance(event, CallbackQuery):
                    await event.answer(message_text, show_alert=True)
            except TelegramBadRequest:
                logger.warning(f"Не удалось отправить сообщение о троттлинге для {key}")
            
            # Логируем превышение лимита
            logger.info(f"Троттлинг для ключа {key} с лимитом {limit} секунд")
            return None
            
        # Если лимит не превышен, выполняем хендлер
        return await handler(event, data)
    
    async def _throttle(self, key: str, limit: float) -> bool:
        """
        Проверяет, не превышен ли лимит для данного ключа
        
        Args:
            key: Ключ для проверки
            limit: Лимит в секундах
            
        Returns:
            bool: True, если лимит не превышен, False в противном случае
        """
        now = datetime.now()
        
        # Получаем время последнего запроса
        if key in throttle_cache:
            last_time = throttle_cache[key]
            if (now - last_time).total_seconds() < limit:
                return False
        
        # Обновляем время последнего запроса
        throttle_cache[key] = now
        return True 