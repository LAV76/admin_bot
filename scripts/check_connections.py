#!/usr/bin/env python
"""
Скрипт для диагностики соединений бота.
Проверяет подключение к Telegram API и базе данных.
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("connection_checker")

# Загрузка переменных окружения
load_dotenv()

async def check_telegram_api():
    """Проверяет подключение к Telegram API."""
    try:
        import aiohttp
        
        api_token = os.getenv("API_TOKEN")
        if not api_token:
            logger.error("API_TOKEN не найден в переменных окружения")
            return False
            
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{api_token}/getMe"
            logger.info(f"Проверка подключения к Telegram API: {url}")
            
            async with session.get(url) as response:
                result = await response.json()
                
                if response.status == 200 and result.get("ok"):
                    bot_info = result.get("result", {})
                    logger.info(f"Успешное подключение к боту: @{bot_info.get('username')} (ID: {bot_info.get('id')})")
                    return True
                else:
                    logger.error(f"Ошибка подключения к Telegram API: {result}")
                    return False
    except Exception as e:
        logger.error(f"Ошибка при проверке Telegram API: {e}")
        return False

async def check_database():
    """Проверяет подключение к базе данных."""
    try:
        import asyncpg
        
        db_user = os.getenv("DB_USER")
        db_pass = os.getenv("DB_PASS")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("DB_NAME")
        
        if not all([db_user, db_pass, db_host, db_port, db_name]):
            logger.error("Не найдены все необходимые параметры подключения к БД")
            missing = [
                name for name, value in {
                    "DB_USER": db_user, 
                    "DB_PASS": db_pass, 
                    "DB_HOST": db_host, 
                    "DB_PORT": db_port, 
                    "DB_NAME": db_name
                }.items() if not value
            ]
            logger.error(f"Отсутствуют параметры: {', '.join(missing)}")
            return False
        
        conn_string = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        logger.info(f"Проверка подключения к БД: {db_host}:{db_port}/{db_name}")
        
        # Скрываем пароль в выводе
        safe_conn_string = conn_string.replace(db_pass, "*****")
        logger.info(f"Строка подключения: {safe_conn_string}")
        
        conn = await asyncpg.connect(conn_string)
        
        # Проверка версии PostgreSQL
        version = await conn.fetchval("SELECT version();")
        logger.info(f"Успешное подключение к БД. Версия PostgreSQL: {version}")
        
        # Проверка существования таблиц
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
        )
        logger.info(f"Найдено таблиц в БД: {len(tables)}")
        for table in tables:
            logger.info(f"  - {table['table_name']}")
        
        await conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при проверке подключения к БД: {e}")
        return False

async def check_env_variables():
    """Проверяет наличие всех необходимых переменных окружения."""
    required_vars = [
        "API_TOKEN", "ADMIN_ID", "CHANNEL_ID", 
        "DB_USER", "DB_PASS", "DB_HOST", "DB_PORT", "DB_NAME"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Отсутствуют следующие переменные окружения: {', '.join(missing_vars)}")
        return False
    
    logger.info("Все необходимые переменные окружения найдены")
    
    # Проверка формата переменных
    try:
        admin_id = int(os.getenv("ADMIN_ID"))
        logger.info(f"ADMIN_ID = {admin_id}")
    except (ValueError, TypeError):
        logger.error(f"ADMIN_ID должен быть целым числом. Текущее значение: {os.getenv('ADMIN_ID')}")
    
    channel_id = os.getenv("CHANNEL_ID")
    logger.info(f"CHANNEL_ID = {channel_id}")
    
    return True

async def main():
    """Основная функция проверки всех соединений."""
    logger.info("Начало проверки подключений")
    
    # Проверка переменных окружения
    logger.info("=== Проверка переменных окружения ===")
    env_ok = await check_env_variables()
    
    # Проверка подключения к Telegram API
    logger.info("\n=== Проверка подключения к Telegram API ===")
    api_ok = await check_telegram_api()
    
    # Проверка подключения к базе данных
    logger.info("\n=== Проверка подключения к базе данных ===")
    db_ok = await check_database()
    
    # Итоговый статус
    logger.info("\n=== Итоги проверки ===")
    logger.info(f"Переменные окружения: {'✅ OK' if env_ok else '❌ ОШИБКА'}")
    logger.info(f"Подключение к Telegram API: {'✅ OK' if api_ok else '❌ ОШИБКА'}")
    logger.info(f"Подключение к базе данных: {'✅ OK' if db_ok else '❌ ОШИБКА'}")
    
    if all([env_ok, api_ok, db_ok]):
        logger.info("✅ Все проверки пройдены успешно. Бот должен работать корректно.")
        return 0
    else:
        logger.error("❌ Обнаружены проблемы, требующие исправления.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 