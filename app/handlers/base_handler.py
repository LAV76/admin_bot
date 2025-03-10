"""
Базовый класс для обработчиков команд бота.
"""

from typing import Optional, Dict, Any, List, Union, Callable
from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.core.logging import setup_logger


class BaseHandler:
    """
    Базовый класс для обработчиков команд бота.
    Предоставляет общую функциональность для всех обработчиков.
    
    Attributes:
        router: Роутер для регистрации обработчиков
        logger: Логгер для записи информации
    """
    
    def __init__(self, router_name: str = "base_handler"):
        """
        Инициализация базового обработчика
        
        Args:
            router_name: Имя роутера для логирования
        """
        self.router = Router()
        self.logger = setup_logger(router_name)
    
    async def handle_error(
        self, 
        update: Union[Message, CallbackQuery], 
        error: Exception,
        error_message: str = "Произошла ошибка при обработке запроса."
    ) -> None:
        """
        Обрабатывает ошибку, возникшую при выполнении команды
        
        Args:
            update: Объект сообщения или callback query
            error: Объект исключения
            error_message: Сообщение об ошибке для пользователя
        """
        # Логируем ошибку
        self.logger.error(
            f"Ошибка при обработке {update.__class__.__name__}: {error}",
            exc_info=True
        )
        
        # Отправляем сообщение пользователю
        try:
            if isinstance(update, Message):
                await update.answer(error_message)
            elif isinstance(update, CallbackQuery):
                await update.answer(error_message, show_alert=True)
        except Exception as e:
            self.logger.error(f"Не удалось отправить сообщение об ошибке: {e}")
    
    async def send_message(
        self, 
        chat_id: int, 
        text: str, 
        bot: Bot,
        **kwargs
    ) -> Optional[Message]:
        """
        Отправляет сообщение пользователю с обработкой ошибок
        
        Args:
            chat_id: ID чата
            text: Текст сообщения
            bot: Экземпляр бота
            **kwargs: Дополнительные параметры для отправки сообщения
            
        Returns:
            Optional[Message]: Отправленное сообщение или None в случае ошибки
        """
        try:
            return await bot.send_message(chat_id=chat_id, text=text, **kwargs)
        except Exception as e:
            self.logger.error(f"Ошибка при отправке сообщения в чат {chat_id}: {e}")
            return None
    
    async def edit_message(
        self, 
        chat_id: int, 
        message_id: int, 
        text: str, 
        bot: Bot,
        **kwargs
    ) -> bool:
        """
        Редактирует сообщение с обработкой ошибок
        
        Args:
            chat_id: ID чата
            message_id: ID сообщения
            text: Новый текст сообщения
            bot: Экземпляр бота
            **kwargs: Дополнительные параметры для редактирования сообщения
            
        Returns:
            bool: True, если сообщение успешно отредактировано
        """
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                **kwargs
            )
            return True
        except Exception as e:
            self.logger.error(
                f"Ошибка при редактировании сообщения {message_id} "
                f"в чате {chat_id}: {e}"
            )
            return False
    
    async def delete_message(
        self, 
        chat_id: int, 
        message_id: int, 
        bot: Bot
    ) -> bool:
        """
        Удаляет сообщение с обработкой ошибок
        
        Args:
            chat_id: ID чата
            message_id: ID сообщения
            bot: Экземпляр бота
            
        Returns:
            bool: True, если сообщение успешно удалено
        """
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            return True
        except Exception as e:
            self.logger.error(
                f"Ошибка при удалении сообщения {message_id} "
                f"в чате {chat_id}: {e}"
            )
            return False
    
    def register_handlers(self) -> Router:
        """
        Регистрирует обработчики команд
        
        Returns:
            Router: Роутер с зарегистрированными обработчиками
        """
        # Этот метод должен быть переопределен в дочерних классах
        self.logger.warning(
            f"Метод register_handlers не переопределен в классе {self.__class__.__name__}"
        )
        return self.router 