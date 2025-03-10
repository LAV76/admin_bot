from typing import Generic, TypeVar, Type, List, Optional, Any, Dict, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.sql.expression import Select

from app.db.base import Base
from app.core.logging import setup_logger

# Типизация для моделей
ModelType = TypeVar("ModelType", bound=Base)

logger = setup_logger("db.repositories.base")

class BaseRepository(Generic[ModelType]):
    """
    Базовый репозиторий для работы с моделями
    
    Attributes:
        model_class: Класс модели, с которой работает репозиторий
    """
    
    def __init__(self, model_class: Type[ModelType]):
        self.model_class = model_class
    
    async def create(self, db: AsyncSession, obj_in: Dict[str, Any]) -> ModelType:
        """
        Создание новой записи
        
        Args:
            db: Сессия базы данных
            obj_in: Данные для создания объекта
            
        Returns:
            ModelType: Созданный объект
        """
        db_obj = self.model_class(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        logger.debug(f"Создан объект {self.model_class.__name__}: {db_obj}")
        return db_obj
    
    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        """
        Получение объекта по ID
        
        Args:
            db: Сессия базы данных
            id: ID объекта
            
        Returns:
            Optional[ModelType]: Найденный объект или None
        """
        statement = select(self.model_class).where(self.model_class.id == id)
        result = await db.execute(statement)
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        *, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[ModelType]:
        """
        Получение списка объектов с пагинацией
        
        Args:
            db: Сессия базы данных
            skip: Количество пропускаемых записей
            limit: Максимальное количество возвращаемых записей
            
        Returns:
            List[ModelType]: Список объектов
        """
        statement = select(self.model_class).offset(skip).limit(limit)
        result = await db.execute(statement)
        return result.scalars().all()
    
    async def update(
        self, 
        db: AsyncSession, 
        *, 
        db_obj: ModelType, 
        obj_in: Union[Dict[str, Any], ModelType]
    ) -> ModelType:
        """
        Обновление объекта
        
        Args:
            db: Сессия базы данных
            db_obj: Существующий объект
            obj_in: Данные для обновления
            
        Returns:
            ModelType: Обновленный объект
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.__dict__
            # Удаляем служебные атрибуты SQLAlchemy
            update_data = {k: v for k, v in update_data.items() if not k.startswith("_")}
        
        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        logger.debug(f"Обновлен объект {self.model_class.__name__}: {db_obj}")
        return db_obj
    
    async def delete(self, db: AsyncSession, *, id: int) -> bool:
        """
        Удаление объекта по ID
        
        Args:
            db: Сессия базы данных
            id: ID объекта
            
        Returns:
            bool: True, если объект был удален
        """
        statement = delete(self.model_class).where(self.model_class.id == id)
        result = await db.execute(statement)
        await db.commit()
        logger.debug(f"Удален объект {self.model_class.__name__} с ID: {id}")
        return result.rowcount > 0
    
    async def count(self, db: AsyncSession) -> int:
        """
        Подсчет количества записей
        
        Args:
            db: Сессия базы данных
            
        Returns:
            int: Количество записей
        """
        statement = select(func.count()).select_from(self.model_class)
        result = await db.execute(statement)
        return result.scalar_one() 