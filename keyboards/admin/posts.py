from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any

def get_post_management_keyboard(post_id: int = None) -> InlineKeyboardMarkup:
    """
    Клавиатура для управления постами
    
    Args:
        post_id: Опциональный ID поста (не используется, но позволяет 
                избежать ошибки при вызове с параметром)
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для управления постами
    """
    buttons = [
        [
            InlineKeyboardButton(text="➕ Создать пост", callback_data="create_post")
        ],
        [
            InlineKeyboardButton(text="📋 Мои посты", callback_data="my_posts")
        ],
        [
            InlineKeyboardButton(text="🔍 Поиск по тегу", callback_data="search_posts_by_tag")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_post_creation_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для отмены создания поста
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой отмены
    """
    buttons = [
        [InlineKeyboardButton(text="🤖 Сгенерировать AI", callback_data="generate_post_ai")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_post_creation")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_post_list_keyboard(posts: List[Dict], page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком постов с пагинацией
    
    Args:
        posts: Список постов
        page: Текущая страница
        per_page: Количество постов на странице
        
    Returns:
        InlineKeyboardMarkup: Клавиатура со списком постов
    """
    buttons = []
    
    # Расчет пагинации
    total_pages = (len(posts) + per_page - 1) // per_page
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, len(posts))
    
    # Добавляем кнопки для каждого поста на текущей странице
    for i in range(start_idx, end_idx):
        post = posts[i]
        title = post.get("title", "")
        
        buttons.append([
            InlineKeyboardButton(
                text=title,
                callback_data=f"view_post_{post.get('id')}"
            )
        ])
    
    # Добавляем кнопки пагинации, если нужно
    nav_buttons = []
    
    if total_pages > 1:
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="◀️", callback_data=f"post_page_{page-1}")
            )
        
        nav_buttons.append(
            InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="ignore")
        )
        
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(text="▶️", callback_data=f"post_page_{page+1}")
            )
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Добавляем кнопку возврата
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_post_management")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_post_actions_keyboard(post_id: int, is_published: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура с действиями для поста
    
    Args:
        post_id: ID поста
        is_published: Флаг публикации поста
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками действий
    """
    buttons = []
    
    if not is_published:
        buttons.append([
            InlineKeyboardButton(
                text="📢 Опубликовать", 
                callback_data=f"publish_post_{post_id}"
            )
        ])
    
    # Добавляем кнопку редактирования поста
    buttons.append([
        InlineKeyboardButton(
            text="✏️ Редактировать", 
            callback_data=f"edit_post_{post_id}"
        )
    ])
    
    buttons.append([
        InlineKeyboardButton(
            text="❌ Удалить", 
            callback_data=f"delete_post_{post_id}"
        )
    ])
    
    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад", 
            callback_data="my_posts"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_confirm_delete_post_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения удаления поста
    
    Args:
        post_id: ID поста
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками подтверждения
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить удаление", 
                callback_data=f"confirm_delete_post_{post_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить", 
                callback_data=f"view_post_{post_id}"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_chat_selection_keyboard(chats: List[Dict[str, Any]], show_skip_button: bool = True) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора чата для публикации поста
    
    Args:
        chats: Список доступных чатов
        show_skip_button: Показывать ли кнопку пропуска (по умолчанию True)
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками выбора чата
    """
    buttons = []
    
    # Добавляем кнопки для каждого доступного чата
    for chat in chats:
        chat_id = chat.get("id")
        chat_title = chat.get("title", f"Чат {chat_id}")
        is_default = chat.get("is_default", False)
        
        # Добавляем метку для чата по умолчанию
        title_text = f"{chat_title} {'(по умолчанию)' if is_default else ''}"
        
        buttons.append([
            InlineKeyboardButton(
                text=title_text,
                callback_data=f"select_chat_{chat_id}"
            )
        ])
    
    # Добавляем кнопку "Пропустить" только если show_skip_button=True
    if show_skip_button:
        buttons.append([
            InlineKeyboardButton(
                text="⏩ Использовать канал по умолчанию",
                callback_data="skip_chat_selection"
            )
        ])
    
    # Добавляем кнопку отмены
    buttons.append([
        InlineKeyboardButton(
            text="❌ Отменить создание поста",
            callback_data="cancel_post_creation"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_save_post_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для сохранения поста
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для сохранения поста
    """
    buttons = [
        [
            InlineKeyboardButton(text="💾 Сохранить пост", callback_data="save_post"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_post_creation")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_after_publish_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру, отображаемую после публикации поста
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками дальнейших действий
    """
    buttons = [
        [
            InlineKeyboardButton(text="➕ Создать новый пост", callback_data="create_post")
        ],
        [
            InlineKeyboardButton(text="📋 Мои посты", callback_data="my_posts")
        ],
        [
            InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_skip_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой "Пропустить"
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой "Пропустить"
    """
    buttons = [
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip")],
        [InlineKeyboardButton(text="❌ Отменить создание поста", callback_data="cancel_post_creation")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_ai_generation_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для действий после генерации контента через AI
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками
    """
    buttons = [
        [InlineKeyboardButton(text="✅ Использовать", callback_data="use_ai_content")],
        [InlineKeyboardButton(text="🔄 Сгенерировать заново", callback_data="regenerate_ai")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_ai_generation")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons) 