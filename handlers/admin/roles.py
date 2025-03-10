from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

import logging
import re
from typing import Dict, List, Tuple, Optional, Any

from app.services.role_service import RoleService
from app.services.user_service import UserService
from app.core.decorators import role_required
from app.db.session import get_session
from app.db.repositories.role_repository import RoleRepository
from app.db.repositories.user_repository import UserRepository
from app.core.logging import setup_logger
from keyboards.admin.roles import (
    get_role_selection_keyboard,
    get_back_to_role_selection_keyboard
)
from keyboards.admin.menu import get_admin_menu_keyboard

# Импортируем функции для работы с ролями
from db_handlers.user_role.manage_roles import (
    get_user_roles,
    add_user_role,
    remove_user_role,
    check_user_role
)

# Импортируем классы состояний
from .states import AdminStates, ContentManagerStates, RemoveRoleStates, RoleStates

# Настраиваем логгер
logger = setup_logger("roles_handler")

# Создаем роутер
router = Router()

# Определяем состояния для FSM
class RoleStates(StatesGroup):
    waiting_for_user_id_add = State()
    waiting_for_role_add = State()
    waiting_for_user_id_remove = State()
    waiting_for_role_remove = State()
    waiting_for_confirm_remove = State()

role_service = RoleService()

async def validate_user_id(bot: Bot, user_id: str) -> tuple[bool, str, dict]:
    """
    Проверяет существование пользователя в Telegram по ID
    
    Args:
        bot: Бот для проверки
        user_id: ID пользователя для проверки
        
    Returns:
        tuple[bool, str, dict]: (существует_ли_пользователь, сообщение, данные_пользователя)
    """
    try:
        # Проверяем, что ID - это число
        user_id_int = int(user_id)
        
        # Проверяем, что ID положительный
        if user_id_int <= 0:
            return False, "ID пользователя должен быть положительным числом", {}
        
        # Пытаемся получить информацию о пользователе
        try:
            user = await bot.get_chat(user_id_int)
            user_data = {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "display_name": user.full_name
            }
            return True, f"Пользователь найден: {user.full_name}", user_data
        except TelegramBadRequest as e:
            if "chat not found" in str(e).lower():
                return False, "Пользователь не найден в Telegram. Возможно указан неверный ID.", {}
            return False, f"Ошибка при поиске пользователя: {e}", {}
    except ValueError:
        return False, "ID пользователя должен быть числом", {}

@router.callback_query(F.data == "make_user_role")
@role_required("admin")
async def process_role_selection(callback: CallbackQuery):
    """Обработчик выбора роли для пользователя"""
    try:
        await callback.message.delete()
        await callback.message.answer(
            "Кого вы хотите добавить? Выберите роль:",
            reply_markup=get_role_selection_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при выборе роли: {e}")
        await callback.message.answer(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=get_back_to_menu_keyboard()
        )

@router.callback_query(F.data == "take_user_role_admin")
@role_required("admin")
async def process_admin_role(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора роли администратора"""
    try:
        await callback.message.edit_text(
            "👤 Роль администратора выбрана\n"
            "Отправьте ID пользователя или нажмите кнопку отмены:",
            reply_markup=get_back_to_menu_keyboard()
        )
        await state.set_state(AdminStates.waiting_for_user_id)
        await state.update_data(role_type="admin")
    except Exception as e:
        logger.error(f"Ошибка при выборе роли администратора: {e}")
        await callback.message.edit_text(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=get_back_to_menu_keyboard()
        )

@router.callback_query(F.data == "take_user_role_content_manager")
@role_required("admin")
async def process_content_manager_role(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора роли контент-менеджера"""
    try:
        await callback.message.edit_text(
            "👤 Роль контент-менеджера выбрана\n"
            "Отправьте ID пользователя или нажмите кнопку отмены:",
            reply_markup=get_back_to_menu_keyboard()
        )
        await state.set_state(ContentManagerStates.waiting_for_user_id)
        await state.update_data(role_type="content_manager")
    except Exception as e:
        logger.error(f"Ошибка при выборе роли контент-менеджера: {e}")
        await callback.message.edit_text(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=get_back_to_menu_keyboard()
        )

@router.message(AdminStates.waiting_for_user_id)
@router.message(ContentManagerStates.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext, bot: Bot):
    """Обработчик получения ID пользователя"""
    try:
        user_id = message.text.strip()
        
        # Проверка валидности ID
        is_valid, error_message, user_data = await validate_user_id(bot, user_id)
        if not is_valid:
            await message.answer(
                f"❌ Ошибка: {error_message}\n\n"
                "Попробуйте еще раз или нажмите кнопку отмены:",
                reply_markup=get_back_to_menu_keyboard()
            )
            return

        data = await state.get_data()
        role_type = data.get("role_type")
        display_name = user_data.get("display_name", "")
        
        # Проверяем, есть ли уже такая роль
        if await role_service.check_user_role(int(user_id), role_type):
            await message.answer(
                f"❌ У пользователя уже есть роль {role_type}",
                reply_markup=get_back_to_menu_keyboard()
            )
            await state.clear()
            return

        # Сохраняем данные и переходим к подтверждению
        await state.update_data(user_id=user_id, display_name=display_name, user_data=user_data)
        await state.set_state(AdminStates.waiting_for_notes if role_type == "admin" else ContentManagerStates.waiting_for_notes)
        
        # Получаем текущие роли пользователя
        current_roles = await role_service.get_user_roles(int(user_id))
        roles_text = "\n• ".join(current_roles) if current_roles else "нет"
        
        await message.answer(
            f"📝 Добавление роли {role_type} для пользователя:\n"
            f"ID: {user_id}\n"
            f"Имя: {display_name}\n"
            f"Текущие роли:\n• {roles_text}\n\n"
            f"Введите примечание к роли (необязательно) или отправьте '-' чтобы пропустить:",
            reply_markup=get_back_to_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке ID пользователя: {e}")
        await message.answer(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=get_back_to_menu_keyboard()
        )
        await state.clear()

@router.message(AdminStates.waiting_for_notes)
@router.message(ContentManagerStates.waiting_for_notes)
async def process_notes(message: Message, state: FSMContext):
    """Обработчик получения примечания к роли"""
    try:
        notes = message.text.strip()
        if notes == "-":
            notes = None
        
        data = await state.get_data()
        user_id = data.get("user_id")
        role_type = data.get("role_type")
        display_name = data.get("display_name", "")
        
        # Сохраняем примечание и переходим к подтверждению
        await state.update_data(notes=notes)
        await state.set_state(AdminStates.confirm_role if role_type == "admin" else ContentManagerStates.confirm_role)
        
        # Формируем сообщение для подтверждения
        notes_text = f"\nПримечание: {notes}" if notes else ""
        
        await message.answer(
            f"⚠️ Подтвердите действие:\n"
            f"ID пользователя: {user_id}\n"
            f"Имя: {display_name}\n"
            f"Действие: назначить роль {role_type}{notes_text}\n\n"
            f"Вы уверены?",
            reply_markup=get_confirm_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке примечания: {e}")
        await message.answer(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=get_back_to_menu_keyboard()
        )
        await state.clear()

@router.callback_query(F.data == "confirm_action", AdminStates.confirm_role)
@router.callback_query(F.data == "confirm_action", ContentManagerStates.confirm_role)
async def process_confirmation(callback: CallbackQuery, state: FSMContext):
    """Обработчик подтверждения действия"""
    try:
        data = await state.get_data()
        user_id = int(data.get("user_id"))
        role_type = data.get("role_type")
        display_name = data.get("display_name", "")
        notes = data.get("notes")
        admin_id = callback.from_user.id
        
        # Добавляем роль через сервис
        success = await role_service.add_role(
            user_id=user_id,
            role_type=role_type,
            admin_id=admin_id,
            display_name=display_name,
            notes=notes
        )
        
        if success:
            # Получаем обновленные роли
            current_roles = await role_service.get_user_roles(user_id)
            roles_text = "\n• ".join(current_roles) if current_roles else "нет"
            
            await callback.message.edit_text(
                f"✅ Роль {role_type} успешно добавлена\n"
                f"Текущие роли пользователя:\n• {roles_text}",
                reply_markup=get_back_to_menu_keyboard()
            )
        else:
            await callback.message.edit_text(
                "❌ Не удалось добавить роль",
                reply_markup=get_back_to_menu_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка при подтверждении действия: {e}")
        await callback.message.edit_text(
            f"❌ Произошла ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
    finally:
        await state.clear()

@router.callback_query(F.data == "remove_user_role")
@role_required("admin")
async def process_remove_role_start(callback: CallbackQuery, state: FSMContext):
    """Обработчик начала процесса удаления роли"""
    try:
        await callback.message.edit_text(
            "👤 Отправьте ID пользователя, у которого хотите удалить роль:",
            reply_markup=get_back_to_role_selection_keyboard()
        )
        await state.set_state(RemoveRoleStates.waiting_for_user_id)
    except Exception as e:
        logger.error(f"Ошибка при начале удаления роли: {e}")
        await callback.message.edit_text(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=get_back_to_role_selection_keyboard()
        )

@router.message(RemoveRoleStates.waiting_for_user_id)
async def process_remove_role_id(message: Message, state: FSMContext, bot: Bot):
    """Обработчик ввода ID пользователя для удаления роли"""
    try:
        # Получаем и очищаем ID пользователя от лишних пробелов
        user_id = message.text.strip()
        logger.info(f"Получен ID пользователя для удаления роли: {user_id} (тип: {type(user_id)})")
        
        # Проверяем валидность ID
        is_valid, error_message, user_data = await validate_user_id(bot, user_id)
        if not is_valid:
            await message.answer(
                f"❌ Ошибка: {error_message}\n\n"
                "Попробуйте еще раз или нажмите кнопку отмены:",
                reply_markup=get_back_to_menu_keyboard()
            )
            return

        user_id_int = int(user_id)
        display_name = user_data.get("display_name", "")
        
        # Получаем роли пользователя
        roles = await role_service.get_user_roles(user_id_int)
        
        if not roles:
            await message.answer(
                f"❌ У пользователя (ID: {user_id}, Имя: {display_name}) нет ролей",
                reply_markup=get_back_to_role_selection_keyboard()
            )
            await state.clear()
            return
        
        # Создаем клавиатуру для выбора роли для удаления
        keyboard = []
        for role in roles:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"❌ {role}", 
                    callback_data=f"remove_role_{user_id}_{role}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="◀️ Назад", 
                callback_data="back_to_role_selection"
            )
        ])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Сохраняем данные в состоянии
        await state.update_data(user_id=user_id, display_name=display_name)
        await state.set_state(RemoveRoleStates.select_role)
        
        await message.answer(
            f"🔍 Выберите роль для удаления у пользователя:\n"
            f"ID: {user_id}\n"
            f"Имя: {display_name}\n"
            f"Доступные роли:\n• " + "\n• ".join(roles),
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке ID для удаления роли: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при обработке ID пользователя. Попробуйте еще раз.",
            reply_markup=get_back_to_role_selection_keyboard()
        )
        await state.clear()

@router.callback_query(lambda c: c.data.startswith("remove_role_"))
async def process_remove_role_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора роли для удаления"""
    try:
        # Получаем данные из callback
        parts = callback.data.split("_")
        user_id = int(parts[2])
        role_type = parts[3]
        
        # Получаем данные из состояния
        data = await state.get_data()
        display_name = data.get("display_name", "")
        
        # Переходим к состоянию ожидания примечания
        await state.update_data(user_id=user_id, role_type=role_type)
        await state.set_state(RemoveRoleStates.waiting_for_notes)
        
        await callback.message.edit_text(
            f"📝 Удаление роли {role_type} у пользователя:\n"
            f"ID: {user_id}\n"
            f"Имя: {display_name}\n\n"
            f"Введите примечание к удалению (необязательно) или отправьте '-' чтобы пропустить:",
            reply_markup=get_back_to_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при выборе роли для удаления: {e}")
        await callback.message.edit_text(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=get_back_to_menu_keyboard()
        )
        await state.clear()

@router.message(RemoveRoleStates.waiting_for_notes)
async def process_remove_role_notes(message: Message, state: FSMContext):
    """Обработчик получения примечания к удалению роли"""
    try:
        notes = message.text.strip()
        if notes == "-":
            notes = None
        
        data = await state.get_data()
        user_id = data.get("user_id")
        role_type = data.get("role_type")
        display_name = data.get("display_name", "")
        
        # Сохраняем примечание и переходим к подтверждению
        await state.update_data(notes=notes)
        await state.set_state(RemoveRoleStates.confirm_action)
        
        # Формируем сообщение для подтверждения
        notes_text = f"\nПримечание: {notes}" if notes else ""
        
        await message.answer(
            f"⚠️ Подтвердите удаление роли:\n"
            f"ID пользователя: {user_id}\n"
            f"Имя: {display_name}\n"
            f"Роль для удаления: {role_type}{notes_text}\n\n"
            f"Вы уверены?",
            reply_markup=get_confirm_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке примечания: {e}")
        await message.answer(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=get_back_to_menu_keyboard()
        )
        await state.clear()

@router.callback_query(F.data == "confirm_action", RemoveRoleStates.confirm_action)
async def process_remove_role_confirmation(callback: CallbackQuery, state: FSMContext):
    """Обработчик подтверждения удаления роли"""
    try:
        data = await state.get_data()
        user_id = int(data.get("user_id"))
        role_type = data.get("role_type")
        admin_id = callback.from_user.id
        
        # Удаляем роль
        success = await role_service.remove_role(
            user_id=user_id,
            role_type=role_type,
            admin_id=admin_id
        )
        
        if success:
            # Получаем обновленные роли
            current_roles = await role_service.get_user_roles(user_id)
            roles_text = "\n• ".join(current_roles) if current_roles else "нет"
            
            await callback.message.edit_text(
                f"✅ Роль {role_type} успешно удалена у пользователя\n"
                f"Текущие роли пользователя:\n• {roles_text}",
                reply_markup=get_back_to_menu_keyboard()
            )
        else:
            await callback.message.edit_text(
                "❌ Не удалось удалить роль",
                reply_markup=get_back_to_menu_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка при подтверждении удаления роли: {e}")
        await callback.message.edit_text(
            f"❌ Произошла ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )
    finally:
        await state.clear()

@router.callback_query(F.data == "cancel_action")
async def process_cancel(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены действия"""
    try:
        await callback.message.edit_text(
            "✅ Действие отменено",
            reply_markup=get_back_to_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при отмене действия: {e}")
        await callback.message.edit_text(
            "Произошла ошибка при отмене.",
            reply_markup=get_back_to_menu_keyboard()
        )
    finally:
        await state.clear()

@router.callback_query(F.data == "back_to_menu")
async def process_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата в главное меню"""
    try:
        await state.clear()
        await callback.message.edit_text(
            "Выберите действие:",
            reply_markup=get_admin_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при возврате в меню: {e}")
        await callback.message.edit_text(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=get_admin_menu_keyboard()
        )

@router.callback_query(F.data == "role_history")
@role_required("admin")
async def process_role_history(callback: CallbackQuery):
    """Обработчик просмотра истории изменений ролей"""
    try:
        # Получаем историю изменений ролей
        history = await role_service.get_role_history(limit=10)
        
        if not history:
            await callback.message.edit_text(
                "📜 История изменений ролей пуста",
                reply_markup=get_back_to_role_selection_keyboard()
            )
            return
        
        # Формируем текст с историей
        history_text = "📜 <b>История изменений ролей:</b>\n\n"
        
        for entry in history:
            action_emoji = "➕" if entry["action"] == "add" else "➖"
            action_text = "добавлена" if entry["action"] == "add" else "удалена"
            
            notes_text = f"\n<i>Примечание: {entry['notes']}</i>" if entry.get("notes") else ""
            
            history_text += (
                f"{action_emoji} Роль <b>{entry['role_type']}</b> {action_text} "
                f"для пользователя <code>{entry['user_id']}</code>\n"
                f"⏱ {entry['performed_at']}\n"
                f"👤 Выполнил: <code>{entry['performed_by']}</code>{notes_text}\n\n"
            )
        
        # Добавляем кнопку для возврата
        await callback.message.edit_text(
            history_text,
            reply_markup=get_back_to_role_selection_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении истории ролей: {e}")
        await callback.message.edit_text(
            "Произошла ошибка при получении истории ролей.",
            reply_markup=get_back_to_role_selection_keyboard()
        )

@router.callback_query(F.data == "list_roles")
@role_required("admin")
async def process_list_roles(callback: CallbackQuery):
    """Обработчик списка пользователей с ролями"""
    try:
        # Получаем список всех доступных ролей
        roles = ["admin", "content_manager"]
        
        # Формируем текст с пользователями
        text = "📋 <b>Пользователи с ролями:</b>\n\n"
        
        # Обрабатываем каждую роль
        for role_type in roles:
            # Получаем пользователей с данной ролью
            users = await role_service.get_by_role(role_type)
            
            if users:
                text += f"<b>📌 {role_type}:</b>\n"
                for user in users:
                    text += f"• ID: <code>{user.user_id}</code>"
                    if user.username:
                        text += f", Имя: {user.username}"
                    text += "\n"
                text += "\n"
        
        if text == "📋 <b>Пользователи с ролями:</b>\n\n":
            text += "Нет пользователей с ролями"
        
        # Выводим результат
        await callback.message.edit_text(
            text,
            reply_markup=get_back_to_role_selection_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей с ролями: {e}")
        await callback.message.edit_text(
            "Произошла ошибка при получении списка пользователей с ролями.",
            reply_markup=get_back_to_role_selection_keyboard()
        )

@router.callback_query(F.data == "manage_roles")
@role_required("admin")
async def process_manage_roles(callback: CallbackQuery):
    """Обработчик выбора управления ролями"""
    try:
        await callback.message.edit_text(
            "Выберите действие с ролями пользователей:",
            reply_markup=get_role_selection_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при выборе управления ролями: {e}")
        await callback.message.edit_text(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=get_admin_menu_keyboard()
        )

@router.callback_query(F.data == "add_user_role")
async def process_add_user_role(callback: CallbackQuery, state: FSMContext):
    """Обработчик добавления роли пользователю"""
    await callback.message.edit_text(
        "Введите ID пользователя или @username для добавления роли:\n\n"
        "Примеры:\n"
        "• 123456789 (ID пользователя)\n"
        "• @username (имя пользователя)",
        reply_markup=get_back_to_role_selection_keyboard()
    )
    await state.set_state(RoleStates.waiting_for_user_id_add)
    logger.info(f"Пользователь {callback.from_user.id} запросил добавление роли")

@router.message(RoleStates.waiting_for_user_id_add)
async def process_add_role_user_id(message: Message, state: FSMContext, bot: Bot):
    """Обработчик ввода ID пользователя или @username для добавления роли"""
    user_input = message.text.strip()
    logger.info(f"Получен ввод пользователя для добавления роли: {user_input}")
    
    # Проверяем, является ли ввод @username или ID
    if user_input.startswith('@') or (not user_input.isdigit() and not user_input.startswith('-')):
        # Обработка ввода @username
        username = user_input.lstrip('@')  # Убираем символ @ если он есть
        logger.info(f"Обрабатываем username: {username}")
        
        # Сначала проверяем, существует ли пользователь в базе данных
        user_service = UserService()
        user = await user_service.get_user_by_username(username)
        
        if user:
            # Пользователь найден в базе данных
            user_id = str(user.user_id)
            display_name = user.full_name or f"@{username}"
            
            logger.info(f"Найден пользователь в базе данных по username @{username}: {display_name} (ID: {user_id})")
            
            # Сохраняем ID пользователя в состоянии
            user_data = {
                "id": user_id,
                "display_name": display_name,
                "username": username
            }
            await state.update_data(user_id=user_id, display_name=display_name, user_data=user_data)
            
            # Проверяем, есть ли уже такая роль
            has_admin_role = await check_user_role(user_id, "admin")
            has_content_manager_role = await check_user_role(user_id, "content_manager")
            
            # Исключаем роли, которые уже есть у пользователя
            roles = []
            if not has_admin_role:
                roles.append({"id": "admin", "name": "Администратор"})
            if not has_content_manager_role:
                roles.append({"id": "content_manager", "name": "Контент-менеджер"})
                
            if not roles:
                await message.answer(
                    f"⚠️ У пользователя <b>{display_name}</b> (ID: {user_id}) уже есть все доступные роли.\n\n"
                    f"Введите другого пользователя или вернитесь назад:",
                    reply_markup=get_back_to_role_selection_keyboard(),
                    parse_mode="HTML"
                )
                return
            
            # Создаем клавиатуру с доступными ролями
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=role["name"], callback_data=f"add_role_{role['id']}_{user_id}")]
                for role in roles
            ] + [
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_role_selection")]
            ])
            
            await message.answer(
                f"Выберите роль для пользователя <b>{display_name}</b> (ID: {user_id}):",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            # Пользователь не найден в базе данных, пробуем получить информацию через Telegram API
            try:
                # Попытка найти пользователя через Telegram API
                logger.info(f"Попытка найти пользователя @{username} через get_chat")
                try:
                    # Метод 1: Пробуем получить информацию через get_chat
                    chat = await bot.get_chat(f"@{username}")
                    user_id = str(chat.id)
                    display_name = chat.full_name or f"@{username}"
                    
                    logger.info(f"Найден пользователь через Telegram API по username @{username}: {display_name} (ID: {user_id})")
                    
                    # Сохраняем ID пользователя в состоянии
                    user_data = {
                        "id": user_id,
                        "display_name": display_name,
                        "username": username
                    }
                    await state.update_data(user_id=user_id, display_name=display_name, user_data=user_data)
                    
                    # Создаем пользователя в базе данных
                    logger.info(f"Пользователь с ID {user_id} не найден в базе данных. Добавляем его.")
                    
                    # Создаем пользователя в базе данных
                    user_service = UserService()
                    created = await user_service.create_user(
                        int(user_id), 
                        username=username, 
                        full_name=display_name
                    )
                    
                    if not created:
                        logger.error(f"Не удалось создать пользователя {user_id} в базе данных")
                        await message.answer(
                            "❌ Не удалось создать пользователя в базе данных. Попробуйте позже.",
                            reply_markup=get_back_to_role_selection_keyboard()
                        )
                        await state.clear()
                        return
                    
                    # Проверяем роли пользователя
                    has_admin_role = await check_user_role(user_id, "admin")
                    has_content_manager_role = await check_user_role(user_id, "content_manager")
                    
                    # Исключаем роли, которые уже есть у пользователя
                    roles = []
                    if not has_admin_role:
                        roles.append({"id": "admin", "name": "Администратор"})
                    if not has_content_manager_role:
                        roles.append({"id": "content_manager", "name": "Контент-менеджер"})
                        
                    if not roles:
                        await message.answer(
                            f"⚠️ У пользователя <b>{display_name}</b> (ID: {user_id}) уже есть все доступные роли.\n\n"
                            f"Введите другого пользователя или вернитесь назад:",
                            reply_markup=get_back_to_role_selection_keyboard(),
                            parse_mode="HTML"
                        )
                        return
                    
                    # Создаем клавиатуру с доступными ролями
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=role["name"], callback_data=f"add_role_{role['id']}_{user_id}")]
                        for role in roles
                    ] + [
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_role_selection")]
                    ])
                    
                    await message.answer(
                        f"Выберите роль для пользователя <b>{display_name}</b> (ID: {user_id}):",
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                except Exception as chat_error:
                    logger.warning(f"Не удалось найти пользователя @{username} через get_chat: {chat_error}")
                    
                    await message.answer(
                        f"⚠️ <b>Не удалось найти пользователя с именем @{username}</b>\n\n"
                        f"Возможные причины:\n"
                        f"• Пользователь не существует\n"
                        f"• Пользователь еще не взаимодействовал с ботом\n"
                        f"• У бота нет доступа к пользователю из-за настроек приватности\n\n"
                        f"<b>Решение:</b>\n"
                        f"1️⃣ Попросите пользователя <b>самостоятельно запустить бота</b> (нажать кнопку Start)\n"
                        f"2️⃣ После этого повторите попытку добавления роли\n"
                        f"3️⃣ Если проблема сохраняется, используйте числовой ID пользователя вместо @username\n\n"
                        f"Введите другого пользователя или вернитесь назад:",
                        reply_markup=get_back_to_role_selection_keyboard(),
                        parse_mode="HTML"
                    )
            except Exception as e:
                logger.error(f"Ошибка при поиске пользователя по username @{username}: {e}", exc_info=True)
                
                await message.answer(
                    f"❌ Не удалось найти пользователя с именем @{username}.\n\n"
                    f"Убедитесь, что имя пользователя указано верно и пользователь взаимодействовал с ботом ранее.\n\n"
                    f"Введите корректный ID пользователя или @username:",
                    reply_markup=get_back_to_role_selection_keyboard(),
                    parse_mode="HTML"
                )
    else:
        # Обработка ввода ID пользователя
        user_id = user_input
        
        # Проверяем существование пользователя
        exists, validation_message, user_data = await validate_user_id(bot, user_id)
        
        if not exists:
            await message.answer(
                f"❌ {validation_message}\n\nВведите корректный ID пользователя или @username:",
                reply_markup=get_back_to_role_selection_keyboard(),
                parse_mode="HTML"
            )
            return
        
        # Сохраняем ID пользователя в состоянии
        await state.update_data(user_id=user_id, display_name=user_data.get("display_name", ""), user_data=user_data)
        
        # Проверяем, существует ли пользователь в базе данных
        user_exists = await check_user_exists(user_id)
        
        if not user_exists:
            # Если пользователя нет в базе данных, создаем его
            logger.info(f"Пользователь с ID {user_id} не найден в базе данных. Добавляем его.")
            
            # Создаем пользователя в базе данных
            user_service = UserService()
            created = await user_service.create_user(
                int(user_id), 
                username=user_data.get("username"), 
                full_name=user_data.get("display_name")
            )
            
            if not created:
                logger.error(f"Не удалось создать пользователя {user_id} в базе данных")
                await message.answer(
                    "❌ Не удалось создать пользователя в базе данных. Попробуйте позже.",
                    reply_markup=get_back_to_role_selection_keyboard()
                )
                await state.clear()
                return
        
        # Проверяем роли пользователя
        has_admin_role = await check_user_role(user_id, "admin")
        has_content_manager_role = await check_user_role(user_id, "content_manager")
        
        # Исключаем роли, которые уже есть у пользователя
        roles = []
        if not has_admin_role:
            roles.append({"id": "admin", "name": "Администратор"})
        if not has_content_manager_role:
            roles.append({"id": "content_manager", "name": "Контент-менеджер"})
            
        if not roles:
            await message.answer(
                f"⚠️ У пользователя <b>{user_data.get('display_name', f'ID: {user_id}')}</b> уже есть все доступные роли.\n\n"
                f"Введите другого пользователя или вернитесь назад:",
                reply_markup=get_back_to_role_selection_keyboard(),
                parse_mode="HTML"
            )
            return
        
        # Создаем клавиатуру с доступными ролями
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=role["name"], callback_data=f"add_role_{role['id']}_{user_id}")]
            for role in roles
        ] + [
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_role_selection")]
        ])
        
        display_name = user_data.get("display_name", f"Пользователь {user_id}")
        
        await message.answer(
            f"Выберите роль для пользователя <b>{display_name}</b> (ID: {user_id}):",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

@router.callback_query(F.data == "back_to_role_selection")
async def process_back_to_role_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата к выбору действия с ролями"""
    try:
        # Очищаем состояние FSM
        await state.clear()
        
        # Редактируем текущее сообщение, показывая меню выбора действий с ролями
        await callback.message.edit_text(
            "Выберите действие с ролями пользователей:",
            reply_markup=get_role_selection_keyboard()
        )
        
        logger.info(f"Пользователь {callback.from_user.id} вернулся к меню выбора действия с ролями")
        
        # Отвечаем на callback, чтобы убрать анимацию загрузки
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при возврате к выбору ролей: {e}", exc_info=True)
        
        # Пробуем отправить новое сообщение, если не удалось отредактировать
        try:
            await callback.message.answer(
                "Выберите действие с ролями пользователей:",
                reply_markup=get_role_selection_keyboard()
            )
            
            # Отвечаем на callback, чтобы убрать анимацию загрузки
            await callback.answer()
        except Exception as send_error:
            logger.error(f"Не удалось отправить сообщение с меню: {send_error}")
            await callback.answer("Произошла ошибка. Попробуйте еще раз.", show_alert=True)

@router.callback_query(lambda c: c.data.startswith("add_role_"))
async def process_add_role_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора роли для добавления"""
    try:
        # Получаем callback_data в формате "add_role_ROLE_TYPE_USER_ID"
        callback_data = callback.data
        
        # Отделяем префикс "add_role_" от остальной части
        _, _, rest = callback_data.partition("add_role_")
        
        # Находим последнее подчеркивание, которое разделяет тип роли и ID пользователя
        last_underscore_index = rest.rfind("_")
        if last_underscore_index == -1:
            raise ValueError("Неверный формат callback_data")
            
        # Разделяем строку на тип роли и ID пользователя
        role_type = rest[:last_underscore_index]
        user_id = int(rest[last_underscore_index + 1:])
        
        admin_id = callback.from_user.id
        
        logger.info(f"Выбрана роль {role_type} для пользователя {user_id}")
        
        # Проверяем, есть ли уже такая роль
        has_role = await check_user_role(user_id, role_type)
        if has_role:
            await callback.message.edit_text(
                f"❌ У пользователя уже есть роль {role_type}",
                reply_markup=get_back_to_role_selection_keyboard()
            )
            await state.clear()
            return
        
        # Добавляем роль
        success = await add_user_role(user_id, role_type, admin_id)
        
        if success:
            # Получаем обновленные роли
            current_roles = await get_user_roles(user_id)
            roles_text = "\n• ".join(current_roles) if current_roles else "нет"
            
            await callback.message.edit_text(
                f"✅ Роль {role_type} успешно добавлена пользователю {user_id}\n"
                f"Текущие роли пользователя:\n• {roles_text}",
                reply_markup=get_back_to_role_selection_keyboard()
            )
        else:
            await callback.message.edit_text(
                "❌ Не удалось добавить роль. Проверьте логи для получения деталей.",
                reply_markup=get_back_to_role_selection_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка при добавлении роли: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Произошла ошибка: {str(e)}",
            reply_markup=get_back_to_role_selection_keyboard()
        )
    finally:
        await state.clear()

async def check_user_exists(user_id: str) -> bool:
    """
    Проверяет существование пользователя в базе данных
    
    Args:
        user_id: ID пользователя для проверки
        
    Returns:
        bool: True если пользователь существует, False в противном случае
    """
    try:
        # Преобразуем user_id в int, если он передан как строка
        if isinstance(user_id, str):
            user_id = int(user_id)
        
        logger.info(f"Проверка существования пользователя с ID: {user_id}")
        
        # Используем UserService для проверки существования пользователя
        user_service = UserService()
        user = await user_service.get_user_by_id(user_id)
        
        if user:
            logger.info(f"Пользователь {user_id} найден в базе данных.")
            return True
        else:
            logger.info(f"Пользователь {user_id} не найден в базе данных.")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при проверке существования пользователя с ID {user_id}: {e}", exc_info=True)
        return False 