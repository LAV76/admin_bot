import re
from typing import List, Optional

def format_tags(tags: str) -> str:
    """
    Форматирует строку тегов, добавляя символ # перед каждым тегом
    
    Args:
        tags: Строка с тегами, разделенными пробелами
        
    Returns:
        str: Отформатированная строка тегов с # перед каждым тегом
    """
    if not tags:
        return ""
    
    # Разбиваем строку на отдельные теги
    tag_list = tags.split()
    
    # Форматируем каждый тег, добавляя #
    formatted_tags = ' '.join([f"#{tag}" for tag in tag_list])
    
    return formatted_tags

def clean_tag(tag: str) -> str:
    """
    Очищает тег от специальных символов, оставляя только буквы, цифры и знак подчеркивания
    
    Args:
        tag: Исходный тег
        
    Returns:
        str: Очищенный тег
    """
    if not tag:
        return ""
    
    # Удаляем все, кроме букв, цифр и знака подчеркивания
    return ''.join(c for c in tag.strip() if c.isalnum() or c == '_')

def parse_tags(tag_input: str) -> List[str]:
    """
    Разбирает строку с тегами, разделенными запятыми или пробелами
    
    Args:
        tag_input: Строка с тегами, разделенными запятыми или пробелами
        
    Returns:
        List[str]: Список тегов
    """
    if not tag_input:
        return []
    
    # Разбиваем строку на отдельные теги
    raw_tags = re.split(r'[,\s]+', tag_input)
    tags = []
    
    for tag in raw_tags:
        if tag and not tag.isspace():
            # Очищаем тег от специальных символов
            clean_tag_value = clean_tag(tag)
            if clean_tag_value:
                tags.append(clean_tag_value)
    
    return tags

def format_html_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Форматирует текст для использования в HTML-разметке
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина текста (если указана)
        
    Returns:
        str: Отформатированный текст
    """
    if not text:
        return ""
    
    # Если указана максимальная длина, обрезаем текст
    if max_length and len(text) > max_length:
        return text[:max_length] + "..."
    
    return text 