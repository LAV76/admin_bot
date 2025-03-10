"""
Сервис для управления резервными копиями базы данных.

Предоставляет функционал для:
- создания резервных копий базы данных
- восстановления из резервных копий
- получения списка доступных резервных копий
- удаления старых резервных копий
"""
import asyncio
import logging
import os
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.core.logging import setup_logger

logger = setup_logger("backup_service")


class BackupService:
    """
    Сервис для управления резервными копиями базы данных.
    
    Позволяет создавать резервные копии PostgreSQL, восстанавливать
    из них и управлять хранилищем копий.
    """
    
    def __init__(self):
        """Инициализирует сервис резервного копирования."""
        # Настройка директории для хранения резервных копий
        self.backup_dir = Path(settings.BACKUPS_DIR)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    async def create_backup(self, admin_id: Optional[int] = None) -> str:
        """
        Создает резервную копию базы данных.
        
        Args:
            admin_id: ID администратора, выполняющего резервное копирование
            
        Returns:
            str: Имя файла созданной резервной копии
            
        Raises:
            RuntimeError: Если создание резервной копии не удалось
        """
        try:
            # Форматируем имя файла с датой и временем
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            admin_suffix = f"_admin{admin_id}" if admin_id else ""
            backup_filename = f"backup_{timestamp}{admin_suffix}.sql"
            backup_path = self.backup_dir / backup_filename
            
            # Получаем параметры подключения
            db_params = {
                "host": settings.DB_HOST,
                "port": settings.DB_PORT,
                "username": settings.DB_USER,
                "password": settings.DB_PASS,
                "dbname": settings.DB_NAME
            }
            
            # Формируем команду pg_dump
            pg_dump_cmd = [
                "pg_dump",
                f"--host={db_params['host']}",
                f"--port={db_params['port']}",
                f"--username={db_params['username']}",
                "--format=c",  # Сжатый формат
                f"--file={backup_path}",
                db_params['dbname']
            ]
            
            # Создаем среду с паролем для pg_dump
            env = os.environ.copy()
            env["PGPASSWORD"] = db_params["password"]
            
            logger.info(f"Создание резервной копии базы данных {db_params['dbname']}...")
            
            # Запускаем pg_dump как внешний процесс
            process = await asyncio.create_subprocess_exec(
                *pg_dump_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Неизвестная ошибка"
                logger.error(
                    f"Ошибка при создании резервной копии: {error_msg}"
                )
                raise RuntimeError(f"Не удалось создать резервную копию: {error_msg}")
            
            logger.info(f"Резервная копия успешно создана: {backup_filename}")
            return backup_filename
            
        except Exception as e:
            error_msg = f"Ошибка при создании резервной копии: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    async def restore_backup(
        self, 
        backup_filename: str, 
        admin_id: Optional[int] = None
    ) -> bool:
        """
        Восстанавливает базу данных из резервной копии.
        
        Args:
            backup_filename: Имя файла резервной копии
            admin_id: ID администратора, выполняющего восстановление
            
        Returns:
            bool: True, если восстановление успешно
            
        Raises:
            FileNotFoundError: Если файл резервной копии не найден
            RuntimeError: Если восстановление не удалось
        """
        try:
            backup_path = self.backup_dir / backup_filename
            
            # Проверяем существование файла
            if not backup_path.exists():
                error_msg = f"Файл резервной копии не найден: {backup_filename}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            # Получаем параметры подключения
            db_params = {
                "host": settings.DB_HOST,
                "port": settings.DB_PORT,
                "username": settings.DB_USER,
                "password": settings.DB_PASS,
                "dbname": settings.DB_NAME
            }
            
            # Создаем временную метку для создания резервной копии перед восстановлением
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pre_restore_backup = f"pre_restore_{timestamp}.sql"
            pre_restore_path = self.backup_dir / pre_restore_backup
            
            # Сначала создаем резервную копию текущего состояния БД
            logger.info("Создание резервной копии текущего состояния перед восстановлением...")
            await self.create_backup(admin_id)
            
            # Формируем команду pg_restore
            pg_restore_cmd = [
                "pg_restore",
                f"--host={db_params['host']}",
                f"--port={db_params['port']}",
                f"--username={db_params['username']}",
                "--clean",  # Очищает БД перед восстановлением
                "--if-exists",  # Использует IF EXISTS при удалении объектов
                f"--dbname={db_params['dbname']}",
                str(backup_path)
            ]
            
            # Создаем среду с паролем для pg_restore
            env = os.environ.copy()
            env["PGPASSWORD"] = db_params["password"]
            
            logger.info(f"Восстановление базы данных из копии {backup_filename}...")
            
            # Запускаем pg_restore как внешний процесс
            process = await asyncio.create_subprocess_exec(
                *pg_restore_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            # Проверяем код возврата (0 - успех, не 0 - ошибка)
            if process.returncode != 0:
                # pg_restore может выдавать предупреждения, но при этом успешно восстанавливать данные
                # Поэтому проверяем вывод на наличие критических ошибок
                stderr_text = stderr.decode() if stderr else ""
                if "error:" in stderr_text.lower():
                    error_msg = f"Ошибка при восстановлении из резервной копии: {stderr_text}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                else:
                    # Если есть предупреждения, но не критические ошибки
                    logger.warning(
                        f"Восстановление выполнено с предупреждениями: {stderr_text}"
                    )
            
            logger.info(f"База данных успешно восстановлена из копии {backup_filename}")
            return True
            
        except FileNotFoundError as e:
            raise e
        except Exception as e:
            error_msg = f"Ошибка при восстановлении из резервной копии: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    async def get_available_backups(self) -> List[Dict[str, Any]]:
        """
        Получает список доступных резервных копий.
        
        Returns:
            List[Dict[str, Any]]: Список информации о резервных копиях
        """
        try:
            backup_files = []
            
            # Перебираем все файлы в директории с резервными копиями
            for file_path in self.backup_dir.glob("backup_*.sql"):
                # Получаем дату создания файла из файловой системы
                created_at = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                # Получаем размер файла в МБ
                size_bytes = file_path.stat().st_size
                size_mb = round(size_bytes / (1024 * 1024), 2)
                
                # Пытаемся извлечь ID администратора из имени файла
                admin_id = None
                filename = file_path.name
                if "_admin" in filename:
                    try:
                        admin_part = filename.split("_admin")[1].split(".")[0]
                        admin_id = int(admin_part)
                    except (ValueError, IndexError):
                        pass
                
                # Добавляем информацию о резервной копии
                backup_files.append({
                    "filename": file_path.name,
                    "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "size_mb": size_mb,
                    "admin_id": admin_id
                })
            
            # Сортируем копии по дате создания (новые сначала)
            backup_files.sort(key=lambda x: x["created_at"], reverse=True)
            
            return backup_files
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка резервных копий: {str(e)}")
            return []
    
    async def delete_backup(self, backup_filename: str) -> bool:
        """
        Удаляет указанную резервную копию.
        
        Args:
            backup_filename: Имя файла резервной копии
            
        Returns:
            bool: True, если удаление успешно
            
        Raises:
            FileNotFoundError: Если файл резервной копии не найден
        """
        try:
            backup_path = self.backup_dir / backup_filename
            
            # Проверяем существование файла
            if not backup_path.exists():
                error_msg = f"Файл резервной копии не найден: {backup_filename}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            # Удаляем файл
            backup_path.unlink()
            logger.info(f"Резервная копия {backup_filename} успешно удалена")
            return True
            
        except FileNotFoundError as e:
            raise e
        except Exception as e:
            logger.error(f"Ошибка при удалении резервной копии: {str(e)}")
            return False
    
    async def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        Удаляет старые резервные копии, оставляя указанное количество новейших.
        
        Args:
            keep_count: Количество копий, которые нужно сохранить
            
        Returns:
            int: Количество удаленных копий
        """
        try:
            # Получаем список всех резервных копий
            backup_files = await self.get_available_backups()
            
            # Если количество копий меньше или равно keep_count, ничего не делаем
            if len(backup_files) <= keep_count:
                logger.info(
                    f"Нет необходимости удалять старые копии. "
                    f"Текущее количество: {len(backup_files)}, "
                    f"Лимит: {keep_count}"
                )
                return 0
            
            # Выбираем копии для удаления (самые старые)
            to_delete = backup_files[keep_count:]
            deleted_count = 0
            
            # Удаляем выбранные копии
            for backup in to_delete:
                try:
                    await self.delete_backup(backup["filename"])
                    deleted_count += 1
                except Exception as e:
                    logger.warning(
                        f"Не удалось удалить копию {backup['filename']}: {str(e)}"
                    )
            
            logger.info(
                f"Очистка старых резервных копий завершена. "
                f"Удалено: {deleted_count}, Сохранено: {keep_count}"
            )
            return deleted_count
            
        except Exception as e:
            logger.error(f"Ошибка при очистке старых резервных копий: {str(e)}")
            return 0


# Создаем экземпляр сервиса для удобного импорта
backup_service = BackupService()


async def create_backup(admin_id: Optional[int] = None) -> str:
    """
    Создает резервную копию базы данных.
    
    Args:
        admin_id: ID администратора, выполняющего резервное копирование
        
    Returns:
        str: Имя файла созданной резервной копии
    """
    return await backup_service.create_backup(admin_id)


async def restore_backup(
    backup_filename: str, 
    admin_id: Optional[int] = None
) -> bool:
    """
    Восстанавливает базу данных из резервной копии.
    
    Args:
        backup_filename: Имя файла резервной копии
        admin_id: ID администратора, выполняющего восстановление
        
    Returns:
        bool: True, если восстановление успешно
    """
    return await backup_service.restore_backup(backup_filename, admin_id)


async def get_available_backups() -> List[Dict[str, Any]]:
    """
    Получает список доступных резервных копий.
    
    Returns:
        List[Dict[str, Any]]: Список информации о резервных копиях
    """
    return await backup_service.get_available_backups()


async def delete_backup(backup_filename: str) -> bool:
    """
    Удаляет указанную резервную копию.
    
    Args:
        backup_filename: Имя файла резервной копии
        
    Returns:
        bool: True, если удаление успешно
    """
    return await backup_service.delete_backup(backup_filename)


async def cleanup_old_backups(keep_count: int = 10) -> int:
    """
    Удаляет старые резервные копии, оставляя указанное количество новейших.
    
    Args:
        keep_count: Количество копий, которые нужно сохранить
        
    Returns:
        int: Количество удаленных копий
    """
    return await backup_service.cleanup_old_backups(keep_count) 