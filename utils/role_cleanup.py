import asyncio
import logging
from datetime import datetime
import asyncpg
from config.bot_config import DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT

logger = logging.getLogger(__name__)

async def cleanup_expired_roles():
    """Удаление истекших временных ролей"""
    while True:
        try:
            conn = await asyncpg.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME,
                port=DB_PORT
            )
            
            # Получаем и удаляем истекшие роли
            expired_users = await conn.fetch(
                """
                DELETE FROM users 
                WHERE expires_at IS NOT NULL 
                AND expires_at < NOW() 
                RETURNING user_id, user_role, username
                """
            )
            
            if expired_users:
                for user in expired_users:
                    logger.info(
                        f"Удалена истекшая роль {user['user_role']} "
                        f"у пользователя {user['username']} (ID: {user['user_id']})"
                    )
            
        except Exception as e:
            logger.error(f"Ошибка при очистке истекших ролей: {e}")
        finally:
            if 'conn' in locals():
                await conn.close()
        
        # Проверяем каждый час
        await asyncio.sleep(3600) 