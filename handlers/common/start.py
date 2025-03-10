from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import F
import os
from keyboards.admin.menu import get_admin_menu_keyboard
from db_handlers.user_role.check_user_role import check_user_role
from config.bot_config import ADMIN_IDS, is_admin
from utils.logger import setup_logger
from app.services.role_service import RoleService
from app.core.decorators import admin_required

router = Router()
logger = setup_logger()
role_service = RoleService()

def get_start_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой "Начать работу"
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой начала работы
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚀 Начать работу", callback_data="start_work")
            ]
        ]
    )
    return keyboard

@router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Обработчик команды /start
    Отображает приветственное сообщение и кнопку для начала работы
    """
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    logger.info(f"Пользователь {user_id} (@{username}) запустил команду /start")
    
    try:
        await message.answer(
            f"👋 Здравствуйте, {message.from_user.first_name}!\n\n"
            f"Это административный бот для управления пользователями и ролями.\n"
            f"Нажмите кнопку ниже, чтобы начать.",
            reply_markup=get_start_keyboard()
        )
        
        # Создаем пользователя в базе, если он еще не существует
        try:
            await role_service.create_user_if_not_exists(user_id=user_id)
            logger.info(f"Пользователь {user_id} создан или уже существует в базе")
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя {user_id}: {e}")
    
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)
        await message.answer('Произошла ошибка при запуске бота')

@router.callback_query(F.data == "start_work")
async def process_start_work(callback: CallbackQuery):
    """
    Обработчик нажатия на кнопку "Начать работу"
    Проверяет права пользователя и отображает соответствующее меню
    """
    user_id = callback.from_user.id
    username = callback.from_user.username or "Unknown"
    
    logger.info(f"Пользователь {user_id} (@{username}) нажал кнопку 'Начать работу'")
    
    try:
        # Проверяем, является ли пользователь администратором в .env файле
        admin_id_from_env = os.getenv("ADMIN_ID")
        if admin_id_from_env and int(admin_id_from_env) == user_id:
            logger.info(f"Пользователь {user_id} (@{username}) соответствует ADMIN_ID в .env файле")
        else:
            logger.info(f"Пользователь {user_id} (@{username}) НЕ соответствует ADMIN_ID в .env файле (ADMIN_ID={admin_id_from_env})")

        # Проверяем, является ли пользователь администратором через сервис ролей
        is_admin_role = await role_service.check_user_role(user_id, "admin")
        logger.info(f"Результат проверки роли для пользователя {user_id}: is_admin={is_admin_role}")
        
        if is_admin_role:
            logger.info(f"Пользователь {user_id} (@{username}) вошел как администратор")
            await callback.message.edit_text(
                '✅ Вы вошли как администратор\n'
                'Выберите действие из меню:',
                reply_markup=get_admin_menu_keyboard()
            )
        else:
            logger.info(f"Пользователь {user_id} (@{username}) не имеет прав администратора")
            await callback.message.edit_text(
                '❌ У вас нет прав администратора\n'
                'Обратитесь к владельцу бота для получения доступа.'
            )
        
    except Exception as e:
        logger.error(f"Ошибка при проверке роли пользователя {user_id}: {e}", exc_info=True)
        await callback.message.edit_text('Произошла ошибка при проверке ваших прав')

# Оставляем старую функцию для совместимости, но переименовываем
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """
    Обработчик команды /admin
    Проверяет права администратора через базу данных и переменные окружения
    """
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    logger.info(f"Пользователь {user_id} (@{username}) запустил команду /admin")
    
    try:
        # Проверяем, является ли пользователь администратором по ID
        admin_by_id = is_admin(user_id)
        logger.info(f"Проверка по ID: {user_id} в списке {ADMIN_IDS} = {admin_by_id}")
        
        # Если пользователь администратор по ID, сразу даем доступ
        if admin_by_id:
            logger.info(f"Пользователь {user_id} (@{username}) вошел как администратор по ID")
            await message.answer(
                'Вы вошли как администратор',
                reply_markup=get_admin_menu_keyboard()
            )
            return
        
        # Проверяем роль через сервис
        admin_by_role = await role_service.check_user_role(user_id, "admin")
        
        if admin_by_role:
            logger.info(f"Пользователь {user_id} (@{username}) вошел как администратор по роли")
            await message.answer(
                'Вы вошли как администратор',
                reply_markup=get_admin_menu_keyboard()
            )
            return
        
        # Если пользователь не администратор
        logger.info(f"Пользователь {user_id} (@{username}) не имеет прав администратора")
        await message.answer('У вас нет прав администратора')
            
    except Exception as e:
        logger.error(f"Ошибка при проверке роли пользователя {user_id}: {e}", exc_info=True)
        await message.answer('Произошла ошибка при проверке ваших прав') 