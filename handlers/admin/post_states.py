from aiogram.fsm.state import State, StatesGroup

class PostStates(StatesGroup):
    """Состояния для создания поста"""
    title = State()           # Ожидание ввода названия поста
    content = State()         # Ожидание ввода описания поста
    image = State()           # Ожидание отправки изображения
    tag = State()             # Ожидание ввода тега поста 
    select_chat = State()     # Ожидание выбора чата для публикации
    
    # Новые состояния для генерации контента с AI
    ai_prompt = State()       # Ожидание ввода подсказки для AI
    ai_generating = State()   # Состояние генерации контента 