# Патч для исправления проблемы с ролями
# Добавляет поддержку алиасов ролей, чтобы роль 'content' считалась эквивалентной 'content_manager'

import logging
from app.services.role_service import RoleService
from app.db.repositories.role_repository import RoleRepository
from app.db.session import get_session
from sqlalchemy import delete
from app.db.models.users import UserRole

logger = logging.getLogger('role_service_patch')

# Сохраняем оригинальные методы
original_check_user_role = RoleService.check_user_role
original_remove_role = RoleService.remove_role

# Мапинг алиасов ролей
ROLE_ALIASES = {
    'content': ['content_manager'],
    'content_manager': ['content']
}

async def patched_check_user_role(self, user_id: int, role_type: str) -> bool:
    # Сначала пробуем прямую проверку
    result = await original_check_user_role(self, user_id, role_type)
    if result:
        return True
        
    # Если роль не найдена, проверяем алиасы
    if role_type in ROLE_ALIASES:
        for alias in ROLE_ALIASES[role_type]:
            try:
                result = await original_check_user_role(self, user_id, alias)
                if result:
                    return True
            except Exception:
                pass
                
    return False

async def patched_remove_role(self, user_id: int, role_type: str, admin_id: int) -> bool:
    # Проверяем наличие роли или её алиасов
    real_role_to_remove = None
    
    # Проверяем основную роль
    has_role = await original_check_user_role(self, user_id, role_type)
    if has_role:
        real_role_to_remove = role_type
    else:
        # Проверяем алиасы
        if role_type in ROLE_ALIASES:
            for alias in ROLE_ALIASES[role_type]:
                has_alias = await original_check_user_role(self, user_id, alias)
                if has_alias:
                    real_role_to_remove = alias
                    break
    
    if real_role_to_remove:
        # Используем прямой доступ к репозиторию для удаления роли
        async with get_session() as session:
            # Удаляем роль напрямую из базы данных
            stmt = delete(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_type == real_role_to_remove
            )
            result = await session.execute(stmt)
            
            # Логируем действие в таблицу аудита
            repo = RoleRepository(session)
            await repo.log_role_action(
                user_id=user_id,
                role_type=real_role_to_remove,
                action="remove",
                performed_by=admin_id
            )
            
            await session.commit()
            logger.info(f"Роль {real_role_to_remove} успешно удалена у пользователя {user_id}")
            return True
    else:
        # Используем оригинальный метод для генерации корректной ошибки
        return await original_remove_role(self, user_id, role_type, admin_id)

# Применяем патчи
RoleService.check_user_role = patched_check_user_role
RoleService.remove_role = patched_remove_role

logger.info("Патч для исправления проблемы с ролями успешно применен")
