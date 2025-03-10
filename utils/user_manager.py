from typing import Optional, List
import logging
from sqlalchemy import select, update, delete
from models.users import User
from config.database import get_session

logger = logging.getLogger(__name__)

class UserManager:
    """Менеджер для работы с пользователями в базе данных"""
    
    @staticmethod
    async def add_user(user_id: int, username: str, role: str = None) -> bool:
        """
        Добавление нового пользователя
        
        Args:
            user_id (int): ID пользователя в Telegram
            username (str): Имя пользователя
            role (str, optional): Роль пользователя
            
        Returns:
            bool: Успешность добавления
        """
        try:
            async with get_session() as session:
                # Проверяем существование пользователя
                exists = await session.execute(
                    select(User).where(User.user_id == user_id)
                )
                if exists.scalar_one_or_none():
                    logger.warning(f"Пользователь {user_id} уже существует")
                    return False
                    
                # Создаем нового пользователя
                new_user = User(
                    user_id=user_id,
                    username=username,
                    user_role=role
                )
                session.add(new_user)
                await session.commit()
                
                logger.info(f"Пользователь {user_id} успешно добавлен")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя: {e}")
            return False
    
    @staticmethod
    async def update_user_role(user_id: int, new_role: str) -> bool:
        """
        Обновление роли пользователя
        
        Args:
            user_id (int): ID пользователя
            new_role (str): Новая роль
            
        Returns:
            bool: Успешность обновления
        """
        try:
            async with get_session() as session:
                result = await session.execute(
                    update(User)
                    .where(User.user_id == user_id)
                    .values(user_role=new_role)
                )
                await session.commit()
                
                if result.rowcount > 0:
                    logger.info(f"Роль пользователя {user_id} обновлена на {new_role}")
                    return True
                else:
                    logger.warning(f"Пользователь {user_id} не найден")
                    return False
                    
        except Exception as e:
            logger.error(f"Ошибка при обновлении роли пользователя: {e}")
            return False
    
    @staticmethod
    async def get_user(user_id: int) -> Optional[User]:
        """
        Получение информации о пользователе
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            Optional[User]: Информация о пользователе или None
        """
        try:
            async with get_session() as session:
                result = await session.execute(
                    select(User).where(User.user_id == user_id)
                )
                return result.scalar_one_or_none()
                
        except Exception as e:
            logger.error(f"Ошибка при получении информации о пользователе: {e}")
            return None
    
    @staticmethod
    async def get_users_by_role(role: str) -> List[User]:
        """
        Получение списка пользователей с указанной ролью
        
        Args:
            role (str): Роль для поиска
            
        Returns:
            List[User]: Список пользователей
        """
        try:
            async with get_session() as session:
                result = await session.execute(
                    select(User).where(User.user_role == role)
                )
                return result.scalars().all()
                
        except Exception as e:
            logger.error(f"Ошибка при получении списка пользователей: {e}")
            return []
    
    @staticmethod
    async def remove_user(user_id: int) -> bool:
        """
        Удаление пользователя
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            bool: Успешность удаления
        """
        try:
            async with get_session() as session:
                result = await session.execute(
                    delete(User).where(User.user_id == user_id)
                )
                await session.commit()
                
                if result.rowcount > 0:
                    logger.info(f"Пользователь {user_id} успешно удален")
                    return True
                else:
                    logger.warning(f"Пользователь {user_id} не найден")
                    return False
                    
        except Exception as e:
            logger.error(f"Ошибка при удалении пользователя: {e}")
            return False 