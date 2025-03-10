from typing import List, Optional, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, exists, func, insert, desc
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.repositories.base import BaseRepository
from app.db.models.users import UserRole, RoleAudit
from app.core.logging import setup_logger

logger = setup_logger("db.repositories.role")

class RoleRepository(BaseRepository[UserRole]):
    """
    Репозиторий для работы с ролями пользователей
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(UserRole)
        self.session = session
        self.logger = setup_logger("role_repository")
    
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
            display_name: Отображаемое имя пользователя (не используется)
            notes: Примечания к роли (не используется)
            
        Returns:
            bool: True в случае успеха
        """
        try:
            # Вставляем новую роль
            stmt = insert(UserRole).values(
                user_id=user_id,
                role_type=role_type,
                created_by=admin_id
            )
            await self.session.execute(stmt)
            
            # Логируем действие
            await self.log_role_action(
                user_id=user_id, 
                role_type=role_type, 
                action="add", 
                performed_by=admin_id,
                notes=notes
            )
            
            await self.session.commit()
            self.logger.info(f"Роль {role_type} добавлена пользователю {user_id} (админ: {admin_id})")
            return True
        except IntegrityError as e:
            await self.session.rollback()
            self.logger.error(f"Ошибка при добавлении роли: {str(e)}")
            return False
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Непредвиденная ошибка при добавлении роли: {str(e)}")
            return False
    
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
        """
        try:
            # Удаляем роль
            stmt = delete(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_type == role_type
            )
            result = await self.session.execute(stmt)
            
            # Если ничего не удалено, значит роли не было
            if result.rowcount == 0:
                self.logger.warning(f"Роль {role_type} не найдена у пользователя {user_id}")
                return False
            
            # Логируем действие
            await self.log_role_action(
                user_id=user_id, 
                role_type=role_type, 
                action="remove", 
                performed_by=admin_id
            )
            
            await self.session.commit()
            self.logger.info(f"Роль {role_type} удалена у пользователя {user_id} (админ: {admin_id})")
            return True
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Ошибка при удалении роли: {str(e)}")
            return False
    
    async def check_role(self, user_id: int, role_type: str) -> bool:
        """
        Проверяет наличие роли у пользователя
        
        Args:
            user_id: ID пользователя
            role_type: Тип роли
            
        Returns:
            bool: True, если роль есть у пользователя
        """
        self.logger.debug(f"Проверка роли {role_type} для пользователя {user_id}")
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_type == role_type
        )
        result = await self.session.execute(stmt)
        role = result.scalar_one_or_none()
        has_role = role is not None
        self.logger.debug(f"Результат проверки: {has_role}, найдена роль: {role}")
        return has_role
    
    async def get_user_roles(self, user_id: int) -> List[str]:
        """
        Получает список ролей пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List[str]: Список ролей
        """
        stmt = select(UserRole.role_type).where(UserRole.user_id == user_id)
        result = await self.session.execute(stmt)
        return [row[0] for row in result]
    
    async def get_role_details(self, user_id: int, role_type: str) -> Optional[Dict[str, Any]]:
        """
        Получает детальную информацию о роли пользователя
        
        Args:
            user_id: ID пользователя
            role_type: Тип роли
            
        Returns:
            Optional[Dict[str, Any]]: Информация о роли или None
        """
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_type == role_type
        )
        result = await self.session.execute(stmt)
        role = result.scalar_one_or_none()
        
        if not role:
            return None
            
        return {
            "user_id": role.user_id,
            "role_type": role.role_type,
            "created_at": role.created_at,
            "created_by": role.created_by
        }
    
    async def get_role_history(self, user_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Получает историю изменений ролей
        
        Args:
            user_id: Опциональный ID пользователя для фильтрации
            limit: Максимальное количество записей
            
        Returns:
            List[Dict[str, Any]]: История изменений
        """
        stmt = select(RoleAudit).order_by(desc(RoleAudit.performed_at))
        
        if user_id:
            stmt = stmt.where(RoleAudit.user_id == user_id)
            
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        
        history = []
        for row in result.scalars():
            history.append({
                "id": row.id,
                "user_id": row.user_id,
                "role_type": row.role_type,
                "action": row.action,
                "performed_by": row.performed_by,
                "performed_at": row.performed_at
            })
            
        return history
    
    async def clear_role_history(self) -> int:
        """
        Очищает историю изменений ролей
        
        Returns:
            int: Количество удаленных записей
        """
        try:
            stmt = delete(RoleAudit)
            result = await self.session.execute(stmt)
            rowcount = result.rowcount
            
            await self.session.commit()
            self.logger.info(f"История ролей очищена, удалено {rowcount} записей")
            return rowcount
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Ошибка при очистке истории ролей: {str(e)}")
            return 0
    
    async def log_role_action(
        self, 
        user_id: int, 
        role_type: str, 
        action: str, 
        performed_by: int,
        notes: Optional[str] = None
    ) -> bool:
        """
        Логирует действие с ролью
        
        Args:
            user_id: ID пользователя
            role_type: Тип роли
            action: Действие (add/remove)
            performed_by: ID пользователя, выполнившего действие
            notes: Примечания к действию (не используется)
            
        Returns:
            bool: True в случае успеха
        """
        try:
            stmt = insert(RoleAudit).values(
                user_id=user_id,
                role_type=role_type,
                action=action,
                performed_by=performed_by
            )
            await self.session.execute(stmt)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при логировании действия с ролью: {str(e)}")
            return False 