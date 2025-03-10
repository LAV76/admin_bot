import logging
import sys
import os
from typing import Optional, Dict, Union, List
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import json

from app.core.config import settings

# Константы для уровней логирования
LOG_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

# Создание директории для логов, если она не существует
Path(settings.LOGS_DIR).mkdir(parents=True, exist_ok=True)

class CustomJsonFormatter(logging.Formatter):
    """
    Форматтер для вывода логов в JSON формате
    """
    def __init__(self, **kwargs):
        self.json_default = kwargs.pop("json_default", str)
        super().__init__(**kwargs)
    
    def format(self, record):
        log_record = {
            "time": self.formatTime(record),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
            
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        if hasattr(record, "stack_info") and record.stack_info:
            log_record["stack_info"] = self.formatStack(record.stack_info)
            
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", 
                          "filename", "funcName", "id", "levelname", "levelno",
                          "lineno", "module", "msecs", "message", "msg", "name", 
                          "pathname", "process", "processName", "relativeCreated", 
                          "stack_info", "thread", "threadName", "request_id"]:
                log_record[key] = value
                
        return json.dumps(log_record, default=self.json_default)

def get_console_handler(log_level: int = logging.INFO) -> logging.Handler:
    """
    Создает обработчик для вывода логов в консоль
    
    Args:
        log_level: Уровень логирования
        
    Returns:
        logging.Handler: Обработчик для консоли
    """
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    return console_handler

def get_file_handler(
    log_name: str, 
    log_level: int = logging.INFO,
    rotate_size: int = 5 * 1024 * 1024,  # 5 МБ
    backup_count: int = 3,
    use_json: bool = False
) -> logging.Handler:
    """
    Создает обработчик для записи логов в файл с ротацией по размеру
    
    Args:
        log_name: Имя лог-файла
        log_level: Уровень логирования
        rotate_size: Размер файла, после которого происходит ротация
        backup_count: Количество хранимых архивных файлов
        use_json: Использовать JSON формат для логов
        
    Returns:
        logging.Handler: Обработчик для файла
    """
    log_file = os.path.join(settings.LOGS_DIR, f"{log_name}.log")
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=rotate_size,
        backupCount=backup_count
    )
    file_handler.setLevel(log_level)
    
    if use_json:
        formatter = CustomJsonFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    file_handler.setFormatter(formatter)
    
    return file_handler

def get_timed_file_handler(
    log_name: str, 
    log_level: int = logging.INFO,
    when: str = 'midnight',
    backup_count: int = 7,
    use_json: bool = False
) -> logging.Handler:
    """
    Создает обработчик для записи логов в файл с ротацией по времени
    
    Args:
        log_name: Имя лог-файла
        log_level: Уровень логирования
        when: Период ротации ('S', 'M', 'H', 'D', 'midnight')
        backup_count: Количество хранимых архивных файлов
        use_json: Использовать JSON формат для логов
        
    Returns:
        logging.Handler: Обработчик для файла
    """
    log_file = os.path.join(settings.LOGS_DIR, f"{log_name}.log")
    
    file_handler = TimedRotatingFileHandler(
        log_file,
        when=when,
        backupCount=backup_count
    )
    file_handler.setLevel(log_level)
    
    if use_json:
        formatter = CustomJsonFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    file_handler.setFormatter(formatter)
    
    return file_handler

def setup_logger(
    name: Optional[str] = None, 
    level: Union[int, str] = logging.INFO,
    use_console: bool = True,
    use_file: bool = True,
    file_rotation: str = "size",  # "size" или "time"
    use_json: bool = False
) -> logging.Logger:
    """
    Настройка логгера с единым форматом для всего приложения
    
    Args:
        name: Имя логгера (если None, используется имя модуля)
        level: Уровень логирования
        use_console: Выводить логи в консоль
        use_file: Записывать логи в файл
        file_rotation: Тип ротации файлов ('size' или 'time')
        use_json: Использовать JSON формат для логов в файле
        
    Returns:
        logging.Logger: Настроенный логгер
    """
    logger_name = name or __name__
    
    # Преобразование уровня логирования из строки в int, если нужно
    if isinstance(level, str):
        level = LOG_LEVEL_MAP.get(level.lower(), logging.INFO)
    
    # Получаем или создаем логгер
    logger = logging.getLogger(logger_name)
    
    # Если логгер уже настроен, возвращаем его
    if logger.handlers:
        return logger
    
    # Устанавливаем уровень логирования
    logger.setLevel(level)
    
    # Добавляем обработчик для консоли, если нужно
    if use_console:
        console_handler = get_console_handler(level)
        logger.addHandler(console_handler)
    
    # Добавляем обработчик для файла, если нужно
    if use_file:
        if file_rotation == "size":
            file_handler = get_file_handler(
                logger_name.replace(".", "_"),
                level,
                use_json=use_json
            )
        else:  # "time"
            file_handler = get_timed_file_handler(
                logger_name.replace(".", "_"),
                level,
                use_json=use_json
            )
        logger.addHandler(file_handler)
    
    # Предотвращаем передачу сообщений родительским логгерам
    logger.propagate = False
    
    return logger 