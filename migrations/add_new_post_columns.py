"""
Скрипт для добавления новых столбцов в таблицу posts
"""

import asyncio
import logging
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.db.session import async_session_maker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('db_migration')

async def add_columns():
    """Добавляет новые столбцы в таблицу posts, если их нет"""
    
    # Определяем столбцы, которые нужно добавить
    columns_to_add = [
        {
            "name": "change_username",
            "type": "VARCHAR(100)",
            "nullable": "NULL",
            "comment": "Имя пользователя, который последним редактировал пост"
        },
        {
            "name": "change_date",
            "type": "TIMESTAMP WITH TIME ZONE",
            "nullable": "NULL",
            "comment": "Дата и время последнего редактирования"
        },
        {
            "name": "is_archived",
            "type": "BOOLEAN",
            "nullable": "NOT NULL DEFAULT FALSE",
            "comment": "Флаг архивации поста"
        },
        {
            "name": "archived_at",
            "type": "TIMESTAMP WITH TIME ZONE",
            "nullable": "NULL",
            "comment": "Дата и время архивации поста"
        },
        {
            "name": "archived_by",
            "type": "BIGINT",
            "nullable": "NULL",
            "comment": "ID пользователя, который архивировал пост"
        },
        {
            "name": "message_id",
            "type": "BIGINT",
            "nullable": "NULL",
            "comment": "ID сообщения в Telegram после публикации"
        }
    ]
    
    async with async_session_maker() as session:
        for column in columns_to_add:
            # Проверяем, существует ли столбец
            try:
                query = text(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'posts' AND column_name = '{column['name']}'
                """)
                result = await session.execute(query)
                exists = result.scalar() is not None
                
                if not exists:
                    # Добавляем столбец, если его нет
                    add_column_query = text(f"""
                    ALTER TABLE posts 
                    ADD COLUMN {column['name']} {column['type']} {column['nullable']} 
                    """)
                    await session.execute(add_column_query)
                    
                    # Добавляем комментарий к столбцу
                    comment_query = text(f"""
                    COMMENT ON COLUMN posts.{column['name']} IS '{column['comment']}'
                    """)
                    await session.execute(comment_query)
                    
                    logger.info(f"Добавлен столбец {column['name']} в таблицу posts")
                else:
                    logger.info(f"Столбец {column['name']} уже существует в таблице posts")
            
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при добавлении столбца {column['name']}: {e}")
                await session.rollback()
                raise
        
        # Фиксируем транзакцию
        await session.commit()
        logger.info("Миграция успешно выполнена")

async def main():
    try:
        logger.info("Запуск миграции для добавления новых столбцов в таблицу posts")
        await add_columns()
        logger.info("Миграция успешно завершена")
    except Exception as e:
        logger.error(f"Ошибка при выполнении миграции: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 