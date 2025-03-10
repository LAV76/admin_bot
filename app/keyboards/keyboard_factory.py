"""
Фабрика для создания клавиатур разных типов.
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)


class KeyboardFactory:
    """
    Фабрика для создания клавиатур разных типов.
    Реализует паттерн Factory Method.
    """
    
    @staticmethod
    def create_inline_keyboard(
        buttons: List[List[Dict[str, str]]],
        row_width: int = 2
    ) -> InlineKeyboardMarkup:
        """
        Создает inline клавиатуру из списка кнопок
        
        Args:
            buttons: Список списков словарей с параметрами кнопок.
                Каждый словарь должен содержать ключи 'text' и 'callback_data'.
                Пример: [[{'text': 'Кнопка 1', 'callback_data': 'btn1'}]]
            row_width: Максимальное количество кнопок в ряду
            
        Returns:
            InlineKeyboardMarkup: Созданная клавиатура
        """
        keyboard = InlineKeyboardMarkup(row_width=row_width)
        
        for row in buttons:
            keyboard_row = []
            for button in row:
                # Проверяем наличие обязательных ключей
                if 'text' not in button:
                    raise ValueError("Кнопка должна содержать ключ 'text'")
                
                # Создаем кнопку в зависимости от переданных параметров
                if 'url' in button:
                    keyboard_row.append(
                        InlineKeyboardButton(
                            text=button['text'],
                            url=button['url']
                        )
                    )
                elif 'callback_data' in button:
                    keyboard_row.append(
                        InlineKeyboardButton(
                            text=button['text'],
                            callback_data=button['callback_data']
                        )
                    )
                elif 'switch_inline_query' in button:
                    keyboard_row.append(
                        InlineKeyboardButton(
                            text=button['text'],
                            switch_inline_query=button['switch_inline_query']
                        )
                    )
                elif 'switch_inline_query_current_chat' in button:
                    keyboard_row.append(
                        InlineKeyboardButton(
                            text=button['text'],
                            switch_inline_query_current_chat=button['switch_inline_query_current_chat']
                        )
                    )
                else:
                    raise ValueError(
                        "Кнопка должна содержать один из ключей: "
                        "'url', 'callback_data', 'switch_inline_query', "
                        "'switch_inline_query_current_chat'"
                    )
            
            # Добавляем ряд кнопок в клавиатуру
            keyboard.inline_keyboard.append(keyboard_row)
        
        return keyboard
    
    @staticmethod
    def create_reply_keyboard(
        buttons: List[List[str]],
        resize_keyboard: bool = True,
        one_time_keyboard: bool = False,
        selective: bool = False,
        input_field_placeholder: Optional[str] = None
    ) -> ReplyKeyboardMarkup:
        """
        Создает обычную клавиатуру из списка кнопок
        
        Args:
            buttons: Список списков строк с текстом кнопок
                Пример: [['Кнопка 1', 'Кнопка 2'], ['Кнопка 3']]
            resize_keyboard: Подгонять размер клавиатуры под количество кнопок
            one_time_keyboard: Скрывать клавиатуру после нажатия
            selective: Показывать клавиатуру только определенным пользователям
            input_field_placeholder: Текст-подсказка в поле ввода
            
        Returns:
            ReplyKeyboardMarkup: Созданная клавиатура
        """
        keyboard = ReplyKeyboardMarkup(
            resize_keyboard=resize_keyboard,
            one_time_keyboard=one_time_keyboard,
            selective=selective,
            input_field_placeholder=input_field_placeholder
        )
        
        for row in buttons:
            keyboard_row = []
            for button_text in row:
                keyboard_row.append(KeyboardButton(text=button_text))
            
            # Добавляем ряд кнопок в клавиатуру
            keyboard.keyboard.append(keyboard_row)
        
        return keyboard
    
    @staticmethod
    def create_contact_keyboard(
        text: str = "Отправить контакт",
        resize_keyboard: bool = True,
        one_time_keyboard: bool = True,
        selective: bool = False
    ) -> ReplyKeyboardMarkup:
        """
        Создает клавиатуру с кнопкой запроса контакта
        
        Args:
            text: Текст кнопки
            resize_keyboard: Подгонять размер клавиатуры под количество кнопок
            one_time_keyboard: Скрывать клавиатуру после нажатия
            selective: Показывать клавиатуру только определенным пользователям
            
        Returns:
            ReplyKeyboardMarkup: Созданная клавиатура
        """
        keyboard = ReplyKeyboardMarkup(
            resize_keyboard=resize_keyboard,
            one_time_keyboard=one_time_keyboard,
            selective=selective
        )
        
        keyboard.keyboard.append([
            KeyboardButton(text=text, request_contact=True)
        ])
        
        return keyboard
    
    @staticmethod
    def create_location_keyboard(
        text: str = "Отправить местоположение",
        resize_keyboard: bool = True,
        one_time_keyboard: bool = True,
        selective: bool = False
    ) -> ReplyKeyboardMarkup:
        """
        Создает клавиатуру с кнопкой запроса местоположения
        
        Args:
            text: Текст кнопки
            resize_keyboard: Подгонять размер клавиатуры под количество кнопок
            one_time_keyboard: Скрывать клавиатуру после нажатия
            selective: Показывать клавиатуру только определенным пользователям
            
        Returns:
            ReplyKeyboardMarkup: Созданная клавиатура
        """
        keyboard = ReplyKeyboardMarkup(
            resize_keyboard=resize_keyboard,
            one_time_keyboard=one_time_keyboard,
            selective=selective
        )
        
        keyboard.keyboard.append([
            KeyboardButton(text=text, request_location=True)
        ])
        
        return keyboard
    
    @staticmethod
    def create_remove_keyboard(selective: bool = False) -> ReplyKeyboardRemove:
        """
        Создает объект для удаления клавиатуры
        
        Args:
            selective: Удалять клавиатуру только у определенных пользователей
            
        Returns:
            ReplyKeyboardRemove: Объект для удаления клавиатуры
        """
        return ReplyKeyboardRemove(selective=selective) 