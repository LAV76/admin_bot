"""
Модель для работы с ролями пользователей.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

# Создаем базовый класс для моделей
Base = declarative_base()

# Таблица связи пользователей и ролей (многие-ко-многим)
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)

class RoleModel(Base):
    """
    Модель для хранения ролей пользователей.
    """
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))
    is_active = Column(Boolean, default=True)
    
    # Связь с пользователями (многие-ко-многим)
    users = relationship("UserModel", secondary=user_roles, back_populates="roles")
    
    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>" 