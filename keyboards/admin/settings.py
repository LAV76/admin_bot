from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек бота"""
    buttons = [
        [
            InlineKeyboardButton(text="🗄 База данных", callback_data="settings_database")
        ],
        [
            InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings_notifications")
        ],
        [
            InlineKeyboardButton(text="⚙️ Параметры бота", callback_data="settings_bot_params")
        ],
        [
            InlineKeyboardButton(text="🔙 Вернуться в меню", callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_database_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек базы данных"""
    buttons = [
        [
            InlineKeyboardButton(text="📊 Статистика БД", callback_data="db_stats")
        ],
        [
            InlineKeyboardButton(text="💾 Создать резервную копию", callback_data="db_backup")
        ],
        [
            InlineKeyboardButton(text="📥 Восстановить из копии", callback_data="db_restore")
        ],
        [
            InlineKeyboardButton(text="🔄 Очистить историю", callback_data="db_clear_history")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад к настройкам", callback_data="settings")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_notification_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек уведомлений"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Включить уведомления", callback_data="notif_enable")
        ],
        [
            InlineKeyboardButton(text="❌ Отключить уведомления", callback_data="notif_disable")
        ],
        [
            InlineKeyboardButton(text="⏰ Настроить расписание", callback_data="notif_schedule")
        ],
        [
            InlineKeyboardButton(text="📝 Типы уведомлений", callback_data="notif_types")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад к настройкам", callback_data="settings")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_bot_params_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура параметров бота"""
    buttons = [
        [
            InlineKeyboardButton(text="🟢 Активный режим", callback_data="bot_active_mode")
        ],
        [
            InlineKeyboardButton(text="🔴 Пассивный режим", callback_data="bot_passive_mode")
        ],
        [
            InlineKeyboardButton(text="🔒 Ограничения доступа", callback_data="bot_access")
        ],
        [
            InlineKeyboardButton(text="⚡ Автоматические действия", callback_data="bot_auto_actions")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад к настройкам", callback_data="settings")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_backup_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения резервного копирования"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="backup_confirm")
        ],
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data="settings_database")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_restore_confirm_keyboard(backup_id: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения восстановления из резервной копии"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"restore_confirm_{backup_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data="settings_database")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_clear_history_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения очистки истории"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Подтвердить очистку", callback_data="clear_history_confirm")
        ],
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data="settings_database")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons) 