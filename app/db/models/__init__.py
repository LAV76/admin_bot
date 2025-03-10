"""
Инициализация моделей базы данных.
Импортируем все модели для автоматической регистрации в SQLAlchemy.
"""

from app.db.base import Base
from app.db.models.users import User, UserRole, RoleAudit
from app.db.models.posts import Post
from app.db.models.channels import Channel

# Экспортируем все модели для удобства импорта
__all__ = [
    'Base',
    'User',
    'UserRole',
    'RoleAudit',
    'Post',
    'Channel',
] 