from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import logging

from app.db.repositories.role_repository import RoleRepository
from app.db.repositories.user_repository import UserRepository
from app.db.models.users import User, UserRole, RoleAudit
from app.core.exceptions import UserNotFoundError, RoleNotFoundError, PermissionDeniedError
from app.core.logging import setup_logger
from app.db.engine import get_db_session
from app.db.session import get_session

logger = setup_logger("services.role")

class RoleService:
    """
    Сервис для управления ролями пользователей
    """
    
    def __init__(self):
        self._role_cache = {}  # Простой кэш для хранения ролей пользователей
        self._cache_ttl = 60   # Время жизни кэша в секундах
        self.logger = setup_logger("role_service")
    
    async def add_role(
        self, 
        user_id: int, 
        role_type: str, 
        admin_id: int,
        display_name: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Добавляет роль пользователю
        
        Args:
            user_id: ID пользователя
            role_type: Тип роли
            admin_id: ID администратора, выполняющего действие
            display_name: Отображаемое имя пользователя
            notes: Примечания к роли
            
        Returns:
            bool: True в случае успеха
            
        Raises:
            UserNotFoundError: Если пользователь не найден
            PermissionDeniedError: Если у администратора недостаточно прав
        """
        async with get_session() as session:
            # Проверяем, что пользователь существует
            user_repo = UserRepository(session)
            if not await user_repo.exists_by_user_id(user_id):
                await self.create_user_if_not_exists(user_id)
                
            # Проверяем, что админ имеет права администратора
            role_repo = RoleRepository(session)
            is_admin = await role_repo.check_role(admin_id, "admin")
            
            if not is_admin:
                self.logger.warning(f"Пользователь {admin_id} пытается добавить роль без прав администратора")
                raise PermissionDeniedError("У вас недостаточно прав для выполнения этого действия")
            
            # Проверяем, есть ли уже такая роль
            if await role_repo.check_role(user_id, role_type):
                self.logger.info(f"Роль {role_type} уже существует у пользователя {user_id}")
                return False
            
            # Добавляем роль
            result = await role_repo.add_role(
                user_id=user_id, 
                role_type=role_type, 
                admin_id=admin_id,
                display_name=display_name,
                notes=notes
            )
            
            if result:
                self.logger.info(f"Роль {role_type} успешно добавлена пользователю {user_id}")
            else:
                self.logger.error(f"Не удалось добавить роль {role_type} пользователю {user_id}")
                
            return result
    
    async def remove_role(
        self, 
        user_id: int, 
        role_type: str, 
        admin_id: int
    ) -> bool:
        """
        Удаляет роль у пользователя
        
        Args:
            user_id: ID пользователя
            role_type: Тип роли
            admin_id: ID администратора, выполняющего действие
            
        Returns:
            bool: True в случае успеха
            
        Raises:
            UserNotFoundError: Если пользователь не найден
            RoleNotFoundError: Если роль не найдена
            PermissionDeniedError: Если у администратора недостаточно прав
        """
        async with get_session() as session:
            # Проверяем, что пользователь существует
            user_repo = UserRepository(session)
            if not await user_repo.exists_by_user_id(user_id):
                self.logger.warning(f"Пользователь {user_id} не найден при удалении роли")
                raise UserNotFoundError(
                    user_id=user_id,
                    details={"action": "remove_role", "role_type": role_type}
                )
            
            # Проверяем, что админ имеет права администратора
            role_repo = RoleRepository(session)
            is_admin = await role_repo.check_role(admin_id, "admin")
            
            if not is_admin:
                self.logger.warning(f"Пользователь {admin_id} пытается удалить роль без прав администратора")
                raise PermissionDeniedError(
                    user_id=admin_id,
                    required_permission="admin",
                    details={
                        "action": "remove_role",
                        "target_user_id": user_id,
                        "role_type": role_type
                    }
                )
            
            # Проверяем, есть ли такая роль
            if not await role_repo.check_role(user_id, role_type):
                self.logger.warning(f"Роль {role_type} не найдена у пользователя {user_id}")
                raise RoleNotFoundError(
                    role_type=role_type,
                    details={"user_id": user_id, "action": "remove_role"}
                )
            
            # Удаляем роль
            result = await role_repo.remove_role(
                user_id=user_id, 
                role_type=role_type, 
                admin_id=admin_id
            )
            
            if result:
                self.logger.info(f"Роль {role_type} успешно удалена у пользователя {user_id}")
            else:
                self.logger.error(f"Не удалось удалить роль {role_type} у пользователя {user_id}")
                
            return result
    
    async def check_user_role(self, user_id: int, role_type: str) -> bool:
        """
        Проверяет наличие роли у пользователя
        
        Args:
            user_id: ID пользователя
            role_type: Тип роли
            
        Returns:
            bool: True, если пользователь имеет указанную роль
        """
        async with get_session() as session:
            role_repo = RoleRepository(session)
            return await role_repo.check_role(user_id, role_type)
    
    async def get_user_roles(self, user_id: int) -> List[str]:
        """
        Получает список ролей пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List[str]: Список ролей
        """
        async with get_session() as session:
            role_repo = RoleRepository(session)
            return await role_repo.get_user_roles(user_id)
    
    async def get_role_details(self, user_id: int, role_type: str) -> Optional[Dict[str, Any]]:
        """
        Получает детальную информацию о роли пользователя
        
        Args:
            user_id: ID пользователя
            role_type: Тип роли
            
        Returns:
            Optional[Dict[str, Any]]: Информация о роли или None
        """
        async with get_session() as session:
            role_repo = RoleRepository(session)
            return await role_repo.get_role_details(user_id, role_type)
    
    async def get_role_history(self, user_id: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает историю изменений ролей
        
        Args:
            user_id: ID пользователя для фильтрации (опционально)
            limit: Максимальное количество записей
            
        Returns:
            List[Dict[str, Any]]: История изменений
        """
        async with get_session() as session:
            role_repo = RoleRepository(session)
            return await role_repo.get_role_history(user_id=user_id, limit=limit)
    
    async def clear_role_history(self, admin_id: int) -> int:
        """
        Очищает историю изменений ролей
        
        Args:
            admin_id: ID администратора, выполняющего действие
            
        Returns:
            int: Количество удаленных записей
            
        Raises:
            PermissionDeniedError: Если у администратора недостаточно прав
        """
        async with get_session() as session:
            # Проверяем, что админ имеет права администратора
            role_repo = RoleRepository(session)
            is_admin = await role_repo.check_role(admin_id, "admin")
            
            if not is_admin:
                self.logger.warning(f"Пользователь {admin_id} пытается очистить историю без прав администратора")
                raise PermissionDeniedError("У вас недостаточно прав для выполнения этого действия")
            
            # Очищаем историю
            return await role_repo.clear_role_history()
    
    async def create_user_if_not_exists(self, user_id: int) -> bool:
        """
        Создает пользователя, если он не существует
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True, если пользователь создан или уже существует
        """
        async with get_session() as session:
            user_repo = UserRepository(session)
            
            # Проверяем, существует ли пользователь
            if await user_repo.exists_by_user_id(user_id):
                return True
            
            # Создаем пользователя
            self.logger.info(f"Создание нового пользователя с ID {user_id}")
            await user_repo.create_user(user_id=user_id)
            return True
    
    async def get_by_role(self, role_type: str) -> List[User]:
        """
        Получает список пользователей с указанной ролью
        
        Args:
            role_type: Тип роли
            
        Returns:
            List[User]: Список пользователей с указанной ролью
        """
        async with get_session() as session:
            user_repo = UserRepository(session)
            return await user_repo.get_by_role(role_type)
    
    def _update_role_cache(self, user_id: int, roles: List[str]) -> None:
        """
        Обновление кэша ролей пользователя
        
        Args:
            user_id: ID пользователя
            roles: Список ролей пользователя
        """
        self._role_cache[str(user_id)] = {
            "roles": roles,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # Планируем очистку кэша через TTL секунд
        asyncio.create_task(self._schedule_cache_cleanup(user_id))
    
    def _clear_user_role_cache(self, user_id: int) -> None:
        """
        Очистка кэша ролей пользователя
        
        Args:
            user_id: ID пользователя
        """
        if str(user_id) in self._role_cache:
            del self._role_cache[str(user_id)]
    
    async def _schedule_cache_cleanup(self, user_id: int) -> None:
        """
        Планирование очистки кэша ролей пользователя
        
        Args:
            user_id: ID пользователя
        """
        await asyncio.sleep(self._cache_ttl)
        self._clear_user_role_cache(user_id) 