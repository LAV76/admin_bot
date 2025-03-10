import asyncpg
from config.bot_config import DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT
import logging

logger = logging.getLogger(__name__)

async def delete_user_role(user_id: int) -> bool:
    """
    Удаление пользователя из базы данных
    
    Args:
        user_id: ID пользователя Telegram
        
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
        
        result = await conn.execute(
            """
            DELETE FROM users 
            WHERE user_id = $1
            """,
            user_id
        )
        
        if result == "DELETE 0":
            logger.warning(f"Попытка удалить несуществующего пользователя: {user_id}")
            return False
            
        logger.info(f"Удален пользователь с ID: {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя: {e}")
        return False
    finally:
        if 'conn' in locals():
            await conn.close() 