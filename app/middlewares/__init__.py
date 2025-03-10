"""
Модуль для middleware, используемых в приложении.
"""

from aiogram import Dispatcher
from app.core.logging import setup_logger

logger = setup_logger("middlewares")

def setup_middlewares(dp: Dispatcher) -> None:
    """
    Настраивает все middleware для диспетчера
    
    Args:
        dp: Диспетчер, для которого настраиваются middleware
    """
    # Импортируем middleware внутри функции для избежания циклических импортов
    from .anti_spam import AntiSpamMiddleware
    
    # Регистрируем middleware для защиты от спама
    anti_spam = AntiSpamMiddleware(rate_limit=10, period=5)
    dp.update.middleware(anti_spam)
    
    logger.info("Все middleware успешно зарегистрированы")

# Экспортируем только функцию setup_middlewares
__all__ = ["setup_middlewares"] 