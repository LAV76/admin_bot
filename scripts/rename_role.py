import asyncio
import os
import sys
import logging
import argparse
from dotenv import load_dotenv

# Устанавливаем рабочую директорию в корень проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('rename_role')

# Импортируем необходимые модули
from app.db.session import get_session
from app.db.models.users import UserRole, RoleAudit
from sqlalchemy import select, update

async def rename_role(old_role_name: str, new_role_name: str, dry_run: bool = False):
    """
    Переименовывает роль в базе данных
    
    Args:
        old_role_name: Старое название роли
        new_role_name: Новое название роли
        dry_run: Если True, только показывает изменения без применения
    """
    # Загружаем переменные окружения
    load_dotenv()
    
    try:
        logger.info(f"Начало процесса переименования роли '{old_role_name}' в '{new_role_name}'")
        
        async with get_session() as session:
            # Проверяем существование старой роли
            stmt = select(UserRole).where(UserRole.role_type == old_role_name)
            result = await session.execute(stmt)
            old_roles = result.scalars().all()
            
            if not old_roles:
                logger.warning(f"Роль '{old_role_name}' не найдена в базе данных")
                return
            
            logger.info(f"Найдено {len(old_roles)} записей с ролью '{old_role_name}'")
            
            # Проверяем, существует ли уже новая роль для тех же пользователей
            user_ids = [role.user_id for role in old_roles]
            
            # Если не сухой запуск, выполняем обновление
            if not dry_run:
                # Обновляем записи в таблице user_roles
                stmt = update(UserRole).where(
                    UserRole.role_type == old_role_name
                ).values(role_type=new_role_name)
                
                result = await session.execute(stmt)
                affected_rows = result.rowcount
                
                logger.info(f"Обновлено {affected_rows} записей в таблице user_roles")
                
                # Обновляем записи в таблице аудита
                stmt = update(RoleAudit).where(
                    RoleAudit.role_type == old_role_name
                ).values(role_type=new_role_name)
                
                result = await session.execute(stmt)
                affected_audit_rows = result.rowcount
                
                logger.info(f"Обновлено {affected_audit_rows} записей в таблице аудита")
                
                # Фиксируем изменения
                await session.commit()
                logger.info(f"Изменения успешно сохранены в базе данных")
            else:
                logger.info(f"Сухой запуск: изменения не были применены")
                for role in old_roles:
                    logger.info(f"Будет переименована роль для пользователя {role.user_id}: {old_role_name} -> {new_role_name}")
        
        logger.info(f"Процесс переименования роли успешно завершен")
        
    except Exception as e:
        logger.error(f"Ошибка при переименовании роли: {e}", exc_info=True)

def main():
    """Основная функция для запуска скрипта"""
    parser = argparse.ArgumentParser(description='Переименование ролей в базе данных')
    parser.add_argument('old_role', help='Старое название роли')
    parser.add_argument('new_role', help='Новое название роли')
    parser.add_argument('--dry-run', action='store_true', help='Сухой запуск без применения изменений')
    
    args = parser.parse_args()
    
    # Запускаем асинхронную функцию
    asyncio.run(rename_role(args.old_role, args.new_role, args.dry_run))

if __name__ == "__main__":
    main() 