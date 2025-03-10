import asyncio
import logging
import os
import json
from datetime import datetime, time
from typing import List, Dict, Optional, Any
import asyncpg
from aiogram import Bot
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)

# Получение параметров подключения к БД из переменных окружения
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tgbot_admin")

# Настройки уведомлений
NOTIFICATIONS_CONFIG_FILE = "config/notifications.json"

# Типы уведомлений
NOTIFICATION_TYPES = {
    "role_changes": "Изменения ролей",
    "new_users": "Новые пользователи",
    "system_events": "Системные события",
    "errors": "Ошибки и предупреждения"
}

# Класс для управления уведомлениями
class NotificationManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotificationManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.config = {
                "enabled": False,
                "schedule": {
                    "daily_time": "10:00",
                    "weekly_day": 1,  # Понедельник
                    "use_daily": True
                },
                "types": {
                    "role_changes": True,
                    "new_users": True,
                    "system_events": True,
                    "errors": True
                },
                "recipients": []  # Список ID пользователей, которые будут получать уведомления
            }
            self._load_config()
            self._initialized = True
    
    def _load_config(self):
        """Загрузка конфигурации уведомлений из файла"""
        try:
            if os.path.exists(NOTIFICATIONS_CONFIG_FILE):
                with open(NOTIFICATIONS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                    logger.info("Конфигурация уведомлений загружена")
            else:
                self._save_config()
                logger.info("Создана новая конфигурация уведомлений")
        except Exception as e:
            logger.error(f"Ошибка при загрузке конфигурации уведомлений: {e}")
    
    def _save_config(self):
        """Сохранение конфигурации уведомлений в файл"""
        try:
            os.makedirs(os.path.dirname(NOTIFICATIONS_CONFIG_FILE), exist_ok=True)
            with open(NOTIFICATIONS_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
                logger.info("Конфигурация уведомлений сохранена")
        except Exception as e:
            logger.error(f"Ошибка при сохранении конфигурации уведомлений: {e}")
    
    def enable_notifications(self, enabled: bool = True) -> bool:
        """Включение или отключение уведомлений"""
        try:
            self.config["enabled"] = enabled
            self._save_config()
            return True
        except Exception as e:
            logger.error(f"Ошибка при {'включении' if enabled else 'отключении'} уведомлений: {e}")
            return False
    
    def set_notification_type(self, notification_type: str, enabled: bool) -> bool:
        """Включение или отключение определенного типа уведомлений"""
        try:
            if notification_type in self.config["types"]:
                self.config["types"][notification_type] = enabled
                self._save_config()
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при настройке типа уведомлений: {e}")
            return False
    
    def set_schedule(self, daily_time: str, weekly_day: int, use_daily: bool) -> bool:
        """Настройка расписания уведомлений"""
        try:
            self.config["schedule"]["daily_time"] = daily_time
            self.config["schedule"]["weekly_day"] = weekly_day
            self.config["schedule"]["use_daily"] = use_daily
            self._save_config()
            return True
        except Exception as e:
            logger.error(f"Ошибка при настройке расписания уведомлений: {e}")
            return False
    
    def add_recipient(self, user_id: int) -> bool:
        """Добавление получателя уведомлений"""
        try:
            if user_id not in self.config["recipients"]:
                self.config["recipients"].append(user_id)
                self._save_config()
            return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении получателя уведомлений: {e}")
            return False
    
    def remove_recipient(self, user_id: int) -> bool:
        """Удаление получателя уведомлений"""
        try:
            if user_id in self.config["recipients"]:
                self.config["recipients"].remove(user_id)
                self._save_config()
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении получателя уведомлений: {e}")
            return False
    
    def get_config(self) -> dict:
        """Получение текущей конфигурации уведомлений"""
        return self.config.copy()
    
    async def send_notification(self, bot: Bot, message: str, notification_type: str = None) -> bool:
        """Отправка уведомления всем получателям"""
        try:
            if not self.config["enabled"]:
                logger.debug("Уведомления отключены")
                return False
            
            if notification_type and not self.config["types"].get(notification_type, False):
                logger.debug(f"Тип уведомлений '{notification_type}' отключен")
                return False
            
            for user_id in self.config["recipients"]:
                try:
                    await bot.send_message(user_id, message, parse_mode="HTML")
                    logger.info(f"Отправлено уведомление пользователю {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомлений: {e}")
            return False
    
    async def schedule_notifications(self, bot: Bot):
        """Запуск планировщика уведомлений"""
        while True:
            try:
                # Получаем текущее время и день недели
                now = datetime.now()
                current_day = now.weekday()  # 0 - понедельник, 6 - воскресенье
                current_time_str = now.strftime("%H:%M")
                
                # Проверяем соответствие расписанию
                if self.config["enabled"]:
                    schedule = self.config["schedule"]
                    
                    if schedule["use_daily"] and current_time_str == schedule["daily_time"]:
                        # Отправляем ежедневные уведомления
                        await self._send_daily_summary(bot)
                    
                    if not schedule["use_daily"] and current_day == schedule["weekly_day"] and current_time_str == schedule["daily_time"]:
                        # Отправляем еженедельные уведомления
                        await self._send_weekly_summary(bot)
                
                # Пауза перед следующей проверкой (1 минута)
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Ошибка в планировщике уведомлений: {e}")
                await asyncio.sleep(60)
    
    async def _send_daily_summary(self, bot: Bot):
        """Отправка ежедневной сводки"""
        try:
            # Подключаемся к базе данных
            conn = await asyncpg.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME
            )
            
            # Формируем сообщение с ежедневной сводкой
            message = "📊 <b>Ежедневная сводка</b>\n\n"
            
            # Получаем статистику по изменениям ролей за последние 24 часа
            if self.config["types"]["role_changes"]:
                role_changes = await conn.fetch(
                    """
                    SELECT COUNT(*) as count, action
                    FROM role_audit
                    WHERE performed_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY action
                    """
                )
                
                message += "<b>Изменения ролей за 24 часа:</b>\n"
                if role_changes:
                    for record in role_changes:
                        action = "добавлены" if record["action"] == "add" else "удалены"
                        message += f"• {record['count']} ролей {action}\n"
                else:
                    message += "• Нет изменений\n"
                
                message += "\n"
            
            # Получаем статистику по новым пользователям за последние 24 часа
            if self.config["types"]["new_users"]:
                new_users = await conn.fetchval(
                    """
                    SELECT COUNT(*) 
                    FROM users
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                    """
                )
                
                message += f"<b>Новые пользователи за 24 часа:</b> {new_users}\n\n"
            
            # Закрываем соединение
            await conn.close()
            
            # Отправляем сообщение всем получателям
            for user_id in self.config["recipients"]:
                try:
                    await bot.send_message(user_id, message, parse_mode="HTML")
                    logger.info(f"Отправлена ежедневная сводка пользователю {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке ежедневной сводки пользователю {user_id}: {e}")
            
        except Exception as e:
            logger.error(f"Ошибка при формировании ежедневной сводки: {e}")
    
    async def _send_weekly_summary(self, bot: Bot):
        """Отправка еженедельной сводки"""
        try:
            # Подключаемся к базе данных
            conn = await asyncpg.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME
            )
            
            # Формируем сообщение с еженедельной сводкой
            message = "📈 <b>Еженедельная сводка</b>\n\n"
            
            # Получаем статистику по изменениям ролей за последнюю неделю
            if self.config["types"]["role_changes"]:
                role_changes = await conn.fetch(
                    """
                    SELECT COUNT(*) as count, action
                    FROM role_audit
                    WHERE performed_at >= NOW() - INTERVAL '7 days'
                    GROUP BY action
                    """
                )
                
                message += "<b>Изменения ролей за неделю:</b>\n"
                if role_changes:
                    for record in role_changes:
                        action = "добавлены" if record["action"] == "add" else "удалены"
                        message += f"• {record['count']} ролей {action}\n"
                else:
                    message += "• Нет изменений\n"
                
                message += "\n"
            
            # Получаем статистику по новым пользователям за последнюю неделю
            if self.config["types"]["new_users"]:
                new_users = await conn.fetchval(
                    """
                    SELECT COUNT(*) 
                    FROM users
                    WHERE created_at >= NOW() - INTERVAL '7 days'
                    """
                )
                
                message += f"<b>Новые пользователи за неделю:</b> {new_users}\n\n"
            
            # Получаем общую статистику базы данных
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            total_roles = await conn.fetchval("SELECT COUNT(*) FROM user_roles")
            
            message += f"<b>Общая статистика:</b>\n"
            message += f"• Всего пользователей: {total_users}\n"
            message += f"• Всего назначенных ролей: {total_roles}\n"
            
            # Закрываем соединение
            await conn.close()
            
            # Отправляем сообщение всем получателям
            for user_id in self.config["recipients"]:
                try:
                    await bot.send_message(user_id, message, parse_mode="HTML")
                    logger.info(f"Отправлена еженедельная сводка пользователю {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке еженедельной сводки пользователю {user_id}: {e}")
            
        except Exception as e:
            logger.error(f"Ошибка при формировании еженедельной сводки: {e}")

# Создаем экземпляр менеджера уведомлений
notification_manager = NotificationManager()

# Функции-обертки для использования извне
def enable_notifications(enabled: bool = True) -> bool:
    """Включение или отключение уведомлений"""
    return notification_manager.enable_notifications(enabled)

def set_notification_type(notification_type: str, enabled: bool) -> bool:
    """Включение или отключение определенного типа уведомлений"""
    return notification_manager.set_notification_type(notification_type, enabled)

def set_schedule(daily_time: str, weekly_day: int, use_daily: bool) -> bool:
    """Настройка расписания уведомлений"""
    return notification_manager.set_schedule(daily_time, weekly_day, use_daily)

def add_recipient(user_id: int) -> bool:
    """Добавление получателя уведомлений"""
    return notification_manager.add_recipient(user_id)

def remove_recipient(user_id: int) -> bool:
    """Удаление получателя уведомлений"""
    return notification_manager.remove_recipient(user_id)

def get_notification_config() -> dict:
    """Получение текущей конфигурации уведомлений"""
    return notification_manager.get_config()

async def send_notification(bot: Bot, message: str, notification_type: str = None) -> bool:
    """Отправка уведомления всем получателям"""
    return await notification_manager.send_notification(bot, message, notification_type)

async def start_notification_scheduler(bot: Bot):
    """Запуск планировщика уведомлений"""
    await notification_manager.schedule_notifications(bot) 