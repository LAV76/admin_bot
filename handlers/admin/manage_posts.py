import logging
from datetime import datetime
import re
from typing import Optional

from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

from app.services.post_service import PostService
from app.core.decorators import role_required, admin_required
from utils.logger import log_error, log_function_call, setup_logger
from keyboards.admin.posts import (
    get_post_management_keyboard, 
    get_post_list_keyboard, 
    get_post_actions_keyboard,
    get_confirm_delete_post_keyboard,
    get_chat_selection_keyboard,
    get_after_publish_keyboard
)
from keyboards.admin.menu import get_admin_menu_keyboard, get_main_menu_keyboard
from app.db.repositories.post_repository import PostRepository
from app.db.session import get_session

# Инициализируем роутер
router = Router(name="admin_manage_posts")

# Инициализируем логгер
logger = logging.getLogger("admin_manage_posts")

# Инициализируем сервис постов
post_service = PostService()

# Состояния для поиска постов
class SearchPostStates(StatesGroup):
    waiting_for_tag = State()

# Состояния для работы с публикацией постов
class PostPublishStates(StatesGroup):
    select_channel = State()
    
# Состояния для редактирования постов
class PostEditStates(StatesGroup):
    edit_name = State()
    edit_description = State()
    edit_image = State()
    edit_tag = State()
    confirm_changes = State()

# Обработчик для отображения меню управления постами
@router.callback_query(F.data == "manage_posts")
@role_required("admin")
async def show_post_management(callback: CallbackQuery, state: FSMContext):
    """Обработчик для отображения меню управления постами"""
    await state.clear()
    await callback.message.edit_text(
        "📝 <b>Управление постами</b>\n\n"
        "Выберите действие из меню ниже:",
        reply_markup=get_post_management_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# Обработчик для возврата в меню управления постами
@router.callback_query(F.data == "back_to_post_management")
async def back_to_post_management(callback: CallbackQuery):
    """Обработчик для возврата в меню управления постами"""
    await callback.message.edit_text(
        "📝 <b>Управление постами</b>\n\n"
        "Выберите действие из меню ниже:",
        reply_markup=get_post_management_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# Обработчик для отображения списка постов пользователя
@router.callback_query(F.data == "my_posts")
async def show_user_posts(callback: CallbackQuery, state: FSMContext = None):
    """Обработчик для отображения списка постов пользователя"""
    try:
        user_id = callback.from_user.id
        logger.info(f"Пользователь {user_id} запросил список своих постов")
    
        # Если есть состояние, очищаем его
        if state:
            await state.clear()
        
        # Получаем посты пользователя
        posts = await post_service.get_user_posts(user_id)
        
        # Проверяем, есть ли у пользователя посты
        if not posts:
            # Сначала пробуем удалить предыдущее сообщение
            try:
                await callback.message.delete()
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение: {e}")
                    
            # Отправляем новое сообщение
            await callback.message.answer(
                "У вас пока нет постов. Создайте новый пост!",
                reply_markup=get_post_management_keyboard()
            )
            await callback.answer()
            return
        
        logger.info(f"Получено {len(posts)} постов для пользователя {user_id}")
        
        # Форматируем посты для отображения
        formatted_posts = []
        for post in posts:
            # Определяем статус публикации
            status = "✅" if post.get("is_published") else "📝"
            
            # Получаем название поста
            title = post.get("title", "")
            if len(title) > 30:
                title = title[:27] + "..."
                
            # Добавляем информацию о чате, если есть
            chat_info = ""
            if post.get("target_chat_title"):
                chat_info = f" → {post.get('target_chat_title')}"
                
            formatted_posts.append({
                "id": post.get("id"),
                "title": f"{status} {title}{chat_info}",
                "is_published": post.get("is_published")
            })
            
        logger.debug(f"Отформатировано {len(formatted_posts)} постов для пользователя {user_id}")
        
        # Отображаем список постов
        try:
            await callback.message.edit_text(
                "📋 <b>Список ваших постов</b>\n\n"
                "Выберите пост для просмотра или управления:",
                reply_markup=get_post_list_keyboard(formatted_posts),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение: {e}")
            
            try:
                await callback.message.delete()
            except Exception as delete_error:
                logger.warning(f"Не удалось удалить сообщение: {delete_error}")
                
            await callback.message.answer(
                "📋 <b>Список ваших постов</b>\n\n"
                "Выберите пост для просмотра или управления:",
                reply_markup=get_post_list_keyboard(formatted_posts),
                parse_mode="HTML"
            )
            
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при отображении списка постов: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при загрузке списка постов", show_alert=True)

# Обработчик для пагинации списка постов
@router.callback_query(F.data.startswith("post_page_"))
async def paginate_posts(callback: CallbackQuery):
    """Обработчик для пагинации списка постов"""
    try:
        page = int(callback.data.split("_")[-1])
        user_id = callback.from_user.id
        logger.info(f"Пользователь {user_id} запросил страницу {page} списка постов")
        
        # Получаем список постов пользователя
        posts = await post_service.get_user_posts(user_id, limit=50)  # Увеличиваем лимит для пагинации
        logger.info(f"Получено {len(posts) if posts else 0} постов для пользователя {user_id}")
        
        if not posts:
            logger.info(f"У пользователя {user_id} нет созданных постов")
            try:
                await callback.message.edit_text(
                    "У вас пока нет созданных постов.",
                    reply_markup=get_post_management_keyboard(),
                    parse_mode="HTML"
                )
            except TelegramBadRequest as e:
                logger.warning(f"Не удалось отредактировать сообщение для пользователя {user_id}: {e}")
                # В случае ошибки попробуем отправить новое сообщение
                await callback.message.answer(
                    "У вас пока нет созданных постов.",
                    reply_markup=get_post_management_keyboard(),
                    parse_mode="HTML"
                )
            await callback.answer()
            return
        
        # Форматируем список постов для отображения
        formatted_posts = []
        for post in posts:
            # Добавляем информацию о чате для публикации, если она есть
            chat_info = ""
            if post.get("target_chat_title"):
                chat_info = f" → {post['target_chat_title']}"
            
            # Добавляем статус публикации
            status = "✅" if post.get("is_published", False) else "📝"
            
            # Форматируем название поста
            title = post.get("title", "")
            if len(title) > 30:
                title = title[:27] + "..."
            
            # Добавляем пост в список
            formatted_posts.append({
                "id": post.get("id"),
                "post_name": f"{status} {title}{chat_info}",
                "is_published": post.get("is_published", False)
            })
        
        logger.debug(f"Сформирован список из {len(formatted_posts)} постов для отображения пользователю {user_id}")
        
        # Отображаем список постов с указанной страницей
        try:
            await callback.message.edit_text(
                "<b>Ваши посты:</b>",
                reply_markup=get_post_list_keyboard(formatted_posts, page),
                parse_mode="HTML"
            )
            logger.debug(f"Список постов (страница {page}) отредактирован для пользователя {user_id}")
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось отредактировать сообщение для пользователя {user_id} (страница {page}): {e}")
            # Если сообщение нельзя редактировать, отправляем новое
            await callback.message.answer(
                "<b>Ваши посты:</b>",
                reply_markup=get_post_list_keyboard(formatted_posts, page),
                parse_mode="HTML"
            )
            logger.debug(f"Отправлено новое сообщение со списком постов (страница {page}) для пользователя {user_id}")
        
        await callback.answer()
        
    except Exception as e:
        log_error(logger, f"Ошибка при пагинации списка постов для пользователя {callback.from_user.id}", e, exc_info=True)
        try:
            await callback.message.edit_text(
                "❌ Произошла ошибка при отображении списка постов.",
                reply_markup=get_post_management_keyboard(),
                parse_mode="HTML"
            )
        except Exception as edit_error:
            log_error(logger, f"Ошибка при отображении сообщения об ошибке пользователю {callback.from_user.id}", edit_error)
            await callback.message.answer(
                "❌ Произошла ошибка при отображении списка постов.",
                reply_markup=get_post_management_keyboard(),
                parse_mode="HTML"
            )
        await callback.answer()

# Обработчик для просмотра поста
@router.callback_query(F.data.startswith("view_post_"))
async def view_post(callback: CallbackQuery, bot: Bot):
    """Обработчик для просмотра поста"""
    try:
        post_id = int(callback.data.split("_")[-1])
        user_id = callback.from_user.id
        
        logger.info(f"Пользователь {user_id} запросил просмотр поста {post_id}")
        
        # Получаем информацию о посте напрямую из репозитория
        async with get_session() as session:
            post_repo = PostRepository(session)
            post_model = await post_repo.get_by_id(post_id)
            
            if not post_model:
                logger.warning(f"Пост {post_id} не найден при попытке просмотра")
                await callback.message.edit_text(
                    "❌ Пост не найден или был удален.",
                    reply_markup=get_post_management_keyboard()
                )
                await callback.answer()
                return
            
            # Преобразуем модель в словарь
            post = {
                "id": post_model.id,
                "title": post_model.title,
                "content": post_model.content,
                "image": post_model.image,
                "tag": post_model.tag or "",
                "username": post_model.username,
                "created_date": post_model.created_date.strftime("%Y-%m-%d %H:%M:%S"),
                "is_published": post_model.is_published == 1,
                "target_chat_id": post_model.target_chat_id,
                "target_chat_title": post_model.target_chat_title
            }
        
        # Форматируем теги для отображения
        tags = post["tag"].split() if post["tag"] else []
        formatted_tags = ' '.join([f"#{tag}" for tag in tags])
        
        # Информация о статусе публикации
        status = "✅ Опубликован" if post["is_published"] else "📝 Черновик"
        
        # Информация о чате для публикации
        chat_info = ""
        if post.get("target_chat_id") and post.get("target_chat_title"):
            chat_info = f"<i>Чат для публикации:</i> {post['target_chat_title']}\n"
        
        # Формируем сообщение с информацией о посте
        message_text = (
            f"<b>Информация о посте</b>\n\n"
            f"<b>{post['title']}</b>\n\n"
            f"{post['content']}\n\n"
            f"<i>{formatted_tags}</i>\n"
            f"{chat_info}"
            f"<i>Автор:</i> {post['username']}\n"
            f"<i>Создан:</i> {post['created_date']}\n"
            f"<i>Статус:</i> {status}"
        )
        
        # Информируем пользователя, что пост загружается
        await callback.answer()
        
        try:
            # Отправляем сообщение с информацией о посте
            if post["image"] and post["image"].strip():
                # Проверяем, является ли изображение валидным
                logger.info(f"Попытка отправки поста {post_id} с изображением {post['image']}")
                
                try:
                    # Отправляем новое сообщение с фото
                    sent_message = await bot.send_photo(
                        chat_id=callback.message.chat.id,
                        photo=post["image"],
                        caption=message_text,
                        reply_markup=get_post_actions_keyboard(post["id"], post["is_published"]),
                        parse_mode="HTML"
                    )
                    
                    # Удаляем предыдущее сообщение только после успешной отправки фото
                    try:
                        await callback.message.delete()
                    except Exception as delete_error:
                        logger.warning(f"Не удалось удалить предыдущее сообщение: {delete_error}")
                        
                except TelegramBadRequest as photo_error:
                    logger.warning(f"Ошибка при отправке фото поста {post_id}: {photo_error}")
                    
                    # Если не удалось отправить фото, пробуем отправить пост без фото
                    await callback.message.edit_text(
                        message_text + "\n\n<i>⚠️ Не удалось загрузить изображение</i>",
                        reply_markup=get_post_actions_keyboard(post["id"], post["is_published"]),
                        parse_mode="HTML"
                    )
            else:
                # Если у поста нет изображения, просто редактируем текущее сообщение
                await callback.message.edit_text(
                    message_text,
                    reply_markup=get_post_actions_keyboard(post["id"], post["is_published"]),
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Ошибка при показе поста {post_id}: {e}", exc_info=True)
            await callback.message.edit_text(
                f"❌ Ошибка при показе поста. Попробуйте еще раз.\nОшибка: {str(e)[:50]}",
                reply_markup=get_post_management_keyboard()
            )
    except Exception as e:
        logger.error(f"Критическая ошибка при отображении поста: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при отображении поста", show_alert=True)
        try:
            await callback.message.edit_text(
                "❌ Произошла ошибка при отображении поста.",
                reply_markup=get_post_management_keyboard()
            )
        except Exception as edit_error:
            logger.error(f"Не удалось отобразить сообщение об ошибке: {edit_error}")
            await callback.message.answer(
                "❌ Произошла ошибка при отображении поста.",
                reply_markup=get_post_management_keyboard()
            )

# Обработчик для публикации поста
@router.callback_query(F.data.startswith("publish_post_"))
@role_required("admin")
async def publish_post(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обработчик публикации поста
    """
    try:
        # Получаем ID поста из callback_data
        post_id = int(callback.data.split('_')[-1])
        logger.info(f"Пользователь {callback.from_user.id} запросил публикацию поста с ID {post_id}")
        
        # Сохраняем ID поста в состоянии для последующего использования
        await state.update_data(post_id=post_id)
        
        # Получаем сервис для работы с постами
        post_service = PostService()
        
        # Получаем список доступных каналов для публикации
        logger.info("Запрос списка доступных чатов для публикации")
        channels = await post_service.get_available_chats(bot)
        logger.info(f"Найдено {len(channels)} доступных каналов для публикации")
        
        if not channels:
            await callback.answer("Нет доступных каналов для публикации. Добавьте бота как администратора в канал.", show_alert=True)
            return
        
        # Создаем текст сообщения
        message_text = f"Выберите канал для публикации поста ID {post_id}:"
        
        # Создаем инлайн-клавиатуру для выбора канала
        buttons = []
        
        # Добавляем кнопку для каждого доступного канала
        for channel in channels:
            title = channel.get("title", f"Канал {channel.get('chat_id')}")
            channel_id = channel.get("chat_id")  # Используем настоящий Telegram ID канала
            
            # Текст кнопки
            button_text = f"{title}"
            
            # Добавляем (по умолчанию) для канала по умолчанию
            if channel.get("is_default"):
                button_text += " (по умолчанию)"
                
            buttons.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"select_channel_{channel_id}"  # Добавляем префикс и преобразуем в строку
                )
            ])
        
        # Добавляем кнопку для использования канала по умолчанию или пропуска выбора
        buttons.append([
            InlineKeyboardButton(
                text="⏩ Использовать канал по умолчанию",
                callback_data="skip_chat_selection"
            )
        ])
        
        # Добавляем кнопку возврата назад
        buttons.append([
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"view_post_{post_id}"
            )
        ])
        
        # Создаем клавиатуру
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Переходим в состояние выбора канала
        await state.set_state(PostPublishStates.select_channel)
        
        # Проверяем, можно ли редактировать сообщение
        can_edit = False
        if callback.message:
            try:
                # Пробуем редактировать сообщение
                await callback.message.edit_text(message_text, reply_markup=keyboard)
                can_edit = True
            except Exception as edit_error:
                logger.warning(f"Не удалось отредактировать сообщение: {edit_error}")
                can_edit = False
        
        # Если не удалось отредактировать, отправляем новое сообщение
        if not can_edit:
            await callback.answer("Подготовка к публикации поста...")
            await callback.message.answer(message_text, reply_markup=keyboard)
    
    except Exception as e:
        logger.error(f"Ошибка при подготовке к публикации поста: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при подготовке к публикации поста", show_alert=True)
        
        # Пробуем отправить информативное сообщение об ошибке
        try:
            if callback.message:
                try:
                    await callback.message.edit_text(
                        f"❌ Ошибка при подготовке к публикации поста:\n{str(e)}",
                        reply_markup=get_post_management_keyboard(post_id)
                    )
                except Exception as edit_error:
                    logger.warning(f"Не удалось отредактировать сообщение об ошибке: {edit_error}")
                await callback.message.answer(
                    f"❌ Ошибка при подготовке к публикации поста:\n{str(e)}",
                    reply_markup=get_post_management_keyboard(post_id)
                )
        except Exception as msg_error:
            logger.error(f"Не удалось отправить сообщение об ошибке: {msg_error}")

# Обработчик для выбора канала при публикации поста
@router.callback_query(F.data.startswith("select_channel_"), StateFilter(PostPublishStates.select_channel))
@role_required("admin")
async def handle_chat_selection(callback: CallbackQuery, state: FSMContext, bot: Bot, post_service: PostService = None):
    """Обработчик выбора канала для публикации поста"""
    try:
        # Получаем ID поста из состояния FSM
        state_data = await state.get_data()
        post_id = state_data.get("post_id")
        
        if not post_id:
            # Если ID поста не найден в состоянии, пытаемся извлечь его из сообщения
            import re
            if callback.message and callback.message.text:
                matches = re.findall(r"ID (\d+)", callback.message.text)
                if matches:
                    post_id = int(matches[0])
    
        if not post_id:
            logger.error("Не удалось определить ID поста для публикации в канал")
            await callback.answer("Не удалось определить ID поста. Попробуйте заново.", show_alert=True)
            await state.clear()
            return
        
        # Извлекаем ID канала из callback_data
        selected_chat_id = int(callback.data.replace("select_channel_", ""))
        logger.info(f"Пользователь {callback.from_user.id} выбрал канал {selected_chat_id} для публикации поста {post_id}")
        
        # Отвечаем на callback
        await callback.answer()
        
        # Редактируем сообщение, чтобы показать процесс публикации
        try:
            await callback.message.edit_text(
                f"⏳ Публикация поста в выбранный канал...\n"
                f"Пожалуйста, подождите...",
                reply_markup=None
            )
        except Exception as edit_error:
            logger.error(f"Ошибка при редактировании сообщения: {str(edit_error)}")
        
        # Если post_service не передан, создаем его
        if post_service is None:
            post_service = PostService()
        
        # Публикуем пост в выбранный канал
        result = await post_service.publish_post_to_channel(post_id, bot, selected_chat_id)
        
        if result["success"]:
            # Пост успешно опубликован
            message_id = result.get("message_id")
            publication_date = result.get("publication_date")
            channel_title = result.get("channel_title")
            
            # Очищаем состояние
            await state.clear()
            
            try:
                await callback.message.edit_text(
                    f"✅ Пост успешно опубликован в канал {channel_title}!\n\n"
                    f"📅 Дата публикации: {publication_date}\n"
                    f"🔢 ID сообщения: {message_id}",
                    reply_markup=get_after_publish_keyboard()
                )
            except Exception as edit_error:
                logger.error(f"Ошибка при обновлении сообщения об успешной публикации: {str(edit_error)}")
                await callback.message.answer(
                    f"✅ Пост успешно опубликован в канал {channel_title}!\n\n"
                    f"📅 Дата публикации: {publication_date}\n"
                    f"🔢 ID сообщения: {message_id}",
                    reply_markup=get_after_publish_keyboard()
                )
        else:
            # Ошибка при публикации поста
            error_message = result.get("error", "Неизвестная ошибка")
            logger.error(f"Ошибка при публикации поста {post_id} в канал {selected_chat_id}: {error_message}")
            
            try:
                await callback.message.edit_text(
                    f"❌ Ошибка при публикации поста в выбранный канал.\n"
                    f"Причина: {error_message}\n\n"
                    "Вы можете повторить попытку позже.",
                    reply_markup=get_post_management_keyboard(post_id)
                )
            except Exception as edit_error:
                logger.error(f"Ошибка при обновлении сообщения об ошибке публикации: {str(edit_error)}")
                await callback.message.answer(
                    f"❌ Ошибка при публикации поста в выбранный канал.\n"
                    f"Причина: {error_message}\n\n"
                    "Вы можете повторить попытку позже.",
                    reply_markup=get_post_management_keyboard(post_id)
                )
    except Exception as e:
        logger.error(f"Критическая ошибка при публикации поста в канал: {str(e)}", exc_info=True)
        await callback.answer(f"Произошла ошибка: {str(e)}", show_alert=True)

# Обработчик для пропуска выбора канала (использование канала по умолчанию)
@router.callback_query(F.data == "skip_chat_selection", StateFilter(PostPublishStates.select_channel))
@role_required("admin")
async def skip_chat_selection(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обработчик пропуска выбора канала (использование канала по умолчанию)
    """
    try:
        # Получаем данные из состояния
        state_data = await state.get_data()
        post_id = state_data.get("post_id")
        
        if not post_id:
            # Если нет ID поста в состоянии, пытаемся его извлечь из сообщения
            import re
            if callback.message and callback.message.text:
                matches = re.findall(r"ID (\d+)", callback.message.text)
                if matches:
                    post_id = int(matches[0])
            
            if not post_id:
                logger.error("Не удалось определить ID поста для публикации")
                await callback.answer("Не удалось определить ID поста. Попробуйте заново.", show_alert=True)
            await state.clear()
            return
            
        logger.info(f"Пользователь {callback.from_user.id} выбрал публикацию поста {post_id} в канал по умолчанию")
        
        # Отвечаем на callback
        await callback.answer()
        
        # Редактируем сообщение, чтобы показать процесс публикации
        try:
            await callback.message.edit_text(
                "⏳ Публикация поста в канал по умолчанию...\n"
                "Пожалуйста, подождите...",
                reply_markup=None
            )
        except Exception as edit_error:
            logger.error(f"Ошибка при редактировании сообщения: {str(edit_error)}")
            
        # Получаем сервис постов
        post_service = PostService()
        
        # Публикуем пост в канал по умолчанию (None означает использование канала по умолчанию)
        result = await post_service.publish_post_to_channel(post_id, bot, None)
        
        if result["success"]:
            # Пост успешно опубликован
            message_id = result.get("message_id")
            publication_date = result.get("publication_date")
            channel_title = result.get("channel_title")
            
            # Очищаем состояние
            await state.clear()
            
            try:
                await callback.message.edit_text(
                    f"✅ Пост успешно опубликован в канал {channel_title}!\n\n"
                    f"📅 Дата публикации: {publication_date}\n"
                    f"🔢 ID сообщения: {message_id}",
                    reply_markup=get_after_publish_keyboard()
                )
            except Exception as edit_error:
                logger.error(f"Ошибка при обновлении сообщения об успешной публикации: {str(edit_error)}")
                await callback.message.answer(
                    f"✅ Пост успешно опубликован в канал {channel_title}!\n\n"
                    f"📅 Дата публикации: {publication_date}\n"
                    f"🔢 ID сообщения: {message_id}",
                    reply_markup=get_after_publish_keyboard()
                )
        else:
            # Ошибка при публикации поста
            error_message = result.get("error", "Неизвестная ошибка")
            logger.error(f"Ошибка при публикации поста {post_id} в канал по умолчанию: {error_message}")
            
            try:
                await callback.message.edit_text(
                    f"❌ Ошибка при публикации поста в канал по умолчанию.\n"
                    f"Причина: {error_message}\n\n"
                    "Вы можете повторить попытку позже.",
                    reply_markup=get_post_management_keyboard(post_id)
                )
            except Exception as edit_error:
                logger.error(f"Ошибка при обновлении сообщения об ошибке публикации: {str(edit_error)}")
                await callback.message.answer(
                    f"❌ Ошибка при публикации поста в канал по умолчанию.\n"
                    f"Причина: {error_message}\n\n"
                    "Вы можете повторить попытку позже.",
                    reply_markup=get_post_management_keyboard(post_id)
                )
    except Exception as e:
        logger.error(f"Критическая ошибка при публикации поста в канал по умолчанию: {str(e)}", exc_info=True)
        await callback.answer(f"Произошла ошибка: {str(e)}", show_alert=True)

# Обработчик для удаления поста
@router.callback_query(F.data.startswith("delete_post_"))
async def delete_post_confirm(callback: CallbackQuery):
    """Обработчик для подтверждения удаления поста"""
    post_id = int(callback.data.split("_")[-1])
    
    try:
        await callback.message.edit_text(
            "⚠️ <b>Подтверждение удаления</b>\n\n"
            f"Вы действительно хотите удалить пост #{post_id}?\n"
            "Это действие нельзя отменить.",
            reply_markup=get_confirm_delete_post_keyboard(post_id),
            parse_mode="HTML"
        )
    except (TelegramBadRequest, Exception) as e:
        # Если сообщение содержит фото или его нельзя редактировать, удаляем его и отправляем новое
        try:
            await callback.message.delete()
            await callback.message.answer(
                "⚠️ <b>Подтверждение удаления</b>\n\n"
                f"Вы действительно хотите удалить пост #{post_id}?\n"
                "Это действие нельзя отменить.",
                reply_markup=get_confirm_delete_post_keyboard(post_id),
                parse_mode="HTML"
            )
        except Exception as e2:
            logger.error(f"Ошибка при отображении подтверждения удаления: {e2}")
    
    await callback.answer()

# Обработчик для подтверждения удаления поста
@router.callback_query(F.data.startswith("confirm_delete_post_"))
async def confirm_delete_post(callback: CallbackQuery):
    """Обработчик для удаления поста после подтверждения"""
    post_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    
    # Создаем сервис и удаляем пост
    result = await post_service.delete_post(post_id, user_id)
    
    try:
        if result:
            await callback.message.edit_text(
                f"✅ Пост #{post_id} успешно удален.",
                reply_markup=get_post_management_keyboard(),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                f"❌ Ошибка при удалении поста #{post_id}.",
                reply_markup=get_post_management_keyboard(),
                parse_mode="HTML"
            )
    except (TelegramBadRequest, Exception) as e:
        # Если сообщение содержит фото или его нельзя редактировать, удаляем его и отправляем новое
        try:
            await callback.message.delete()
            
            if result:
                await callback.message.answer(
                    f"✅ Пост #{post_id} успешно удален.",
                    reply_markup=get_post_management_keyboard(),
                    parse_mode="HTML"
                )
            else:
                await callback.message.answer(
                    f"❌ Ошибка при удалении поста #{post_id}.",
                    reply_markup=get_post_management_keyboard(),
                    parse_mode="HTML"
                )
        except Exception as e2:
            logger.error(f"Ошибка при отображении результата удаления: {e2}")
    
    await callback.answer()

# Обработчик для возврата в главное меню админа
@router.callback_query(F.data == "back_to_menu")
async def back_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик для возврата в главное меню админа"""
    await state.clear()
    try:
        # Пробуем отредактировать текущее сообщение
        await callback.message.edit_text(
            "🔑 <b>Панель администратора</b>\n\n"
            "Выберите действие из меню ниже:",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode="HTML"
        )
    except (TelegramBadRequest, Exception) as e:
        # Если сообщение содержит фото или его нельзя редактировать, удаляем его и отправляем новое
        try:
            await callback.message.delete()
            await callback.message.answer(
                "🔑 <b>Панель администратора</b>\n\n"
                "Выберите действие из меню ниже:",
                reply_markup=get_admin_menu_keyboard(),
                parse_mode="HTML"
            )
        except Exception as e2:
            logger.error(f"Ошибка при возврате в меню: {e2}")
    
    await callback.answer()

# Обработчик для поиска постов по тегу
@router.callback_query(F.data == "search_posts_by_tag")
async def search_posts_by_tag(callback: CallbackQuery, state: FSMContext):
    """Обработчик для начала поиска постов по тегу"""
    try:
        # Пробуем отредактировать текущее сообщение
        await callback.message.edit_text(
            "🔍 <b>Поиск постов по тегу</b>\n\n"
            "Пожалуйста, введите тег для поиска постов.\n"
            "Можно ввести несколько тегов через запятую или пробел.",
            reply_markup=get_post_management_keyboard(),
            parse_mode="HTML"
        )
    except (TelegramBadRequest, Exception) as e:
        # Если сообщение содержит фото или его нельзя редактировать, удаляем его и отправляем новое
        try:
            await callback.message.delete()
            await callback.message.answer(
                "🔍 <b>Поиск постов по тегу</b>\n\n"
                "Пожалуйста, введите тег для поиска постов.\n"
                "Можно ввести несколько тегов через запятую или пробел.",
                reply_markup=get_post_management_keyboard(),
                parse_mode="HTML"
            )
        except Exception as e2:
            logger.error(f"Ошибка при переходе к поиску: {e2}")
    
    await state.set_state(SearchPostStates.waiting_for_tag)
    await callback.answer()

# Обработчик для получения тега и отображения результатов поиска
@router.message(StateFilter(SearchPostStates.waiting_for_tag))
async def process_tag_search(message: Message, state: FSMContext, bot: Bot):
    """Обработчик для поиска постов по введенному тегу"""
    # Очищаем состояние
    await state.clear()
    
    # Получаем теги из сообщения
    tag_text = message.text.strip() if message.text else ""
    
    if not tag_text:
        await message.answer(
            "❌ Пожалуйста, введите тег для поиска.",
            reply_markup=get_post_management_keyboard()
        )
        return
    
    # Разбиваем строку на отдельные теги и очищаем от возможных # в начале
    tags = []
    for tag in re.split(r'[,\s]+', tag_text):
        if tag and not tag.isspace():
            # Удаляем # в начале, если есть
            clean_tag = tag.strip().lstrip('#')
            if clean_tag:
                tags.append(clean_tag)
    
    if not tags:
        await message.answer(
            "❌ Не удалось распознать теги. Пожалуйста, введите корректные теги.",
            reply_markup=get_post_management_keyboard()
        )
        return
    
    await message.answer(f"🔍 Ищем посты по тегам: {', '.join(['#' + tag for tag in tags])}")
    
    # Создаем сервис и ищем посты
    
    try:
        # Ищем посты по каждому тегу отдельно и объединяем результаты
        all_posts = []
        seen_ids = set()  # Для отслеживания уже добавленных постов
        
        for tag in tags:
            posts = await post_service.get_posts_by_tag(tag)
            # Добавляем только уникальные посты
            for post in posts:
                if post["id"] not in seen_ids:
                    all_posts.append(post)
                    seen_ids.add(post["id"])
        
        if not all_posts:
            await message.answer(
                f"🔍 <b>Результаты поиска</b>\n\n"
                f"По тегам {', '.join(['#' + tag for tag in tags])} ничего не найдено.",
                reply_markup=get_post_management_keyboard(),
                parse_mode="HTML"
            )
            return
        
        await message.answer(
            f"🔍 <b>Результаты поиска</b>\n\n"
            f"Найдено постов: {len(all_posts)}",
            reply_markup=get_post_list_keyboard(all_posts),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при поиске постов по тегам: {e}")
        await message.answer(
            "❌ Произошла ошибка при поиске постов.",
            reply_markup=get_post_management_keyboard()
        ) 

# Обработчик для начала редактирования поста
@router.callback_query(F.data.startswith("edit_post_"))
async def start_edit_post(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработчик для начала процесса редактирования поста"""
    try:
        # Извлекаем ID поста из callback.data
        post_id = int(callback.data.split("_")[-1])
        user_id = callback.from_user.id
        
        logger.info(f"Пользователь {user_id} начал редактирование поста с ID {post_id}")
        
        # Получаем информацию о посте
        async with get_session() as session:
            post_repo = PostRepository(session)
            post_model = await post_repo.get_by_id(post_id)
            if not post_model:
                await callback.answer("Пост не найден", show_alert=True)
                return
                
            # Преобразуем модель в словарь
            post = {
                "id": post_model.id,
                "title": post_model.title,
                "content": post_model.content,
                "image": post_model.image,
                "tag": post_model.tag,
                "username": post_model.username,
                "created_date": post_model.created_date.strftime("%Y-%m-%d %H:%M:%S"),
                "is_published": post_model.is_published == 1,
                "target_chat_id": post_model.target_chat_id,
                "target_chat_title": post_model.target_chat_title
            }
        
        # Проверяем права на редактирование
        from app.services.role_service import RoleService
        role_service = RoleService()
        is_admin = await role_service.check_user_role(user_id, "admin")
        can_edit = (post.get("user_id") == user_id) or is_admin
        
        if not can_edit:
            await callback.answer("У вас нет прав на редактирование этого поста", show_alert=True)
            return
        
        # Сохраняем данные поста в состояние
        await state.update_data(
            edit_post_id=post_id,
            current_title=post.get("title", ""),
            current_content=post.get("content", ""),
            current_image=post.get("image", ""),
            current_tag=post.get("tag", "")
        )
        
        # Создаем клавиатуру для выбора поля для редактирования
        buttons = [
            [InlineKeyboardButton(text="📝 Изменить название", callback_data="edit_field_name")],
            [InlineKeyboardButton(text="📄 Изменить описание", callback_data="edit_field_description")],
            [InlineKeyboardButton(text="🖼 Изменить изображение", callback_data="edit_field_image")],
            [InlineKeyboardButton(text="🏷 Изменить тег", callback_data="edit_field_tag")],
            [InlineKeyboardButton(text="✅ Сохранить изменения", callback_data="save_edited_post")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"view_post_{post_id}")]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Формируем сообщение с текущими данными поста
        message_text = (
            f"📝 <b>Редактирование поста #{post_id}</b>\n\n"
            f"<b>Название:</b> {post.get('title', '')}\n\n"
            f"<b>Описание:</b>\n{post.get('content', '')[:200]}{'...' if len(post.get('content', '')) > 200 else ''}\n\n"
            f"<b>Тег:</b> {post.get('tag', '') or 'Нет'}\n\n"
            f"<b>Изображение:</b> {'Есть' if post.get('image') else 'Нет'}\n\n"
            "Выберите поле для редактирования:"
        )
        
        # Проверяем наличие изображения
        if post.get("image"):
            # Если есть изображение, отправляем фото с подписью
            try:
                # Сначала удаляем предыдущее сообщение
                await callback.message.delete()
            except Exception as e:
                logger.warning(f"Не удалось удалить предыдущее сообщение: {e}")
                
            # Отправляем новое сообщение с фото
            await bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=post.get("image"),
                caption=message_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            # Если изображения нет, пробуем редактировать текущее сообщение
            try:
                await callback.message.edit_text(
                    message_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Не удалось отредактировать сообщение: {e}")
                # Если не удалось редактировать, удаляем и отправляем новое
                try:
                    await callback.message.delete()
                except Exception as delete_error:
                    logger.error(f"Ошибка при удалении сообщения: {delete_error}")
            
                await callback.message.answer(
                    message_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при начале редактирования поста: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при подготовке к редактированию поста", show_alert=True)

# Обработчики для редактирования полей поста
@router.callback_query(F.data == "edit_field_name")
async def edit_post_title(callback: CallbackQuery, state: FSMContext):
    """Обработчик для редактирования названия поста"""
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        post_id = data.get("edit_post_id")
        current_name = data.get("current_title", "")
        
        # Устанавливаем состояние редактирования названия
        await state.set_state(PostEditStates.edit_name)
        
        # Формируем текст сообщения
        message_text = (
            f"📝 <b>Редактирование названия поста #{post_id}</b>\n\n"
            f"Текущее название: <b>{current_name}</b>\n\n"
            "Введите новое название для поста:"
        )
        
        # Создаем клавиатуру
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"edit_post_{post_id}")]
        ])
        
        # Проверяем, можно ли редактировать сообщение
        try:
            # Пробуем редактировать сообщение
            await callback.message.edit_text(
                message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение: {e}")
            # Если сообщение нельзя редактировать, удаляем его и отправляем новое
            try:
                await callback.message.delete()
            except Exception as delete_error:
                logger.error(f"Ошибка при удалении сообщения: {delete_error}")
            
            await callback.message.answer(
                message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при редактировании названия поста: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)

@router.callback_query(F.data == "edit_field_description")
async def edit_post_content(callback: CallbackQuery, state: FSMContext):
    """Обработчик для редактирования описания поста"""
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        post_id = data.get("edit_post_id")
        current_description = data.get("current_content", "")
        
        # Устанавливаем состояние редактирования описания
        await state.set_state(PostEditStates.edit_description)
        
        # Формируем текст сообщения
        message_text = (
            f"📝 <b>Редактирование описания поста #{post_id}</b>\n\n"
            f"Текущее описание:\n<i>{current_description[:200]}{'...' if len(current_description) > 200 else ''}</i>\n\n"
            "Введите новое описание для поста:"
        )
        
        # Создаем клавиатуру
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"edit_post_{post_id}")]
        ])
        
        # Проверяем, можно ли редактировать сообщение
        try:
            # Пробуем редактировать сообщение
            await callback.message.edit_text(
                message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение: {e}")
            # Если сообщение нельзя редактировать, удаляем его и отправляем новое
            try:
                await callback.message.delete()
            except Exception as delete_error:
                logger.error(f"Ошибка при удалении сообщения: {delete_error}")
            
            await callback.message.answer(
                message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при редактировании описания поста: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)

@router.callback_query(F.data == "edit_field_image")
async def edit_post_image(callback: CallbackQuery, state: FSMContext):
    """Обработчик для редактирования изображения поста"""
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        post_id = data.get("edit_post_id")
        current_image = data.get("current_image", "")
        
        # Устанавливаем состояние редактирования изображения
        await state.set_state(PostEditStates.edit_image)
        
        # Формируем текст сообщения
        message_text = (
            f"📝 <b>Редактирование изображения поста #{post_id}</b>\n\n"
            f"{'Текущее изображение: <i>Есть</i>' if current_image else 'Текущее изображение: <i>Нет</i>'}\n\n"
            "Отправьте новое изображение для поста или введите URL-адрес изображения.\n"
            "Чтобы удалить изображение, введите слово <b>удалить</b>."
        )
        
        # Создаем клавиатуру
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"edit_post_{post_id}")]
        ])
        
        # Проверяем, можно ли редактировать сообщение
        try:
            # Пробуем редактировать сообщение
            await callback.message.edit_text(
                message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение: {e}")
            # Если сообщение нельзя редактировать, удаляем его и отправляем новое
            try:
                await callback.message.delete()
            except Exception as delete_error:
                logger.error(f"Ошибка при удалении сообщения: {delete_error}")
            
            await callback.message.answer(
                message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при редактировании изображения поста: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)

@router.callback_query(F.data == "edit_field_tag")
async def edit_post_tag(callback: CallbackQuery, state: FSMContext):
    """Обработчик для редактирования тега поста"""
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        post_id = data.get("edit_post_id")
        current_tag = data.get("current_tag", "")
        
        # Устанавливаем состояние редактирования тега
        await state.set_state(PostEditStates.edit_tag)
        
        # Формируем текст сообщения
        message_text = (
            f"📝 <b>Редактирование тега поста #{post_id}</b>\n\n"
            f"Текущий тег: <b>{current_tag or 'Нет'}</b>\n\n"
            "Введите новый тег для поста (без символа #).\n"
            "Чтобы удалить тег, введите слово <b>удалить</b>."
        )
        
        # Создаем клавиатуру
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"edit_post_{post_id}")]
        ])
        
        # Проверяем, можно ли редактировать сообщение
        try:
            # Пробуем редактировать сообщение
            await callback.message.edit_text(
                message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение: {e}")
            # Если сообщение нельзя редактировать, удаляем его и отправляем новое
            try:
                await callback.message.delete()
            except Exception as delete_error:
                logger.error(f"Ошибка при удалении сообщения: {delete_error}")
            
            await callback.message.answer(
                message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при редактировании тега поста: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)

# Обработчик для сохранения отредактированного поста
@router.callback_query(F.data == "save_edited_post")
async def save_edited_post(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработчик для сохранения отредактированного поста"""
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        post_id = data.get("edit_post_id")
        new_name = data.get("current_title", "")
        new_description = data.get("current_content", "")
        new_image = data.get("current_image", "")
        new_tag = data.get("current_tag", "")
        
        # Проверяем, что все необходимые поля заполнены
        if not new_name or not new_description:
            await callback.answer("Название и описание не могут быть пустыми", show_alert=True)
            return
        
        # Сохраняем изменения
        username = callback.from_user.username or f"user_{callback.from_user.id}"
        
        result = await post_service.update_post(
            post_id=post_id,
            title=new_name,
            content=new_description,
            image=new_image,
            tag=new_tag,
            change_username=username
        )
        
        if result["success"]:
            # Очищаем состояние
            await state.clear()
            
            # Информируем пользователя об успехе
            await callback.answer("✅ Пост успешно обновлен", show_alert=True)
            
            # Пытаемся удалить сообщение с интерфейсом редактирования
            try:
                await callback.message.delete()
            except Exception as delete_error:
                logger.warning(f"Не удалось удалить сообщение: {delete_error}")
            
            # Форматируем теги для отображения
            tags = new_tag.split() if new_tag else []
            formatted_tags = ' '.join([f"#{tag}" for tag in tags])
            
            # Формируем сообщение с информацией о посте
            message_text = (
                f"<b>Информация о посте (обновлен)</b>\n\n"
                f"<b>{new_name}</b>\n\n"
                f"{new_description}\n\n"
                f"<i>{formatted_tags}</i>\n"
                f"<i>Автор:</i> {username}\n"
                f"<i>Обновлен:</i> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Отправляем сообщение с информацией о посте
            if new_image:
                # Если у поста есть изображение, отправляем его с подписью
                await bot.send_photo(
                    chat_id=callback.message.chat.id,
                    photo=new_image,
                    caption=message_text,
                    reply_markup=get_post_actions_keyboard(post_id, False),
                    parse_mode="HTML"
                )
            else:
                # Если у поста нет изображения, отправляем текстовое сообщение
                await bot.send_message(
                    chat_id=callback.message.chat.id,
                    text=message_text,
                    reply_markup=get_post_actions_keyboard(post_id, False),
                    parse_mode="HTML"
                )
        else:
            # Информируем пользователя об ошибке
            await callback.answer(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка при сохранении отредактированного поста: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при сохранении изменений", show_alert=True)

# Обработчики для приема новых значений полей
@router.message(StateFilter(PostEditStates.edit_name))
async def process_new_name(message: Message, state: FSMContext, bot: Bot):
    """Обработчик для приема нового названия поста"""
    try:
        # Получаем новое название
        new_name = message.text.strip()
        
        if not new_name:
            await message.answer(
                "❌ Название не может быть пустым. Введите другое название:"
            )
            return
        
        # Получаем данные из состояния
        data = await state.get_data()
        post_id = data.get("edit_post_id")
        
        # Обновляем данные в состоянии
        await state.update_data(current_title=new_name)
        
        # Сообщаем пользователю об успешном изменении
        await message.answer(
            f"✅ Название поста успешно изменено на:\n<b>{new_name}</b>",
            parse_mode="HTML"
        )
        
        # Отображаем интерфейс редактирования
        await show_edit_interface(message.chat.id, post_id, state, bot)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке нового названия поста: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обновлении названия поста")

@router.message(StateFilter(PostEditStates.edit_description))
async def process_new_description(message: Message, state: FSMContext, bot: Bot):
    """Обработчик для приема нового описания поста"""
    try:
        # Получаем новое описание
        new_description = message.text.strip()
        
        if not new_description:
            await message.answer(
                "❌ Описание не может быть пустым. Введите другое описание:"
            )
            return
        
        # Получаем данные из состояния
        data = await state.get_data()
        post_id = data.get("edit_post_id")
        
        # Обновляем данные в состоянии
        await state.update_data(current_content=new_description)
        
        # Сообщаем пользователю об успешном изменении
        await message.answer(
            f"✅ Описание поста успешно изменено на:\n<b>{new_description[:100]}{'...' if len(new_description) > 100 else ''}</b>",
            parse_mode="HTML"
        )
        
        # Отображаем интерфейс редактирования
        await show_edit_interface(message.chat.id, post_id, state, bot)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке нового описания поста: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обновлении описания поста")

@router.message(StateFilter(PostEditStates.edit_image))
async def process_new_image(message: Message, state: FSMContext, bot: Bot):
    """Обработчик для приема нового изображения поста"""
    try:
        new_image = ""
        
        # Проверяем, пришло ли текстовое сообщение
        if message.text:
            text = message.text.strip().lower()
            
            # Если пользователь хочет удалить изображение
            if text == "удалить":
                new_image = ""
            else:
                # Иначе считаем, что пользователь прислал URL
                new_image = text
        
        # Проверяем, пришло ли изображение
        elif message.photo:
            # Получаем ID файла
            file_id = message.photo[-1].file_id
            new_image = file_id
        
        # Получаем данные из состояния
        data = await state.get_data()
        post_id = data.get("edit_post_id")
        
        # Обновляем данные в состоянии
        await state.update_data(current_image=new_image)
        
        # Сообщаем пользователю об успешном изменении
        if new_image:
            await message.answer(
                "✅ Изображение поста успешно обновлено",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "✅ Изображение поста успешно удалено",
                parse_mode="HTML"
            )
        
        # Отображаем интерфейс редактирования
        await show_edit_interface(message.chat.id, post_id, state, bot)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке нового изображения поста: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обновлении изображения поста")

@router.message(StateFilter(PostEditStates.edit_tag))
async def process_new_tag(message: Message, state: FSMContext, bot: Bot):
    """Обработчик для приема нового тега поста"""
    try:
        # Получаем новый тег
        text = message.text.strip()
        
        # Если пользователь хочет удалить тег
        if text.lower() == "удалить":
            new_tag = ""
        else:
            # Удаляем # если он есть
            new_tag = text.replace("#", "").strip()
        
        # Получаем данные из состояния
        data = await state.get_data()
        post_id = data.get("edit_post_id")
        
        # Обновляем данные в состоянии
        await state.update_data(current_tag=new_tag)
        
        # Сообщаем пользователю об успешном изменении
        if new_tag:
            await message.answer(
                f"✅ Тег поста успешно изменен на: <b>{new_tag}</b>",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "✅ Тег поста успешно удален",
                parse_mode="HTML"
            )
        
        # Отображаем интерфейс редактирования
        await show_edit_interface(message.chat.id, post_id, state, bot)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке нового тега поста: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обновлении тега поста")

# Вспомогательная функция для отображения интерфейса редактирования
async def show_edit_interface(chat_id: int, post_id: int, state: FSMContext, bot: Bot):
    """Отображает интерфейс редактирования поста"""
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        current_name = data.get("current_title", "")
        current_description = data.get("current_content", "")
        current_image = data.get("current_image", "")
        current_tag = data.get("current_tag", "")
        
        # Создаем клавиатуру
        buttons = [
            [InlineKeyboardButton(text="📝 Изменить название", callback_data="edit_field_name")],
            [InlineKeyboardButton(text="📄 Изменить описание", callback_data="edit_field_description")],
            [InlineKeyboardButton(text="🖼 Изменить изображение", callback_data="edit_field_image")],
            [InlineKeyboardButton(text="🏷 Изменить тег", callback_data="edit_field_tag")],
            [InlineKeyboardButton(text="✅ Сохранить изменения", callback_data="save_edited_post")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"view_post_{post_id}")]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Формируем сообщение
        message_text = (
            f"📝 <b>Редактирование поста #{post_id}</b>\n\n"
            f"<b>Название:</b> {current_name}\n\n"
            f"<b>Описание:</b>\n{current_description[:200]}{'...' if len(current_description) > 200 else ''}\n\n"
            f"<b>Тег:</b> {current_tag or 'Нет'}\n\n"
            f"<b>Изображение:</b> {'Есть' if current_image else 'Нет'}\n\n"
            "Выберите поле для редактирования:"
        )
        
        # Отправляем сообщение в зависимости от наличия изображения
        if current_image:
            await bot.send_photo(
                chat_id=chat_id,
                photo=current_image,
                caption=message_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Ошибка при отображении интерфейса редактирования: {e}", exc_info=True)
        await bot.send_message(
            chat_id=chat_id,
            text="❌ Произошла ошибка при отображении интерфейса редактирования"
        ) 