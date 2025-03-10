from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging
import asyncio

from aiogram import Bot
from aiogram.types import ChatMemberAdministrator
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.db.session import get_session
from app.db.models.channels import Channel
from app.db.repositories.channel_repository import ChannelRepository
from utils.logger import setup_logger, log_error, log_params
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, func, desc
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("channel_service")

class ChannelService:
    """Сервис для работы с каналами"""
    
    def __init__(self):
        """
        Инициализирует сервис для работы с каналами
        """
        # Для хранения сессии БД и репозитория
        self.session_factory = get_session
        logger.info("ChannelService инициализирован")
        
        # Запускаем задачу проверки каналов (раз в сутки)
        asyncio.create_task(self._schedule_channel_verification())
        
    async def _schedule_channel_verification(self):
        """
        Планирует регулярную проверку каналов
        """
        while True:
            try:
                # Проверяем каналы раз в сутки (86400 секунд)
                await asyncio.sleep(86400)
                logger.info("Запуск плановой проверки каналов")
                
                # Получаем бота для проверки
                from main import BotApplication
                bot_app = BotApplication()
                await self.verify_all_channels(bot_app.bot)
                
                # Очистка устаревших каналов
                await self.cleanup_inactive_channels(days=60)
                
                logger.info("Плановая проверка каналов завершена")
            except Exception as e:
                logger.error(f"Ошибка при плановой проверке каналов: {e}", exc_info=True)
                # В случае ошибки ждем час и пробуем снова
                await asyncio.sleep(3600)

    async def verify_all_channels(self, bot: Bot) -> Dict[str, Any]:
        """
        Проверяет все каналы на доступность и обновляет информацию о них
        
        Args:
            bot: Экземпляр бота для проверки
            
        Returns:
            Dict[str, Any]: Результат проверки в формате:
            {
                "total": int,  # Общее количество каналов
                "verified": int,  # Количество успешно проверенных каналов
                "updated": int,  # Количество обновленных каналов
                "failed": int,  # Количество недоступных каналов
                "details": List[Dict[str, Any]]  # Подробная информация о каждом канале
            }
        """
        logger.info("Начинаем проверку всех каналов")
        
        result = {
            "total": 0,
            "verified": 0,
            "updated": 0,
            "failed": 0,
            "details": []
        }
        
        try:
            async with self.session_factory() as session:
                channel_repo = ChannelRepository(session)
                
                # Получаем все каналы из базы данных
                channels = await channel_repo.get_all_channels()
                result["total"] = len(channels)
                
                for channel in channels:
                    channel_detail = {
                        "id": channel.id,
                        "chat_id": channel.chat_id,
                        "title": channel.title,
                        "status": "unknown"
                    }
                    
                    try:
                        # Проверяем доступ к каналу
                        chat_info = await bot.get_chat(channel.chat_id)
                        
                        # Проверяем права бота в канале
                        bot_member = await bot.get_chat_member(channel.chat_id, bot.id)
                        
                        # Обновляем информацию о канале, если она изменилась
                        if chat_info.title != channel.title or chat_info.username != channel.username:
                            await channel_repo.update_channel(
                                channel.id,
                                {
                                    "title": chat_info.title,
                                    "username": chat_info.username,
                                    "verified_at": datetime.now(),
                                    "is_valid": True
                                }
                            )
                            result["updated"] += 1
                            channel_detail["status"] = "updated"
                            logger.info(f"Канал {channel.chat_id} обновлен: {chat_info.title}")
                        else:
                            # Обновляем только время проверки
                            await channel_repo.update_channel(
                                channel.id,
                                {
                                    "verified_at": datetime.now(),
                                    "is_valid": True
                                }
                            )
                            result["verified"] += 1
                            channel_detail["status"] = "verified"
                            logger.debug(f"Канал {channel.chat_id} проверен и актуален")
                    
                    except Exception as e:
                        # Отмечаем канал как недоступный
                        await channel_repo.update_channel(
                            channel.id,
                            {
                                "verified_at": datetime.now(),
                                "is_valid": False,
                                "error_message": str(e)
                            }
                        )
                        result["failed"] += 1
                        channel_detail["status"] = "failed"
                        channel_detail["error"] = str(e)
                        logger.warning(f"Канал {channel.chat_id} недоступен: {e}")
                    
                    result["details"].append(channel_detail)
                
                await session.commit()
                logger.info(f"Проверка каналов завершена: {result['verified']} доступны, {result['failed']} недоступны")
                
                return result
        
        except Exception as e:
            logger.error(f"Ошибка при проверке каналов: {e}", exc_info=True)
            return {
                "total": result["total"],
                "verified": result["verified"],
                "updated": result["updated"],
                "failed": result["failed"],
                "error": str(e),
                "details": result["details"]
            }
    
    async def cleanup_inactive_channels(self, days: int = 30) -> Dict[str, Any]:
        """
        Очищает неактивные каналы, которые не использовались указанное количество дней
        
        Args:
            days: Количество дней неактивности для удаления канала
            
        Returns:
            Dict[str, Any]: Результат очистки в формате:
            {
                "total_removed": int,  # Количество удаленных каналов
                "invalid_removed": int,  # Количество удаленных недоступных каналов
                "inactive_removed": int,  # Количество удаленных неактивных каналов
                "details": List[Dict[str, Any]]  # Подробная информация об удаленных каналах
            }
        """
        logger.info(f"Начинаем очистку неактивных каналов (более {days} дней неактивности)")
        
        result = {
            "total_removed": 0,
            "invalid_removed": 0,
            "inactive_removed": 0,
            "details": []
        }
        
        try:
            async with self.session_factory() as session:
                channel_repo = ChannelRepository(session)
                
                # Получаем неактивные каналы
                inactive_date = datetime.now() - timedelta(days=days)
                
                # Сначала удаляем недоступные каналы
                invalid_channels = await channel_repo.get_invalid_channels()
                
                for channel in invalid_channels:
                    # Проверяем, что канал не является каналом по умолчанию
                    if not channel.is_default:
                        await channel_repo.delete_channel(channel.id)
                        result["invalid_removed"] += 1
                        result["total_removed"] += 1
                        
                        result["details"].append({
                            "id": channel.id,
                            "chat_id": channel.chat_id,
                            "title": channel.title,
                            "reason": "invalid"
                        })
                        
                        logger.info(f"Удален недоступный канал: {channel.title} ({channel.chat_id})")
                
                # Затем удаляем неактивные каналы
                inactive_channels = await channel_repo.get_inactive_channels(inactive_date)
                
                for channel in inactive_channels:
                    # Проверяем, что канал не является каналом по умолчанию
                    if not channel.is_default:
                        await channel_repo.delete_channel(channel.id)
                        result["inactive_removed"] += 1
                        result["total_removed"] += 1
                        
                        result["details"].append({
                            "id": channel.id,
                            "chat_id": channel.chat_id,
                            "title": channel.title,
                            "reason": "inactive",
                            "last_used": channel.last_used.isoformat() if channel.last_used else None
                        })
                        
                        logger.info(f"Удален неактивный канал: {channel.title} ({channel.chat_id})")
                
                await session.commit()
                logger.info(f"Очистка каналов завершена: удалено {result['total_removed']} каналов")
                
                return result
        
        except Exception as e:
            logger.error(f"Ошибка при очистке каналов: {e}", exc_info=True)
            return {
                "total_removed": result["total_removed"],
                "invalid_removed": result["invalid_removed"],
                "inactive_removed": result["inactive_removed"],
                "error": str(e),
                "details": result["details"]
            }
            
    async def verify_channel(self, chat_id: int, bot: Bot) -> Dict[str, Any]:
        """
        Проверяет доступность конкретного канала и обновляет информацию о нем
        
        Args:
            chat_id: ID канала для проверки
            bot: Экземпляр бота для проверки
            
        Returns:
            Dict[str, Any]: Результат проверки в формате:
            {
                "success": bool,  # Успешность проверки
                "is_valid": bool,  # Доступен ли канал
                "title": str,  # Название канала (если доступен)
                "error": str,  # Текст ошибки (если недоступен)
                "updated": bool  # Была ли обновлена информация о канале
            }
        """
        logger.info(f"Проверка канала {chat_id}")
        
        try:
            async with self.session_factory() as session:
                channel_repo = ChannelRepository(session)
                
                # Получаем канал из базы данных
                channel = await channel_repo.get_channel_by_chat_id(chat_id)
                
                if not channel:
                    return {
                        "success": False,
                        "is_valid": False,
                        "error": f"Канал с ID {chat_id} не найден в базе данных"
                    }
                
                try:
                    # Проверяем доступ к каналу
                    chat_info = await bot.get_chat(chat_id)
                    
                    # Проверяем права бота в канале
                    bot_member = await bot.get_chat_member(chat_id, bot.id)
                    
                    # Определяем, нужно ли обновить информацию о канале
                    update_needed = (
                        chat_info.title != channel.title or
                        chat_info.username != channel.username
                    )
                    
                    if update_needed:
                        await channel_repo.update_channel(
                            channel.id,
                            {
                                "title": chat_info.title,
                                "username": chat_info.username,
                                "verified_at": datetime.now(),
                                "is_valid": True,
                                "error_message": None
                            }
                        )
                        
                        logger.info(f"Обновлена информация о канале {chat_id}: {chat_info.title}")
                        
                        return {
                            "success": True,
                            "is_valid": True,
                            "title": chat_info.title,
                            "username": chat_info.username,
                            "updated": True
                        }
                    else:
                        # Обновляем только время проверки
                        await channel_repo.update_channel(
                            channel.id,
                            {
                                "verified_at": datetime.now(),
                                "is_valid": True,
                                "error_message": None
                            }
                        )
                        
                        logger.debug(f"Канал {chat_id} проверен и актуален")
                        
                        return {
                            "success": True,
                            "is_valid": True,
                            "title": channel.title,
                            "username": channel.username,
                            "updated": False
                        }
                
                except Exception as e:
                    # Отмечаем канал как недоступный
                    error_message = f"Ошибка доступа к каналу: {str(e)}"
                    
                    await channel_repo.update_channel(
                        channel.id,
                        {
                            "verified_at": datetime.now(),
                            "is_valid": False,
                            "error_message": error_message
                        }
                    )
                    
                    logger.warning(f"Канал {chat_id} недоступен: {e}")
                    
                    return {
                        "success": True,
                        "is_valid": False,
                        "title": channel.title,
                        "error": error_message,
                        "updated": True
                    }
                
                finally:
                    await session.commit()
        
        except Exception as e:
            logger.error(f"Ошибка при проверке канала {chat_id}: {e}", exc_info=True)
            return {
                "success": False,
                "is_valid": False,
                "error": f"Ошибка при проверке канала: {str(e)}"
            }
            
    async def add_channel(
        self, 
        chat_id: int, 
        title: str, 
        chat_type: str, 
        username: Optional[str], 
        added_by: int,
        is_default: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Добавляет новый канал в базу данных
        
        Args:
            chat_id: ID чата
            title: Название чата
            chat_type: Тип чата (channel, group, supergroup)
            username: Username чата (опционально)
            added_by: ID пользователя, добавившего канал
            is_default: Является ли канал каналом по умолчанию
            
        Returns:
            Dict[str, Any]: Информация о добавленном канале или информация об ошибке
        """
        try:
            # Проверяем, существует ли уже такой канал
            async with self.session_factory() as session:
                channel_repo = ChannelRepository(session)
                existing_channel = await channel_repo.get_channel_by_chat_id(chat_id)
                
                if existing_channel:
                    logger.warning(f"Канал с chat_id {chat_id} уже существует в базе данных")
                    
                    # Возвращаем информацию о существующем канале и ошибке
                    return {
                        "success": False,
                        "error": "already_exists",
                        "message": f"Канал '{title}' уже добавлен в базу данных",
                        "channel": {
                            "id": existing_channel.id,
                            "chat_id": existing_channel.chat_id,
                            "title": existing_channel.title,
                            "username": existing_channel.username,
                            "chat_type": existing_channel.chat_type,
                            "is_default": existing_channel.is_default
                        }
                    }
                
                # Если канал устанавливается как канал по умолчанию, сбрасываем текущий по умолчанию
                if is_default:
                    await channel_repo.reset_default_flag()
                
                # Добавляем новый канал
                new_channel = await channel_repo.create_channel(
                    chat_id=chat_id,
                    title=title,
                    username=username,
                    type=chat_type,
                    is_default=is_default,
                    added_by=added_by
                )
                
                # Преобразуем SQLAlchemy объект в словарь
                return {
                    "success": True,
                    "id": new_channel.id,
                    "chat_id": new_channel.chat_id,
                    "title": new_channel.title,
                    "username": new_channel.username,
                    "chat_type": new_channel.chat_type,
                    "is_default": new_channel.is_default,
                    "added_by": new_channel.added_by,
                    "created_at": new_channel.created_at,
                    "last_used_at": new_channel.last_used_at
                }
        except Exception as e:
            logger.error(f"Ошибка при добавлении канала: {e}")
            return {
                "success": False,
                "error": "server_error",
                "message": f"Произошла ошибка при добавлении канала: {str(e)}"
            }
    
    async def get_all_channels(self) -> List[Dict[str, Any]]:
        """
        Получает список всех каналов из базы данных
        
        Returns:
            List[Dict[str, Any]]: Список каналов
        """
        logger.info("Запрос списка всех каналов")
        try:
            async with self.session_factory() as session:
                channel_repo = ChannelRepository(session)
                channels = await channel_repo.get_all_channels()
                
                # Преобразуем объекты SQLAlchemy в словари
                result = []
                for channel in channels:
                    result.append({
                        "id": channel.id,
                        "chat_id": channel.chat_id,
                        "title": channel.title,
                        "username": channel.username,
                        "chat_type": channel.chat_type,
                        "is_default": channel.is_default,
                        "last_used_at": channel.last_used_at,
                        "created_at": channel.created_at
                    })
                return result
        except Exception as e:
            logger.error(f"Ошибка при получении списка каналов: {e}")
            return []
    
    async def get_default_channel(self) -> Optional[Dict[str, Any]]:
        """
        Получение канала по умолчанию
        
        Returns:
            Optional[Dict[str, Any]]: Канал по умолчанию или None, если не найден
        """
        async with get_session() as session:
            try:
                query = select(Channel).where(Channel.is_default == True)
                result = await session.execute(query)
                channel = result.scalars().first()
                
                if not channel:
                    return None
                
                return {
                    "id": channel.id,
                    "chat_id": channel.chat_id,
                    "title": channel.title,
                    "chat_type": channel.chat_type,
                    "username": channel.username,
                    "is_default": channel.is_default,
                    "created_at": channel.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "added_by": channel.added_by,
                    "last_used_at": channel.last_used_at.strftime("%Y-%m-%d %H:%M:%S") if channel.last_used_at else None
                }
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при получении канала по умолчанию: {e}")
                return None
    
    async def set_default_channel(self, channel_id: int) -> bool:
        """
        Установка канала по умолчанию
        
        Args:
            channel_id: ID канала в базе данных
            
        Returns:
            bool: True, если канал успешно установлен как дефолтный
        """
        async with get_session() as session:
            try:
                channel_repo = ChannelRepository(session)
                result = await channel_repo.set_default_channel(channel_id)
                return result
            except Exception as e:
                logger.error(f"Ошибка при установке канала по умолчанию: {e}")
                return False
    
    async def delete_channel(self, channel_id: int) -> bool:
        """
        Удаление канала
        
        Args:
            channel_id: ID канала в базе данных
            
        Returns:
            bool: True, если канал успешно удален
        """
        async with get_session() as session:
            try:
                channel_repo = ChannelRepository(session)
                result = await channel_repo.delete_channel(channel_id)
                return result
            except Exception as e:
                logger.error(f"Ошибка при удалении канала: {e}")
                return False
    
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
        async with get_session() as session:
            try:
                channel_repo = ChannelRepository(session)
                result = await channel_repo.update_channel_info(channel_id, title, username)
                return result
            except Exception as e:
                logger.error(f"Ошибка при обновлении информации о канале: {e}")
                return False
    
    async def check_bot_access(self, chat_id: int, bot: Bot) -> Dict[str, Any]:
        """
        Проверка доступа бота к каналу
        
        Args:
            chat_id: ID канала/чата в Telegram
            bot: Экземпляр бота
            
        Returns:
            Dict[str, Any]: Результат проверки доступа
        """
        try:
            # Получаем информацию о чате
            chat = await bot.get_chat(chat_id)
            
            # Проверяем права бота в чате
            bot_member = await bot.get_chat_member(chat_id, bot.id)
            
            is_admin = False
            can_post_messages = False
            
            if isinstance(bot_member, ChatMemberAdministrator):
                is_admin = True
                can_post_messages = bot_member.can_post_messages
            
            return {
                "success": True,
                "chat_id": chat.id,
                "title": chat.title,
                "type": chat.type,
                "username": chat.username,
                "is_admin": is_admin,
                "can_post_messages": can_post_messages
            }
        except TelegramBadRequest as e:
            log_error(logger, f"Ошибка при получении информации о чате {chat_id}", e)
            return {
                "success": False,
                "error": "bad_request",
                "message": str(e)
            }
        except TelegramForbiddenError as e:
            log_error(logger, f"Нет доступа к чату {chat_id}", e)
            return {
                "success": False,
                "error": "forbidden",
                "message": "Бот не имеет доступа к этому чату. Убедитесь, что бот добавлен в чат и имеет необходимые права."
            }
        except Exception as e:
            log_error(logger, f"Ошибка при проверке доступа к чату {chat_id}", e)
            return {
                "success": False,
                "error": "unknown",
                "message": str(e)
            }
    
    async def update_last_used(self, channel_id: int) -> bool:
        """
        Обновление даты последнего использования канала
        
        Args:
            channel_id: ID канала в базе данных
            
        Returns:
            bool: True, если дата успешно обновлена
        """
        async with get_session() as session:
            try:
                channel_repo = ChannelRepository(session)
                result = await channel_repo.update_last_used(channel_id)
                return result
            except Exception as e:
                logger.error(f"Ошибка при обновлении даты использования канала: {e}")
                return False
    
    async def get_channel_by_id(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение канала по ID
        
        Args:
            channel_id: ID канала в базе данных
            
        Returns:
            Optional[Dict[str, Any]]: Данные канала или None, если не найден
        """
        async with get_session() as session:
            try:
                channel_repo = ChannelRepository(session)
                channel = await channel_repo.get_by_id(channel_id)
                
                if not channel:
                    return None
                
                return {
                    "id": channel.id,
                    "chat_id": channel.chat_id,
                    "title": channel.title,
                    "chat_type": channel.chat_type,
                    "username": channel.username,
                    "is_default": channel.is_default,
                    "created_at": channel.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "added_by": channel.added_by,
                    "last_used_at": channel.last_used_at.strftime("%Y-%m-%d %H:%M:%S") if channel.last_used_at else None
                }
            except Exception as e:
                logger.error(f"Ошибка при получении канала по ID {channel_id}: {e}")
                return None
    
    async def get_channel_by_chat_id(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о канале по его chat_id
        
        Args:
            chat_id: Chat ID канала
            
        Returns:
            Optional[Dict[str, Any]]: Информация о канале или None, если канал не найден
        """
        logger.info(f"Запрос информации о канале с chat_id {chat_id}")
        try:
            async with self.session_factory() as session:
                channel_repo = ChannelRepository(session)
                channel = await channel_repo.get_channel_by_chat_id(chat_id)
                
                if not channel:
                    logger.warning(f"Канал с chat_id {chat_id} не найден")
                    return None
                
                return {
                    "id": channel.id,
                    "chat_id": channel.chat_id,
                    "title": channel.title,
                    "username": channel.username,
                    "chat_type": channel.chat_type,
                    "is_default": channel.is_default,
                    "last_used_at": channel.last_used_at,
                    "created_at": channel.created_at
                }
        except Exception as e:
            logger.error(f"Ошибка при получении информации о канале с chat_id {chat_id}: {e}")
            return None
    
    async def update_channel_last_used(self, chat_id: int) -> bool:
        """
        Обновляет время последнего использования канала
        
        Args:
            chat_id: ID чата в Telegram (а не ID записи в базе данных)
            
        Returns:
            bool: True, если обновление успешно, иначе False
        """
        logger.info(f"Обновление времени последнего использования канала с chat_id {chat_id}")
        try:
            async with self.session_factory() as session:
                channel_repo = ChannelRepository(session)
                return await channel_repo.update_last_used(chat_id)
        except Exception as e:
            logger.error(f"Ошибка при обновлении времени последнего использования канала {chat_id}: {e}")
            return False
    
    async def get_available_chats(
        self, 
        bot: Bot, 
        filter_publishing_rights: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Получает список доступных каналов для публикации
        
        Args:
            bot: Экземпляр бота
            filter_publishing_rights: Фильтровать каналы по правам на публикацию
            
        Returns:
            List[Dict[str, Any]]: Список доступных каналов в формате:
            [
                {
                    "id": int,         # ID канала в базе данных
                    "chat_id": int,    # ID чата в Telegram
                    "title": str,      # Название канала
                    "username": str,   # Username канала (если есть)
                    "is_default": bool,# Флаг канала по умолчанию
                    "last_used": str,  # Время последнего использования (если есть)
                },
                ...
            ]
        """
        logger.info("Запрос списка всех каналов")
        
        available_chats = []
        
        async with self.session_factory() as session:
            try:
                # Получаем все каналы
                channels = await self._get_channels(session)
                
                for channel in channels:
                    # Проверяем права бота в канале, если требуется
                    has_rights = True
                    if filter_publishing_rights:
                        try:
                            bot_member = await bot.get_chat_member(channel.chat_id, bot.id)
                            
                            # Проверяем наличие прав на публикацию
                            if hasattr(bot_member, 'can_post_messages'):
                                has_rights = bot_member.can_post_messages
                            elif hasattr(bot_member, 'status') and bot_member.status in ['administrator', 'creator']:
                                has_rights = True
                            else:
                                has_rights = False
                                
                            logger.debug(f"Проверка прав бота в канале {channel.title} ({channel.chat_id}): {has_rights}")
                        except Exception as e:
                            logger.warning(f"Ошибка при проверке прав бота в канале {channel.title} ({channel.chat_id}): {e}")
                            has_rights = False
                    
                    # Добавляем канал в список, если есть права
                    if has_rights:
                        chat_info = {
                            "id": channel.id,
                            "chat_id": channel.chat_id,  # Важно возвращать оригинальный Telegram ID канала
                            "title": channel.title,
                            "username": channel.username,
                            "is_default": channel.is_default,
                            "last_used": channel.last_used_at.isoformat() if channel.last_used_at else None,
                        }
                        available_chats.append(chat_info)
                
                logger.info(f"Найдено {len(available_chats)} доступных каналов")
                return available_chats
                
            except Exception as e:
                logger.error(f"Ошибка при получении списка доступных каналов: {e}", exc_info=True)
                return [] 