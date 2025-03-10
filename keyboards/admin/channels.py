from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any, Optional

def get_channels_management_keyboard(channels: Optional[List[Dict[str, Any]]] = None) -> InlineKeyboardMarkup:
    """
    Клавиатура для управления каналами
    
    Args:
        channels: Список каналов
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками управления каналами
    """
    buttons = []
    
    # Добавляем кнопки для каждого канала, если они есть
    if channels:
        for channel in channels:
            channel_id = channel["id"]
            title = channel["title"]
            
            # Определяем маркер канала по умолчанию
            default_mark = " ✅" if channel["is_default"] else ""
            
            # Добавляем имя пользователя, если оно есть
            username_info = ""
            if channel.get("username"):
                username_info = f" (@{channel['username']})"
            
            # Создаем текст кнопки
            button_text = f"{title}{default_mark}{username_info}"
            
            buttons.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"channel_{channel_id}"
                )
            ])
    
    # Добавляем кнопку для добавления нового канала
    buttons.append([
        InlineKeyboardButton(text="➕ Добавить канал", callback_data="add_channel")
    ])
    
    # Добавляем кнопку для обновления списка каналов
    buttons.append([
        InlineKeyboardButton(text="🔄 Обновить список", callback_data="refresh_channels_list")
    ])
    
    # Добавляем кнопку для возврата в меню
    buttons.append([
        InlineKeyboardButton(text="🔙 Вернуться в меню", callback_data="back_to_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_channel_actions_keyboard(channel_id: int, is_default: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура действий с каналом
    
    Args:
        channel_id: ID канала
        is_default: Флаг канала по умолчанию
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с действиями для канала
    """
    buttons = []
    
    # Кнопка для установки канала по умолчанию (если он еще не установлен)
    if not is_default:
        buttons.append([
            InlineKeyboardButton(
                text="✓ Установить по умолчанию",
                callback_data=f"set_default_{channel_id}"
            )
        ])
    
    # Кнопка для удаления канала
    buttons.append([
        InlineKeyboardButton(
            text="🗑 Удалить канал",
            callback_data=f"delete_channel_{channel_id}"
        )
    ])
    
    # Кнопка для возврата к списку каналов
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_channels")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_confirm_delete_channel_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения удаления канала
    
    Args:
        channel_id: ID канала
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками подтверждения/отмены
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Да, удалить",
                callback_data=f"confirm_delete_{channel_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"channel_{channel_id}"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_to_channels_keyboard(show_continue: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура для возврата к списку каналов
    
    Args:
        show_continue: Флаг отображения кнопки "Продолжить"
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой возврата
    """
    buttons = []
    
    # Добавляем кнопку "Продолжить", если нужно
    if show_continue:
        buttons.append([
            InlineKeyboardButton(text="▶️ Продолжить", callback_data="continue")
        ])
    
    # Добавляем кнопку для возврата к списку каналов
    buttons.append([
        InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_channels")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons) 