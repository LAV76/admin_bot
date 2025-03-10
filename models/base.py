"""
Модуль для обеспечения обратной совместимости с существующим кодом.
Перенаправляет импорты из models.base в app.db.base
"""

from app.db.base import Base, BaseModel, TimestampMixin

# Экспортируем Base для использования в других модулях
__all__ = ['Base', 'BaseModel', 'TimestampMixin'] 