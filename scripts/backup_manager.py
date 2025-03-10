#!/usr/bin/env python3
"""
Скрипт для управления резервными копиями базы данных из командной строки.

Возможности:
- Создание резервной копии базы данных
- Восстановление базы данных из резервной копии
- Просмотр списка доступных резервных копий
- Удаление старых резервных копий
- Очистка устаревших резервных копий

Использование:
    python backup_manager.py create [--admin-id ADMIN_ID]
    python backup_manager.py restore BACKUP_NAME [--admin-id ADMIN_ID]
    python backup_manager.py list
    python backup_manager.py delete BACKUP_NAME
    python backup_manager.py cleanup [--keep N]
"""

import asyncio
import argparse
import sys
from typing import List, Optional
from pathlib import Path
from datetime import datetime

# Добавляем родительский каталог в sys.path для импорта приложения
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import setup_logger
from app.core.config import load_config
from scripts.backup_service import (
    create_backup,
    restore_backup,
    get_available_backups,
    delete_backup,
    cleanup_old_backups,
)

logger = setup_logger("backup_manager")

# Загружаем конфигурацию приложения
config = load_config()


async def cmd_create_backup(admin_id: Optional[int] = None) -> None:
    """
    Создает резервную копию базы данных
    
    Args:
        admin_id: ID администратора, выполняющего операцию
    """
    try:
        backup_path = await create_backup(admin_id)
        print(f"✅ Резервная копия успешно создана: {backup_path}")
    except Exception as e:
        print(f"❌ Ошибка при создании резервной копии: {e}")
        logger.error(f"Ошибка при создании резервной копии: {e}")
        sys.exit(1)


async def cmd_restore_backup(
    backup_name: str,
    admin_id: Optional[int] = None
) -> None:
    """
    Восстанавливает базу данных из резервной копии
    
    Args:
        backup_name: Имя файла резервной копии
        admin_id: ID администратора, выполняющего операцию
    """
    try:
        success = await restore_backup(backup_name, admin_id)
        if success:
            print(f"✅ База данных успешно восстановлена из резервной копии: {backup_name}")
        else:
            print("❌ Не удалось восстановить базу данных")
            sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Резервная копия не найдена: {backup_name}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при восстановлении из резервной копии: {e}")
        logger.error(f"Ошибка при восстановлении из резервной копии: {e}")
        sys.exit(1)


async def cmd_list_backups() -> None:
    """
    Выводит список доступных резервных копий
    """
    try:
        backups = await get_available_backups()
        
        if not backups:
            print("📂 Резервные копии не найдены")
            return
        
        print(f"📂 Найдено резервных копий: {len(backups)}")
        print("=" * 80)
        print(f"{'Имя файла':<40} {'Размер':<10} {'Дата создания':<20} {'Админ ID':<10}")
        print("-" * 80)
        
        for backup in backups:
            created_at = datetime.fromtimestamp(backup["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
            size_mb = f"{backup['size'] / (1024 * 1024):.2f} МБ"
            admin_id = backup.get("admin_id", "Н/Д")
            
            print(f"{backup['filename']:<40} {size_mb:<10} {created_at:<20} {admin_id:<10}")
        
        print("=" * 80)
    except Exception as e:
        print(f"❌ Ошибка при получении списка резервных копий: {e}")
        logger.error(f"Ошибка при получении списка резервных копий: {e}")
        sys.exit(1)


async def cmd_delete_backup(backup_name: str) -> None:
    """
    Удаляет указанную резервную копию
    
    Args:
        backup_name: Имя файла резервной копии
    """
    try:
        success = await delete_backup(backup_name)
        if success:
            print(f"✅ Резервная копия успешно удалена: {backup_name}")
        else:
            print(f"❌ Не удалось удалить резервную копию: {backup_name}")
            sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Резервная копия не найдена: {backup_name}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при удалении резервной копии: {e}")
        logger.error(f"Ошибка при удалении резервной копии: {e}")
        sys.exit(1)


async def cmd_cleanup_backups(keep: int = 5) -> None:
    """
    Очищает старые резервные копии, оставляя указанное количество
    
    Args:
        keep: Количество сохраняемых последних копий
    """
    try:
        deleted_count = await cleanup_old_backups(keep)
        if deleted_count > 0:
            print(f"✅ Удалено старых резервных копий: {deleted_count}")
        else:
            print("ℹ️ Нет резервных копий для удаления")
    except Exception as e:
        print(f"❌ Ошибка при очистке старых резервных копий: {e}")
        logger.error(f"Ошибка при очистке старых резервных копий: {e}")
        sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """
    Разбирает аргументы командной строки
    
    Returns:
        argparse.Namespace: Объект с аргументами командной строки
    """
    parser = argparse.ArgumentParser(
        description="Управление резервными копиями базы данных"
    )
    
    # Создаем подпарсеры для различных команд
    subparsers = parser.add_subparsers(dest="command", help="Команда для выполнения")
    
    # Команда create
    create_parser = subparsers.add_parser(
        "create", help="Создать резервную копию базы данных"
    )
    create_parser.add_argument(
        "--admin-id", 
        type=int, 
        help="ID администратора, выполняющего операцию"
    )
    
    # Команда restore
    restore_parser = subparsers.add_parser(
        "restore", help="Восстановить базу данных из резервной копии"
    )
    restore_parser.add_argument(
        "backup_name", 
        help="Имя файла резервной копии"
    )
    restore_parser.add_argument(
        "--admin-id", 
        type=int, 
        help="ID администратора, выполняющего операцию"
    )
    
    # Команда list
    subparsers.add_parser("list", help="Вывести список доступных резервных копий")
    
    # Команда delete
    delete_parser = subparsers.add_parser(
        "delete", help="Удалить указанную резервную копию"
    )
    delete_parser.add_argument(
        "backup_name", 
        help="Имя файла резервной копии"
    )
    
    # Команда cleanup
    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Очистить старые резервные копии"
    )
    cleanup_parser.add_argument(
        "--keep",
        type=int,
        default=5,
        help="Количество сохраняемых последних копий (по умолчанию: 5)"
    )
    
    return parser.parse_args()


async def main() -> None:
    """
    Основная функция скрипта
    """
    args = parse_arguments()
    
    if args.command == "create":
        await cmd_create_backup(args.admin_id)
    elif args.command == "restore":
        await cmd_restore_backup(args.backup_name, args.admin_id)
    elif args.command == "list":
        await cmd_list_backups()
    elif args.command == "delete":
        await cmd_delete_backup(args.backup_name)
    elif args.command == "cleanup":
        await cmd_cleanup_backups(args.keep)
    else:
        print("❌ Не указана команда")
        print("Используйте: python backup_manager.py [create|restore|list|delete|cleanup]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 