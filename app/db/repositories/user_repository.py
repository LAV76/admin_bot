import logging
from typing import List, Optional
from sqlalchemy import select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.users import User
from app.db.repositories.base_repository import BaseRepository
from app.core.logging import setup_logger

class UserRepository(BaseRepository[User]):
    """Репозиторий для работы с пользователями"""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)
        self.logger = setup_logger("user_repository")

    async def get_by_user_id(self, user_id: int) -> Optional[User]:
        """
        Получает пользователя по его Telegram ID
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            Optional[User]: Объект пользователя или None, если не найден
        """
        stmt = select(User).where(User.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Получает пользователя по его username
        
        Args:
            username: Username пользователя (с символом @ или без)
            
        Returns:
            Optional[User]: Объект пользователя или None, если не найден
        """
        try:
            # Удаляем символ @ в начале, если он есть
            clean_username = username.lstrip('@').lower()
            self.logger.info(f"Поиск пользователя по username: {clean_username}")
            
            # Пробуем сначала точное совпадение (без учета регистра)
            stmt = select(User).where(User.username.ilike(clean_username))
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                self.logger.info(f"Найден пользователь по точному username {clean_username}: ID {user.user_id}")
                return user
            
            # Если точное совпадение не найдено, пробуем поиск по частичному совпадению
            self.logger.info(f"Точное совпадение для username {clean_username} не найдено, пробуем частичное")
            stmt = select(User).where(User.username.ilike(f"%{clean_username}%"))
            result = await self.session.execute(stmt)
            users = result.scalars().all()
            
            if users:
                # Если найдено несколько пользователей, возвращаем первого
                user = users[0]
                self.logger.info(f"Найден пользователь по частичному совпадению username {clean_username}: ID {user.user_id}")
                return user
            
            self.logger.info(f"Пользователь с username {clean_username} не найден ни по точному, ни по частичному совпадению")
            return None
        except Exception as e:
            self.logger.error(f"Ошибка при поиске пользователя по username {username}: {e}", exc_info=True)
            return None

    async def exists_by_user_id(self, user_id: int) -> bool:
        """
        Проверяет, существует ли пользователь с указанным Telegram ID
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            bool: True, если пользователь существует
        """
        user = await self.get_by_user_id(user_id)
        return user is not None

    async def get_by_role(self, role_type: str) -> List[User]:
        """
        Получает список пользователей с указанной ролью
        
        Args:
            role_type: Тип роли
            
        Returns:
            List[User]: Список пользователей
        """
        from app.db.models.users import UserRole
        
        stmt = select(User).join(UserRole, User.user_id == UserRole.user_id).where(
            UserRole.role_type == role_type
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_user(self, user_id: int, username: Optional[str] = None, full_name: Optional[str] = None) -> User:
        """
        Создает нового пользователя
        
        Args:
            user_id: Telegram ID пользователя
            username: Имя пользователя в Telegram
            full_name: Полное имя пользователя
            
        Returns:
            User: Созданный пользователь
        """
        try:
            # Проверяем, существует ли пользователь
            existing_user = await self.get_by_user_id(user_id)
            if existing_user:
                # Обновляем существующего пользователя
                stmt = update(User).where(User.user_id == user_id).values(
                    username=username if username else existing_user.username,
                    full_name=full_name if full_name else existing_user.full_name
                ).returning(User)
                
                result = await self.session.execute(stmt)
                await self.session.commit()
                
                self.logger.info(f"Обновлен пользователь с ID {user_id}")
                return result.scalar_one()
            else:
                # Создаем нового пользователя
                stmt = insert(User).values(
                    user_id=user_id,
                    username=username,
                    full_name=full_name
                ).returning(User)
                
                result = await self.session.execute(stmt)
                await self.session.commit()
                
                self.logger.info(f"Создан новый пользователь с ID {user_id}")
                return result.scalar_one()
        except Exception as e:
            self.logger.error(f"Ошибка при создании/обновлении пользователя с ID {user_id}: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def update_role(self, user_id: int, role: str) -> bool:
        """
        Обновляет роль пользователя
        
        Args:
            user_id: Telegram ID пользователя
            role: Новая роль
            
        Returns:
            bool: True в случае успеха
        """
        stmt = update(User).where(User.user_id == user_id).values(
            user_role=role
        )
        
        try:
            await self.session.execute(stmt)
            await self.session.commit()
            self.logger.info(f"Обновлена роль пользователя {user_id} на {role}")
            return True
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Ошибка при обновлении роли пользователя {user_id}: {str(e)}")
            return False 