import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Устанавливаем рабочую директорию в корень проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('check_user_role')

# Импортируем сервис для работы с ролями
from app.services.role_service import RoleService
from app.db.repositories.role_repository import RoleRepository
from app.db.session import get_session
from app.db.models.users import UserRole, User
from sqlalchemy import select

async def check_user_role():
    """Проверяет наличие роли 'content' у пользователя"""
    
    # Загружаем переменные окружения
    load_dotenv()
    
    try:
        # Запрашиваем ID пользователя
        user_id = input("Введите ID пользователя для проверки: ")
        try:
            user_id = int(user_id.strip())
        except ValueError:
            logger.error(f"Некорректный ID пользователя: {user_id}")
            return
            
        logger.info(f"Проверка роли 'content' для пользователя с ID: {user_id}")
        
        # Используем RoleService для проверки роли
        role_service = RoleService()
        
        # Получаем все роли пользователя
        roles = await role_service.get_user_roles(user_id)
        logger.info(f"Роли пользователя {user_id}: {roles}")
        
        # Проверяем наличие роли 'content'
        has_content_role = await role_service.check_user_role(user_id, "content")
        logger.info(f"Наличие роли 'content': {has_content_role}")
        
        # Получаем детали роли 'content', если она есть
        role_details = await role_service.get_role_details(user_id, "content")
        logger.info(f"Детали роли 'content': {role_details}")
        
        # Используем прямой запрос к базе для дополнительной проверки
        async with get_session() as session:
            # Проверяем записи в таблице user_roles
            stmt = select(UserRole).where(
                UserRole.user_id == user_id, 
                UserRole.role_type == "content"
            )
            result = await session.execute(stmt)
            role_record = result.scalar_one_or_none()
            
            logger.info(f"Запись о роли в БД: {role_record}")
            
            # Проверяем, существует ли пользователь
            stmt = select(User).where(User.user_id == user_id)
            result = await session.execute(stmt)
            user_record = result.scalar_one_or_none()
            
            logger.info(f"Запись о пользователе в БД: {user_record}")
            
            if role_record is None:
                logger.warning(f"Роль 'content' не найдена в базе данных у пользователя {user_id}")
            
    except Exception as e:
        logger.error(f"Ошибка при проверке роли: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(check_user_role()) 