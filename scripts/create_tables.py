import asyncio
import sys
import logging
from utils.database_initializer import initialize_database

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    print("Инициализация базы данных и таблиц...")
    success = asyncio.run(initialize_database())
    
    if success:
        print("✅ База данных и таблицы успешно инициализированы")
    else:
        print("❌ Ошибка при инициализации базы данных")
        sys.exit(1) 