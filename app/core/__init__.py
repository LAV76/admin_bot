"""
Модуль для основных компонентов приложения.
"""

from .config import settings

__all__ = [
    "settings",
]

# Другие компоненты должны импортироваться напрямую, чтобы избежать циклических импортов
# Например: from app.core.decorators import admin_required
# и from app.core.di import inject

# Экспорт исключений для удобства импорта
from app.core.exceptions import (
    BotException,
    DatabaseError,
    UserNotFoundError,
    RoleNotFoundError,
    PermissionDeniedError,
    ConfigurationError,
    ValidationError,
    ExternalServiceError,
) 