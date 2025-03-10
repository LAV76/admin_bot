from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from keyboards.admin.settings import (
    get_settings_keyboard,
    get_database_settings_keyboard,
    get_notification_settings_keyboard,
    get_bot_params_keyboard,
    get_backup_confirm_keyboard,
    get_restore_confirm_keyboard,
    get_clear_history_confirm_keyboard
)
from keyboards.admin.menu import get_back_to_menu_keyboard
from utils.logger import setup_logger
from utils.database_backup import create_backup, restore_backup, get_database_stats, get_available_backups, clear_role_history
import os

router = Router()
logger = setup_logger()

@router.callback_query(F.data == "settings_database")
async def show_database_settings(callback: CallbackQuery, state: FSMContext):
    """Обработчик настроек базы данных"""
    try:
        await callback.message.edit_text(
            "🗄 <b>Настройки базы данных</b>\n\n"
            "В этом разделе вы можете управлять базой данных бота:",
            reply_markup=get_database_settings_keyboard(),
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {callback.from_user.id} открыл настройки базы данных")
    except Exception as e:
        logger.error(f"Ошибка при открытии настроек базы данных: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

@router.callback_query(F.data == "settings_notifications")
async def show_notification_settings(callback: CallbackQuery, state: FSMContext):
    """Обработчик настроек уведомлений"""
    try:
        await callback.message.edit_text(
            "🔔 <b>Настройки уведомлений</b>\n\n"
            "В этом разделе вы можете настроить уведомления бота:",
            reply_markup=get_notification_settings_keyboard(),
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {callback.from_user.id} открыл настройки уведомлений")
    except Exception as e:
        logger.error(f"Ошибка при открытии настроек уведомлений: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

@router.callback_query(F.data == "settings_bot_params")
async def show_bot_params_settings(callback: CallbackQuery, state: FSMContext):
    """Обработчик настроек параметров бота"""
    try:
        await callback.message.edit_text(
            "⚙️ <b>Параметры бота</b>\n\n"
            "В этом разделе вы можете настроить параметры работы бота:",
            reply_markup=get_bot_params_keyboard(),
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {callback.from_user.id} открыл параметры бота")
    except Exception as e:
        logger.error(f"Ошибка при открытии параметров бота: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

# Обработчики для действий с базой данных
@router.callback_query(F.data == "db_stats")
async def show_database_stats(callback: CallbackQuery):
    """Обработчик показа статистики базы данных"""
    try:
        # Получаем статистику базы данных
        stats = await get_database_stats()
        
        # Формируем сообщение со статистикой
        stats_text = (
            "📊 <b>Статистика базы данных</b>\n\n"
            f"<b>Общая информация:</b>\n"
            f"• Размер базы данных: {stats['db_size']}\n"
            f"• Количество таблиц: {stats['tables_count']}\n\n"
            f"<b>Таблицы:</b>\n"
        )
        
        # Добавляем информацию о таблицах
        for table, count in stats['tables_data'].items():
            stats_text += f"• {table}: {count} записей\n"
        
        # Отправляем сообщение с результатами
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_database_settings_keyboard(),
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {callback.from_user.id} просмотрел статистику базы данных")
    except Exception as e:
        logger.error(f"Ошибка при получении статистики базы данных: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при получении статистики базы данных.",
            reply_markup=get_database_settings_keyboard()
        )

@router.callback_query(F.data == "db_backup")
async def backup_database(callback: CallbackQuery):
    """Обработчик создания резервной копии базы данных"""
    try:
        await callback.message.edit_text(
            "💾 <b>Создание резервной копии</b>\n\n"
            "Вы уверены, что хотите создать резервную копию базы данных?",
            reply_markup=get_backup_confirm_keyboard(),
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {callback.from_user.id} запросил создание резервной копии базы данных")
    except Exception as e:
        logger.error(f"Ошибка при создании резервной копии базы данных: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

@router.callback_query(F.data == "backup_confirm")
async def confirm_backup_database(callback: CallbackQuery):
    """Обработчик подтверждения создания резервной копии"""
    try:
        # Отправляем сообщение о начале создания резервной копии
        await callback.message.edit_text(
            "⏳ <b>Создание резервной копии...</b>\n\n"
            "Пожалуйста, подождите. Это может занять некоторое время.",
            parse_mode="HTML"
        )
        
        # Создаем резервную копию
        backup_file = await create_backup()
        
        if not backup_file:
            # Если не удалось создать резервную копию
            await callback.message.edit_text(
                "❌ <b>Ошибка!</b>\n\n"
                "Не удалось создать резервную копию базы данных.",
                reply_markup=get_database_settings_keyboard(),
                parse_mode="HTML"
            )
            return
        
        # Отправляем файл с резервной копией
        await callback.message.answer_document(
            FSInputFile(backup_file),
            caption=f"💾 <b>Резервная копия базы данных</b>\n\nФайл: {os.path.basename(backup_file)}\nДата: {os.path.getmtime(backup_file)}",
            parse_mode="HTML"
        )
        
        # Отправляем сообщение об успешном создании резервной копии
        await callback.message.edit_text(
            "✅ <b>Резервная копия создана!</b>\n\n"
            f"Файл резервной копии: {os.path.basename(backup_file)}",
            reply_markup=get_database_settings_keyboard(),
            parse_mode="HTML"
        )
        
        logger.info(f"Пользователь {callback.from_user.id} создал резервную копию базы данных: {backup_file}")
    except Exception as e:
        logger.error(f"Ошибка при создании резервной копии базы данных: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка!</b>\n\n"
            f"Произошла ошибка при создании резервной копии: {str(e)}",
            reply_markup=get_database_settings_keyboard(),
            parse_mode="HTML"
        )

@router.callback_query(F.data == "db_restore")
async def restore_database(callback: CallbackQuery):
    """Обработчик восстановления базы данных из резервной копии"""
    try:
        # Получаем список доступных резервных копий
        backups = await get_available_backups()
        
        if not backups:
            # Если нет доступных резервных копий
            await callback.message.edit_text(
                "❌ <b>Ошибка!</b>\n\n"
                "Нет доступных резервных копий для восстановления.",
                reply_markup=get_database_settings_keyboard(),
                parse_mode="HTML"
            )
            return
        
        # Создаем сообщение со списком доступных резервных копий
        message_text = "📥 <b>Восстановление из резервной копии</b>\n\n"
        message_text += "Выберите резервную копию для восстановления:\n\n"
        
        for idx, backup in enumerate(backups):
            backup_name = os.path.basename(backup)
            backup_date = os.path.getmtime(backup)
            message_text += f"{idx + 1}. {backup_name} ({backup_date})\n"
        
        # Используем последнюю резервную копию по умолчанию
        latest_backup = backups[-1]
        backup_id = os.path.basename(latest_backup)
        
        await callback.message.edit_text(
            message_text,
            reply_markup=get_restore_confirm_keyboard(backup_id),
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {callback.from_user.id} запросил восстановление базы данных из резервной копии")
    except Exception as e:
        logger.error(f"Ошибка при восстановлении базы данных: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

@router.callback_query(F.data.startswith("restore_confirm_"))
async def confirm_restore_database(callback: CallbackQuery):
    """Обработчик подтверждения восстановления базы данных"""
    try:
        # Получаем имя файла резервной копии из callback_data
        backup_id = callback.data.replace("restore_confirm_", "")
        backup_file = os.path.join("backups", backup_id)
        
        # Проверяем существование файла
        if not os.path.exists(backup_file):
            await callback.message.edit_text(
                "❌ <b>Ошибка!</b>\n\n"
                f"Файл резервной копии не найден: {backup_id}",
                reply_markup=get_database_settings_keyboard(),
                parse_mode="HTML"
            )
            return
        
        # Отправляем сообщение о начале восстановления
        await callback.message.edit_text(
            "⏳ <b>Восстановление из резервной копии...</b>\n\n"
            "Пожалуйста, подождите. Это может занять некоторое время.",
            parse_mode="HTML"
        )
        
        # Восстанавливаем базу данных из резервной копии
        success = await restore_backup(backup_file)
        
        if not success:
            # Если не удалось восстановить из резервной копии
            await callback.message.edit_text(
                "❌ <b>Ошибка!</b>\n\n"
                "Не удалось восстановить базу данных из резервной копии.",
                reply_markup=get_database_settings_keyboard(),
                parse_mode="HTML"
            )
            return
        
        # Отправляем сообщение об успешном восстановлении
        await callback.message.edit_text(
            "✅ <b>База данных восстановлена!</b>\n\n"
            f"Восстановление выполнено из файла: {os.path.basename(backup_file)}",
            reply_markup=get_database_settings_keyboard(),
            parse_mode="HTML"
        )
        
        logger.info(f"Пользователь {callback.from_user.id} восстановил базу данных из резервной копии: {backup_file}")
    except Exception as e:
        logger.error(f"Ошибка при восстановлении базы данных: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка!</b>\n\n"
            f"Произошла ошибка при восстановлении базы данных: {str(e)}",
            reply_markup=get_database_settings_keyboard(),
            parse_mode="HTML"
        )

@router.callback_query(F.data == "db_clear_history")
async def clear_database_history(callback: CallbackQuery):
    """Обработчик очистки истории базы данных"""
    try:
        await callback.message.edit_text(
            "🔄 <b>Очистка истории изменений ролей</b>\n\n"
            "Вы уверены, что хотите очистить всю историю изменений ролей? Это действие нельзя отменить.",
            reply_markup=get_clear_history_confirm_keyboard(),
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {callback.from_user.id} запросил очистку истории изменений ролей")
    except Exception as e:
        logger.error(f"Ошибка при запросе очистки истории: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

@router.callback_query(F.data == "clear_history_confirm")
async def confirm_clear_history(callback: CallbackQuery):
    """Обработчик подтверждения очистки истории"""
    try:
        # Отправляем сообщение о начале очистки
        await callback.message.edit_text(
            "⏳ <b>Очистка истории...</b>\n\n"
            "Пожалуйста, подождите.",
            parse_mode="HTML"
        )
        
        # Очищаем историю изменений ролей
        success = await clear_role_history()
        
        if not success:
            # Если не удалось очистить историю
            await callback.message.edit_text(
                "❌ <b>Ошибка!</b>\n\n"
                "Не удалось очистить историю изменений ролей.",
                reply_markup=get_database_settings_keyboard(),
                parse_mode="HTML"
            )
            return
        
        # Отправляем сообщение об успешной очистке
        await callback.message.edit_text(
            "✅ <b>История очищена!</b>\n\n"
            "История изменений ролей была успешно очищена.",
            reply_markup=get_database_settings_keyboard(),
            parse_mode="HTML"
        )
        
        logger.info(f"Пользователь {callback.from_user.id} очистил историю изменений ролей")
    except Exception as e:
        logger.error(f"Ошибка при очистке истории: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка!</b>\n\n"
            f"Произошла ошибка при очистке истории: {str(e)}",
            reply_markup=get_database_settings_keyboard(),
            parse_mode="HTML"
        )

# Обработчики для уведомлений
@router.callback_query(F.data == "notif_enable")
async def enable_notifications(callback: CallbackQuery):
    """Обработчик включения уведомлений"""
    try:
        await callback.message.edit_text(
            "✅ <b>Уведомления включены</b>\n\n"
            "Теперь вы будете получать уведомления о важных событиях.",
            reply_markup=get_notification_settings_keyboard(),
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {callback.from_user.id} включил уведомления")
    except Exception as e:
        logger.error(f"Ошибка при включении уведомлений: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

@router.callback_query(F.data == "notif_disable")
async def disable_notifications(callback: CallbackQuery):
    """Обработчик отключения уведомлений"""
    try:
        await callback.message.edit_text(
            "❌ <b>Уведомления отключены</b>\n\n"
            "Вы больше не будете получать уведомления о событиях.",
            reply_markup=get_notification_settings_keyboard(),
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {callback.from_user.id} отключил уведомления")
    except Exception as e:
        logger.error(f"Ошибка при отключении уведомлений: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

# Обработчики для режимов бота
@router.callback_query(F.data == "bot_active_mode")
async def set_active_mode(callback: CallbackQuery):
    """Обработчик установки активного режима"""
    try:
        await callback.message.edit_text(
            "🟢 <b>Активный режим включен</b>\n\n"
            "Бот будет активно обрабатывать все сообщения и команды.",
            reply_markup=get_bot_params_keyboard(),
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {callback.from_user.id} включил активный режим бота")
    except Exception as e:
        logger.error(f"Ошибка при включении активного режима: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

@router.callback_query(F.data == "bot_passive_mode")
async def set_passive_mode(callback: CallbackQuery):
    """Обработчик установки пассивного режима"""
    try:
        await callback.message.edit_text(
            "🔴 <b>Пассивный режим включен</b>\n\n"
            "Бот будет обрабатывать только команды администраторов.",
            reply_markup=get_bot_params_keyboard(),
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {callback.from_user.id} включил пассивный режим бота")
    except Exception as e:
        logger.error(f"Ошибка при включении пассивного режима: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.") 