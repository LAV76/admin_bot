from typing import List, Optional, Dict, Any
import logging
from sqlalchemy import select, insert, delete, and_, update, exists
from sqlalchemy.exc import SQLAlchemyError
from app.db.session import async_session_maker
from models.users import User, UserRole, RoleAudit
import asyncpg
import os
from dotenv import load_dotenv
from aiogram import Bot
from aiogram.types import Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

# Настройка логирования
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

async def get_connection():
    """Получение соединения с базой данных"""
    try:
        # Загружаем переменные окружения
        load_dotenv()
        
        # Получаем параметры подключения к БД
        db_user = os.getenv("DB_USER", "postgres")
        db_pass = os.getenv("DB_PASS", "")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "tgbot_admin")
        
        # Формируем строку подключения
        dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        
        # Подключаемся к базе данных
        conn = await asyncpg.connect(dsn)
        return conn
    except Exception as e:
        logger.error(f"Ошибка при подключении к базе данных: {e}", exc_info=True)
        return None

async def add_user_role(user_id: int, role_type: str, admin_id: int) -> bool:
    """
    Добавление роли пользователю
    
    Args:
        user_id: ID пользователя
        role_type: Тип роли (admin, content_manager)
        admin_id: ID администратора, выполняющего действие
        
    Returns:
        bool: True если успешно, False в противном случае
    """
    conn = None
    try:
        conn = await get_connection()
        if not conn:
            return False
        
        # Проверяем существование пользователя
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE user_id = $1",
            user_id
        )
        
        # Если пользователя нет, добавляем его
        if not user:
            await conn.execute(
                """
                INSERT INTO users (user_id, username, user_role)
                VALUES ($1, $2, $3)
                """,
                user_id, f"user_{user_id}", role_type
            )
            logger.info(f"Добавлен новый пользователь с ID: {user_id}")
        
        # Проверяем, есть ли уже такая роль
        role = await conn.fetchrow(
            """
            SELECT * FROM user_roles 
            WHERE user_id = $1 AND role_type = $2
            """,
            user_id, role_type
        )
        
        if role:
            logger.info(f"Роль {role_type} уже существует у пользователя {user_id}")
            return True
        
        # Добавляем роль
        await conn.execute(
            """
            INSERT INTO user_roles (user_id, role_type, created_by)
            VALUES ($1, $2, $3)
            """,
            user_id, role_type, admin_id
        )
        
        # Проверяем существование таблицы role_audit
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        table_names = [t['tablename'] for t in tables]
        
        # Логируем действие в таблицу role_audit, если она существует
        if 'role_audit' in table_names:
            await conn.execute(
                """
                INSERT INTO role_audit (user_id, role_type, action, performed_by)
                VALUES ($1, $2, $3, $4)
                """,
                user_id, role_type, 'add', admin_id
            )
            logger.info(f"Добавлена запись в role_audit: пользователь {user_id}, роль {role_type}, действие add")
        
        logger.info(f"Роль {role_type} успешно добавлена пользователю {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении роли: {e}", exc_info=True)
        return False
    finally:
        if conn:
            await conn.close()

async def remove_user_role(user_id: int, role_type: str, admin_id: int) -> bool:
    """
    Удаление роли у пользователя
    
    Args:
        user_id: ID пользователя
        role_type: Тип роли (admin, content_manager)
        admin_id: ID администратора, выполняющего действие
        
    Returns:
        bool: True если успешно, False в противном случае
    """
    conn = None
    try:
        conn = await get_connection()
        if not conn:
            return False
        
        # Проверяем существование роли
        role = await conn.fetchrow(
            """
            SELECT * FROM user_roles 
            WHERE user_id = $1 AND role_type = $2
            """,
            user_id, role_type
        )
        
        if not role:
            logger.warning(f"Роль {role_type} не найдена у пользователя {user_id}")
            return False
        
        # Удаляем роль
        await conn.execute(
            """
            DELETE FROM user_roles 
            WHERE user_id = $1 AND role_type = $2
            """,
            user_id, role_type
        )
        
        # Проверяем существование таблицы role_audit
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        table_names = [t['tablename'] for t in tables]
        
        # Логируем действие в таблицу role_audit, если она существует
        if 'role_audit' in table_names:
            await conn.execute(
                """
                INSERT INTO role_audit (user_id, role_type, action, performed_by)
                VALUES ($1, $2, $3, $4)
                """,
                user_id, role_type, 'remove', admin_id
            )
            logger.info(f"Добавлена запись в role_audit: пользователь {user_id}, роль {role_type}, действие remove")
        
        logger.info(f"Роль {role_type} успешно удалена у пользователя {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при удалении роли: {e}", exc_info=True)
        return False
    finally:
        if conn:
            await conn.close()

async def check_user_role(user_id: int, role_type: str) -> bool:
    """
    Проверка наличия роли у пользователя
    
    Args:
        user_id: ID пользователя
        role_type: Тип роли (admin, content_manager)
        
    Returns:
        bool: True если роль есть, False в противном случае
    """
    conn = None
    try:
        conn = await get_connection()
        if not conn:
            return False
        
        # Проверяем существование роли
        role = await conn.fetchrow(
            """
            SELECT * FROM user_roles 
            WHERE user_id = $1 AND role_type = $2
            """,
            user_id, role_type
        )
        
        return role is not None
        
    except Exception as e:
        logger.error(f"Ошибка при проверке роли: {e}", exc_info=True)
        return False
    finally:
        if conn:
            await conn.close()

async def get_user_roles(user_id: int) -> List[str]:
    """
    Получение списка ролей пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        List[str]: Список ролей пользователя
    """
    conn = None
    try:
        conn = await get_connection()
        if not conn:
            return []
        
        # Получаем роли пользователя
        roles = await conn.fetch(
            """
            SELECT role_type FROM user_roles 
            WHERE user_id = $1
            """,
            user_id
        )
        
        return [role['role_type'] for role in roles]
        
    except Exception as e:
        logger.error(f"Ошибка при получении ролей пользователя: {e}", exc_info=True)
        return []
    finally:
        if conn:
            await conn.close()

async def get_role_history(limit: int = 10) -> list:
    """
    Получение истории изменений ролей пользователей
    
    Args:
        limit: Максимальное количество записей для возврата
        
    Returns:
        list: Список записей истории изменений ролей
    """
    try:
        # Подключаемся к базе данных
        conn_string = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        conn = await asyncpg.connect(conn_string)
        
        # Проверяем существование таблицы role_audit
        tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        table_names = [t['tablename'] for t in tables]
        
        if 'role_audit' not in table_names:
            logger.warning("Таблица role_audit не существует")
            return []
        
        # Получаем расширенную историю изменений с информацией о пользователях
        query = """
        SELECT 
            ra.id, 
            ra.user_id, 
            u1.username as target_username,
            ra.role_type, 
            ra.action, 
            ra.performed_by, 
            u2.username as performed_by_username,
            ra.performed_at,
            to_char(ra.performed_at, 'DD.MM.YYYY HH24:MI:SS') as formatted_date
        FROM 
            role_audit ra
        LEFT JOIN 
            users u1 ON ra.user_id = u1.user_id
        LEFT JOIN 
            users u2 ON ra.performed_by = u2.user_id
        ORDER BY 
            ra.performed_at DESC
        LIMIT $1
        """
        
        history = await conn.fetch(query, limit)
        logger.info(f"Получено {len(history)} записей истории изменений ролей")
        
        return history
    except Exception as e:
        logger.error(f"Ошибка при получении истории изменений ролей: {e}")
        return []
    finally:
        if 'conn' in locals():
            await conn.close()

async def get_available_roles() -> list:
    """
    Получение списка доступных ролей
    
    Returns:
        list: Список ролей в формате [{id: int, name: str}, ...]
    """
    try:
        # Подключаемся к базе данных
        conn = await get_connection()
        
        # Получаем список ролей
        query = "SELECT id, name FROM roles ORDER BY id"
        rows = await conn.fetch(query)
        
        # Формируем результат
        roles = [{"id": row["id"], "name": row["name"]} for row in rows]
        
        await conn.close()
        return roles
    except Exception as e:
        logger.error(f"Ошибка при получении списка доступных ролей: {e}")
        return []

async def check_user_exists(user_id: int) -> bool:
    """
    Проверяет существование пользователя в базе данных.
    
    Args:
        user_id: ID пользователя для проверки
        
    Returns:
        bool: True если пользователь существует, False в противном случае
    """
    try:
        # Преобразуем user_id в int, если он передан как строка
        if isinstance(user_id, str):
            user_id = int(user_id)
        
        logger.info(f"Проверка существования пользователя с ID: {user_id} (тип: {type(user_id)})")
        
        # Получаем соединение с базой данных
        conn = await get_connection()
        if not conn:
            logger.error("Не удалось получить соединение с базой данных")
            return False
            
        try:
            # Проверяем наличие в таблице users напрямую
            users_exists_query = "SELECT EXISTS(SELECT 1 FROM users WHERE user_id = $1)"
            user_result = await conn.fetchval(users_exists_query, user_id)
            
            if user_result:
                logger.info(f"Пользователь {user_id} найден в таблице users.")
                return True
            
            # Проверяем таблицу user_roles
            roles_exists_query = "SELECT EXISTS(SELECT 1 FROM user_roles WHERE user_id = $1)"
            roles_result = await conn.fetchval(roles_exists_query, user_id)
            
            if roles_result:
                logger.info(f"Пользователь {user_id} найден в таблице user_roles.")
                return True
                
            # Получаем список всех пользователей для диагностики
            all_users = await conn.fetch("SELECT user_id FROM users LIMIT 5")
            logger.info(f"Пример пользователей в базе: {all_users}")
            
            # Пользователь не найден
            logger.warning(f"Пользователь с ID {user_id} не найден в базе данных.")
            return False
        finally:
            # Закрываем соединение
            await conn.close()
    except Exception as e:
        logger.error(f"Ошибка при проверке существования пользователя с ID {user_id}: {e}", exc_info=True)
        return False

async def create_user(user_id: str) -> bool:
    """
    Создает пользователя в базе данных
    
    Args:
        user_id: ID пользователя для создания
        
    Returns:
        bool: True если успешно, False в противном случае
    """
    try:
        # Преобразуем ID в число
        if isinstance(user_id, str):
            user_id = int(user_id)
            
        logger.info(f"Создание пользователя с ID {user_id} в базе данных")
        
        # Подключаемся к базе данных
        conn = await get_connection()
        if not conn:
            logger.error("Не удалось подключиться к базе данных")
            return False
        
        try:
            # Начинаем транзакцию
            tr = conn.transaction()
            await tr.start()
            
            # Создаем пользователя с указанием всех обязательных полей
            query = """
            INSERT INTO users (user_id, username, user_role, created_at) 
            VALUES ($1, $2, $3, NOW()) 
            ON CONFLICT (user_id) DO UPDATE 
            SET username = $2, user_role = $3
            """
            await conn.execute(query, user_id, f"user_{user_id}", "user")
            
            # Проверяем, что пользователь создан
            check_query = "SELECT EXISTS(SELECT 1 FROM users WHERE user_id = $1)"
            exists = await conn.fetchval(check_query, user_id)
            
            if exists:
                await tr.commit()
                logger.info(f"Пользователь с ID {user_id} успешно создан/обновлен в базе данных")
                return True
            else:
                await tr.rollback()
                logger.error(f"Пользователь с ID {user_id} не найден после вставки")
                return False
        except Exception as e:
            if 'tr' in locals():
                await tr.rollback()
            logger.error(f"Ошибка при создании пользователя: {e}", exc_info=True)
            return False
        finally:
            # Закрываем соединение
            await conn.close()
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя с ID {user_id}: {e}", exc_info=True)
        return False

async def process_remove_role_id(message: Message, state: FSMContext, bot: Bot):
    """
    Обработчик ввода ID пользователя для удаления роли
    Проверяет валидность ID и переводит в режим выбора роли
    """
    try:
        # Получаем введенный ID пользователя
        user_id = message.text.strip()
        logger.info(f"Получен ID пользователя для удаления роли: {user_id} (тип: {type(user_id)})")
        
        # Проверяем, что ID это положительное число
        try:
            user_id_int = int(user_id)
            logger.info(f"ID пользователя после преобразования: {user_id_int} (тип: {type(user_id_int)})")
            
            if user_id_int <= 0:
                await message.answer("❌ ID пользователя должен быть положительным числом. Пожалуйста, введите корректный ID.")
                return
                
        except ValueError:
            await message.answer("❌ ID пользователя должен быть числом. Пожалуйста, введите корректный ID.")
            return
            
        # Отправляем сообщение о проверке
        loading_msg = await message.answer("🔍 Проверяю наличие пользователя в базе данных...")
            
        # Проверяем существование пользователя в базе данных
        user_exists = await check_user_exists(user_id_int)
        logger.info(f"Результат проверки существования пользователя {user_id}: {user_exists}")
        
        if not user_exists:
            logger.warning(f"Пользователь с ID {user_id} не найден в базе данных")
            
            # Попытка создать пользователя для диагностики
            logger.info(f"Попытка создать пользователя с ID {user_id} для диагностики")
            created = await create_user(user_id)
            logger.info(f"Результат создания пользователя: {created}")
            
            # Проверяем еще раз после создания
            user_exists = await check_user_exists(user_id_int)
            logger.info(f"Повторная проверка после создания: {user_exists}")
            
            if not user_exists:
                # Удаляем сообщение загрузки
                await bot.delete_message(chat_id=message.chat.id, message_id=loading_msg.message_id)
                
                # Отправляем сообщение об ошибке
                await message.answer(
                    f"❌ Пользователь с ID {user_id} не найден в базе данных.\n"
                    f"Проверьте правильность ID и убедитесь, что пользователь существует в системе.\n\n"
                    f"Результат проверки: {user_exists}\n"
                    f"Создан для диагностики: {created}\n"
                    f"Повторная проверка: {user_exists}"
                )
                return
        
        # Получаем роли пользователя
        roles = await get_user_roles(user_id_int)
        logger.info(f"Роли пользователя {user_id}: {roles}")
        
        # Если у пользователя нет ролей, сообщаем об этом
        if not roles:
            logger.warning(f"У пользователя {user_id} нет ролей для удаления")
            
            # Удаляем сообщение загрузки
            await bot.delete_message(chat_id=message.chat.id, message_id=loading_msg.message_id)
            
            await message.answer(
                f"ℹ️ У пользователя с ID {user_id} нет ролей для удаления.\n"
                f"Возможно, вы хотите добавить роль этому пользователю?"
            )
            return
        
        # Сохраняем ID пользователя в состоянии
        await state.update_data(user_id=user_id_int)
        
        # Создаем клавиатуру с ролями пользователя
        keyboard = InlineKeyboardBuilder()
        
        # Добавляем кнопки для каждой роли
        for role in roles:
            keyboard.button(
                text=f"🗑 Удалить роль: {role}",
                callback_data=f"remove_role_{role}_{user_id}"
            )
        
        # Добавляем кнопку возврата
        keyboard.button(
            text="↩️ Назад",
            callback_data="back_to_menu"
        )
        
        # Выравниваем кнопки по одной в ряд
        keyboard.adjust(1)
        
        # Удаляем сообщение загрузки
        await bot.delete_message(chat_id=message.chat.id, message_id=loading_msg.message_id)
        
        # Отправляем список ролей пользователя
        await message.answer(
            f"👤 Текущие роли пользователя с ID {user_id}:\n\n"
            f"• " + "\n• ".join(roles) + "\n\n"
            f"Выберите роль для удаления:",
            reply_markup=keyboard.as_markup()
        )
        
        # Устанавливаем состояние выбора роли
        await state.set_state(RemoveRoleStates.select_role)
        
    except ValueError as e:
        logger.error(f"Ошибка при обработке ID пользователя: {e}")
        await message.answer(
            "❌ Произошла ошибка при обработке ID пользователя.\n"
            "Пожалуйста, введите корректный ID (только цифры)."
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке ID пользователя: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла неизвестная ошибка при обработке запроса.\n"
            "Пожалуйста, попробуйте снова или обратитесь к администратору."
        ) 