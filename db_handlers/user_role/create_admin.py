import asyncpg
from config.bot_config import DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def create_admin(user_id: int, username: str) -> bool:
    """
    Добавление нового администратора в базу данных
    
    Args:
        user_id: ID пользователя Telegram
        username: Имя пользователя
        
    Returns:
        bool: True если успешно, False если произошла ошибка
    """
    try:
        conn = await asyncpg.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            port=DB_PORT
        )
        
        await conn.execute(
            """
            INSERT INTO users (user_id, user_role, username) 
            VALUES ($1, 'admin', $2)
            """,
            user_id, username
        )
        
        logger.info(f"Добавлен новый администратор: {username} (ID: {user_id})")
        return True
        
    except asyncpg.UniqueViolationError:
        logger.warning(f"Попытка добавить существующего пользователя: {user_id}")
        return False
    except Exception as e:
        logger.error(f"Ошибка при добавлении администратора: {e}")
        return False
    finally:
        if 'conn' in locals():
            await conn.close()

async def create_admin_with_expiry(user_id: int, username: str, expires_at: datetime = None) -> bool:
    """
    Добавление администратора с временным ограничением
    
    Args:
        user_id: ID пользователя Telegram
        username: Имя пользователя
        expires_at: Дата истечения роли
    """
    try:
        conn = await asyncpg.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            port=DB_PORT
        )
        
        await conn.execute(
            """
            INSERT INTO users (user_id, user_role, username, expires_at) 
            VALUES ($1, 'admin', $2, $3)
            """,
            user_id, username, expires_at
        )
        
        logger.info(f"Добавлен временный администратор: {username} (ID: {user_id})")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении временного администратора: {e}")
        return False
    finally:
        if 'conn' in locals():
            await conn.close() 