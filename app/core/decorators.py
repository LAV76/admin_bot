import functools
from typing import Callable, Any, Optional, Union, Set, List
from aiogram import types
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from aiogram import Bot
from aiogram.methods import SendMessage

from app.core.exceptions import PermissionDeniedError
from app.core.logging import setup_logger
from app.services.access_control import check_user_role, get_access_control, has_permission

logger = setup_logger("core.decorators")

def admin_required(func: Callable) -> Callable:
    """
    Декоратор для проверки прав администратора.
    Позволяет выполнить функцию только если пользователь имеет роль admin.
    
    Args:
        func: Декорируемая функция
        
    Returns:
        Callable: Обёрнутая функция
    """
    @functools.wraps(func)
    async def wrapper(update: types.base.TelegramObject, *args, **kwargs):
        # Получаем ID пользователя из обновления
        user_id = _extract_user_id(update)
        
        if not user_id:
            logger.warning("Не удалось определить ID пользователя")
            return
        
        # Проверяем наличие роли администратора
        is_admin = await check_user_role(user_id, "admin")
        
        if not is_admin:
            logger.warning(
                f"Пользователь {user_id} пытается выполнить действие "
                f"без прав администратора"
            )
            
            # Отправляем сообщение о недостаточных правах
            await _send_permission_denied_message(update)
            return
        
        # Если пользователь администратор, выполняем функцию
        return await func(update, *args, **kwargs)
    
    return wrapper

def role_required(role_type: str) -> Callable:
    """
    Декоратор для проверки наличия определенной роли.
    Позволяет выполнить функцию только если пользователь имеет указанную роль.
    
    Args:
        role_type: Тип роли для проверки
        
    Returns:
        Callable: Декоратор для функции
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update: types.base.TelegramObject, *args, **kwargs):
            # Получаем ID пользователя из обновления
            user_id = _extract_user_id(update)
            
            if not user_id:
                logger.warning("Не удалось определить ID пользователя")
                return
            
            # Проверяем наличие указанной роли
            has_role = await check_user_role(user_id, role_type)
            
            if not has_role:
                logger.warning(
                    f"Пользователь {user_id} пытается выполнить действие "
                    f"без роли {role_type}"
                )
                
                # Отправляем сообщение о недостаточных правах
                await _send_permission_denied_message(update)
                return
            
            # Если пользователь имеет роль, выполняем функцию
            return await func(update, *args, **kwargs)
        
        return wrapper
    
    return decorator

def permission_required(
    permission: Union[str, List[str], Set[str]]
) -> Callable:
    """
    Декоратор, который проверяет наличие у пользователя указанных разрешений.
    
    Args:
        permission (Union[str, List[str], Set[str]]): Разрешение или список разрешений
        
    Returns:
        Callable: Декоратор, проверяющий наличие разрешений
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update: types.base.TelegramObject, *args, **kwargs):
            # Получаем ID пользователя из обновления
            user_id = _extract_user_id(update)
            if not user_id:
                logger.warning("Не удалось извлечь ID пользователя из обновления")
                return
                
            # Получаем все разрешения пользователя
            ac = await get_access_control()
            user_permissions = await ac.get_user_permissions(user_id)
            
            # Преобразуем входной параметр в множество
            required_permissions = {permission} if isinstance(permission, str) else set(permission)
            
            # Проверяем наличие всех требуемых разрешений
            if required_permissions.issubset(user_permissions):
                # Если у пользователя есть все разрешения, продолжаем выполнение
                return await func(update, *args, **kwargs)
            else:
                # Если нет нужных разрешений, отправляем сообщение об отказе
                missing = required_permissions - user_permissions
                logger.warning(f"Пользователь {user_id} не имеет разрешений: {missing}")
                await _send_permission_denied_message(update)
                return None
        
        return wrapper
    
    return decorator

def any_permission_required(
    permissions: Union[List[str], Set[str]]
) -> Callable:
    """
    Декоратор, который проверяет наличие у пользователя хотя бы одного разрешения из списка.
    
    Args:
        permissions (Union[List[str], Set[str]]): Список разрешений
        
    Returns:
        Callable: Декоратор, проверяющий наличие хотя бы одного разрешения
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update: types.base.TelegramObject, *args, **kwargs):
            # Получаем ID пользователя из обновления
            user_id = _extract_user_id(update)
            if not user_id:
                logger.warning("Не удалось извлечь ID пользователя из обновления")
                return
                
            # Получаем все разрешения пользователя
            ac = await get_access_control()
            user_permissions = await ac.get_user_permissions(user_id)
            
            # Преобразуем входной параметр в множество
            required_permissions = set(permissions)
            
            # Проверяем наличие хотя бы одного разрешения
            if user_permissions.intersection(required_permissions):
                # Если у пользователя есть хотя бы одно разрешение, продолжаем
                return await func(update, *args, **kwargs)
            else:
                # Если нет ни одного разрешения, отправляем сообщение об отказе
                logger.warning(f"Пользователь {user_id} не имеет ни одного из разрешений: {required_permissions}")
                await _send_permission_denied_message(update)
                return None
        
        return wrapper
    
    return decorator

async def check_admin_rights(user_id: int) -> bool:
    """
    Функция для проверки прав администратора по ID пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        bool: True, если пользователь администратор
    """
    return await check_user_role(user_id, "admin")

def _extract_user_id(update: types.base.TelegramObject) -> Optional[int]:
    """
    Извлекает ID пользователя из объекта обновления Telegram
    
    Args:
        update: Объект обновления Telegram
        
    Returns:
        Optional[int]: ID пользователя или None, если не удалось получить
    """
    if isinstance(update, Message):
        return update.from_user.id
    elif isinstance(update, CallbackQuery):
        return update.from_user.id
    else:
        # Для других типов обновлений
        try:
            if hasattr(update, "from_user") and update.from_user:
                return update.from_user.id
            elif hasattr(update, "message") and update.message:
                return update.message.from_user.id
        except (AttributeError, TypeError):
            pass
    
    return None

async def _send_permission_denied_message(
    update: types.base.TelegramObject
) -> None:
    """
    Отправляет сообщение о недостаточных правах
    
    Args:
        update: Объект обновления Telegram
    """
    message = "У вас недостаточно прав для выполнения этого действия."
    
    try:
        if isinstance(update, Message):
            await update.answer(message, parse_mode="HTML")
        elif isinstance(update, CallbackQuery):
            await update.answer(message, show_alert=True)
            # Также отправляем сообщение в чат для лучшей видимости
            await update.message.answer(message, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения о правах: {e}") 