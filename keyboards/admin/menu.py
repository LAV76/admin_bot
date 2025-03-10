from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт главную клавиатуру администратора
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(text="Управление ролями", callback_data="manage_roles"),
            InlineKeyboardButton(text="История изменений", callback_data="role_history")
        ],
        [
            InlineKeyboardButton(text="Управление постами", callback_data="manage_posts")
        ],
        [
            InlineKeyboardButton(text="Управление каналами", callback_data="manage_channels")
        ],
        [
            InlineKeyboardButton(text="Настройки", callback_data="settings")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_role_selection_keyboard(remove: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура выбора роли"""
    prefix = "remove_" if remove else "take_user_role_"
    buttons = [
        [
            InlineKeyboardButton(
                text="👑 Администратор",
                callback_data=f"{prefix}admin"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Контент-менеджер",
                callback_data=f"{prefix}content_manager"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="back_to_menu"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_role_list_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру со списком действий для управления ролями
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками действий с ролями
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="➕ Добавить роль пользователю",
                callback_data="add_user_role"
            )
        ],
        [
            InlineKeyboardButton(
                text="➖ Удалить роль пользователя",
                callback_data="remove_user_role"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Вернуться в меню",
                callback_data="back_to_menu"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data="confirm_action"
            ),
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="cancel_action"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой возврата в меню"""
    buttons = [
        [
            InlineKeyboardButton(
                text="🔙 Вернуться в меню",
                callback_data="back_to_menu"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_to_role_selection_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой возврата к выбору роли
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой возврата
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🔙 Вернуться к выбору роли",
                callback_data="back_to_role_selection"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_menu_keyboard():
    """
    Создает клавиатуру с меню администратора
    """
    buttons = [
        [
            InlineKeyboardButton(text="Управление ролями", callback_data="manage_roles"),
            InlineKeyboardButton(text="История изменений", callback_data="role_history")
        ],
        [
            InlineKeyboardButton(text="Управление постами", callback_data="manage_posts")
        ],
        [
            InlineKeyboardButton(text="Управление каналами", callback_data="manage_channels")
        ],
        [
            InlineKeyboardButton(text="Настройки", callback_data="settings")
        ]
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def get_back_to_menu_keyboard():
    """
    Создает клавиатуру с кнопкой возврата в главное меню
    """
    buttons = [
        [
            InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_menu")
        ]
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с главным меню пользователя
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(text="📝 Создать пост", callback_data="create_post")
        ],
        [
            InlineKeyboardButton(text="📋 Мои посты", callback_data="my_posts")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons) 