from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import os

from aiogram import Bot
from aiogram.types import FSInputFile, ChatMemberAdministrator
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.db.session import get_session
from app.db.repositories.post_repository import PostRepository
from app.db.repositories.user_repository import UserRepository
from app.services.channel_service import ChannelService
from utils.logger import setup_logger, log_error, log_params
from app.core.config import settings
from app.db.models.posts import Post

class PostService:
    """Сервис для работы с постами"""
    
    def __init__(self):
        self.logger = setup_logger("post_service")
        self.session_factory = get_session
        
    async def _get_post_repository(self):
        """
        Получает репозиторий постов с новой сессией
        
        Returns:
            PostRepository: Репозиторий постов
        """
        async with self.session_factory() as session:
            return PostRepository(session)
        
    async def create_post(
        self, 
        title: str, 
        content: str, 
        image: str, 
        tag: str, 
        user_id: int,
        target_chat_id: Optional[int] = None,
        target_chat_title: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Создание нового поста
        
        Args:
            title: Название поста
            content: Описание поста
            image: Ссылка на изображение поста
            tag: Теги поста, разделенные пробелами
            user_id: ID пользователя, создавшего пост
            target_chat_id: ID чата для публикации (обязательно для публикации)
            target_chat_title: Название чата для публикации (опционально)
            
        Returns:
            Optional[Dict[str, Any]]: Данные созданного поста или None в случае ошибки
        """
        self.logger.info(f"Начало создания поста пользователем {user_id}")
        self.logger.debug(f"Параметры: title='{title}', content_length={len(content)}, image={bool(image)}, tag='{tag}', target_chat_id={target_chat_id}, target_chat_title='{target_chat_title}'")
        
        async with get_session() as session:
            try:
                # Получение информации о пользователе
                user_repo = UserRepository(session)
                user = await user_repo.get_by_user_id(user_id)
                
                if not user:
                    self.logger.error(f"Пользователь с ID {user_id} не найден в базе данных")
                    return None
                
                username = user.username or f"user_{user_id}"
                self.logger.debug(f"Получена информация о пользователе: username='{username}'")
                
                # Нормализация тегов: убираем лишние пробелы, убеждаемся, что теги разделены одним пробелом
                normalized_tags = ' '.join([t.strip() for t in tag.split() if t.strip()])
                self.logger.debug(f"Нормализованные теги: '{normalized_tags}'")
                
                # Проверка наличия чата для публикации
                if target_chat_id is None or target_chat_id == 0:
                    self.logger.warning(f"Пост создается без указания чата для публикации")
                
                # Создание поста
                post_repo = PostRepository(session)
                self.logger.debug(f"Вызов метода create_post в репозитории")
                post = await post_repo.create_post(
                    title=title,
                    content=content,
                    image=image,
                    tag=normalized_tags,
                    username=username,
                    user_id=user_id,
                    target_chat_id=target_chat_id,
                    target_chat_title=target_chat_title
                )
                
                if not post:
                    self.logger.error(f"Не удалось создать пост: репозиторий вернул None")
                    return None
                
                self.logger.info(f"Пост успешно создан: ID={post.id}")
                
                # Преобразование объекта поста в словарь для возврата
                # Разбиваем строку тегов на список для удобства клиента
                tags_list = normalized_tags.split() if normalized_tags else []
                
                result = {
                    "id": post.id,
                    "title": post.title,
                    "content": post.content,
                    "image": post.image,
                    "tag": post.tag,
                    "tags_list": tags_list,  # Добавляем список тегов для удобства
                    "username": post.username,
                    "created_date": post.created_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "target_chat_id": post.target_chat_id,
                    "target_chat_title": post.target_chat_title
                }
                
                self.logger.debug(f"Возвращаемые данные поста: {result}")
                return result
            except Exception as e:
                self.logger.error(f"Ошибка при создании поста: {e}", exc_info=True)
                return None

    async def publish_post_to_channel(self, post_id: int, bot: Bot, target_chat_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Публикует пост в канал
        
        Args:
            post_id: ID поста
            bot: Экземпляр бота
            target_chat_id: ID чата для публикации (опционально)
            
        Returns:
            Dict[str, Any]: Результат публикации в формате:
            {
                "success": bool,  # Успешно ли опубликован пост
                "error": str,     # Текст ошибки (если success=False)
                "publication_date": str,  # Дата публикации (если success=True)
                "channel_title": str,     # Название канала (если success=True)
                "message_id": int,        # ID сообщения (если success=True)
            }
        """
        self.logger.info(f"Запрос на публикацию поста {post_id} в канал. target_chat_id={target_chat_id}")
        
        # Получаем пост из базы данных
        try:
            post_repository = await self._get_post_repository()
            post = await post_repository.get_by_id(post_id)
            
            if not post:
                return self._create_error_response(f"Пост с ID {post_id} не найден")
            
            # Проверяем, не опубликован ли уже пост
            if post.is_published and post.published_at:
                return self._create_error_response(
                    f"Пост уже опубликован {post.published_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            
            # Определяем целевой чат
            chat_info = await self._determine_target_chat(bot, target_chat_id, post)
            if not chat_info["success"]:
                return chat_info
            
            chat_id = chat_info["chat_id"]
            chat_title = chat_info["chat_title"]
            test_mode = chat_info["test_mode"]
            
            # Проверяем права бота в канале
            if not test_mode:
                bot_rights = await self._check_bot_rights(bot, chat_id)
                if not bot_rights["success"]:
                    return bot_rights
            
            # Публикуем пост
            publish_result = await self._send_post_to_channel(bot, post, chat_id)
            if not publish_result["success"]:
                return publish_result
            
            # Обновляем статус поста в БД
            await post_repository.mark_as_published(
                post_id=post_id,
                message_id=publish_result["message_id"],
                chat_id=chat_id,
                chat_title=chat_title
            )
            
            # Обновляем время использования канала, если это не тестовый режим
            if not test_mode:
                await self._update_channel_last_used(chat_id)
            
            self.logger.info(f"Пост {post_id} успешно опубликован в канал {chat_title} ({chat_id})")
            return {
                "success": True,
                "message_id": publish_result["message_id"],
                "publication_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "channel_title": chat_title
            }
        except Exception as e:
            self.logger.error(f"Критическая ошибка при публикации поста: {e}", exc_info=True)
            return self._create_error_response(f"Неожиданная ошибка: {str(e)}")

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """
        Создает стандартный ответ с ошибкой
        
        Args:
            error_message: Текст ошибки
            
        Returns:
            Dict[str, Any]: Ответ с ошибкой
        """
        return {
            "success": False,
            "error": error_message
        }

    async def _determine_target_chat(self, bot: Bot, target_chat_id: Optional[Union[int, str]], post: Post) -> Dict[str, Any]:
        """
        Определяет целевой чат для публикации поста
        
        Args:
            bot: Экземпляр бота
            target_chat_id: ID чата для публикации (опционально)
            post: Объект поста
            
        Returns:
            Dict[str, Any]: Информация о целевом чате
        """
        try:
            chat_id = None
            chat_title = "Неизвестный канал"
            test_mode = False
            
            # Преобразуем target_chat_id в int, если возможно
            if target_chat_id is not None:
                try:
                    if isinstance(target_chat_id, str):
                        if target_chat_id.isdigit() or (target_chat_id.startswith('-') and target_chat_id[1:].isdigit()):
                            target_chat_id = int(target_chat_id)
                        else:
                            self.logger.warning(f"Некорректный ID канала: {target_chat_id}. Используем канал по умолчанию.")
                            target_chat_id = None
                except Exception as e:
                    self.logger.warning(f"Ошибка при преобразовании ID канала: {e}. Используем канал по умолчанию.")
                    target_chat_id = None
            
            # Если указан ID чата, используем его
            if target_chat_id is not None:
                chat_id = target_chat_id
                self.logger.info(f"Используем указанный ID чата: {chat_id}")
                
                # Получаем информацию о канале, чтобы проверить его существование и получить название
                try:
                    chat_info = await bot.get_chat(chat_id)
                    chat_title = chat_info.title or chat_info.username or str(chat_id)
                    self.logger.info(f"Получена информация о канале: {chat_title} ({chat_id})")
                except Exception as e:
                    self.logger.warning(f"Не удалось получить информацию о канале {chat_id}: {e}")
                    # Продолжаем, даже если не удалось получить информацию о канале
            else:
                # Пытаемся использовать существующий целевой чат из поста
                if post.target_chat_id:
                    chat_id = post.target_chat_id
                    chat_title = post.target_chat_title or "Целевой канал"
                    self.logger.info(f"Используем целевой канал из поста: {chat_title} ({chat_id})")
                else:
                    # Получаем список доступных каналов
                    try:
                        channels = await self.get_available_chats(bot)
                        
                        # Ищем канал по умолчанию
                        default_channel = next((c for c in channels if c.get("is_default")), None)
                        
                        if default_channel:
                            # Если найден канал по умолчанию, используем его
                            chat_id = default_channel.get("chat_id")
                            chat_title = default_channel.get("title")
                            self.logger.info(f"Найден канал по умолчанию: {chat_title} ({chat_id})")
                        elif channels:
                            # Если нет канала по умолчанию, берем первый из списка
                            chat_id = channels[0].get("chat_id")
                            chat_title = channels[0].get("title")
                            self.logger.info(f"Канал по умолчанию не найден, используем первый: {chat_title} ({chat_id})")
                        else:
                            self.logger.warning("Не найдено доступных каналов для публикации")
                            return self._create_error_response("Не найдено доступных каналов для публикации")
                    except Exception as e:
                        self.logger.error(f"Ошибка при получении списка доступных каналов: {e}", exc_info=True)
                        return self._create_error_response(f"Ошибка при получении списка каналов: {str(e)}")
            
            # Если это тестовый режим (chat_id = 0), публикуем в текущий чат
            if chat_id == 0:
                test_mode = True
                self.logger.info("Активирован тестовый режим публикации (в текущий чат)")
                
                # В тестовом режиме используем user_id автора поста
                chat_id = post.user_id
                self.logger.info(f"В тестовом режиме используем ID пользователя как chat_id: {chat_id}")
                chat_title = "Тестовый режим (текущий чат)"
            
            # Если не удалось определить chat_id, возвращаем ошибку
            if not chat_id:
                self.logger.error("Не удалось определить ID чата для публикации")
                return self._create_error_response("Не удалось определить ID чата для публикации")
            
            return {
                "success": True,
                "chat_id": chat_id,
                "chat_title": chat_title,
                "test_mode": test_mode
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при определении целевого чата: {e}", exc_info=True)
            return self._create_error_response(f"Ошибка при определении целевого чата: {str(e)}")

    async def _check_bot_rights(self, bot: Bot, chat_id: int) -> Dict[str, Any]:
        """
        Проверяет права бота в канале
        
        Args:
            bot: Экземпляр бота
            chat_id: ID чата
            
        Returns:
            Dict[str, Any]: Результат проверки
        """
        try:
            self.logger.info(f"Проверка прав бота в канале {chat_id}")
            
            # Сначала проверим, существует ли чат
            try:
                chat_info = await bot.get_chat(chat_id)
                self.logger.debug(f"Канал {chat_id} найден: {chat_info.title}")
            except Exception as e:
                self.logger.error(f"Не удалось получить информацию о канале {chat_id}: {e}")
                return self._create_error_response(
                    f"Канал не найден или недоступен: {str(e)}"
                )
            
            # Проверяем права бота в канале
            try:
                bot_member = await bot.get_chat_member(chat_id, bot.id)
                self.logger.debug(f"Права бота в канале {chat_id}: {bot_member}")
            except Exception as e:
                self.logger.error(f"Не удалось получить информацию о правах бота в канале {chat_id}: {e}")
                return self._create_error_response(
                    f"Не удалось проверить права бота: {str(e)}"
                )
                
            # Проверяем необходимые права
            bot_has_rights = False
            
            if hasattr(bot_member, 'can_post_messages') and bot_member.can_post_messages:
                bot_has_rights = True
                self.logger.debug(f"Бот имеет право отправлять сообщения в канал {chat_id}")
            elif hasattr(bot_member, 'status') and bot_member.status in ['administrator', 'creator']:
                bot_has_rights = True
                self.logger.debug(f"Бот имеет статус {bot_member.status} в канале {chat_id}")
            
            if not bot_has_rights:
                self.logger.error(f"Бот не имеет прав для публикации сообщений в канале {chat_id}")
                return self._create_error_response(
                    "Бот не имеет прав для публикации сообщений в этом канале. "
                    "Добавьте бота как администратора с правом публикации сообщений."
                )
            
            self.logger.info(f"Бот имеет необходимые права в канале {chat_id}")
            return {"success": True}
        except Exception as e:
            self.logger.error(f"Ошибка при проверке прав бота в канале {chat_id}: {e}", exc_info=True)
            return self._create_error_response(f"Ошибка при проверке прав бота: {str(e)}")

    async def _send_post_to_channel(self, bot: Bot, post: Post, chat_id: int) -> Dict[str, Any]:
        """
        Отправляет пост в канал
        
        Args:
            bot: Экземпляр бота
            post: Объект поста
            chat_id: ID чата
            
        Returns:
            Dict[str, Any]: Результат отправки
        """
        try:
            # Формируем текст сообщения
            caption = f"{post.content}"
            if post.tag:
                caption += f"\n\n#{post.tag}"
                
            # Ограничиваем длину подписи до 1024 символов
            if len(caption) > 1024:
                caption = caption[:1021] + "..."
                
            # Публикуем пост
            self.logger.info(f"Отправка текстового сообщения в чат {chat_id}")
            
            # Если есть изображение
            if post.image:
                self.logger.info(f"Отправка фото в чат {chat_id}")
                try:
                    message = await bot.send_photo(
                        chat_id=chat_id,
                        photo=post.image,
                        caption=caption
                    )
                except Exception as media_error:
                    self.logger.error(f"Ошибка при отправке фото: {media_error}, отправляем как текст")
                    message = await bot.send_message(
                        chat_id=chat_id,
                        text=caption
                    )
            else:
                # Отправляем как текстовое сообщение
                message = await bot.send_message(
                    chat_id=chat_id,
                    text=caption
                )
            
            return {
                "success": True,
                "message_id": message.message_id
            }
        except TelegramBadRequest as e:
            self.logger.error(f"Ошибка Telegram API при публикации поста: {e}", exc_info=True)
            return self._create_error_response(f"Ошибка Telegram API: {str(e)}")
        except TelegramForbiddenError as e:
            self.logger.error(f"Ошибка доступа Telegram API: {e}", exc_info=True)
            return self._create_error_response(
                "Ошибка доступа: бот не может отправить сообщение в этот чат. Проверьте права бота."
            )
        except Exception as e:
            self.logger.error(f"Ошибка при отправке поста: {e}", exc_info=True)
            return self._create_error_response(f"Неожиданная ошибка при отправке: {str(e)}")

    async def _update_channel_last_used(self, chat_id: int) -> None:
        """
        Обновляет время последнего использования канала
        
        Args:
            chat_id: ID чата
        """
        try:
            channel_service = ChannelService()
            await channel_service.update_channel_last_used(chat_id)
        except Exception as e:
            self.logger.warning(f"Не удалось обновить время последнего использования канала: {e}")

    async def get_user_posts(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Получение постов пользователя
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество постов
            
        Returns:
            List[Dict[str, Any]]: Список постов
        """
        async with get_session() as session:
            try:
                post_repo = PostRepository(session)
                posts = await post_repo.get_posts_by_user_id(user_id, limit)
                
                result = []
                for post in posts:
                    result.append({
                        "id": post.id,
                        "title": post.title,
                        "content": post.content[:50] + "..." if len(post.content) > 50 else post.content,
                        "tag": post.tag,
                        "created_date": post.created_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "is_published": post.is_published == 1,
                        "target_chat_id": post.target_chat_id,
                        "target_chat_title": post.target_chat_title or f"Чат {post.target_chat_id}" if post.target_chat_id else None
                    })
                
                return result
            except Exception as e:
                self.logger.error(f"Ошибка при получении постов пользователя {user_id}: {e}")
                return []
                
    async def get_available_chats(self, bot: Bot = None) -> List[Dict[str, Any]]:
        """
        Получает список доступных чатов для публикации поста
        
        Args:
            bot: Экземпляр бота для проверки прав
            
        Returns:
            List[Dict[str, Any]]: Список доступных чатов
        """
        self.logger.info("Запрос списка доступных чатов для публикации")
        try:
            # Получаем список всех каналов из базы данных
            channel_service = ChannelService()
            channels = await channel_service.get_all_channels()
            
            if not channels:
                self.logger.warning("Нет доступных каналов для публикации")
                return []
                
            # Если бот не передан, просто возвращаем список каналов
            if not bot:
                self.logger.info(f"Бот не передан, возвращаем все {len(channels)} каналов")
                return channels
                
            # Проверяем права бота в каждом канале
            available_channels = []
            for channel in channels:
                try:
                    chat_id = channel.get("chat_id")
                    # Проверяем права бота в канале
                    chat_member = await bot.get_chat_member(chat_id=chat_id, user_id=bot.id)
                    
                    # Проверяем, может ли бот публиковать сообщения в этом канале
                    if chat_member and (chat_member.status in ["administrator", "creator"]):
                        if hasattr(chat_member, "can_post_messages") and chat_member.can_post_messages:
                            available_channels.append(channel)
                        elif chat_member.status == "creator":
                            available_channels.append(channel)
                except Exception as e:
                    self.logger.error(f"Ошибка при проверке прав бота в канале {chat_id}: {e}")
                    # Пропускаем каналы, где бот не имеет прав
                    continue
                    
            self.logger.info(f"Найдено {len(available_channels)} доступных каналов для публикации")
            return available_channels
        except Exception as e:
            self.logger.error(f"Ошибка при получении списка доступных чатов: {e}")
            return []
    
    async def delete_post(self, post_id: int, user_id: int, soft_delete: bool = False) -> Dict[str, Any]:
        """
        Удаление поста с проверкой прав (только автор или админ)
        
        Args:
            post_id: ID поста
            user_id: ID пользователя, который пытается удалить пост
            soft_delete: Если True, то пост будет помечен как удаленный, но не удален из БД
            
        Returns:
            Dict[str, Any]: Результат операции удаления
        """
        from app.services.role_service import RoleService
        
        async with get_session() as session:
            try:
                # Проверка прав (только автор или админ)
                role_service = RoleService()
                is_admin = await role_service.check_user_role(user_id, "admin")
                
                post_repo = PostRepository(session)
                post = await post_repo.get_by_id(post_id)
                
                if not post:
                    error_msg = f"Пост с ID {post_id} не найден"
                    self.logger.error(error_msg)
                    return {"success": False, "error": error_msg}
                
                # Проверка прав на удаление
                if post.user_id != user_id and not is_admin:
                    error_msg = f"Недостаточно прав для удаления поста {post_id}"
                    self.logger.warning(f"Пользователь {user_id} не имеет прав на удаление поста {post_id}")
                    return {"success": False, "error": error_msg}
                
                # Удаление поста
                if soft_delete:
                    # Архивирование поста
                    result = await post_repo.archive_post(post_id, user_id)
                    action = "архивирован"
                else:
                    # Физическое удаление поста
                    result = await post_repo.delete_post(post_id)
                    action = "удален"
                    
                if result:
                    self.logger.info(f"Пост с ID {post_id} успешно {action} пользователем {user_id}")
                    return {"success": True, "message": f"Пост успешно {action}"}
                else:
                    error_msg = f"Ошибка при выполнении операции с постом {post_id}"
                    self.logger.error(error_msg)
                    return {"success": False, "error": error_msg}
            except Exception as e:
                error_msg = f"Ошибка при удалении поста {post_id}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                return {"success": False, "error": error_msg}

    async def restore_post(self, post_id: int, user_id: int) -> Dict[str, Any]:
        """
        Восстановление архивированного поста
        
        Args:
            post_id: ID поста
            user_id: ID пользователя, который восстанавливает пост
            
        Returns:
            Dict[str, Any]: Результат операции восстановления
        """
        from app.services.role_service import RoleService
        
        async with get_session() as session:
            try:
                # Проверка прав (только автор или админ)
                role_service = RoleService()
                is_admin = await role_service.check_user_role(user_id, "admin")
                
                post_repo = PostRepository(session)
                post = await post_repo.get_archived_post(post_id)
                
                if not post:
                    error_msg = f"Архивированный пост с ID {post_id} не найден"
                    self.logger.error(error_msg)
                    return {"success": False, "error": error_msg}
                
                # Проверка прав на восстановление
                if post.user_id != user_id and not is_admin:
                    error_msg = f"Недостаточно прав для восстановления поста {post_id}"
                    self.logger.warning(f"Пользователь {user_id} не имеет прав на восстановление поста {post_id}")
                    return {"success": False, "error": error_msg}
                
                # Восстановление поста
                result = await post_repo.restore_post(post_id)
                    
                if result:
                    self.logger.info(f"Пост с ID {post_id} успешно восстановлен пользователем {user_id}")
                    return {"success": True, "message": "Пост успешно восстановлен"}
                else:
                    error_msg = f"Ошибка при восстановлении поста {post_id}"
                    self.logger.error(error_msg)
                    return {"success": False, "error": error_msg}
            except Exception as e:
                error_msg = f"Ошибка при восстановлении поста {post_id}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                return {"success": False, "error": error_msg}

    async def get_posts_by_tag(self, tag: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получение постов по тегу
        
        Args:
            tag: Тег для поиска
            limit: Максимальное количество постов
            
        Returns:
            List[Dict[str, Any]]: Список постов
        """
        async with get_session() as session:
            try:
                post_repo = PostRepository(session)
                posts = await post_repo.get_posts_by_tag(tag, limit)
                
                result = []
                for post in posts:
                    result.append({
                        "id": post.id,
                        "title": post.title,
                        "content": post.content[:50] + "..." if len(post.content) > 50 else post.content,
                        "tag": post.tag,
                        "created_date": post.created_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "is_published": post.is_published == 1
                    })
                
                return result
            except Exception as e:
                self.logger.error(f"Ошибка при поиске постов по тегу '{tag}': {e}")
                return []

    async def get_bot_chats(self, bot: Bot) -> List[Dict[str, Any]]:
        """
        Получение списка чатов, где бот является администратором
        
        Args:
            bot: Экземпляр бота
            
        Returns:
            List[Dict[str, Any]]: Список чатов с информацией
        """
        try:
            chats = []
            
            # Добавляем основной канал из .env файла
            from app.core.config import settings
            if settings.channel_id_as_int is not None:
                channel_id = settings.channel_id_as_int
                try:
                    # Пытаемся получить информацию о канале
                    chat = await bot.get_chat(channel_id)
                    chat_title = chat.title or f"Канал {channel_id}"
                    self.logger.info(f"Добавлен основной канал: {chat_title} ({channel_id})")
                    
                    chats.append({
                        "id": channel_id,
                        "title": f"{chat_title} (основной канал)",
                        "type": "channel",
                        "is_default": True
                    })
                except Exception as e:
                    self.logger.warning(f"Не удалось получить информацию о канале {channel_id}: {e}")
                    # Всё равно добавляем канал в список, чтобы пользователь мог его выбрать
                    chats.append({
                        "id": channel_id,
                        "title": f"Основной канал ({channel_id})",
                        "type": "channel",
                        "is_default": True
                    })
            
            # Для тестирования и разработки добавляем возможность публикации в текущий чат
            chats.append({
                "id": 0,  # Специальный ID для обозначения "Текущий чат"
                "title": "Текущий чат (для тестирования)",
                "type": "private",
                "is_default": False
            })
            
            return chats
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении списка чатов: {e}")
            return []

    async def get_post_by_id(self, post_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение информации о посте по его ID
        
        Args:
            post_id: ID поста
            
        Returns:
            Optional[Dict[str, Any]]: Данные поста или None, если пост не найден
        """
        async with get_session() as session:
            try:
                post_repo = PostRepository(session)
                post = await post_repo.get_by_id(post_id)
                
                if not post:
                    return None
                
                # Преобразование объекта поста в словарь для возврата
                return {
                    "id": post.id,
                    "title": post.title,
                    "content": post.content,
                    "image": post.image,
                    "tag": post.tag,
                    "username": post.username,
                    "created_date": post.created_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "is_published": post.is_published == 1,
                    "published_at": post.published_at.strftime("%Y-%m-%d %H:%M:%S") if post.published_at else None,
                    "target_chat_id": post.target_chat_id,
                    "target_chat_title": post.target_chat_title
                }
                
            except Exception as e:
                self.logger.error(f"Ошибка при получении поста с ID {post_id}: {e}")
                return None

    async def update_post_target_chat(self, post_id: int, chat_id: int, chat_title: str) -> bool:
        """
        Обновление целевого чата для поста
        
        Args:
            post_id: ID поста
            chat_id: ID чата
            chat_title: Название чата
            
        Returns:
            bool: True, если обновление прошло успешно
        """
        async with get_session() as session:
            try:
                post_repo = PostRepository(session)
                result = await post_repo.update_target_chat(post_id, chat_id, chat_title)
                return result
            except Exception as e:
                self.logger.error(f"Ошибка при обновлении целевого чата для поста {post_id}: {e}")
                return False

    async def update_post(
        self,
        post_id: int,
        title: str,
        content: str,
        image: str,
        tag: str,
        change_username: str
    ) -> Dict[str, Any]:
        """
        Редактирует существующий пост в базе данных
        
        Args:
            post_id: ID поста для редактирования
            title: Новое название поста
            content: Новое описание поста
            image: Новая ссылка на изображение поста
            tag: Новый тег поста
            change_username: Имя пользователя, который редактировал пост
            
        Returns:
            Dict[str, Any]: Результат операции с информацией о посте
        """
        try:
            async with get_session() as session:
                post_repository = PostRepository(session)
                
                # Проверяем существование поста
                post = await post_repository.get_by_id(post_id)
                if not post:
                    self.logger.error(f"Пост с ID {post_id} не найден при попытке редактирования")
                    return {
                        "success": False,
                        "error": f"Пост с ID {post_id} не найден"
                    }
                
                # Сохраняем дату и время редактирования
                change_date = datetime.now()
                
                # Обновляем пост
                await post_repository.update_post(
                    post_id=post_id,
                    title=title,
                    content=content,
                    image=image,
                    tag=tag,
                    change_username=change_username,
                    change_date=change_date
                )
                
                self.logger.info(f"Пост с ID {post_id} успешно отредактирован пользователем {change_username}")
                
                # Возвращаем обновленные данные
                updated_post = await post_repository.get_by_id(post_id)
                
                return {
                    "success": True,
                    "post": {
                        "id": updated_post.id,
                        "title": updated_post.title,
                        "content": updated_post.content,
                        "image": updated_post.image,
                        "tag": updated_post.tag,
                        "change_username": updated_post.change_username,
                        "change_date": updated_post.change_date.strftime("%Y-%m-%d %H:%M:%S") if updated_post.change_date else None
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка при редактировании поста {post_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Ошибка при редактировании поста: {str(e)}"
            }

    async def get_archived_posts(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получение архивированных постов пользователя
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество постов
            
        Returns:
            List[Dict[str, Any]]: Список архивированных постов
        """
        from app.services.role_service import RoleService
        
        async with get_session() as session:
            try:
                # Проверяем роль пользователя
                role_service = RoleService()
                is_admin = await role_service.check_user_role(user_id, "admin")
                
                post_repo = PostRepository(session)
                
                # Для админа - все архивированные посты, для пользователя - только его посты
                if is_admin:
                    posts = await post_repo.get_all_archived_posts(limit)
                else:
                    posts = await post_repo.get_archived_posts_by_user_id(user_id, limit)
                
                result = []
                for post in posts:
                    result.append({
                        "id": post.id,
                        "title": post.title,
                        "content": post.content[:50] + "..." if len(post.content) > 50 else post.content,
                        "tag": post.tag,
                        "username": post.username,
                        "created_date": post.created_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "archived_date": post.archived_date.strftime("%Y-%m-%d %H:%M:%S") if hasattr(post, "archived_date") and post.archived_date else None,
                        "archived_by": post.archived_by if hasattr(post, "archived_by") else None
                    })
                
                return result
            except Exception as e:
                self.logger.error(f"Ошибка при получении архивированных постов пользователя {user_id}: {e}", exc_info=True)
                return [] 