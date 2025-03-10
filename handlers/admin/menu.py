from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from keyboards.admin.menu import get_admin_main_keyboard, get_back_to_menu_keyboard
from keyboards.admin.settings import get_settings_keyboard
from utils.logger import setup_logger

router = Router()
logger = setup_logger()

@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик возврата в главное меню админа.
    Завершает текущее состояние FSM если оно есть.
    
    Args:
        callback (CallbackQuery): Callback запрос
        state (FSMContext): Контекст состояния FSM
    """
    try:
        # Получаем текущее состояние
        current_state = await state.get_state()
        
        # Если есть активное состояние - завершаем его
        if current_state is not None:
            await state.clear()
            logger.info(f"Состояние {current_state} завершено при возврате в главное меню")
            
        # Удаляем предыдущее сообщение
        await callback.message.delete()
        
        # Отправляем новое сообщение с главным меню
        await callback.message.answer(
            'Вы находитесь в главном меню',
            reply_markup=get_admin_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при возврате в главное меню: {e}")
        await callback.message.answer(
            "Произошла ошибка при возврате в главное меню. Попробуйте еще раз."
        )

@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки настроек.
    Показывает меню настроек бота.
    
    Args:
        callback (CallbackQuery): Callback запрос
        state (FSMContext): Контекст состояния FSM
    """
    try:
        # Удаляем предыдущее сообщение
        await callback.message.delete()
        
        # Создаем текст с описанием настроек
        settings_text = (
            "⚙️ <b>Настройки бота</b>\n\n"
            "Здесь вы можете настроить параметры работы бота:\n"
            "• Управление базой данных\n"
            "• Настройка уведомлений\n"
            "• Параметры работы бота\n\n"
            "<i>Выберите раздел настроек:</i>"
        )
        
        # Отправляем сообщение с настройками и клавиатурой
        await callback.message.answer(
            settings_text,
            reply_markup=get_settings_keyboard(),
            parse_mode="HTML"
        )
        
        logger.info(f"Пользователь {callback.from_user.id} открыл меню настроек")
        
    except Exception as e:
        logger.error(f"Ошибка при открытии настроек: {e}")
        await callback.message.answer(
            "Произошла ошибка при открытии настроек. Попробуйте еще раз.",
            reply_markup=get_back_to_menu_keyboard()
        )

# Обработчики для подразделов настроек
@router.callback_query(F.data == "settings_database")
async def show_database_settings(callback: CallbackQuery):
    """Обработчик настроек базы данных"""
    try:
        await callback.message.edit_text(
            "🗄 <b>Настройки базы данных</b>\n\n"
            "В этом разделе вы можете управлять базой данных бота:\n"
            "• Просмотр статистики базы данных\n"
            "• Создание резервной копии\n"
            "• Восстановление из резервной копии\n\n"
            "<i>Функционал находится в разработке.</i>",
            reply_markup=get_settings_keyboard(),
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {callback.from_user.id} открыл настройки базы данных")
    except Exception as e:
        logger.error(f"Ошибка при открытии настроек базы данных: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

@router.callback_query(F.data == "settings_notifications")
async def show_notification_settings(callback: CallbackQuery):
    """Обработчик настроек уведомлений"""
    try:
        await callback.message.edit_text(
            "🔔 <b>Настройки уведомлений</b>\n\n"
            "В этом разделе вы можете настроить уведомления бота:\n"
            "• Включение/отключение уведомлений\n"
            "• Настройка времени отправки\n"
            "• Выбор типов уведомлений\n\n"
            "<i>Функционал находится в разработке.</i>",
            reply_markup=get_settings_keyboard(),
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {callback.from_user.id} открыл настройки уведомлений")
    except Exception as e:
        logger.error(f"Ошибка при открытии настроек уведомлений: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

@router.callback_query(F.data == "settings_bot_params")
async def show_bot_params_settings(callback: CallbackQuery):
    """Обработчик настроек параметров бота"""
    try:
        await callback.message.edit_text(
            "⚙️ <b>Параметры бота</b>\n\n"
            "В этом разделе вы можете настроить параметры работы бота:\n"
            "• Режим работы (активный/пассивный)\n"
            "• Ограничения доступа\n"
            "• Настройка автоматических действий\n\n"
            "<i>Функционал находится в разработке.</i>",
            reply_markup=get_settings_keyboard(),
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {callback.from_user.id} открыл параметры бота")
    except Exception as e:
        logger.error(f"Ошибка при открытии параметров бота: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.") 