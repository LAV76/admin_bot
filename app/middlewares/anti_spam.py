from typing import Dict, Any, Callable, Awaitable, Optional, Union
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from aiogram.dispatcher.event.bases import CancelHandler
from aiogram.types.error_event import ErrorEvent

from app.core.logging import setup_logger


class AntiSpamMiddleware(BaseMiddleware):
    """
    Middleware для защиты от спама.
    Ограничивает количество запросов от пользователя в определенный промежуток времени.
    
    Attributes:
        rate_limit: Максимальное количество запросов в указанный период
        period: Период в секундах, за который считаются запросы
        user_requests: Словарь для хранения информации о запросах пользователей
        logger: Логгер для записи информации
        message_text: Текст сообщения при превышении лимита
    """
    
    def __init__(
        self, 
        rate_limit: int = 5, 
        period: int = 3,
        message_text: str = "Слишком много запросов. Пожалуйста, подождите немного."
    ):
        """
        Инициализация middleware для защиты от спама
        
        Args:
            rate_limit: Максимальное количество запросов в указанный период
            period: Период в секундах, за который считаются запросы
            message_text: Текст сообщения при превышении лимита
        """
        self.rate_limit = rate_limit
        self.period = period
        self.user_requests = defaultdict(list)
        self.logger = setup_logger("anti_spam_middleware")
        self.message_text = message_text
        
        # Запускаем задачу очистки старых записей
        asyncio.create_task(self._cleanup_old_records())
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery, ErrorEvent],
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработка события перед передачей его обработчику
        
        Args:
            handler: Обработчик события
            event: Событие (сообщение, callback query и т.д.)
            data: Дополнительные данные
            
        Returns:
            Any: Результат обработки события
            
        Raises:
            CancelHandler: Если превышен лимит запросов
        """
        # Получаем ID пользователя
        user_id = self._get_user_id(event)
        if not user_id:
            # Если не удалось получить ID пользователя, пропускаем проверку
            return await handler(event, data)
        
        # Проверяем, не превышен ли лимит запросов
        current_time = datetime.now()
        
        # Добавляем текущий запрос
        self.user_requests[user_id].append(current_time)
        
        # Удаляем устаревшие запросы для этого пользователя
        self._clean_old_requests(user_id, current_time)
        
        # Проверяем количество запросов за период
        request_count = len(self.user_requests[user_id])
        
        if request_count > self.rate_limit:
            self.logger.warning(
                f"Обнаружен спам от пользователя {user_id}: "
                f"{request_count} запросов за {self.period} секунд"
            )
            
            # Отправляем сообщение о превышении лимита
            await self._send_rate_limit_message(event)
            
            # Отменяем обработку события
            raise CancelHandler()
        
        # Если лимит не превышен, продолжаем обработку
        return await handler(event, data)
    
    def _get_user_id(self, event: Union[Message, CallbackQuery, ErrorEvent]) -> Optional[int]:
        """
        Извлекает ID пользователя из события
        
        Args:
            event: Событие (сообщение, callback query и т.д.)
            
        Returns:
            Optional[int]: ID пользователя или None, если не удалось получить
        """
        if isinstance(event, Message):
            return event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            return event.from_user.id if event.from_user else None
        elif hasattr(event, 'from_user') and event.from_user:
            return event.from_user.id
        
        return None
    
    def _clean_old_requests(self, user_id: int, current_time: datetime) -> None:
        """
        Удаляет устаревшие запросы для указанного пользователя
        
        Args:
            user_id: ID пользователя
            current_time: Текущее время
        """
        # Определяем время, ранее которого запросы считаются устаревшими
        threshold_time = current_time - timedelta(seconds=self.period)
        
        # Фильтруем запросы, оставляя только те, которые новее порогового времени
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id]
            if req_time >= threshold_time
        ]
        
        # Если у пользователя нет запросов, удаляем его из словаря
        if not self.user_requests[user_id]:
            del self.user_requests[user_id]
    
    async def _cleanup_old_records(self) -> None:
        """
        Периодически очищает устаревшие записи для всех пользователей
        """
        while True:
            try:
                await asyncio.sleep(self.period * 2)  # Очищаем в два раза реже, чем период
                
                current_time = datetime.now()
                users_to_check = list(self.user_requests.keys())
                
                for user_id in users_to_check:
                    self._clean_old_requests(user_id, current_time)
                    
                self.logger.debug(
                    f"Очистка устаревших записей завершена. "
                    f"Активных пользователей: {len(self.user_requests)}"
                )
            except Exception as e:
                self.logger.error(f"Ошибка при очистке устаревших записей: {e}")
    
    async def _send_rate_limit_message(self, event: Union[Message, CallbackQuery]) -> None:
        """
        Отправляет сообщение о превышении лимита запросов
        
        Args:
            event: Событие (сообщение или callback query)
        """
        try:
            if isinstance(event, Message):
                await event.answer(self.message_text)
            elif isinstance(event, CallbackQuery):
                await event.answer(self.message_text, show_alert=True)
        except Exception as e:
            self.logger.error(f"Ошибка при отправке сообщения о превышении лимита: {e}") 