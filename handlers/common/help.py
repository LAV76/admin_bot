from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from utils.logger import setup_logger

router = Router()
logger = setup_logger()

@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Обработчик команды /help
    Отправляет справочную информацию о боте
    """
    try:
        help_text = (
            "📚 <b>Справка по использованию бота</b>\n\n"
            "<b>Основные команды:</b>\n"
            "/start - Запустить бота\n"
            "/help - Показать эту справку\n\n"
            "<b>Для администраторов:</b>\n"
            "• Управление ролями пользователей\n"
            "• Просмотр истории изменений\n"
            "• Настройка параметров бота\n\n"
            "<i>Для получения дополнительной информации обратитесь к документации.</i>"
        )
        
        await message.answer(help_text, parse_mode="HTML")
        logger.info(f"Пользователь {message.from_user.id} запросил справку")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке справки: {e}")
        await message.answer("Произошла ошибка при отображении справки. Попробуйте позже.") 