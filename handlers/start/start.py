from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config.bot_config import bot, ADMIN_ID

# Создание роутера для обработки команды /start
router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
    """
    Обработчик команды /start
    Проверяет, является ли пользователь администратором
    """
    user_id = message.from_user.id
    if str(user_id) == ADMIN_ID:
        # Если пользователь админ - показываем приветствие
        await message.answer(
            'Вошли как администратор. Используйте доступные команды для управления ботом.'
        )
    else:
        # Если не админ - отправляем сообщение об отказе
        await message.answer('Вы не администратор!')
