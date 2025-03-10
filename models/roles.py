"""
Модуль для обеспечения обратной совместимости.
Реэкспортирует модели из app.db.models.users для поддержки существующего кода.
"""

from app.db.models.users import UserRole, RoleAudit

# Реэкспорт моделей для обратной совместимости
__all__ = ['UserRole', 'RoleAudit']