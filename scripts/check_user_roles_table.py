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
logger = logging.getLogger('check_user_roles_table')

# Импортируем необходимые модули
from app.db.session import get_session
from app.db.models.users import UserRole, User
from sqlalchemy import select, text

async def check_user_roles_table():
    """Проверяет структуру таблицы user_roles и доступные типы ролей"""
    
    # Загружаем переменные окружения
    load_dotenv()
    
    try:
        logger.info("Проверка структуры таблицы user_roles и доступных типов ролей")
        
        async with get_session() as session:
            # Получаем информацию о структуре таблицы user_roles
            stmt = text("SELECT column_name, data_type, character_maximum_length FROM information_schema.columns WHERE table_name = 'user_roles' ORDER BY ordinal_position")
            result = await session.execute(stmt)
            columns = result.fetchall()
            
            logger.info("Структура таблицы user_roles:")
            for column in columns:
                logger.info(f"Колонка: {column.column_name}, Тип: {column.data_type}, Макс. длина: {column.character_maximum_length}")
            
            # Получаем все уникальные типы ролей, которые есть в базе
            stmt = select(UserRole.role_type).distinct()
            result = await session.execute(stmt)
            role_types = [row[0] for row in result]
            
            logger.info(f"Доступные типы ролей в базе: {role_types}")
            
            # Получаем все записи из таблицы user_roles
            stmt = select(UserRole)
            result = await session.execute(stmt)
            roles = result.scalars().all()
            
            logger.info(f"Всего записей в таблице user_roles: {len(roles)}")
            
            if roles:
                logger.info("Примеры записей в таблице user_roles:")
                for role in roles[:5]:  # Показываем первые 5 записей для примера
                    logger.info(f"ID пользователя: {role.user_id}, Тип роли: {role.role_type}, Создан: {role.created_at}, Создан администратором: {role.created_by}")
            
            # Проверяем существование роли 'content'
            stmt = select(UserRole).where(UserRole.role_type == "content")
            result = await session.execute(stmt)
            content_roles = result.scalars().all()
            
            if content_roles:
                logger.info(f"Найдено {len(content_roles)} записей с ролью 'content':")
                for role in content_roles:
                    logger.info(f"ID пользователя: {role.user_id}, Тип роли: {role.role_type}")
            else:
                logger.warning("Роль 'content' не найдена ни у одного пользователя")
            
            # Проверяем существование роли 'content_manager'
            stmt = select(UserRole).where(UserRole.role_type == "content_manager")
            result = await session.execute(stmt)
            content_manager_roles = result.scalars().all()
            
            if content_manager_roles:
                logger.info(f"Найдено {len(content_manager_roles)} записей с ролью 'content_manager':")
                for role in content_manager_roles:
                    logger.info(f"ID пользователя: {role.user_id}, Тип роли: {role.role_type}")
            else:
                logger.warning("Роль 'content_manager' не найдена ни у одного пользователя")
    
    except Exception as e:
        logger.error(f"Ошибка при проверке таблицы user_roles: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(check_user_roles_table()) 