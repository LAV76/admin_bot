import os
import asyncio
import datetime
import json
import shutil
from typing import Dict, List, Optional, Any
import asyncpg
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import setup_logger
from app.core.exceptions import DatabaseError, PermissionDeniedError
from app.db.engine import get_db_session
from app.db.models.users import User, UserRole, RoleAudit
from app.services.role_service import RoleService

logger = setup_logger("services.database")

class DatabaseService:
    """
    Сервис для работы с базой данных
    """
    
    def __init__(self):
        self.role_service = RoleService()
        self.backup_dir = os.path.join(os.getcwd(), "backups")
        
        # Создаем директорию для резервных копий, если она не существует
        os.makedirs(self.backup_dir, exist_ok=True)
    
    async def create_backup(self, admin_id: int) -> str:
        """
        Создание резервной копии базы данных
        
        Args:
            admin_id: ID администратора, выполняющего действие
            
        Returns:
            str: Имя файла резервной копии
            
        Raises:
            PermissionDeniedError: Если у пользователя нет прав администратора
            DatabaseError: Если произошла ошибка при создании резервной копии
        """
        # Проверяем права администратора
        is_admin = await self.role_service.check_user_role(admin_id, "admin")
        if not is_admin:
            logger.warning(f"Пользователь {admin_id} пытается создать резервную копию без прав администратора")
            raise PermissionDeniedError("Недостаточно прав для создания резервной копии")
        
        try:
            # Формируем имя файла резервной копии
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"backup_{timestamp}.json"
            backup_path = os.path.join(self.backup_dir, backup_file)
            
            # Подключаемся к базе данных напрямую через asyncpg
            conn = await asyncpg.connect(
                user=settings.DB_USER,
                password=settings.DB_PASS,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME
            )
            
            try:
                # Получаем данные из таблиц
                users = await conn.fetch("SELECT * FROM users")
                user_roles = await conn.fetch("SELECT * FROM user_roles")
                role_audit = await conn.fetch("SELECT * FROM role_audit")
                
                # Преобразуем данные в словари
                users_data = [dict(user) for user in users]
                user_roles_data = [dict(role) for role in user_roles]
                role_audit_data = [dict(audit) for audit in role_audit]
                
                # Преобразуем datetime в строки
                for user in users_data:
                    if "created_at" in user:
                        user["created_at"] = user["created_at"].isoformat()
                    if "updated_at" in user:
                        user["updated_at"] = user["updated_at"].isoformat()
                
                for role in user_roles_data:
                    if "created_at" in role:
                        role["created_at"] = role["created_at"].isoformat()
                
                for audit in role_audit_data:
                    if "performed_at" in audit:
                        audit["performed_at"] = audit["performed_at"].isoformat()
                
                # Формируем данные для резервной копии
                backup_data = {
                    "metadata": {
                        "created_at": datetime.datetime.now().isoformat(),
                        "created_by": admin_id,
                        "db_version": "1.0"
                    },
                    "tables": {
                        "users": users_data,
                        "user_roles": user_roles_data,
                        "role_audit": role_audit_data
                    }
                }
                
                # Сохраняем данные в файл
                with open(backup_path, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Создана резервная копия базы данных: {backup_file}")
                return backup_file
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Ошибка при создании резервной копии: {e}")
            raise DatabaseError(f"Ошибка при создании резервной копии: {e}")
    
    async def restore_backup(self, backup_file: str, admin_id: int) -> bool:
        """
        Восстановление базы данных из резервной копии
        
        Args:
            backup_file: Имя файла резервной копии
            admin_id: ID администратора, выполняющего действие
            
        Returns:
            bool: True, если восстановление успешно выполнено
            
        Raises:
            PermissionDeniedError: Если у пользователя нет прав администратора
            DatabaseError: Если произошла ошибка при восстановлении
        """
        # Проверяем права администратора
        is_admin = await self.role_service.check_user_role(admin_id, "admin")
        if not is_admin:
            logger.warning(f"Пользователь {admin_id} пытается восстановить базу без прав администратора")
            raise PermissionDeniedError("Недостаточно прав для восстановления базы данных")
        
        try:
            # Формируем путь к файлу резервной копии
            backup_path = os.path.join(self.backup_dir, backup_file)
            
            # Проверяем существование файла
            if not os.path.exists(backup_path):
                logger.error(f"Файл резервной копии не найден: {backup_path}")
                raise DatabaseError(f"Файл резервной копии не найден: {backup_file}")
            
            # Загружаем данные из файла
            with open(backup_path, "r", encoding="utf-8") as f:
                backup_data = json.load(f)
            
            # Подключаемся к базе данных напрямую через asyncpg
            conn = await asyncpg.connect(
                user=settings.DB_USER,
                password=settings.DB_PASS,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME
            )
            
            try:
                # Начинаем транзакцию
                async with conn.transaction():
                    # Очищаем таблицы
                    await conn.execute("DELETE FROM role_audit")
                    await conn.execute("DELETE FROM user_roles")
                    await conn.execute("DELETE FROM users")
                    
                    # Восстанавливаем данные пользователей
                    for user in backup_data["tables"]["users"]:
                        columns = ", ".join(user.keys())
                        placeholders = ", ".join(f"${i+1}" for i in range(len(user)))
                        values = list(user.values())
                        
                        await conn.execute(
                            f"INSERT INTO users ({columns}) VALUES ({placeholders})",
                            *values
                        )
                    
                    # Восстанавливаем данные ролей
                    for role in backup_data["tables"]["user_roles"]:
                        columns = ", ".join(role.keys())
                        placeholders = ", ".join(f"${i+1}" for i in range(len(role)))
                        values = list(role.values())
                        
                        await conn.execute(
                            f"INSERT INTO user_roles ({columns}) VALUES ({placeholders})",
                            *values
                        )
                    
                    # Восстанавливаем данные аудита
                    for audit in backup_data["tables"]["role_audit"]:
                        columns = ", ".join(audit.keys())
                        placeholders = ", ".join(f"${i+1}" for i in range(len(audit)))
                        values = list(audit.values())
                        
                        await conn.execute(
                            f"INSERT INTO role_audit ({columns}) VALUES ({placeholders})",
                            *values
                        )
                
                logger.info(f"База данных успешно восстановлена из резервной копии: {backup_file}")
                return True
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Ошибка при восстановлении базы данных: {e}")
            raise DatabaseError(f"Ошибка при восстановлении базы данных: {e}")
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """
        Получение статистики базы данных
        
        Returns:
            Dict[str, Any]: Статистика базы данных
        """
        try:
            async with get_db_session() as db:
                # Получаем количество пользователей
                users_count = await db.execute(select(func.count()).select_from(User))
                users_count = users_count.scalar_one()
                
                # Получаем количество ролей
                roles_count = await db.execute(select(func.count()).select_from(UserRole))
                roles_count = roles_count.scalar_one()
                
                # Получаем количество записей аудита
                audit_count = await db.execute(select(func.count()).select_from(RoleAudit))
                audit_count = audit_count.scalar_one()
                
                # Получаем статистику по ролям
                role_stats_query = select(
                    UserRole.role_type, 
                    func.count().label("count")
                ).group_by(UserRole.role_type)
                
                role_stats_result = await db.execute(role_stats_query)
                role_stats = {row[0]: row[1] for row in role_stats_result}
                
                # Получаем последние изменения
                last_changes_query = select(RoleAudit).order_by(
                    RoleAudit.performed_at.desc()
                ).limit(5)
                
                last_changes_result = await db.execute(last_changes_query)
                last_changes = last_changes_result.scalars().all()
                
                last_changes_data = []
                for change in last_changes:
                    last_changes_data.append({
                        "id": change.id,
                        "user_id": change.user_id,
                        "role_type": change.role_type,
                        "action": change.action,
                        "performed_by": change.performed_by,
                        "performed_at": change.performed_at.isoformat()
                    })
                
                # Формируем результат
                return {
                    "users_count": users_count,
                    "roles_count": roles_count,
                    "audit_count": audit_count,
                    "role_stats": role_stats,
                    "last_changes": last_changes_data,
                    "database_name": settings.DB_NAME,
                    "database_host": settings.DB_HOST,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Ошибка при получении статистики базы данных: {e}")
            raise DatabaseError(f"Ошибка при получении статистики базы данных: {e}")
    
    async def get_available_backups(self) -> List[Dict[str, Any]]:
        """
        Получение списка доступных резервных копий
        
        Returns:
            List[Dict[str, Any]]: Список резервных копий
        """
        try:
            backups = []
            
            # Получаем список файлов в директории резервных копий
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("backup_") and filename.endswith(".json"):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_stat = os.stat(file_path)
                    
                    # Получаем метаданные из файла
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            metadata = data.get("metadata", {})
                    except:
                        metadata = {}
                    
                    # Формируем информацию о резервной копии
                    backup_info = {
                        "filename": filename,
                        "size": file_stat.st_size,
                        "created_at": metadata.get("created_at", datetime.datetime.fromtimestamp(file_stat.st_mtime).isoformat()),
                        "created_by": metadata.get("created_by", "unknown"),
                        "db_version": metadata.get("db_version", "unknown"),
                        "tables": list(data.get("tables", {}).keys()) if "tables" in data else []
                    }
                    
                    backups.append(backup_info)
            
            # Сортируем по дате создания (от новых к старым)
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка резервных копий: {e}")
            raise DatabaseError(f"Ошибка при получении списка резервных копий: {e}")
    
    async def clear_role_history(self, admin_id: int) -> bool:
        """
        Очистка истории изменений ролей
        
        Args:
            admin_id: ID администратора, выполняющего действие
            
        Returns:
            bool: True, если очистка успешно выполнена
            
        Raises:
            PermissionDeniedError: Если у пользователя нет прав администратора
        """
        try:
            # Используем метод из RoleService
            deleted_count = await self.role_service.clear_role_history(admin_id)
            logger.info(f"Очищена история изменений ролей: удалено {deleted_count} записей")
            return True
        except PermissionDeniedError:
            raise
        except Exception as e:
            logger.error(f"Ошибка при очистке истории изменений ролей: {e}")
            raise DatabaseError(f"Ошибка при очистке истории изменений ролей: {e}") 