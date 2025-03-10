import asyncpg
from config.bot_config import DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT
import logging
from datetime import datetime
from typing import List, Tuple

logger = logging.getLogger(__name__)

async def bulk_add_users(users: List[Tuple[int, str, str]]) -> tuple[int, int]:
    """
    Массовое добавление пользователей
    
    Args:
        users: Список кортежей (user_id, role, username)
    
    Returns:
        tuple: (количество успешных, количество ошибок)
    """
    success = 0
    errors = 0
    
    try:
        conn = await asyncpg.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            port=DB_PORT
        )
        
        for user_id, role, username in users:
            try:
                await conn.execute(
                    """
                    INSERT INTO users (user_id, user_role, username) 
                    VALUES ($1, $2, $3)
                    """,
                    user_id, role, username
                )
                success += 1
            except Exception as e:
                logger.error(f"Ошибка при добавлении пользователя {user_id}: {e}")
                errors += 1
                
        return success, errors
        
    finally:
        if 'conn' in locals():
            await conn.close()

async def bulk_delete_users(user_ids: List[int]) -> tuple[int, int]:
    """
    Массовое удаление пользователей
    
    Args:
        user_ids: Список ID пользователей
    
    Returns:
        tuple: (количество успешных, количество ошибок)
    """
    success = 0
    errors = 0
    
    try:
        conn = await asyncpg.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            port=DB_PORT
        )
        
        for user_id in user_ids:
            try:
                result = await conn.execute(
                    """
                    DELETE FROM users 
                    WHERE user_id = $1
                    """,
                    user_id
                )
                if result == "DELETE 1":
                    success += 1
                else:
                    errors += 1
            except Exception as e:
                logger.error(f"Ошибка при удалении пользователя {user_id}: {e}")
                errors += 1
                
        return success, errors
        
    finally:
        if 'conn' in locals():
            await conn.close() 