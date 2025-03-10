import logging
from datetime import datetime
import re
from typing import Optional, Any

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.exceptions import TelegramBadRequest

from handlers.admin.post_states import PostStates
from app.services.post_service import PostService
from app.core.decorators import role_required
from app.core.config import settings
from app.core.utils import format_tags
from utils.logger import log_function_call
from utils.ai_service import AIService
from keyboards.admin.posts import (
    get_post_management_keyboard,
    get_post_creation_cancel_keyboard,
    get_chat_selection_keyboard,
    get_save_post_keyboard,
    get_skip_keyboard,
    get_ai_generation_keyboard,
)

router = Router()
logger = logging.getLogger(__name__)

def log_error(logger, message: str, error: Exception, exc_info: bool = False) -> None:
    """Логирует ошибку с дополнительной информацией"""
    error_message = f"{message}: {str(error)}"
    logger.error(error_message, exc_info=exc_info)

# Начало создания поста
@router.callback_query(F.data == "create_post")
@log_function_call
async def start_post_creation(callback: CallbackQuery, state: FSMContext):
    """Обработчик для начала создания поста"""
    try:
        user_id = callback.from_user.id
        logger.info(f"Пользователь {user_id} начал создание нового поста")
        
        try:
            await callback.message.edit_text(
                "📝 <b>Создание нового поста</b>\n\n"
                "Пожалуйста, отправьте <b>название</b> поста.",
                reply_markup=get_post_creation_cancel_keyboard(),
                parse_mode="HTML"
            )
            logger.debug(f"Отправлено сообщение о начале создания поста для пользователя {user_id}")
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось отредактировать сообщение для пользователя {user_id}: {e}")
            await callback.message.answer(
                "📝 <b>Создание нового поста</b>\n\n"
                "Пожалуйста, отправьте <b>название</b> поста.",
                reply_markup=get_post_creation_cancel_keyboard(),
                parse_mode="HTML"
            )
        
        await state.set_state(PostStates.title)
        logger.debug(f"Установлено состояние {PostStates.title} для пользователя {user_id}")
        await callback.answer()
    
    except Exception as e:
        user_id = callback.from_user.id
        log_error(logger, f"Ошибка при начале создания поста пользователем {user_id}", e, exc_info=True)
        
        try:
            await callback.message.edit_text(
                "❌ Произошла ошибка при начале создания поста. Пожалуйста, попробуйте позже.",
                reply_markup=get_post_management_keyboard()
            )
        except Exception:
            await callback.message.answer(
                "❌ Произошла ошибка при начале создания поста. Пожалуйста, попробуйте позже.",
                reply_markup=get_post_management_keyboard()
            )
        
        await callback.answer("Произошла ошибка")

# Обработка названия поста
@router.message(StateFilter(PostStates.title))
async def process_post_name(message: Message, state: FSMContext):
    """Обработчик для получения названия поста"""
    try:
        user_id = message.from_user.id
        
        # Получаем название поста из сообщения
        title = message.html_text  # Сохраняем с HTML-форматированием
        logger.info(f"Пользователь {user_id} отправил название поста: '{title}'")
        
        # Проверяем, что название не пустое
        if not title or title.isspace():
            logger.warning(f"Пользователь {user_id} отправил пустое название поста")
            await message.answer(
                "❌ Название поста не может быть пустым. Пожалуйста, введите название поста:"
            )
            return
        
        # Сохраняем название поста в состоянии
        await state.update_data(title=title)
        
        # Переходим к следующему шагу - вводу описания поста
        await state.set_state(PostStates.content)
        logger.debug(f"Установлено состояние {PostStates.content} для пользователя {user_id}")
        
        await message.answer(
            f"✅ Название поста сохранено: <b>{title}</b>\n\n"
            "Теперь введите описание поста:",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке названия поста: {e}")
        await message.answer(
            "❌ Произошла ошибка при сохранении названия поста. Пожалуйста, попробуйте еще раз:"
        )

# Обработка описания поста
@router.message(StateFilter(PostStates.content))
async def process_post_description(message: Message, state: FSMContext):
    """Обработчик для получения описания поста"""
    try:
        user_id = message.from_user.id
        
        # Получаем описание поста из сообщения
        content = message.html_text  # Сохраняем с HTML-форматированием
        logger.info(f"Пользователь {user_id} отправил описание поста длиной {len(content)} символов")
        
        # Проверяем, что описание не пустое
        if not content or content.isspace():
            logger.warning(f"Пользователь {user_id} отправил пустое описание поста")
            await message.answer(
                "❌ Описание поста не может быть пустым. Пожалуйста, введите описание поста:"
            )
            return
        
        # Сохраняем описание поста в состоянии
        await state.update_data(content=content)
        
        # Переходим к следующему шагу - загрузке изображения
        await state.set_state(PostStates.image)
        logger.debug(f"Установлено состояние {PostStates.image} для пользователя {user_id}")
        
        await message.answer(
            "✅ Описание поста сохранено!\n\n"
            "Теперь отправьте изображение для поста или нажмите кнопку \"Пропустить\":",
            reply_markup=get_skip_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке описания поста: {e}")
        await message.answer(
            "❌ Произошла ошибка при сохранении описания поста. Пожалуйста, попробуйте еще раз:"
        )

# Обработка изображения поста
@router.message(StateFilter(PostStates.image))
async def process_post_image(message: Message, state: FSMContext, bot: Bot):
    """Обработчик для получения изображения поста"""
    try:
        user_id = message.from_user.id
        
        # Проверяем, что сообщение содержит фото
        if not message.photo:
            logger.warning(f"Пользователь {user_id} отправил сообщение без фото")
            await message.answer(
                "❌ Пожалуйста, отправьте изображение или нажмите кнопку \"Пропустить\":",
                reply_markup=get_skip_keyboard()
            )
            return
        
        # Получаем файл с наилучшим качеством
        photo = message.photo[-1]
        file_id = photo.file_id
        
        # Проверяем размер файла
        try:
            file_info = await bot.get_file(file_id)
            file_size = file_info.file_size
            
            # Если размер файла превышает 5 МБ, предупреждаем пользователя
            if file_size and file_size > 5 * 1024 * 1024:
                logger.warning(f"Пользователь {user_id} отправил слишком большое изображение: {file_size} байт")
                await message.answer(
                    "⚠️ Изображение слишком большое. Рекомендуется использовать изображения размером до 5 МБ.\n"
                    "Изображение будет сохранено, но это может вызвать проблемы при публикации."
                )
        except Exception as e:
            logger.warning(f"Не удалось получить информацию о файле: {e}")
        
        # Сохраняем ссылку на изображение в состоянии
        await state.update_data(image=file_id)
        logger.debug(f"Изображение сохранено в состоянии для пользователя {user_id}")
        
        # Переходим к следующему шагу - вводу тега
        await state.set_state(PostStates.tag)
        logger.debug(f"Установлено состояние {PostStates.tag} для пользователя {user_id}")
        
        await message.answer(
            "✅ Изображение сохранено!\n\n"
            "Теперь введите теги для поста (через пробел) или нажмите кнопку \"Пропустить\":",
            reply_markup=get_skip_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения поста: {e}")
        await message.answer(
            "❌ Произошла ошибка при сохранении изображения. Пожалуйста, попробуйте еще раз или нажмите кнопку \"Пропустить\":",
            reply_markup=get_skip_keyboard()
        )

# Обработка тега поста и завершение создания
@router.message(StateFilter(PostStates.tag))
async def process_post_tag(message: Message, state: FSMContext, bot: Bot):
    """Обработчик для получения тега поста"""
    try:
        user_id = message.from_user.id
        
        # Получаем теги из сообщения
        tag = message.text.strip()
        
        # Проверяем формат тегов
        if tag:
            # Нормализуем теги: убираем лишние пробелы, приводим к нижнему регистру
            tag = ' '.join([t.strip().lower() for t in tag.split() if t.strip()])
            
            # Проверяем, что теги не содержат специальных символов
            import re
            if re.search(r'[^\w\s]', tag):
                logger.warning(f"Пользователь {user_id} отправил теги с недопустимыми символами: '{tag}'")
                await message.answer(
                    "❌ Теги могут содержать только буквы, цифры и пробелы. Пожалуйста, введите теги снова:"
                )
                return
        
        logger.info(f"Теги сохранены для пользователя {user_id}: '{tag}'")
        
        # Сохраняем теги поста в состоянии
        await state.update_data(tag=tag)
        logger.debug(f"Теги сохранены в состоянии для пользователя {user_id}")
        
        try:
            # Получаем список доступных чатов для публикации
            post_service = PostService()
            chats = await post_service.get_available_chats(bot)
            
            if not chats:
                logger.warning(f"Не найдены доступные чаты для публикации для пользователя {user_id}")
                await message.answer(
                    "❌ Не найдены доступные чаты для публикации. Убедитесь, что бот добавлен в канал и имеет права администратора.",
                    reply_markup=get_post_management_keyboard()
                )
                await state.clear()
                return
            
            # Переходим к выбору чата для публикации
            await state.set_state(PostStates.select_chat)
            logger.debug(f"Установлено состояние {PostStates.select_chat} для пользователя {user_id}")
            
            await message.answer(
                "✅ Теги сохранены!\n\n"
                "Выберите чат для публикации поста:",
                reply_markup=get_chat_selection_keyboard(chats)
            )
        except Exception as e:
            logger.error(f"Ошибка при получении списка чатов: {e}")
            await message.answer(
                "❌ Произошла ошибка при получении списка чатов. Пожалуйста, попробуйте позже.",
                reply_markup=get_post_management_keyboard()
            )
            await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при обработке тегов поста: {e}")
        await message.answer(
            "❌ Произошла ошибка при сохранении тегов. Пожалуйста, попробуйте еще раз или нажмите кнопку \"Пропустить\":",
            reply_markup=get_skip_keyboard()
        )

# Обработка выбора чата
@router.callback_query(F.data.startswith("select_chat_"), StateFilter(PostStates.select_chat))
async def process_chat_selection(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработчик для выбора чата и завершения создания поста"""
    try:
        user_id = callback.from_user.id
        # Извлекаем ID выбранного чата
        chat_id_str = callback.data.split("_")[-1]
        logger.info(f"Пользователь {user_id} выбрал чат с ID: {chat_id_str}")
        
        try:
            # Преобразуем ID чата в число (0 для текущего чата)
            chat_id = int(chat_id_str)
            
            # Если выбран текущий чат, используем ID текущего чата
            if chat_id == 0:
                chat_id = callback.message.chat.id
                chat_title = "Текущий чат (тестовый режим)"
                logger.info(f"Пользователь {user_id} выбрал текущий чат (тестовый режим) с ID: {chat_id}")
            else:
                # Получаем информацию о выбранном чате
                try:
                    chat = await bot.get_chat(chat_id)
                    chat_title = chat.title or f"Чат {chat_id}"
                    logger.info(f"Получена информация о чате {chat_id}: {chat_title}")
                except Exception as e:
                    logger.error(f"Ошибка при получении информации о чате {chat_id}: {e}")
                    chat_title = f"Чат {chat_id}"
                    logger.warning(f"Используется стандартное название для чата {chat_id}")
            
            # Сохраняем информацию о выбранном чате
            await state.update_data(target_chat_id=chat_id, target_chat_title=chat_title)
            logger.debug(f"Сохранена информация о выбранном чате: ID={chat_id}, название='{chat_title}'")
            
            # Отправляем сообщение о выборе чата
            try:
                await callback.answer(f"Выбран чат: {chat_title}")
            except TelegramBadRequest as e:
                logger.warning(f"Не удалось отправить уведомление о выборе чата: {e}")
            
            # Завершаем создание поста
            await finish_post_creation(callback.message, state, bot)
            
        except ValueError as e:
            logger.error(f"Некорректный ID чата: {chat_id_str}: {e}")
            await callback.message.answer(
                "❌ Произошла ошибка при выборе чата. Пожалуйста, попробуйте снова.",
                reply_markup=get_post_management_keyboard()
            )
            await state.clear()
    
    except Exception as e:
        user_id = callback.from_user.id
        log_error(logger, f"Непредвиденная ошибка при выборе чата пользователем {user_id}", e, exc_info=True)
        
        try:
            await callback.message.edit_text(
                "❌ Произошла непредвиденная ошибка при выборе чата. Пожалуйста, попробуйте позже.",
                reply_markup=get_post_management_keyboard()
            )
        except Exception:
            await callback.message.answer(
                "❌ Произошла непредвиденная ошибка при выборе чата. Пожалуйста, попробуйте позже.",
                reply_markup=get_post_management_keyboard()
            )
        
        await callback.answer("Произошла ошибка")
        await state.clear()

# Обработка пропуска выбора чата
@router.callback_query(F.data == "skip_chat_selection", StateFilter(PostStates.select_chat))
async def skip_chat_selection(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработчик для пропуска выбора чата"""
    try:
        user_id = callback.from_user.id
        logger.info(f"Пользователь {user_id} выбрал использование канала по умолчанию")
        
        # Получаем канал по умолчанию из настроек
        from app.core.config import settings
        if settings.channel_id_as_int is not None:
            channel_id = settings.channel_id_as_int
            
            # Пытаемся получить информацию о канале
            try:
                chat = await bot.get_chat(channel_id)
                chat_title = chat.title or f"Канал {channel_id}"
            except Exception as e:
                log_error(logger, f"Не удалось получить информацию о канале {channel_id}", e)
                chat_title = f"Канал по умолчанию ({channel_id})"
            
            # Сохраняем информацию о выбранном чате
            await state.update_data(target_chat_id=channel_id, target_chat_title=chat_title)
            logger.debug(f"Сохранена информация о канале по умолчанию: ID={channel_id}, название='{chat_title}'")
            
            # Отправляем сообщение о выборе чата
            try:
                await callback.answer(f"Выбран канал по умолчанию: {chat_title}")
            except TelegramBadRequest as e:
                logger.warning(f"Не удалось отправить уведомление о выборе канала: {e}")
            
            # Завершаем создание поста
            await finish_post_creation(callback.message, state, bot)
            
        else:
            logger.warning(f"Пользователь {user_id} попытался пропустить выбор чата, но канал по умолчанию не настроен")
            
            # Получаем список доступных чатов для повторного отображения
            post_service = PostService()
            chats = await post_service.get_available_chats(bot)
            
            # Сообщаем пользователю о необходимости выбрать чат
            try:
                await callback.answer("Канал по умолчанию не настроен. Необходимо выбрать чат для публикации")
                await callback.message.edit_text(
                    "❗ <b>Выбор чата обязателен</b> для публикации поста, так как канал по умолчанию не настроен.\n\n"
                    "Пожалуйста, выберите один из доступных чатов:",
                    reply_markup=get_chat_selection_keyboard(chats, show_skip_button=False),
                    parse_mode="HTML"
                )
            except TelegramBadRequest as e:
                logger.warning(f"Не удалось отправить уведомление или обновить сообщение: {e}")
                await callback.message.answer(
                    "❗ <b>Выбор чата обязателен</b> для публикации поста, так как канал по умолчанию не настроен.\n\n"
                    "Пожалуйста, выберите один из доступных чатов:",
                    reply_markup=get_chat_selection_keyboard(chats, show_skip_button=False),
                    parse_mode="HTML"
                )
    
    except Exception as e:
        user_id = callback.from_user.id
        log_error(logger, f"Ошибка при обработке пропуска выбора чата пользователем {user_id}", e, exc_info=True)
        
        try:
            await callback.message.edit_text(
                "❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.",
                reply_markup=get_post_management_keyboard()
            )
        except Exception:
            await callback.message.answer(
                "❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.",
                reply_markup=get_post_management_keyboard()
            )
        
        await callback.answer("Произошла ошибка")
        await state.clear()

# Функция для завершения создания поста
async def finish_post_creation(message, state: FSMContext, bot: Bot):
    """Функция для завершения создания поста и сохранения его в базе данных"""
    try:
        # Получаем все данные из состояния
        data = await state.get_data()
        title = data.get("title", "")
        content = data.get("content", "")
        image = data.get("image", "")
        tag = data.get("tag", "")
        target_chat_id = data.get("target_chat_id")
        target_chat_title = data.get("target_chat_title")
        
        user_id = message.chat.id if hasattr(message, 'chat') else message.from_user.id
        logger.info(f"Завершение создания поста пользователем {user_id}: '{title}'")
        logger.debug(f"Данные поста: title='{title}', content_length={len(content)}, image={bool(image)}, tag='{tag}', target_chat={target_chat_title} ({target_chat_id})")
        
        # Проверяем, указан ли чат для публикации
        if target_chat_id is None:
            logger.error(f"Не указан чат для публикации поста пользователем {user_id}")
            
            try:
                # Получаем список доступных чатов для отображения
                post_service = PostService()
                chats = await post_service.get_available_chats(bot)
                logger.debug(f"Получено {len(chats)} доступных чатов для выбора")
                
                await message.edit_text(
                    "❗ <b>Выбор чата обязателен</b> для публикации поста.\n\n"
                    "Пожалуйста, выберите один из доступных чатов:",
                    reply_markup=get_chat_selection_keyboard(chats, show_skip_button=False),
                    parse_mode="HTML"
                )
            except TelegramBadRequest as e:
                logger.warning(f"Не удалось отредактировать сообщение для пользователя {user_id}: {e}")
                await message.answer(
                    "❗ <b>Ошибка при создании поста</b>: не выбран чат для публикации.\n\n"
                    "Пожалуйста, попробуйте создать пост заново и выберите чат.",
                    reply_markup=get_post_management_keyboard(),
                    parse_mode="HTML"
                )
            
            # Сохраняем данные в состоянии, чтобы пользователь мог продолжить создание поста
            await state.set_state(PostStates.select_chat)
            return
        
        # Создаем пост в базе данных
        post_service = PostService()
        
        # Отправляем сообщение о создании поста
        try:
            creation_message = await message.edit_text(
                "⏳ Создание поста...",
                parse_mode="HTML"
            )
            logger.debug(f"Отправлено сообщение о процессе создания поста для пользователя {user_id}")
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось отредактировать сообщение для пользователя {user_id}: {e}")
            creation_message = await message.answer(
                "⏳ Создание поста...",
                parse_mode="HTML"
            )
        
        # Создаем пост
        logger.debug(f"Вызов метода create_post с параметрами: title='{title}', content_length={len(content)}, image={bool(image)}, tag='{tag}', user_id={user_id}, target_chat_id={target_chat_id}, target_chat_title='{target_chat_title}'")
        post_data = await post_service.create_post(
            title=title,
            content=content,
            image=image,
            tag=tag,
            user_id=user_id,
            target_chat_id=target_chat_id,
            target_chat_title=target_chat_title
        )
        
        # Очищаем состояние
        await state.clear()
        logger.debug(f"Состояние очищено для пользователя {user_id}")
        
        if not post_data:
            logger.error(f"Ошибка при создании поста пользователем {user_id}: post_data is None")
            await creation_message.edit_text(
                "❌ Произошла ошибка при создании поста. Пожалуйста, попробуйте позже.",
                reply_markup=get_post_management_keyboard()
            )
            return
        
        logger.info(f"Пост успешно создан пользователем {user_id}, ID поста: {post_data.get('id')}")
        logger.debug(f"Данные созданного поста: {post_data}")
        
        # Форматируем теги для отображения
        tags = tag.split()
        formatted_tags = ' '.join([f"#{tag}" for tag in tags])
        
        # Информация о чате для публикации
        chat_info = ""
        if target_chat_id and target_chat_title:
            chat_info = f"<i>Чат для публикации:</i> {target_chat_title}\n"
        
        # Отправляем сообщение с предпросмотром поста
        try:
            if image:
                logger.debug(f"Отправка предпросмотра поста с изображением для пользователя {user_id}")
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=image,
                    caption=(
                        f"✅ Пост успешно создан!\n\n"
                        f"<b>{title}</b>\n\n"
                        f"{content}\n\n"
                        f"<i>{formatted_tags}</i>\n"
                        f"{chat_info}"
                    ),
                    reply_markup=get_post_management_keyboard(),
                    parse_mode="HTML"
                )
            else:
                logger.debug(f"Отправка предпросмотра поста без изображения для пользователя {user_id}")
                await creation_message.edit_text(
                    text=(
                        f"✅ Пост успешно создан!\n\n"
                        f"<b>{title}</b>\n\n"
                        f"{content}\n\n"
                        f"<i>{formatted_tags}</i>\n"
                        f"{chat_info}"
                    ),
                    reply_markup=get_post_management_keyboard(),
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Ошибка при отправке предпросмотра поста для пользователя {user_id}: {e}", exc_info=True)
            await creation_message.edit_text(
                "✅ Пост успешно создан, но произошла ошибка при отображении предпросмотра.",
                reply_markup=get_post_management_keyboard()
            )
    except Exception as e:
        logger.error(f"Критическая ошибка при создании поста: {e}", exc_info=True)
        
        try:
            await message.edit_text(
                "❌ Произошла ошибка при создании поста. Пожалуйста, попробуйте позже.",
                reply_markup=get_post_management_keyboard()
            )
        except Exception as edit_error:
            logger.error(f"Не удалось отредактировать сообщение об ошибке: {edit_error}")
            await message.answer(
                "❌ Произошла ошибка при создании поста. Пожалуйста, попробуйте позже.",
                reply_markup=get_post_management_keyboard()
            )
        
        # Очищаем состояние в случае ошибки
        await state.clear()

# Отмена создания поста
@router.callback_query(F.data == "cancel_post_creation")
async def cancel_post_creation(callback: CallbackQuery, state: FSMContext):
    """Обработчик для отмены создания поста"""
    try:
        user_id = callback.from_user.id
        current_state = await state.get_state()
        logger.info(f"Пользователь {user_id} запросил отмену создания поста. Текущее состояние: {current_state}")
        
        if current_state in [s.state for s in PostStates.__states__]:
            await state.clear()
            logger.info(f"Состояние очищено для пользователя {user_id}")
            
            try:
                await callback.message.edit_text(
                    "❌ Создание поста отменено.",
                    reply_markup=get_post_management_keyboard()
                )
                logger.debug(f"Отправлено сообщение об отмене создания поста для пользователя {user_id}")
            except TelegramBadRequest as e:
                logger.warning(f"Не удалось отредактировать сообщение для пользователя {user_id}: {e}")
                await callback.message.answer(
                    "❌ Создание поста отменено.",
                    reply_markup=get_post_management_keyboard()
                )
        else:
            logger.info(f"Пользователь {user_id} пытается отменить создание поста, но активного процесса нет")
            
            try:
                await callback.message.edit_text(
                    "Нет активного процесса создания поста.",
                    reply_markup=get_post_management_keyboard()
                )
            except TelegramBadRequest as e:
                logger.warning(f"Не удалось отредактировать сообщение для пользователя {user_id}: {e}")
                await callback.message.answer(
                    "Нет активного процесса создания поста.",
                    reply_markup=get_post_management_keyboard()
                )
        
        await callback.answer()
        
    except Exception as e:
        user_id = callback.from_user.id
        log_error(logger, f"Ошибка при отмене создания поста пользователем {user_id}", e, exc_info=True)
        
        try:
            await callback.message.edit_text(
                "Произошла ошибка при отмене создания поста.",
                reply_markup=get_post_management_keyboard()
            )
        except Exception:
            await callback.message.answer(
                "Произошла ошибка при отмене создания поста.",
                reply_markup=get_post_management_keyboard()
            )
        
        # В любом случае очищаем состояние
        await state.clear()
        await callback.answer("Произошла ошибка, но создание поста отменено")

@router.callback_query(F.data == "skip")
async def skip_current_step(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработчик для пропуска текущего шага при создании поста"""
    try:
        user_id = callback.from_user.id
        current_state = await state.get_state()
        logger.info(f"Пользователь {user_id} пропускает шаг {current_state}")
        
        if current_state == PostStates.image.state:
            # Если пропускаем загрузку изображения
            await state.update_data(image="")
            logger.debug(f"Пропущен этап добавления изображения для пользователя {user_id}")
            
            # Переходим к следующему шагу - вводу тега
            await state.set_state(PostStates.tag)
            
            await callback.message.edit_text(
                "✅ Этап добавления изображения пропущен.\n\n"
                "Теперь введите теги для поста (через пробел) или нажмите кнопку \"Пропустить\":",
                reply_markup=get_skip_keyboard()
            )
            
        elif current_state == PostStates.tag.state:
            # Если пропускаем ввод тегов
            await state.update_data(tag="")
            logger.debug(f"Пропущен этап добавления тегов для пользователя {user_id}")
            
            # Получаем список доступных чатов для публикации
            post_service = PostService()
            chats = await post_service.get_available_chats(bot)
            
            if not chats:
                logger.warning(f"Не найдены доступные чаты для публикации для пользователя {user_id}")
                await callback.message.edit_text(
                    "❌ Не найдены доступные чаты для публикации. Убедитесь, что бот добавлен в канал и имеет права администратора.",
                    reply_markup=get_post_management_keyboard()
                )
                await state.clear()
                return
            
            # Переходим к выбору чата для публикации
            await state.set_state(PostStates.select_chat)
            
            await callback.message.edit_text(
                "✅ Этап добавления тегов пропущен.\n\n"
                "Выберите чат для публикации поста:",
                reply_markup=get_chat_selection_keyboard(chats)
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при пропуске шага: {e}")
        await callback.answer("Произошла ошибка при пропуске шага")

# Обработчик кнопки "Сгенерировать AI"
@router.callback_query(F.data == "generate_post_ai")
@log_function_call
async def start_ai_generation(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс генерации контента с помощью AI"""
    try:
        user_id = callback.from_user.id
        logger.info(f"Пользователь {user_id} выбрал генерацию контента через AI")
        
        await callback.message.edit_text(
            "🤖 <b>Генерация поста с помощью AI</b>\n\n"
            "Введите тему или идею для генерации контента. Чем подробнее вы опишете, тем лучше будет результат.\n\n"
            "Примеры:\n"
            "• Как медитация помогает управлять стрессом\n"
            "• 5 способов улучшить свои коммуникативные навыки\n"
            "• Что происходит с мозгом во время сна",
            reply_markup=get_post_creation_cancel_keyboard(),
            parse_mode="HTML"
        )
        
        await state.set_state(PostStates.ai_prompt)
        logger.debug(f"Установлено состояние {PostStates.ai_prompt} для пользователя {user_id}")
        await callback.answer()
        
    except Exception as e:
        user_id = callback.from_user.id
        log_error(logger, f"Ошибка при начале генерации AI контента пользователем {user_id}", e, exc_info=True)
        
        try:
            await callback.message.edit_text(
                "❌ Произошла ошибка при запуске генерации контента. Пожалуйста, попробуйте позже.",
                reply_markup=get_post_creation_cancel_keyboard()
            )
        except Exception:
            await callback.message.answer(
                "❌ Произошла ошибка при запуске генерации контента. Пожалуйста, попробуйте позже.",
                reply_markup=get_post_creation_cancel_keyboard()
            )
        
        await callback.answer("Произошла ошибка")

# Обработчик ввода темы для генерации
@router.message(StateFilter(PostStates.ai_prompt))
async def process_ai_prompt(message: Message, state: FSMContext):
    """Обрабатывает ввод темы для генерации контента с помощью AI"""
    try:
        user_id = message.from_user.id
        prompt = message.text
        
        # Проверяем, что тема не пустая
        if not prompt or prompt.isspace():
            logger.warning(f"Пользователь {user_id} отправил пустой промт для AI")
            await message.answer(
                "❌ Тема не может быть пустой. Пожалуйста, введите тему для генерации контента:"
            )
            return
        
        logger.info(f"Пользователь {user_id} отправил тему для генерации: '{prompt}'")
        
        # Сохраняем промт в состоянии
        await state.update_data(ai_prompt=prompt)
        
        # Отправляем сообщение о процессе генерации
        await message.answer(
            "⏳ <b>Генерация контента...</b>\n\n"
            "Пожалуйста, подождите. Это может занять некоторое время.",
            parse_mode="HTML"
        )
        
        # Устанавливаем состояние генерации
        await state.set_state(PostStates.ai_generating)
        
        # Создаем экземпляр сервиса AI
        ai_service = AIService()
        
        # Генерируем текст поста
        generated_content = await ai_service.generate_post_content(prompt)
        
        # Генерируем название на основе содержимого
        generated_title = await ai_service.generate_post_title(generated_content)
        
        # Генерируем хештеги
        generated_tags = await ai_service.generate_post_tags(generated_content)
        
        # Сохраняем сгенерированные данные в состоянии
        await state.update_data(
            ai_generated_content=generated_content,
            ai_generated_title=generated_title,
            ai_generated_tags=generated_tags
        )
        
        # Отправляем результат пользователю
        result_message = (
            f"✅ <b>Контент успешно сгенерирован!</b>\n\n"
            f"<b>Название:</b>\n{generated_title}\n\n"
            f"<b>Текст:</b>\n{generated_content}\n\n"
            f"<b>Хештеги:</b>\n{generated_tags}\n\n"
            f"Выберите действие:"
        )
        
        await message.answer(
            result_message,
            reply_markup=get_ai_generation_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при генерации контента через AI: {e}", exc_info=True)
        await message.answer(
            "❌ <b>Произошла ошибка при генерации контента.</b>\n\n"
            "Пожалуйста, попробуйте еще раз или введите контент вручную.",
            reply_markup=get_post_creation_cancel_keyboard(),
            parse_mode="HTML"
        )

# Обработчик использования сгенерированного контента
@router.callback_query(F.data == "use_ai_content")
async def use_ai_content(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает принятие сгенерированного AI контента"""
    try:
        user_id = callback.from_user.id
        logger.info(f"Пользователь {user_id} принял сгенерированный AI контент")
        
        # Получаем сгенерированные данные из состояния
        data = await state.get_data()
        generated_title = data.get("ai_generated_title", "")
        generated_content = data.get("ai_generated_content", "")
        generated_tags = data.get("ai_generated_tags", "")
        
        # Сохраняем данные в состоянии для дальнейшего использования
        await state.update_data(
            title=generated_title,
            content=generated_content,
            tag=generated_tags
        )
        
        # Переходим к загрузке изображения
        await state.set_state(PostStates.image)
        
        await callback.message.edit_text(
            "✅ <b>Контент принят!</b>\n\n"
            "Теперь отправьте изображение для поста или нажмите кнопку \"Пропустить\":",
            reply_markup=get_skip_keyboard(),
            parse_mode="HTML"
        )
        
        await callback.answer()
        
    except Exception as e:
        log_error(logger, f"Ошибка при обработке сгенерированного контента: {e}", exc_info=True)
        
        try:
            await callback.message.edit_text(
                "❌ Произошла ошибка при обработке контента. Пожалуйста, попробуйте снова.",
                reply_markup=get_post_creation_cancel_keyboard()
            )
        except Exception:
            await callback.message.answer(
                "❌ Произошла ошибка при обработке контента. Пожалуйста, попробуйте снова.",
                reply_markup=get_post_creation_cancel_keyboard()
            )
        
        await callback.answer("Произошла ошибка")

# Обработчик повторной генерации контента
@router.callback_query(F.data == "regenerate_ai")
async def regenerate_ai_content(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает запрос на повторную генерацию контента через AI"""
    try:
        user_id = callback.from_user.id
        logger.info(f"Пользователь {user_id} запросил повторную генерацию контента")
        
        # Получаем исходный промт
        data = await state.get_data()
        original_prompt = data.get("ai_prompt", "")
        
        # Сообщаем о начале повторной генерации
        await callback.message.edit_text(
            "⏳ <b>Повторная генерация контента...</b>\n\n"
            "Пожалуйста, подождите. Это может занять некоторое время.",
            parse_mode="HTML"
        )
        
        # Создаем экземпляр сервиса AI
        ai_service = AIService()
        
        # Генерируем текст поста
        generated_content = await ai_service.generate_post_content(original_prompt)
        
        # Генерируем название на основе содержимого
        generated_title = await ai_service.generate_post_title(generated_content)
        
        # Генерируем хештеги
        generated_tags = await ai_service.generate_post_tags(generated_content)
        
        # Сохраняем сгенерированные данные в состоянии
        await state.update_data(
            ai_generated_content=generated_content,
            ai_generated_title=generated_title,
            ai_generated_tags=generated_tags
        )
        
        # Отправляем результат пользователю
        result_message = (
            f"✅ <b>Новый контент успешно сгенерирован!</b>\n\n"
            f"<b>Название:</b>\n{generated_title}\n\n"
            f"<b>Текст:</b>\n{generated_content}\n\n"
            f"<b>Хештеги:</b>\n{generated_tags}\n\n"
            f"Выберите действие:"
        )
        
        await callback.message.edit_text(
            result_message,
            reply_markup=get_ai_generation_keyboard(),
            parse_mode="HTML"
        )
        
        await callback.answer()
        
    except Exception as e:
        log_error(logger, f"Ошибка при повторной генерации контента: {e}", exc_info=True)
        
        try:
            await callback.message.edit_text(
                "❌ Произошла ошибка при повторной генерации контента. Пожалуйста, попробуйте позже.",
                reply_markup=get_post_creation_cancel_keyboard()
            )
        except Exception:
            await callback.message.answer(
                "❌ Произошла ошибка при повторной генерации контента. Пожалуйста, попробуйте позже.",
                reply_markup=get_post_creation_cancel_keyboard()
            )
        
        await callback.answer("Произошла ошибка")

# Обработчик отмены генерации через AI
@router.callback_query(F.data == "cancel_ai_generation")
async def cancel_ai_generation(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает отмену генерации контента AI и возвращает к ручному вводу"""
    try:
        user_id = callback.from_user.id
        logger.info(f"Пользователь {user_id} отменил генерацию контента через AI")
        
        # Возвращаемся к первому шагу создания поста
        await state.set_state(PostStates.title)
        
        await callback.message.edit_text(
            "📝 <b>Создание нового поста</b>\n\n"
            "Пожалуйста, отправьте <b>название</b> поста.",
            reply_markup=get_post_creation_cancel_keyboard(),
            parse_mode="HTML"
        )
        
        await callback.answer()
        
    except Exception as e:
        log_error(logger, f"Ошибка при отмене генерации контента: {e}", exc_info=True)
        
        try:
            await callback.message.edit_text(
                "❌ Произошла ошибка при отмене генерации. Пожалуйста, попробуйте снова.",
                reply_markup=get_post_creation_cancel_keyboard()
            )
        except Exception:
            await callback.message.answer(
                "❌ Произошла ошибка при отмене генерации. Пожалуйста, попробуйте снова.",
                reply_markup=get_post_creation_cancel_keyboard()
            )
        
        await callback.answer("Произошла ошибка") 