from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func

# Базовый класс для всех моделей SQLAlchemy
Base = declarative_base()

class TimestampMixin:
    """
    Миксин для добавления полей created_at и updated_at
    """
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class BaseModel(Base):
    """
    Базовый класс для всех моделей с общими полями
    """
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    def __repr__(self):
        """Строковое представление модели"""
        attrs = []
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                attrs.append(f"{key}={value}")
        return f"<{self.__class__.__name__}({', '.join(attrs)})>" 