from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict

def get_role_selection_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора действия с ролями
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками действий
    """
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить роль", callback_data="add_user_role")],
        [InlineKeyboardButton(text="➖ Удалить роль", callback_data="remove_user_role")],
        [InlineKeyboardButton(text="📋 Список пользователей с ролями", callback_data="list_roles")],
        [InlineKeyboardButton(text="🔄 История изменений", callback_data="role_history")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_to_role_selection_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для возврата к выбору действия с ролями
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой возврата
    """
    keyboard = [
        [InlineKeyboardButton(text="◀️ Назад к выбору действия", callback_data="back_to_role_selection")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_role_list_keyboard(roles: List[Dict], action: str) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком доступных ролей
    
    Args:
        roles: Список ролей в формате [{id: int, name: str}, ...]
        action: Действие с ролью (add/remove)
        
    Returns:
        InlineKeyboardMarkup: Клавиатура со списком ролей
    """
    keyboard = []
    
    for role in roles:
        keyboard.append([
            InlineKeyboardButton(
                text=role['name'], 
                callback_data=f"{action}_role_{role['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_role_selection")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_user_roles_keyboard(roles: List[Dict], user_id: str) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком ролей пользователя для удаления
    
    Args:
        roles: Список ролей пользователя в формате [{id: int, name: str}, ...]
        user_id: ID пользователя
        
    Returns:
        InlineKeyboardMarkup: Клавиатура со списком ролей
    """
    keyboard = []
    
    for role in roles:
        keyboard.append([
            InlineKeyboardButton(
                text=f"❌ {role['name']}", 
                callback_data=f"remove_user_role_{user_id}_{role['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_role_selection")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_confirm_action_keyboard(action: str, user_id: str, role_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для подтверждения действия с ролью
    
    Args:
        action: Действие с ролью (add/remove)
        user_id: ID пользователя
        role_id: ID роли
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками подтверждения
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить", 
                callback_data=f"confirm_{action}_role_{user_id}_{role_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить", 
                callback_data="back_to_role_selection"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 