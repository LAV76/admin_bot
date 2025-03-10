from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, insert, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.db.models.posts import Post
from app.db.repositories.base_repository import BaseRepository
from app.core.logging import setup_logger

class PostRepository(BaseRepository[Post]):
    """Репозиторий для работы с постами"""

    def __init__(self, session: AsyncSession):
        super().__init__(Post, session)
        self.logger = setup_logger("post_repository")

    async def create_post(
        self, 
        title: str, 
        content: str, 
        image: str, 
        tag: str, 
        username: str,
        user_id: int,
        target_chat_id: Optional[int] = None,
        target_chat_title: Optional[str] = None
    ) -> Optional[Post]:
        """
        Создание нового поста
        
        Args:
            title: Название поста
            content: Описание поста
            image: Ссылка на изображение поста
            tag: Тег поста
            username: Имя пользователя, создавшего пост
            user_id: ID пользователя, создавшего пост
            target_chat_id: ID чата для публикации (опционально)
            target_chat_title: Название чата для публикации (опционально)
            
        Returns:
            Optional[Post]: Созданный пост или None в случае ошибки
        """
        try:
            # Проверка обязательных полей
            if not title:
                self.logger.error("Невозможно создать пост: отсутствует название")
                return None
                
            if not content:
                self.logger.error("Невозможно создать пост: отсутствует описание")
                return None
                
            if not user_id:
                self.logger.error("Невозможно создать пост: отсутствует ID пользователя")
                return None
                
            # Подготовка данных поста
            self.logger.debug(f"Подготовка данных для создания поста: title='{title}', content_length={len(content)}, image={bool(image)}, tag='{tag}', username='{username}', user_id={user_id}, target_chat_id={target_chat_id}, target_chat_title='{target_chat_title}'")
            
            post_data = {
                "title": title,
                "content": content,
                "status": "draft",
                "image": image,
                "tag": tag,
                "username": username,
                "user_id": user_id,
                "created_date": datetime.now(),
                "is_published": 0
            }
            
            if target_chat_id:
                post_data["target_chat_id"] = target_chat_id
                
            if target_chat_title:
                post_data["target_chat_title"] = target_chat_title
                
            # Создаем новый пост
            try:
                new_post = Post(**post_data)
                self.session.add(new_post)
                await self.session.commit()
                await self.session.refresh(new_post)
                
                self.logger.info(f"Создан новый пост с ID {new_post.id}")
                return new_post
            except SQLAlchemyError as db_error:
                self.logger.error(f"Ошибка базы данных при создании поста: {db_error}", exc_info=True)
                await self.session.rollback()
                return None
            
        except Exception as e:
            self.logger.error(f"Непредвиденная ошибка при создании поста: {e}", exc_info=True)
            await self.session.rollback()
            return None

    async def publish_post(self, post_id: int) -> bool:
        """
        Публикация поста (установка флага is_published=1)
        
        Args:
            post_id: ID поста
            
        Returns:
            bool: True, если пост успешно опубликован
        """
        try:
            stmt = update(Post).where(Post.id == post_id).values(
                is_published=1,
                published_at=datetime.now()
            )
            
            result = await self.session.execute(stmt)
            await self.session.commit()
            
            if result.rowcount > 0:
                self.logger.info(f"Пост с ID {post_id} опубликован")
                return True
            else:
                self.logger.warning(f"Пост с ID {post_id} не найден для публикации")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка при публикации поста {post_id}: {e}")
            await self.session.rollback()
            return False

    async def get_latest_posts(self, limit: int = 10) -> List[Post]:
        """
        Получение последних постов
        
        Args:
            limit: Максимальное количество постов
            
        Returns:
            List[Post]: Список постов
        """
        stmt = select(Post).order_by(desc(Post.created_date)).limit(limit)
        result = await self.session.execute(stmt)
        posts = result.scalars().all()
        return list(posts)
    
    async def get_posts_by_user_id(self, user_id: int, limit: int = 10) -> List[Post]:
        """
        Получение постов, созданных определенным пользователем
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество постов
            
        Returns:
            List[Post]: Список постов
        """
        stmt = select(Post).where(Post.user_id == user_id).order_by(desc(Post.created_date)).limit(limit)
        result = await self.session.execute(stmt)
        posts = result.scalars().all()
        return list(posts)
    
    async def get_posts_by_tag(self, tag: str, limit: int = 10) -> List[Post]:
        """
        Получение постов по тегу
        
        Args:
            tag: Тег для поиска
            limit: Максимальное количество постов
            
        Returns:
            List[Post]: Список постов
        """
        # Создаем условие для поиска тегов (ищем, входит ли тег в строку с тегами)
        # Используем ILIKE для регистронезависимого поиска
        # Ищем "%tag%" или "tag%" или "%tag " для точного поиска тегов
        stmt = select(Post).where(
            Post.tag.ilike(f"% {tag} %") |  # Тег в середине списка
            Post.tag.ilike(f"{tag} %") |    # Тег в начале списка
            Post.tag.ilike(f"% {tag}") |    # Тег в конце списка
            (Post.tag == tag)               # Тег является единственным
        ).order_by(desc(Post.created_date)).limit(limit)
        
        result = await self.session.execute(stmt)
        posts = result.scalars().all()
        return list(posts)
    
    async def delete_post(self, post_id: int) -> bool:
        """
        Удаление поста по ID

        Args:
            post_id: ID поста

        Returns:
            bool: True, если пост успешно удален
        """
        try:
            post = await self.get_by_id(post_id)
            if not post:
                return False
                
            await self.session.delete(post)
            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            raise e
            
    async def update_target_chat(self, post_id: int, chat_id: int, chat_title: str) -> bool:
        """
        Обновление целевого чата для поста

        Args:
            post_id: ID поста
            chat_id: ID чата
            chat_title: Название чата

        Returns:
            bool: True, если обновление прошло успешно
        """
        try:
            post = await self.get_by_id(post_id)
            if not post:
                return False
                
            post.target_chat_id = chat_id
            post.target_chat_title = chat_title
            
            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            raise e

    async def mark_as_published(self, post_id: int, message_id: int, chat_id: int, chat_title: str = None) -> bool:
        """
        Помечает пост как опубликованный
        
        Args:
            post_id: ID поста
            message_id: ID сообщения в Telegram
            chat_id: ID канала/чата
            chat_title: Название канала/чата
            
        Returns:
            bool: True, если пост успешно обновлен
        """
        try:
            post = await self.get_by_id(post_id)
            if not post:
                self.logger.warning(f"Невозможно пометить как опубликованный: пост с ID {post_id} не найден")
                return False
                
            post.is_published = True
            post.published_at = datetime.now()
            post.message_id = message_id
            post.target_chat_id = chat_id
            if chat_title:
                post.target_chat_title = chat_title
                
            await self.session.commit()
            self.logger.info(f"Пост с ID {post_id} помечен как опубликованный в канал {chat_title} ({chat_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении статуса публикации поста {post_id}: {e}", exc_info=True)
            await self.session.rollback()
            return False
            
    async def update_post_target_chat(self, post_id: int, chat_id: int, chat_title: str = None) -> bool:
        """
        Обновляет информацию о целевом канале поста
        
        Args:
            post_id: ID поста
            chat_id: ID канала/чата
            chat_title: Название канала/чата
            
        Returns:
            bool: True, если пост успешно обновлен
        """
        try:
            post = await self.get_by_id(post_id)
            if not post:
                self.logger.warning(f"Невозможно обновить целевой канал: пост с ID {post_id} не найден")
                return False
                
            post.target_chat_id = chat_id
            if chat_title:
                post.target_chat_title = chat_title
                
            await self.session.commit()
            self.logger.info(f"Обновлен целевой канал поста с ID {post_id}: {chat_title} ({chat_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении целевого канала поста {post_id}: {e}", exc_info=True)
            await self.session.rollback()
            return False

    async def archive_post(self, post_id: int, user_id: int) -> bool:
        """
        Архивирование поста (мягкое удаление)
        
        Args:
            post_id: ID поста
            user_id: ID пользователя, выполнившего архивацию
            
        Returns:
            bool: True, если пост успешно архивирован
        """
        try:
            # Получаем пост
            post = await self.get_by_id(post_id)
            if not post:
                self.logger.warning(f"Невозможно архивировать: пост с ID {post_id} не найден")
                return False
            
            # Обновляем статус
            post.is_archived = True
            post.archived_at = datetime.now()
            post.archived_by = user_id
            
            await self.session.commit()
            self.logger.info(f"Пост с ID {post_id} архивирован пользователем {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при архивировании поста {post_id}: {e}", exc_info=True)
            await self.session.rollback()
            return False
            
    async def get_archived_post(self, post_id: int) -> Optional[Post]:
        """
        Получение архивированного поста по ID
        
        Args:
            post_id: ID поста
            
        Returns:
            Optional[Post]: Объект поста или None, если не найден
        """
        try:
            stmt = select(Post).where(
                (Post.id == post_id) & 
                (Post.is_archived == True)
            )
            result = await self.session.execute(stmt)
            post = result.scalar_one_or_none()
            return post
        except Exception as e:
            self.logger.error(f"Ошибка при получении архивированного поста {post_id}: {e}", exc_info=True)
            return None
            
    async def get_all_archived_posts(self, limit: int = 50) -> List[Post]:
        """
        Получение всех архивированных постов
        
        Args:
            limit: Максимальное количество постов
            
        Returns:
            List[Post]: Список архивированных постов
        """
        try:
            stmt = select(Post).where(
                Post.is_archived == True
            ).order_by(desc(Post.archived_at)).limit(limit)
            
            result = await self.session.execute(stmt)
            posts = result.scalars().all()
            return list(posts)
        except Exception as e:
            self.logger.error(f"Ошибка при получении списка архивированных постов: {e}", exc_info=True)
            return []
            
    async def get_archived_posts_by_user_id(self, user_id: int, limit: int = 50) -> List[Post]:
        """
        Получение архивированных постов пользователя
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество постов
            
        Returns:
            List[Post]: Список архивированных постов
        """
        try:
            stmt = select(Post).where(
                (Post.user_id == user_id) & 
                (Post.is_archived == True)
            ).order_by(desc(Post.archived_at)).limit(limit)
            
            result = await self.session.execute(stmt)
            posts = result.scalars().all()
            return list(posts)
        except Exception as e:
            self.logger.error(f"Ошибка при получении списка архивированных постов пользователя {user_id}: {e}", exc_info=True)
            return []
            
    async def restore_post(self, post_id: int) -> bool:
        """
        Восстановление архивированного поста
        
        Args:
            post_id: ID поста
            
        Returns:
            bool: True, если пост успешно восстановлен
        """
        try:
            # Получаем пост
            post = await self.get_archived_post(post_id)
            if not post:
                self.logger.warning(f"Невозможно восстановить: архивированный пост с ID {post_id} не найден")
                return False
            
            # Обновляем статус
            post.is_archived = False
            post.archived_at = None
            post.archived_by = None
            
            await self.session.commit()
            self.logger.info(f"Пост с ID {post_id} восстановлен")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при восстановлении поста {post_id}: {e}", exc_info=True)
            await self.session.rollback()
            return False

    async def update_post(
        self,
        post_id: int,
        title: str,
        content: str,
        image: str,
        tag: str,
        change_username: str,
        change_date: datetime
    ) -> bool:
        """
        Обновление данных поста
        
        Args:
            post_id: ID поста
            title: Новое название поста
            content: Новое описание поста
            image: Новая ссылка на изображение поста
            tag: Новый тег поста
            change_username: Имя пользователя, который редактировал пост
            change_date: Дата и время редактирования
            
        Returns:
            bool: True, если пост успешно обновлен
        """
        try:
            post = await self.get_by_id(post_id)
            if not post:
                self.logger.warning(f"Невозможно обновить: пост с ID {post_id} не найден")
                return False
                
            # Обновляем данные поста
            post.title = title
            post.content = content
            post.image = image
            post.tag = tag
            post.change_username = change_username
            post.change_date = change_date
            
            await self.session.commit()
            self.logger.info(f"Пост с ID {post_id} обновлен пользователем {change_username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении поста {post_id}: {e}", exc_info=True)
            await self.session.rollback()
            return False 