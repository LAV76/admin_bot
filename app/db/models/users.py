from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Index, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin, BaseModel

class User(BaseModel, TimestampMixin):
    """Модель пользователя"""
    __tablename__ = 'users'

    user_id = Column(BigInteger, nullable=False, unique=True, index=True)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    role = Column(String, nullable=True)
    
    # Отношение к ролям пользователя
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, user_id={self.user_id}, role={self.role})>"


class UserRole(Base):
    """Модель для хранения ролей пользователей"""
    __tablename__ = "user_roles"

    user_id = Column(BigInteger, ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    role_type = Column(String(50), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(BigInteger, nullable=True, comment="ID администратора, добавившего роль")
    
    # Отношение к пользователю
    user = relationship("User", back_populates="roles")

    # Индексы для оптимизации запросов
    __table_args__ = (
        Index('idx_user_roles_user_id', 'user_id'),
        Index('idx_user_roles_role_type', 'role_type'),
    )

    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role_type={self.role_type})>"


class RoleAudit(BaseModel):
    """Модель для аудита изменений ролей"""
    __tablename__ = "role_audit"

    user_id = Column(BigInteger, ForeignKey('users.user_id', ondelete='SET NULL'), nullable=False)
    role_type = Column(String(50), nullable=False)
    action = Column(String(20), nullable=False)  # 'add' или 'remove'
    performed_by = Column(BigInteger, nullable=False)
    performed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Индексы для оптимизации запросов
    __table_args__ = (
        Index('idx_role_audit_user_id', 'user_id'),
        Index('idx_role_audit_performed_at', 'performed_at'),
    ) 