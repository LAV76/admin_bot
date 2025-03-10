import asyncio
import os
from dotenv import load_dotenv
import logging
import sys

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append('.')

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_role_service():
    # Загружаем переменные окружения
    load_dotenv()
    
    # Получаем значение ADMIN_ID
    admin_id_str = os.getenv("ADMIN_ID")
    if not admin_id_str:
        logger.error("ADMIN_ID не указан в .env файле")
        return False
    
    try:
        admin_id = int(admin_id_str)
        logger.info(f"ID администратора: {admin_id}")
    except ValueError:
        logger.error(f"Некорректный ADMIN_ID: {admin_id_str}")
        return False
    
    try:
        # Импортируем RoleService
        from app.services.role_service import RoleService
        
        # Создаем экземпляр сервиса
        role_service = RoleService()
        logger.info("RoleService успешно создан")
        
        # Проверяем роль администратора
        is_admin = await role_service.check_user_role(admin_id, "admin")
        logger.info(f"Результат проверки роли администратора: {is_admin}")
        
        # Получаем список ролей пользователя
        roles = await role_service.get_user_roles(admin_id)
        logger.info(f"Роли пользователя {admin_id}: {roles}")
        
        return is_admin
    except Exception as e:
        logger.error(f"Ошибка при работе с RoleService: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    print("Проверка работы RoleService...")
    result = asyncio.run(check_role_service())
    if result:
        print("✅ Пользователь имеет роль администратора согласно RoleService")
    else:
        print("❌ Пользователь НЕ имеет роли администратора согласно RoleService") 