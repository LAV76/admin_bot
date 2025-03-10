from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import BaseModel, TimestampMixin

class Post(BaseModel, TimestampMixin):
    """Модель поста для Telegram-канала"""
    __tablename__ = 'posts'

    # Основные поля из базы данных
    title = Column(String(255), nullable=False, comment="Название поста")
    content = Column(Text, nullable=False, comment="Текст поста")
    status = Column(String(50), nullable=False, default='draft', comment="Статус поста (draft, published)")
    created_by = Column(BigInteger, ForeignKey('users.user_id'), comment="ID пользователя, создавшего пост")
    
    # Дополнительные поля для работы с постами
    image = Column(String(255), nullable=True, comment="Ссылка на изображение поста")
    tag = Column(String(100), nullable=True, comment="Тег поста")
    username = Column(String(100), nullable=True, comment="Имя пользователя, создавшего пост")
    user_id = Column(BigInteger, nullable=True, comment="ID пользователя, создавшего пост")
    created_date = Column(DateTime(timezone=True), nullable=True, comment="Дата создания поста")
    is_published = Column(Integer, default=0, nullable=True, comment="Флаг публикации поста (0 - черновик, 1 - опубликован)")
    published_at = Column(DateTime(timezone=True), nullable=True, comment="Дата и время публикации поста")
    target_chat_id = Column(BigInteger, nullable=True, comment="ID чата, в который должен быть опубликован пост")
    target_chat_title = Column(String(255), nullable=True, comment="Название чата для публикации")
    
    # Поля для редактирования
    change_username = Column(String(100), nullable=True, comment="Имя пользователя, который последним редактировал пост")
    change_date = Column(DateTime(timezone=True), nullable=True, comment="Дата и время последнего редактирования")
    
    # Поля для архивирования (мягкого удаления)
    is_archived = Column(Boolean, default=False, nullable=True, comment="Флаг архивации поста")
    archived_at = Column(DateTime(timezone=True), nullable=True, comment="Дата и время архивации поста")
    archived_by = Column(BigInteger, nullable=True, comment="ID пользователя, который архивировал пост")
    
    # Идентификатор сообщения в Telegram после публикации
    message_id = Column(BigInteger, nullable=True, comment="ID сообщения в Telegram после публикации")

    def __repr__(self):
        return f"<Post(id={self.id}, title={self.title}, status={self.status})>" 