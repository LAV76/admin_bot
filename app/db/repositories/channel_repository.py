from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, insert, desc, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.channels import Channel
from app.db.repositories.base_repository import BaseRepository
from app.core.logging import setup_logger

class ChannelRepository(BaseRepository[Channel]):
    """Репозиторий для работы с каналами"""

    def __init__(self, session: AsyncSession):
        super().__init__(Channel, session)
        self.logger = setup_logger("channel_repository")

    async def create_channel(
        self,
        chat_id: int,
        title: str,
        username: Optional[str],
        type: str,
        is_default: bool = False,
        added_by: int = None
    ) -> Channel:
        """
        Создает новый канал в базе данных
        
        Args:
            chat_id: ID чата в Telegram
            title: Название канала
            username: Username канала (опционально)
            type: Тип чата (channel, group, supergroup)
            is_default: Является ли канал каналом по умолчанию
            added_by: ID пользователя, добавившего канал
            
        Returns:
            Channel: Созданный объект канала
        """
        channel = Channel(
            chat_id=chat_id,
            title=title,
            username=username,
            chat_type=type,
            is_default=is_default,
            added_by=added_by
        )
        self.session.add(channel)
        await self.session.flush()
        return channel

    async def get_by_chat_id(self, chat_id: int) -> Optional[Channel]:
        """
        Получение канала по его chat_id
        
        Args:
            chat_id: ID канала/чата в Telegram
            
        Returns:
            Optional[Channel]: Канал или None, если не найден
        """
        stmt = select(Channel).where(Channel.chat_id == chat_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_channels(self) -> List[Channel]:
        """
        Получает все каналы из базы данных
        
        Returns:
            List[Channel]: Список всех каналов
        """
        query = select(Channel).order_by(Channel.id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_invalid_channels(self) -> List[Channel]:
        """
        Получает недоступные каналы
        
        Returns:
            List[Channel]: Список недоступных каналов
        """
        query = select(Channel).where(Channel.is_valid == False)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_inactive_channels(self, older_than_date: datetime) -> List[Channel]:
        """
        Получает неактивные каналы, которые не использовались после указанной даты
        
        Args:
            older_than_date: Дата, после которой канал считается неактивным
            
        Returns:
            List[Channel]: Список неактивных каналов
        """
        # Выбираем каналы с last_used меньше указанной даты или NULL
        query = select(Channel).where(
            or_(
                Channel.last_used < older_than_date,
                Channel.last_used == None
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_default_channel(self) -> Optional[Channel]:
        """
        Получение канала по умолчанию
        
        Returns:
            Optional[Channel]: Канал по умолчанию или None, если не найден
        """
        stmt = select(Channel).where(Channel.is_default == True)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def set_default_channel(self, channel_id: int) -> bool:
        """
        Установка канала по умолчанию
        
        Args:
            channel_id: ID канала в базе данных
            
        Returns:
            bool: True, если канал успешно установлен как дефолтный
        """
        try:
            # Сначала сбрасываем флаг у всех каналов
            await self.reset_default_flag()
            
            # Устанавливаем флаг у выбранного канала
            stmt = update(Channel).where(Channel.id == channel_id).values(is_default=True)
            result = await self.session.execute(stmt)
            await self.session.commit()
            
            if result.rowcount > 0:
                self.logger.info(f"Канал с ID {channel_id} установлен как канал по умолчанию")
                return True
            else:
                self.logger.warning(f"Канал с ID {channel_id} не найден при попытке установить его как дефолтный")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка при установке канала по умолчанию: {e}")
            await self.session.rollback()
            return False

    async def reset_default_flag(self) -> bool:
        """
        Сброс флага is_default у всех каналов
        
        Returns:
            bool: True, если операция выполнена успешно
        """
        try:
            stmt = update(Channel).values(is_default=False)
            await self.session.execute(stmt)
            await self.session.commit()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при сбросе флага is_default: {e}")
            await self.session.rollback()
            return False

    async def update_last_used(self, channel_id: int) -> bool:
        """
        Обновление даты последнего использования канала
        
        Args:
            channel_id: ID канала в Telegram (chat_id)
            
        Returns:
            bool: True, если дата успешно обновлена
        """
        try:
            # Используем chat_id вместо id для поиска канала
            stmt = update(Channel).where(Channel.chat_id == channel_id).values(
                last_used_at=datetime.now()
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            
            if result.rowcount > 0:
                return True
            else:
                self.logger.warning(f"Канал с chat_id {channel_id} не найден при обновлении даты использования")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении даты использования канала {channel_id}: {e}")
            await self.session.rollback()
            return False

    async def delete_channel(self, channel_id: int) -> bool:
        """
        Удаление канала
        
        Args:
            channel_id: ID канала в базе данных
            
        Returns:
            bool: True, если канал успешно удален
        """
        return await self.delete(channel_id)

    async def update_channel_info(self, channel_id: int, title: str, username: Optional[str] = None) -> bool:
        """
        Обновление информации о канале
        
        Args:
            channel_id: ID канала в базе данных
            title: Новое название канала
            username: Новый username канала
            
        Returns:
            bool: True, если информация успешно обновлена
        """
        try:
            update_data = {"title": title}
            if username is not None:
                update_data["username"] = username
                
            stmt = update(Channel).where(Channel.id == channel_id).values(**update_data)
            result = await self.session.execute(stmt)
            await self.session.commit()
            
            if result.rowcount > 0:
                self.logger.info(f"Обновлена информация о канале с ID {channel_id}")
                return True
            else:
                self.logger.warning(f"Канал с ID {channel_id} не найден при обновлении информации")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении информации о канале {channel_id}: {e}")
            await self.session.rollback()
            return False

    async def get_channel_by_chat_id(self, chat_id: int) -> Optional[Channel]:
        """
        Получает канал по ID чата в Telegram
        
        Args:
            chat_id: ID чата в Telegram
            
        Returns:
            Optional[Channel]: Канал или None, если не найден
        """
        query = select(Channel).where(Channel.chat_id == chat_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_channel(self, channel_id: int, data: Dict[str, Any]) -> Optional[Channel]:
        """
        Обновляет данные канала
        
        Args:
            channel_id: ID канала в базе данных
            data: Словарь с обновляемыми полями
            
        Returns:
            Optional[Channel]: Обновленный канал или None, если не найден
        """
        channel = await self.get_by_id(channel_id)
        if not channel:
            return None
            
        for key, value in data.items():
            if hasattr(channel, key):
                setattr(channel, key, value)
                
        await self.session.flush()
        return channel 