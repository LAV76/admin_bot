from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean
from sqlalchemy.sql import func

from app.db.base import BaseModel

class Channel(BaseModel):
    """Модель канала для публикации постов"""
    __tablename__ = 'channels'

    chat_id = Column(BigInteger, nullable=False, unique=True, comment="ID чата в Telegram")
    title = Column(String(255), nullable=False, comment="Название канала")
    username = Column(String(100), nullable=True, comment="Username канала")
    chat_type = Column(String(50), nullable=False, default='channel', comment="Тип чата (channel, group, supergroup)")
    is_default = Column(Boolean, default=False, nullable=False, comment="Флаг канала по умолчанию")
    last_used_at = Column(DateTime(timezone=True), nullable=True, comment="Время последнего использования")
    added_by = Column(BigInteger, nullable=False, comment="ID пользователя, добавившего канал")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Channel(id={self.id}, title={self.title}, chat_id={self.chat_id})>" 