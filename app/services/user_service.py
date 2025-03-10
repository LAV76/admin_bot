from typing import Optional, List, Dict, Any

from app.db.session import get_session
from app.db.repositories.user_repository import UserRepository
from app.db.models.users import User
from utils.logger import setup_logger

class UserService:
    """Сервис для работы с пользователями"""
    
    def __init__(self):
        self.logger = setup_logger("user_service")
        self.session_factory = get_session
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Получает пользователя по username
        
        Args:
            username: Username пользователя
            
        Returns:
            Optional[User]: Объект пользователя или None, если пользователь не найден
        """
        async with self.session_factory() as session:
            try:
                user_repo = UserRepository(session)
                user = await user_repo.get_by_username(username)
                return user
            except Exception as e:
                self.logger.error(f"Ошибка при получении пользователя по username {username}: {e}")
                return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Получает пользователя по ID
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Optional[User]: Объект пользователя или None, если пользователь не найден
        """
        async with self.session_factory() as session:
            try:
                user_repo = UserRepository(session)
                user = await user_repo.get_by_user_id(user_id)
                return user
            except Exception as e:
                self.logger.error(f"Ошибка при получении пользователя по ID {user_id}: {e}")
                return None
    
    async def create_user(self, user_id: int, username: str = None, full_name: str = None) -> bool:
        """
        Создает нового пользователя
        
        Args:
            user_id: ID пользователя
            username: Username пользователя
            full_name: Полное имя пользователя
            
        Returns:
            bool: True, если пользователь успешно создан, иначе False
        """
        async with self.session_factory() as session:
            try:
                user_repo = UserRepository(session)
                user = await user_repo.create_user(user_id=user_id, username=username, full_name=full_name)
                return user is not None
            except Exception as e:
                self.logger.error(f"Ошибка при создании пользователя с ID {user_id}: {e}")
                return False 