import asyncpg
from config.bot_config import DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT
import logging

logger = logging.getLogger(__name__)

async def create_content_manager(user_id: int, username: str) -> bool:
    """
    Добавление нового контент-менеджера в базу данных
    
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
            VALUES ($1, 'content_manager', $2)
            """,
            user_id, username
        )
        
        logger.info(f"Добавлен новый контент-менеджер: {username} (ID: {user_id})")
        return True
        
    except asyncpg.UniqueViolationError:
        logger.warning(f"Попытка добавить существующего пользователя: {user_id}")
        return False
    except Exception as e:
        logger.error(f"Ошибка при добавлении контент-менеджера: {e}")
        return False
    finally:
        if 'conn' in locals():
            await conn.close() 