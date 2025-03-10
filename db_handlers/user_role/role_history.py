import asyncpg
from config.bot_config import DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def log_role_change(
    user_id: int,
    old_role: str,
    new_role: str,
    changed_by: int,
    reason: str = None
) -> bool:
    """
    Логирование изменения роли пользователя
    
    Args:
        user_id: ID пользователя
        old_role: Предыдущая роль
        new_role: Новая роль
        changed_by: ID администратора, выполнившего изменение
        reason: Причина изменения
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
            INSERT INTO role_history 
            (user_id, old_role, new_role, changed_by, changed_at, reason)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_id, old_role, new_role, changed_by, datetime.utcnow(), reason
        )
        
        logger.info(f"Изменение роли записано: {user_id} ({old_role} -> {new_role})")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при логировании изменения роли: {e}")
        return False
    finally:
        if 'conn' in locals():
            await conn.close()

async def get_user_role_history(user_id: int) -> list:
    """Получение истории изменений ролей пользователя"""
    try:
        conn = await asyncpg.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            port=DB_PORT
        )
        
        history = await conn.fetch(
            """
            SELECT * FROM role_history 
            WHERE user_id = $1 
            ORDER BY changed_at DESC
            """,
            user_id
        )
        
        return history
        
    except Exception as e:
        logger.error(f"Ошибка при получении истории ролей: {e}")
        return []
    finally:
        if 'conn' in locals():
            await conn.close() 