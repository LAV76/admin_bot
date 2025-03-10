import asyncio
import os
import sys
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(str(Path(__file__).parent.parent))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('migration_generator')

def generate_empty_revision(message: str, head: str = "base") -> bool:
    """
    Генерирует пустую миграцию (revision) с указанным сообщением
    
    Args:
        message: Сообщение для миграции
        head: Родительская ревизия (по умолчанию 'base' для первой миграции)
        
    Returns:
        bool: True если успешно, False в случае ошибки
    """
    try:
        # Формируем дату в формате YYYY_MM_DD_HHMM
        date_prefix = datetime.now().strftime("%Y_%m_%d_%H%M")
        
        # Формируем команду для alembic
        cmd = [
            sys.executable, 
            "-m", 
            "alembic", 
            "revision", 
            "-m", 
            message,
            "--head", 
            head
        ]
        
        logger.info(f"Запуск команды: {' '.join(cmd)}")
        
        # Запускаем процесс
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Получаем вывод
        stdout, stderr = process.communicate()
        
        # Проверяем код возврата
        if process.returncode != 0:
            logger.error(f"Ошибка при создании миграции: {stderr}")
            return False
        
        logger.info(f"Миграция успешно создана: {stdout}")
        
        # Находим id созданной миграции
        if "Generating" in stdout:
            lines = stdout.strip().split("\n")
            for line in lines:
                if "migrations/versions/" in line:
                    revision_path = line.split("/")[-1]
                    revision_id = revision_path.split("_")[0]
                    logger.info(f"Идентификатор ревизии: {revision_id}")
                    
                    # Переименовываем файл миграции для добавления префикса даты
                    versions_dir = Path(__file__).parent.parent / "migrations" / "versions"
                    for file in versions_dir.glob(f"*{revision_id}*.py"):
                        new_name = f"{date_prefix}-{file.name}"
                        file.rename(versions_dir / new_name)
                        logger.info(f"Файл миграции переименован: {new_name}")
        
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при генерации миграции: {e}")
        return False


def main():
    """Основная функция для запуска из командной строки"""
    if len(sys.argv) < 2:
        logger.error("Не указано сообщение для миграции")
        print(f"Использование: python -m scripts.{Path(__file__).stem} <message> [head]")
        return 1
    
    message = sys.argv[1]
    head = sys.argv[2] if len(sys.argv) > 2 else "base"
    
    success = generate_empty_revision(message, head)
    return 0 if success else 1


if __name__ == "__main__":
    result = main()
    sys.exit(result) 