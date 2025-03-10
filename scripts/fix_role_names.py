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
logger = logging.getLogger('fix_role_names')

# Импортируем необходимый код
from app.core.exceptions import RoleNotFoundError
from app.services.role_service import RoleService
from app.db.repositories.role_repository import RoleRepository
from app.db.session import get_session
from sqlalchemy import delete
from app.db.models.users import UserRole

# Создаем патч для метода проверки роли
original_check_user_role = RoleService.check_user_role

async def patched_check_user_role(self, user_id: int, role_type: str) -> bool:
    """
    Патч для метода check_user_role, который добавляет поддержку алиасов ролей.
    Если роль 'content' не найдена, проверяет наличие роли 'content_manager'.
    """
    # Создаем маппинг алиасов ролей
    role_aliases = {
        'content': ['content_manager'],
        'content_manager': ['content']
    }
    
    # Сначала пробуем прямую проверку
    try:
        result = await original_check_user_role(self, user_id, role_type)
        if result:
            return True
            
        # Если роль не найдена, проверяем алиасы
        if role_type in role_aliases:
            logger.info(f"Роль {role_type} не найдена, проверяем алиасы: {role_aliases[role_type]}")
            for alias in role_aliases[role_type]:
                try:
                    result = await original_check_user_role(self, user_id, alias)
                    if result:
                        logger.info(f"Найден алиас {alias} для роли {role_type}")
                        return True
                except Exception as e:
                    logger.error(f"Ошибка при проверке алиаса {alias}: {e}")
                    
        logger.info(f"Роль {role_type} и её алиасы не найдены у пользователя {user_id}")
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке роли: {e}")
        return False

# Патч для метода remove_role
original_remove_role = RoleService.remove_role

async def patched_remove_role(self, user_id: int, role_type: str, admin_id: int) -> bool:
    """
    Патч для метода remove_role, который добавляет поддержку алиасов ролей.
    Если роль 'content' не найдена, пытается удалить роль 'content_manager'.
    """
    # Создаем маппинг алиасов ролей
    role_aliases = {
        'content': ['content_manager'],
        'content_manager': ['content']
    }
    
    try:
        # Проверяем наличие роли или её алиасов
        real_role_to_remove = None
        
        # Проверяем основную роль
        has_role = await self.check_user_role(user_id, role_type)
        if has_role:
            real_role_to_remove = role_type
        else:
            # Проверяем алиасы
            if role_type in role_aliases:
                for alias in role_aliases[role_type]:
                    has_alias = await original_check_user_role(self, user_id, alias)
                    if has_alias:
                        logger.info(f"Найден алиас {alias} для роли {role_type}")
                        real_role_to_remove = alias
                        break
        
        if real_role_to_remove:
            logger.info(f"Удаление роли {real_role_to_remove} у пользователя {user_id}")
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
            # Если ни роль, ни алиасы не найдены
            logger.warning(f"Роль {role_type} и её алиасы не найдены у пользователя {user_id}")
            raise RoleNotFoundError(f"Роль {role_type} не найдена у пользователя")
            
    except Exception as e:
        logger.error(f"Ошибка при удалении роли: {e}")
        if isinstance(e, RoleNotFoundError):
            raise e
        return False

def apply_patches():
    """Применяет патчи к методам RoleService"""
    logger.info("Применение патчей к методам RoleService")
    RoleService.check_user_role = patched_check_user_role
    RoleService.remove_role = patched_remove_role
    logger.info("Патчи успешно применены")

def remove_patches():
    """Удаляет патчи и восстанавливает оригинальные методы"""
    logger.info("Восстановление оригинальных методов RoleService")
    RoleService.check_user_role = original_check_user_role
    RoleService.remove_role = original_remove_role
    logger.info("Оригинальные методы восстановлены")

async def test_patches():
    """Тестирует работу патчей"""
    # Загружаем переменные окружения
    load_dotenv()
    
    try:
        logger.info("Начало тестирования патчей")
        
        # Запрашиваем ID пользователя
        user_id_input = input("Введите ID пользователя для тестирования: ")
        if not user_id_input.strip():
            logger.error("ID пользователя не введен")
            return
            
        try:
            user_id = int(user_id_input.strip())
        except ValueError:
            logger.error(f"Некорректный ID пользователя: {user_id_input}")
            return
            
        # Создаем экземпляр сервиса
        role_service = RoleService()
        
        # Получаем текущие роли пользователя
        roles = await role_service.get_user_roles(user_id)
        logger.info(f"Текущие роли пользователя {user_id}: {roles}")
        
        # Проверяем наличие роли 'content' без патчей
        has_content_role = await role_service.check_user_role(user_id, "content")
        logger.info(f"Наличие роли 'content' без патчей: {has_content_role}")
        
        # Применяем патчи
        apply_patches()
        
        # Проверяем наличие роли 'content' с патчами
        has_content_role_patched = await role_service.check_user_role(user_id, "content")
        logger.info(f"Наличие роли 'content' с патчами: {has_content_role_patched}")
        
        # Тестируем удаление роли, если она есть
        if has_content_role_patched:
            admin_id = int(os.getenv("ADMIN_ID", "0"))
            if admin_id > 0:
                try:
                    logger.info(f"Попытка удалить роль 'content' у пользователя {user_id}")
                    result = await role_service.remove_role(user_id, "content", admin_id)
                    logger.info(f"Результат удаления роли 'content': {result}")
                    
                    # Проверяем, удалилась ли роль
                    roles_after = await role_service.get_user_roles(user_id)
                    logger.info(f"Роли пользователя {user_id} после удаления: {roles_after}")
                    
                except Exception as e:
                    logger.error(f"Ошибка при удалении роли 'content': {e}")
            else:
                logger.warning("Не удалось получить ADMIN_ID для тестирования удаления роли")
        else:
            logger.info(f"У пользователя {user_id} нет роли 'content' или её алиасов")
        
        # Восстанавливаем оригинальные методы
        remove_patches()
        
        logger.info("Тестирование патчей завершено")
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании патчей: {e}", exc_info=True)
        # Убедимся, что оригинальные методы восстановлены
        remove_patches()

async def create_permanent_patch():
    """Создает постоянный патч для исправления проблемы с ролями"""
    logger.info("Создание постоянного патча для app/services/role_service.py")
    
    # Здесь можно добавить код для создания файла с патчем или внесения изменений в исходный код
    # Например, создать файл с monkey patch, который будет загружаться при старте приложения
    
    patch_code = """
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
            return True
    else:
        # Используем оригинальный метод для генерации корректной ошибки
        return await original_remove_role(self, user_id, role_type, admin_id)

# Применяем патчи
RoleService.check_user_role = patched_check_user_role
RoleService.remove_role = patched_remove_role

logger.info("Патч для исправления проблемы с ролями успешно применен")
"""
    
    try:
        # Создаем директорию для патчей, если её нет
        patches_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "patches")
        os.makedirs(patches_dir, exist_ok=True)
        
        # Создаем файл с патчем
        patch_file = os.path.join(patches_dir, "role_aliases_patch.py")
        with open(patch_file, "w") as f:
            f.write(patch_code)
        logger.info(f"Патч создан и сохранен в файле {patch_file}")
        
        # Создаем или обновляем файл __init__.py в директории patches
        init_file = os.path.join(patches_dir, "__init__.py")
        with open(init_file, "w") as f:
            f.write("# Initialization file for patches package\n")
            f.write("from . import role_aliases_patch\n")
        logger.info(f"Файл инициализации патчей обновлен: {init_file}")
        
        # Проверяем наличие импорта патчей в основном файле app/__init__.py
        app_init = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "__init__.py")
        if os.path.exists(app_init):
            with open(app_init, "r") as f:
                content = f.read()
            
            if "from app.patches import" not in content:
                with open(app_init, "a") as f:
                    f.write("\n# Импорт патчей\ntry:\n    from app.patches import *\nexcept ImportError:\n    pass\n")
                logger.info(f"Добавлен импорт патчей в {app_init}")
            else:
                logger.info(f"Импорт патчей уже присутствует в {app_init}")
        else:
            logger.warning(f"Файл {app_init} не найден, невозможно добавить импорт патчей")
        
        logger.info("Постоянный патч успешно создан")
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании постоянного патча: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    # Выбираем действие
    print("Выберите действие:")
    print("1 - Протестировать временный патч")
    print("2 - Создать постоянный патч")
    choice = input("Введите номер действия (1 или 2): ")
    
    if choice.strip() == "1":
        asyncio.run(test_patches())
    elif choice.strip() == "2":
        asyncio.run(create_permanent_patch())
    else:
        print("Некорректный выбор. Запуск тестирования временного патча по умолчанию.")
        asyncio.run(test_patches()) 