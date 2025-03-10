from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, Field, field_validator
from typing import Optional, Dict, Any, List
import os
from pathlib import Path
from dotenv import load_dotenv

# Определение пути к корневой директории проекта
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()

# Пути к возможным .env файлам
ENV_FILES = [
    PROJECT_ROOT / ".env",
    PROJECT_ROOT / "config" / ".env",
]

# Загружаем переменные окружения из всех .env файлов
for env_file in ENV_FILES:
    if env_file.exists():
        load_dotenv(env_file)
        break


class Settings(BaseSettings):
    """
    Настройки приложения, получаемые из переменных окружения
    """
    # Версия приложения
    VERSION: str = "1.0.0"
    
    # Настройки бота
    API_TOKEN: str
    ADMIN_ID: str
    BOT_TOKEN: Optional[str] = None  # Добавлено для совместимости
    CHANNEL_ID: Optional[str] = None  # ID канала для публикации постов
    
    # Настройки базы данных
    DB_USER: str
    DB_PASS: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    
    # Автоматически собираемый DSN для базы данных
    DATABASE_URL: Optional[str] = None
    
    # Пути к директориям
    LOGS_DIR: str = str(PROJECT_ROOT / "logs")
    BACKUPS_DIR: str = str(PROJECT_ROOT / "backups")
    
    # Настройки для уведомлений
    NOTIFICATION_ENABLED: bool = False
    NOTIFICATION_RECIPIENTS: List[int] = []
    
    # Режимы работы бота
    ACTIVE_MODE: bool = True
    
    # Настройки кэширования
    CACHE_TTL: int = 3600  # время жизни кэша в секундах
    
    @field_validator("DATABASE_URL", mode='before')
    def assemble_db_connection(cls, v: Optional[str], info) -> Any:
        """
        Собираем URL подключения к базе данных из отдельных компонентов
        """
        if isinstance(v, str):
            return v
            
        values = info.data
        
        # Получаем компоненты для DSN
        username = values.get("DB_USER", "")
        password = values.get("DB_PASS", "")
        host = values.get("DB_HOST", "")
        port = values.get("DB_PORT", "")
        database = values.get("DB_NAME", "")
        
        # Формируем DSN для asyncpg
        return f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}"
    
    @property
    def admin_id_as_int(self) -> int:
        """
        Возвращает ADMIN_ID как целое число
        
        Returns:
            int: ID администратора
        """
        try:
            return int(self.ADMIN_ID)
        except (ValueError, TypeError):
            raise ValueError(f"Некорректный ADMIN_ID: {self.ADMIN_ID}")
    
    @property
    def channel_id_as_int(self) -> Optional[int]:
        """
        Возвращает CHANNEL_ID как целое число
        
        Returns:
            Optional[int]: ID канала или None
        """
        if not self.CHANNEL_ID:
            return None
            
        try:
            return int(self.CHANNEL_ID)
        except (ValueError, TypeError):
            return None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow",  # Разрешаем дополнительные поля
    )
    
    def create_directories(self) -> None:
        """Создаёт необходимые директории, если они не существуют"""
        for path_str in [self.LOGS_DIR, self.BACKUPS_DIR]:
            path = Path(path_str)
            path.mkdir(parents=True, exist_ok=True)


# Создаем экземпляр настроек
settings = Settings() 

# Для обратной совместимости
TELEGRAM_BOT_TOKEN = settings.API_TOKEN
config = settings  # Добавляем для обратной совместимости

def load_config() -> Settings:
    """
    Загружает и возвращает конфигурацию приложения.
    
    Returns:
        Settings: Объект с настройками приложения
    """
    return settings 