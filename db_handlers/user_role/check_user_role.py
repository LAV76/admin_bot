import logging
from sqlalchemy import select, exists
from models.users import UserRole
from app.db.session import async_session_maker

logger = logging.getLogger(__name__)

async def check_db_user_role(user_id: int) -> str | None:
    """
    Проверяет роль пользователя в базе данных
    
    Args:
        user_id (int): ID пользователя в Telegram
        
    Returns:
        str | None: Роль пользователя или None если пользователь не найден
    """
    try:
        async with async_session_maker() as session:
            # Создаем запрос на выборку роли пользователя
            query = select(UserRole.role_type).where(UserRole.user_id == user_id)
            
            # Выполняем запрос
            result = await session.execute(query)
            roles = result.scalars().all()
            
            # Логируем результат для отладки
            logger.debug(f"Найдены роли для пользователя {user_id}: {roles}")
            
            # Возвращаем первую роль или None
            return roles[0] if roles else None
            
    except Exception as e:
        logger.error(f"Ошибка при проверке роли пользователя {user_id}: {e}", exc_info=True)
        return None

async def check_user_role(user_id: int, role_type: str) -> bool:
    """
    Проверяет, имеет ли пользователь указанную роль
    
    Args:
        user_id (int): ID пользователя в Telegram
        role_type (str): Тип роли для проверки
        
    Returns:
        bool: True если пользователь имеет указанную роль, иначе False
    """
    try:
        async with async_session_maker() as session:
            # Создаем запрос на проверку наличия роли
            query = select(exists().where(
                (UserRole.user_id == user_id) & 
                (UserRole.role_type == role_type)
            ))
            
            # Выполняем запрос
            result = await session.execute(query)
            has_role = result.scalar()
            
            logger.debug(f"Пользователь {user_id} имеет роль {role_type}: {has_role}")
            
            return has_role
            
    except Exception as e:
        logger.error(f"Ошибка при проверке роли {role_type} для пользователя {user_id}: {e}", exc_info=True)
        return False 