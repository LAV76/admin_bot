from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, ChatMemberAdministrator
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from app.services.channel_service import ChannelService
from app.services.role_service import RoleService
from keyboards.admin.channels import (
    get_channels_management_keyboard,
    get_channel_actions_keyboard,
    get_confirm_delete_channel_keyboard,
    get_back_to_channels_keyboard
)
from keyboards.admin.menu import get_back_to_menu_keyboard
from utils.logger import setup_logger, log_error

router = Router()
logger = setup_logger("channels_handler")

# Определение состояний FSM для добавления канала
class ChannelStates(StatesGroup):
    waiting_for_channel_id = State()
    waiting_for_channel_title = State()

# Обработчик для открытия меню управления каналами
@router.callback_query(F.data == "manage_channels")
async def show_channels_management(callback: CallbackQuery, bot: Bot):
    """Обработчик для отображения меню управления каналами"""
    try:
        # Проверка прав администратора
        role_service = RoleService()
        is_admin = await role_service.check_user_role(callback.from_user.id, "admin")
        
        if not is_admin:
            await callback.answer("У вас нет прав для управления каналами", show_alert=True)
            return
        
        # Получение списка каналов
        channel_service = ChannelService()
        channels = await channel_service.get_all_channels()
        
        # Формирование сообщения
        if channels:
            message_text = "📢 <b>Управление каналами</b>\n\n"
            message_text += f"<b>Всего каналов:</b> {len(channels)}\n\n"
            message_text += "<b>Список доступных каналов:</b>\n\n"
            
            for idx, channel in enumerate(channels, 1):
                default_mark = " ✅" if channel["is_default"] else ""
                message_text += f"<b>{idx}. {channel['title']}</b>{default_mark}\n"
                message_text += f"   📋 ID: <code>{channel['chat_id']}</code>\n"
                
                if channel["username"]:
                    message_text += f"   🔗 @{channel['username']}\n"
                
                # Проверка разных вариантов названия поля типа канала
                chat_type = None
                if "chat_type" in channel:
                    chat_type = channel["chat_type"]
                elif "type" in channel:
                    chat_type = channel["type"]
                
                if chat_type:
                    message_text += f"   📊 Тип: {chat_type}\n"
                
                # Добавляем информацию о времени создания
                created_at = channel.get("created_at")
                if created_at:
                    try:
                        if isinstance(created_at, str):
                            message_text += f"   🕒 Добавлен: {created_at}\n"
                        else:
                            message_text += f"   🕒 Добавлен: {created_at.strftime('%d.%m.%Y %H:%M')}\n"
                    except:
                        # В случае ошибки форматирования просто пропускаем
                        pass
                
                # Добавляем информацию о последнем использовании
                last_used = channel.get("last_used")
                if not last_used:
                    last_used = channel.get("last_used_at")
                
                if last_used:
                    try:
                        if isinstance(last_used, str):
                            message_text += f"   🔄 Последнее использование: {last_used}\n"
                        else:
                            message_text += f"   🔄 Последнее использование: {last_used.strftime('%d.%m.%Y %H:%M')}\n"
                    except:
                        # В случае ошибки форматирования просто пропускаем
                        pass
                
                message_text += "\n"
                
            message_text += "Выберите канал для управления или добавьте новый:"
        else:
            message_text = "📢 <b>Управление каналами</b>\n\n"
            message_text += "❗ У вас пока нет добавленных каналов.\n\n"
            message_text += "Нажмите кнопку «Добавить канал», чтобы добавить новый канал для публикации."
        
        # Отправка сообщения с клавиатурой
        await callback.message.edit_text(
            message_text,
            reply_markup=get_channels_management_keyboard(channels),
            parse_mode="HTML"
        )
        
        logger.info(f"Пользователь {callback.from_user.id} открыл меню управления каналами")
    except Exception as e:
        log_error(logger, f"Ошибка при отображении меню управления каналами", e)
        if "message is not modified" not in str(e).lower():
            await callback.answer("Произошла ошибка. Попробуйте позже.")

# Обработчик для начала добавления канала
@router.callback_query(F.data == "add_channel")
async def start_add_channel(callback: CallbackQuery, state: FSMContext):
    """Обработчик для начала процесса добавления канала"""
    try:
        # Проверка прав администратора
        role_service = RoleService()
        is_admin = await role_service.check_user_role(callback.from_user.id, "admin")
        
        if not is_admin:
            await callback.answer("У вас нет прав для добавления каналов", show_alert=True)
            return
        
        # Переходим в состояние ожидания ввода ID или названия канала
        await state.set_state(ChannelStates.waiting_for_channel_id)
        
        # Отправляем сообщение с инструкцией
        await callback.message.edit_text(
            "📢 <b>Добавление нового канала</b>\n\n"
            "Вы можете добавить канал одним из способов:\n\n"
            "1️⃣ <b>По ID канала</b> - введите числовой ID канала\n"
            "2️⃣ <b>По названию канала</b> - введите @username канала\n\n"
            "Для добавления канала по ID, бот должен быть администратором канала.\n"
            "Для добавления по @username, канал должен быть публичным.",
            reply_markup=get_back_to_channels_keyboard(),
            parse_mode="HTML"
        )
        
        logger.info(f"Пользователь {callback.from_user.id} начал процесс добавления канала")
    except Exception as e:
        log_error(logger, f"Ошибка при начале добавления канала", e)
        await callback.answer("Произошла ошибка. Попробуйте позже.")

# Обработчик для получения ID или названия канала
@router.message(StateFilter(ChannelStates.waiting_for_channel_id))
async def process_channel_id_input(message: Message, state: FSMContext, bot: Bot):
    """Обработчик для получения ID или названия канала"""
    try:
        user_id = message.from_user.id
        channel_input = message.text.strip()
        
        # Проверяем, является ли ввод числом (ID канала) или строкой (@username)
        if channel_input.startswith('@'):
            # Обработка ввода @username
            channel_username = channel_input[1:]  # Убираем символ @
            logger.info(f"Пользователь {user_id} ввел username канала: @{channel_username}")
            
            try:
                # Пытаемся получить информацию о канале по username
                chat = await bot.get_chat(f"@{channel_username}")
                chat_id = chat.id
                chat_title = chat.title or f"Канал @{channel_username}"
                chat_type = chat.type
                
                logger.info(f"Найден канал по username @{channel_username}: {chat_title} (ID: {chat_id}, тип: {chat_type})")
                
                # Проверяем права бота в канале
                try:
                    bot_member = await bot.get_chat_member(chat_id, bot.id)
                    is_admin = isinstance(bot_member, ChatMemberAdministrator)
                    
                    if not is_admin:
                        await message.answer(
                            "❌ <b>Ошибка доступа</b>\n\n"
                            f"Бот не является администратором канала <b>{chat_title}</b>.\n"
                            "Пожалуйста, добавьте бота как администратора канала и попробуйте снова.",
                            reply_markup=get_back_to_channels_keyboard(),
                            parse_mode="HTML"
                        )
                        return
                    
                    # Сохраняем информацию о канале в состоянии
                    await state.update_data(
                        chat_id=chat_id,
                        chat_title=chat_title,
                        chat_type=chat_type,
                        chat_username=channel_username
                    )
                    
                    # Переходим к вводу названия канала
                    await state.set_state(ChannelStates.waiting_for_channel_title)
                    
                    await message.answer(
                        f"✅ Канал <b>{chat_title}</b> найден!\n\n"
                        f"ID канала: <code>{chat_id}</code>\n"
                        f"Тип: {chat_type}\n\n"
                        "Теперь введите название для этого канала (или нажмите «Продолжить», чтобы использовать текущее название):",
                        reply_markup=get_back_to_channels_keyboard(show_continue=True),
                        parse_mode="HTML"
                    )
                    
                except TelegramForbiddenError:
                    await message.answer(
                        "❌ <b>Ошибка доступа</b>\n\n"
                        f"Бот не имеет доступа к каналу <b>{chat_title}</b>.\n"
                        "Пожалуйста, добавьте бота в канал как администратора и попробуйте снова.",
                        reply_markup=get_back_to_channels_keyboard(),
                        parse_mode="HTML"
                    )
                
            except TelegramBadRequest:
                await message.answer(
                    "❌ <b>Канал не найден</b>\n\n"
                    f"Не удалось найти канал с username <b>@{channel_username}</b>.\n"
                    "Убедитесь, что канал публичный и username указан верно.",
                    reply_markup=get_back_to_channels_keyboard(),
                    parse_mode="HTML"
                )
            
        else:
            # Обработка ввода ID канала
            try:
                chat_id = int(channel_input)
                logger.info(f"Пользователь {user_id} ввел ID канала: {chat_id}")
                
                # Проверяем, существует ли канал с таким ID
                try:
                    chat = await bot.get_chat(chat_id)
                    chat_title = chat.title or f"Канал {chat_id}"
                    chat_type = chat.type
                    chat_username = chat.username
                    
                    logger.info(f"Найден канал по ID {chat_id}: {chat_title} (тип: {chat_type})")
                    
                    # Проверяем права бота в канале
                    try:
                        bot_member = await bot.get_chat_member(chat_id, bot.id)
                        is_admin = isinstance(bot_member, ChatMemberAdministrator)
                        
                        if not is_admin:
                            await message.answer(
                                "❌ <b>Ошибка доступа</b>\n\n"
                                f"Бот не является администратором канала <b>{chat_title}</b>.\n"
                                "Пожалуйста, добавьте бота как администратора канала и попробуйте снова.",
                                reply_markup=get_back_to_channels_keyboard(),
                                parse_mode="HTML"
                            )
                            return
                        
                        # Сохраняем информацию о канале в состоянии
                        await state.update_data(
                            chat_id=chat_id,
                            chat_title=chat_title,
                            chat_type=chat_type,
                            chat_username=chat_username
                        )
                        
                        # Переходим к вводу названия канала
                        await state.set_state(ChannelStates.waiting_for_channel_title)
                        
                        await message.answer(
                            f"✅ Канал <b>{chat_title}</b> найден!\n\n"
                            f"ID канала: <code>{chat_id}</code>\n"
                            f"Тип: {chat_type}\n"
                            f"Username: {f'@{chat_username}' if chat_username else 'отсутствует'}\n\n"
                            "Теперь введите название для этого канала (или нажмите «Продолжить», чтобы использовать текущее название):",
                            reply_markup=get_back_to_channels_keyboard(show_continue=True),
                            parse_mode="HTML"
                        )
                        
                    except TelegramForbiddenError:
                        await message.answer(
                            "❌ <b>Ошибка доступа</b>\n\n"
                            f"Бот не имеет доступа к каналу <b>{chat_title}</b>.\n"
                            "Пожалуйста, добавьте бота в канал как администратора и попробуйте снова.",
                            reply_markup=get_back_to_channels_keyboard(),
                            parse_mode="HTML"
                        )
                    
                except TelegramBadRequest:
                    await message.answer(
                        "❌ <b>Канал не найден</b>\n\n"
                        f"Не удалось найти канал с ID <code>{chat_id}</code>.\n"
                        "Убедитесь, что ID указан верно и бот имеет доступ к каналу.",
                        reply_markup=get_back_to_channels_keyboard(),
                        parse_mode="HTML"
                    )
                
            except ValueError:
                await message.answer(
                    "❌ <b>Некорректный ввод</b>\n\n"
                    f"Введенное значение <code>{channel_input}</code> не является корректным ID канала или @username.\n"
                    "Пожалуйста, введите числовой ID канала или @username канала.",
                    reply_markup=get_back_to_channels_keyboard(),
                    parse_mode="HTML"
                )
    
    except Exception as e:
        user_id = message.from_user.id
        log_error(logger, f"Ошибка при обработке ввода ID/названия канала от пользователя {user_id}", e, exc_info=True)
        await message.answer(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Не удалось обработать ваш ввод. Пожалуйста, попробуйте еще раз или вернитесь к списку каналов.",
            reply_markup=get_back_to_channels_keyboard(),
            parse_mode="HTML"
        )

# Обработчик для получения названия канала
@router.message(StateFilter(ChannelStates.waiting_for_channel_title))
async def process_channel_title(message: Message, state: FSMContext):
    """Обработчик для получения названия канала"""
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        chat_id = data.get("chat_id")
        chat_type = data.get("chat_type")
        username = data.get("chat_username")
        
        # Получаем название канала из сообщения
        title = message.text.strip()
        
        if not title:
            await message.answer(
                "❌ Название канала не может быть пустым.\n"
                "Пожалуйста, введите название для канала:",
                reply_markup=get_back_to_channels_keyboard(show_continue=True)
            )
            return
        
        if len(title) > 255:
            await message.answer(
                "❌ Название канала слишком длинное (максимум 255 символов).\n"
                "Пожалуйста, введите более короткое название:",
                reply_markup=get_back_to_channels_keyboard(show_continue=True)
            )
            return
        
        # Добавляем канал в базу данных
        channel_service = ChannelService()
        result = await channel_service.add_channel(
            chat_id=chat_id,
            title=title,
            chat_type=chat_type,
            username=username,
            added_by=message.from_user.id,
            is_default=False  # По умолчанию не устанавливаем как канал по умолчанию
        )
        
        # Очищаем состояние
        await state.clear()
        
        if result:
            # Проверяем, был ли канал уже добавлен ранее
            if result.get("already_exists", False):
                await message.answer(
                    f"ℹ️ <b>Канал уже добавлен</b>\n\n"
                    f"Канал «{title}» уже был добавлен ранее.",
                    reply_markup=get_back_to_channels_keyboard(),
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    f"✅ <b>Канал успешно добавлен!</b>\n\n"
                    f"Название: {title}\n"
                    f"ID: {chat_id}\n"
                    f"Тип: {chat_type}\n\n"
                    f"Теперь вы можете использовать этот канал для публикации постов.",
                    reply_markup=get_back_to_channels_keyboard(),
                    parse_mode="HTML"
                )
                
                logger.info(f"Пользователь {message.from_user.id} добавил канал {chat_id} с названием '{title}'")
        else:
            await message.answer(
                "❌ <b>Ошибка!</b>\n\n"
                "Не удалось добавить канал. Попробуйте еще раз.",
                reply_markup=get_back_to_channels_keyboard(),
                parse_mode="HTML"
            )
    except Exception as e:
        log_error(logger, f"Ошибка при добавлении канала", e)
        await message.answer(
            "❌ Произошла ошибка при добавлении канала. Попробуйте еще раз.",
            reply_markup=get_back_to_channels_keyboard()
        )
        await state.clear()

# Обработчик для кнопки "Продолжить" при вводе названия канала
@router.callback_query(F.data == "continue", StateFilter(ChannelStates.waiting_for_channel_title))
async def use_default_channel_title(callback: CallbackQuery, state: FSMContext):
    """Обработчик для использования названия канала по умолчанию"""
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        chat_id = data.get("chat_id")
        chat_type = data.get("chat_type")
        username = data.get("chat_username")
        title = data.get("chat_title", f"Канал {chat_id}")
        
        # Добавляем канал в базу данных
        channel_service = ChannelService()
        result = await channel_service.add_channel(
            chat_id=chat_id,
            title=title,
            chat_type=chat_type,
            username=username,
            added_by=callback.from_user.id,
            is_default=False  # По умолчанию не устанавливаем как канал по умолчанию
        )
        
        # Очищаем состояние
        await state.clear()
        
        if result:
            # Проверяем, был ли канал уже добавлен ранее
            if result.get("already_exists", False):
                await callback.message.edit_text(
                    f"ℹ️ <b>Канал уже добавлен</b>\n\n"
                    f"Канал «{title}» уже был добавлен ранее.",
                    reply_markup=get_back_to_channels_keyboard(),
                    parse_mode="HTML"
                )
            else:
                await callback.message.edit_text(
                    f"✅ <b>Канал успешно добавлен!</b>\n\n"
                    f"Название: {title}\n"
                    f"ID: {chat_id}\n"
                    f"Тип: {chat_type}\n\n"
                    f"Теперь вы можете использовать этот канал для публикации постов.",
                    reply_markup=get_back_to_channels_keyboard(),
                    parse_mode="HTML"
                )
                
                logger.info(f"Пользователь {callback.from_user.id} добавил канал {chat_id} с названием '{title}'")
        else:
            await callback.message.edit_text(
                "❌ <b>Ошибка!</b>\n\n"
                "Не удалось добавить канал. Попробуйте еще раз.",
                reply_markup=get_back_to_channels_keyboard(),
                parse_mode="HTML"
            )
    except Exception as e:
        log_error(logger, f"Ошибка при добавлении канала", e)
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")
        await state.clear()

# Обработчик для выбора канала из списка
@router.callback_query(F.data.startswith("channel_"))
async def show_channel_actions(callback: CallbackQuery):
    """Обработчик для отображения действий с выбранным каналом"""
    try:
        # Получаем ID канала из callback_data
        channel_id = int(callback.data.replace("channel_", ""))
        
        # Получаем информацию о канале
        channel_service = ChannelService()
        channel = await channel_service.get_channel_by_id(channel_id)
        
        if not channel:
            await callback.answer("Канал не найден", show_alert=True)
            return
        
        # Формируем сообщение с информацией о канале
        default_mark = " (по умолчанию)" if channel["is_default"] else ""
        message_text = f"📢 <b>{channel['title']}{default_mark}</b>\n\n"
        message_text += f"ID: {channel['chat_id']}\n"
        message_text += f"Тип: {channel['chat_type']}\n"
        
        if channel["username"]:
            message_text += f"Username: @{channel['username']}\n"
        
        message_text += f"Добавлен: {channel['created_at']}\n"
        
        if channel["last_used_at"]:
            message_text += f"Последнее использование: {channel['last_used_at']}\n"
        
        message_text += "\nВыберите действие с этим каналом:"
        
        # Отправляем сообщение с клавиатурой действий
        await callback.message.edit_text(
            message_text,
            reply_markup=get_channel_actions_keyboard(channel_id, channel["is_default"]),
            parse_mode="HTML"
        )
        
        logger.info(f"Пользователь {callback.from_user.id} выбрал канал {channel_id}")
    except Exception as e:
        log_error(logger, f"Ошибка при отображении действий с каналом", e)
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

# Обработчик для установки канала по умолчанию
@router.callback_query(F.data.startswith("set_default_"))
async def set_default_channel(callback: CallbackQuery):
    """Обработчик для установки канала по умолчанию"""
    try:
        # Получаем ID канала из callback_data
        channel_id = int(callback.data.replace("set_default_", ""))
        
        # Устанавливаем канал по умолчанию
        channel_service = ChannelService()
        result = await channel_service.set_default_channel(channel_id)
        
        if result:
            # Получаем обновленную информацию о канале
            channel = await channel_service.get_channel_by_id(channel_id)
            
            if channel:
                await callback.message.edit_text(
                    f"✅ <b>Канал установлен по умолчанию</b>\n\n"
                    f"Канал «{channel['title']}» теперь используется по умолчанию для публикации постов.",
                    reply_markup=get_back_to_channels_keyboard(),
                    parse_mode="HTML"
                )
                
                logger.info(f"Пользователь {callback.from_user.id} установил канал {channel_id} по умолчанию")
            else:
                await callback.answer("Канал не найден", show_alert=True)
        else:
            await callback.answer("Не удалось установить канал по умолчанию", show_alert=True)
    except Exception as e:
        log_error(logger, f"Ошибка при установке канала по умолчанию", e)
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

# Обработчик для удаления канала
@router.callback_query(F.data.startswith("delete_channel_"))
async def confirm_delete_channel(callback: CallbackQuery):
    """Обработчик для подтверждения удаления канала"""
    try:
        # Получаем ID канала из callback_data
        channel_id = int(callback.data.replace("delete_channel_", ""))
        
        # Получаем информацию о канале
        channel_service = ChannelService()
        channel = await channel_service.get_channel_by_id(channel_id)
        
        if not channel:
            await callback.answer("Канал не найден", show_alert=True)
            return
        
        # Отправляем сообщение с подтверждением удаления
        await callback.message.edit_text(
            f"❓ <b>Подтверждение удаления</b>\n\n"
            f"Вы действительно хотите удалить канал «{channel['title']}»?\n\n"
            f"<i>Это действие нельзя отменить.</i>",
            reply_markup=get_confirm_delete_channel_keyboard(channel_id),
            parse_mode="HTML"
        )
        
        logger.info(f"Пользователь {callback.from_user.id} запросил удаление канала {channel_id}")
    except Exception as e:
        log_error(logger, f"Ошибка при подтверждении удаления канала", e)
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

# Обработчик для подтверждения удаления канала
@router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_channel(callback: CallbackQuery):
    """Обработчик для удаления канала"""
    try:
        # Получаем ID канала из callback_data
        channel_id = int(callback.data.replace("confirm_delete_", ""))
        
        # Получаем информацию о канале перед удалением
        channel_service = ChannelService()
        channel = await channel_service.get_channel_by_id(channel_id)
        
        if not channel:
            await callback.answer("Канал не найден", show_alert=True)
            return
        
        # Удаляем канал
        result = await channel_service.delete_channel(channel_id)
        
        if result:
            await callback.message.edit_text(
                f"✅ <b>Канал удален</b>\n\n"
                f"Канал «{channel['title']}» успешно удален.",
                reply_markup=get_back_to_channels_keyboard(),
                parse_mode="HTML"
            )
            
            logger.info(f"Пользователь {callback.from_user.id} удалил канал {channel_id}")
        else:
            await callback.answer("Не удалось удалить канал", show_alert=True)
    except Exception as e:
        log_error(logger, f"Ошибка при удалении канала", e)
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

# Обработчик для возврата к списку каналов
@router.callback_query(F.data == "back_to_channels")
async def back_to_channels(callback: CallbackQuery, bot: Bot):
    """Обработчик для возврата к списку каналов"""
    try:
        # Очищаем состояние FSM, если оно было установлено
        await callback.message.edit_text("Возвращаемся к списку каналов...")
        
        # Вызываем обработчик отображения списка каналов
        await show_channels_management(callback, bot)
    except Exception as e:
        log_error(logger, f"Ошибка при возврате к списку каналов", e)
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

# Обработчик для обновления списка каналов
@router.callback_query(F.data == "refresh_channels_list")
async def refresh_channels_list(callback: CallbackQuery, bot: Bot):
    """Обработчик для обновления списка каналов"""
    # Просто вызываем тот же обработчик, что и для управления каналами
    await show_channels_management(callback, bot) 