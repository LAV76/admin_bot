"""
Декораторы для проверки ролей пользователей
"""

from typing import List, Callable, Dict, Any, Optional, Union
from functools import wraps

from aiogram import types
from aiogram.fsm.context import FSMContext

from app.services.role_service import RoleService
from app.core.logging import setup_logger

# Настройка логирования
logger = setup_logger("decorators.role_check")


def role_required(role_name: Union[str, List[str]]):
    """
    Декоратор для проверки роли пользователя
    
    Args:
        role_name: Имя роли или список ролей, необходимых для выполнения функции
        
    Returns:
        Callable: Декорированная функция
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(event: Union[types.Message, types.CallbackQuery], *args, **kwargs):
            # Получаем ID пользователя
            user_id = event.from_user.id
            
            # Если переданы FSMContext или state в аргументах, используем их
            state = kwargs.get('state')
            if not state:
                for arg in args:
                    if isinstance(arg, FSMContext):
                        state = arg
                        break

            # Проверяем роль пользователя
            role_service = RoleService()
            
            # Если передана одна роль
            if isinstance(role_name, str):
                has_role = await role_service.check_user_role(user_id, role_name)
                roles_to_check = [role_name]
            # Если передан список ролей
            else:
                has_role = False
                roles_to_check = role_name
                for role in roles_to_check:
                    if await role_service.check_user_role(user_id, role):
                        has_role = True
                        break
            
            # Если у пользователя нет нужной роли
            if not has_role:
                logger.warning(f"Пользователь {user_id} не имеет требуемой роли {roles_to_check}")
                
                # Формируем сообщение об ошибке
                if isinstance(roles_to_check, list) and len(roles_to_check) > 1:
                    roles_text = ", ".join(roles_to_check)
                    message_text = f"⛔ У вас недостаточно прав для этого действия.\nТребуется одна из ролей: {roles_text}"
                else:
                    message_text = f"⛔ У вас недостаточно прав для этого действия.\nТребуется роль: {roles_to_check[0] if isinstance(roles_to_check, list) else roles_to_check}"
                
                # Отправляем сообщение об ошибке
                if isinstance(event, types.Message):
                    await event.answer(message_text)
                elif isinstance(event, types.CallbackQuery):
                    await event.answer(message_text, show_alert=True)
                    
                # Если есть FSM состояние, очищаем его
                if state:
                    await state.clear()
                    
                return None
            
            # Если роль проверена, выполняем функцию
            logger.debug(f"Пользователь {user_id} прошел проверку роли {roles_to_check}")
            return await func(event, *args, **kwargs)
            
        return wrapper
    return decorator


def admin_required(func: Callable):
    """
    Декоратор для проверки роли администратора
    
    Args:
        func: Декорируемая функция
        
    Returns:
        Callable: Декорированная функция
    """
    return role_required("admin")(func)


def content_manager_required(func: Callable):
    """
    Декоратор для проверки роли контент-менеджера
    
    Args:
        func: Декорируемая функция
        
    Returns:
        Callable: Декорированная функция
    """
    return role_required(["admin", "content_manager"])(func) 