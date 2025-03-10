import logging
import os
import functools
from datetime import datetime
from typing import Callable, Any

def setup_logger(name=None, log_to_file=True):
    """Настройка системы логирования с возможностью вывода в файл"""
    logger = logging.getLogger(name or __name__)
    
    # Уже настроенный логгер возвращаем без изменений
    if logger.handlers:
        return logger
    
    # Общий формат логов
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Добавление обработчика для записи в файл, если разрешено
    if log_to_file:
        try:
            # Создаем директорию logs, если её нет
            os.makedirs('logs', exist_ok=True)
            
            # Имя файла с текущей датой
            log_filename = f'logs/bot_{datetime.now().strftime("%Y-%m-%d")}.log'
            
            # Обработчик для файла
            file_handler = logging.FileHandler(log_filename, encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"Не удалось настроить логирование в файл: {e}")
    
    logger.setLevel(logging.INFO)
    return logger

def log_error(logger, message, exception=None, exc_info=False):
    """Расширенное логирование ошибок с контекстом"""
    if exception:
        logger.error(f"{message}: {type(exception).__name__} - {exception}", exc_info=exc_info)
    else:
        logger.error(message, exc_info=exc_info)

def log_function_call(func: Callable) -> Callable:
    """
    Декоратор для логирования вызова функции с её параметрами
    
    Args:
        func: Декорируемая функция
        
    Returns:
        Callable: Обёрнутая функция
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Получаем имя функции
        function_name = func.__name__
        
        # Получаем логгер
        logger = logging.getLogger(func.__module__)
        
        # Фильтруем конфиденциальные данные
        safe_kwargs = {k: v for k, v in kwargs.items() if k not in ['password', 'token']}
        
        # Логируем вызов функции
        logger.debug(f"Вызов функции {function_name}()")
        
        # Вызываем оригинальную функцию
        return await func(*args, **kwargs)
    
    return wrapper

def log_params(logger, function_name, **kwargs):
    """Логирование параметров функции"""
    params = ', '.join([f"{k}={v}" for k, v in kwargs.items() if k != 'password' and k != 'token'])
    logger.debug(f"Параметры функции {function_name}: {params}") 