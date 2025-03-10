from typing import Generic, TypeVar, Type, List, Optional, Any, Dict, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.sql.expression import Select
from sqlalchemy.sql import expression

from app.db.base import Base
from app.core.logging import setup_logger

# Типизация для моделей
ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """
    Базовый репозиторий для работы с моделями базы данных.
    Предоставляет общие методы для работы с базой данных и реализует паттерн Repository.
    
    Attributes:
        model_class: Класс модели, с которой работает репозиторий
        session: Асинхронная сессия SQLAlchemy
        logger: Логгер для репозитория
    """
    
    def __init__(self, model_class: Type[ModelType], session: AsyncSession = None):
        """
        Инициализация репозитория
        
        Args:
            model_class: Класс модели
            session: Асинхронная сессия SQLAlchemy (опционально)
        """
        self.model_class = model_class
        self.session = session
        self.logger = setup_logger(f"db.repositories.{model_class.__name__.lower()}")
    
    def set_session(self, session: AsyncSession) -> None:
        """
        Устанавливает сессию для репозитория
        
        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        self.session = session
    
    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        Получение записи по ID
        
        Args:
            id: ID записи
            
        Returns:
            Optional[ModelType]: Найденный объект или None
        """
        if not self.session:
            raise ValueError("Session is not set")
            
        stmt = select(self.model_class).where(self.model_class.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Получение всех записей с пагинацией
        
        Args:
            skip: Смещение
            limit: Лимит выборки
            
        Returns:
            List[ModelType]: Список объектов
        """
        if not self.session:
            raise ValueError("Session is not set")
            
        stmt = select(self.model_class).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def create(self, data: Dict[str, Any]) -> ModelType:
        """
        Создание новой записи
        
        Args:
            data: Данные для создания
            
        Returns:
            ModelType: Созданный объект
        """
        if not self.session:
            raise ValueError("Session is not set")
            
        obj = self.model_class(**data)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        self.logger.info(f"Создан объект {self.model_class.__name__}: {obj}")
        return obj
    
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[ModelType]:
        """
        Обновление записи
        
        Args:
            id: ID записи
            data: Новые данные
            
        Returns:
            Optional[ModelType]: Обновленный объект или None
        """
        if not self.session:
            raise ValueError("Session is not set")
            
        obj = await self.get_by_id(id)
        if obj is None:
            return None
            
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
            
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        self.logger.info(f"Обновлен объект {self.model_class.__name__} с ID {id}")
        return obj
    
    async def delete(self, id: int) -> bool:
        """
        Удаление записи
        
        Args:
            id: ID записи
            
        Returns:
            bool: True, если запись удалена
        """
        if not self.session:
            raise ValueError("Session is not set")
            
        obj = await self.get_by_id(id)
        if obj is None:
            return False
            
        await self.session.delete(obj)
        await self.session.commit()
        self.logger.info(f"Удален объект {self.model_class.__name__} с ID {id}")
        return True
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Подсчет количества записей
        
        Args:
            filters: Словарь с условиями фильтрации {имя_поля: значение}
            
        Returns:
            int: Количество записей
        """
        if not self.session:
            raise ValueError("Session is not set")
            
        query = select(func.count()).select_from(self.model_class)
        
        if filters:
            filter_conditions = []
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    filter_conditions.append(getattr(self.model_class, key) == value)
            
            if filter_conditions:
                query = query.where(and_(*filter_conditions))
                
        result = await self.session.execute(query)
        return result.scalar_one()
    
    async def filter_by(
        self, 
        filters: Dict[str, Any], 
        skip: int = 0, 
        limit: int = 100, 
        order_by: Optional[str] = None,
        desc: bool = False
    ) -> List[ModelType]:
        """
        Получение записей с фильтрацией и сортировкой
        
        Args:
            filters: Словарь с условиями фильтрации {имя_поля: значение}
            skip: Смещение
            limit: Лимит выборки
            order_by: Поле для сортировки
            desc: Сортировка по убыванию
            
        Returns:
            List[ModelType]: Список объектов
        """
        if not self.session:
            raise ValueError("Session is not set")
            
        query = select(self.model_class)
        
        # Добавляем условия фильтрации
        filter_conditions = []
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                filter_conditions.append(getattr(self.model_class, key) == value)
        
        if filter_conditions:
            query = query.where(and_(*filter_conditions))
        
        # Добавляем сортировку
        if order_by and hasattr(self.model_class, order_by):
            order_attr = getattr(self.model_class, order_by)
            if desc:
                query = query.order_by(order_attr.desc())
            else:
                query = query.order_by(order_attr)
        
        # Добавляем пагинацию
        query = query.offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def exists(self, filters: Dict[str, Any]) -> bool:
        """
        Проверка существования записи с указанными фильтрами
        
        Args:
            filters: Словарь с условиями фильтрации {имя_поля: значение}
            
        Returns:
            bool: True, если запись существует
        """
        if not self.session:
            raise ValueError("Session is not set")
            
        query = select(expression.exists().where(
            and_(*[getattr(self.model_class, key) == value for key, value in filters.items() if hasattr(self.model_class, key)])
        ))
        
        result = await self.session.execute(query)
        return result.scalar_one()
    
    async def get_or_create(self, filters: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None) -> tuple[ModelType, bool]:
        """
        Получение объекта, если он существует, или создание нового
        
        Args:
            filters: Словарь с условиями фильтрации {имя_поля: значение}
            defaults: Значения по умолчанию для новой записи
            
        Returns:
            tuple[ModelType, bool]: (объект, создан ли он)
        """
        if not self.session:
            raise ValueError("Session is not set")
            
        # Пытаемся найти объект
        query = select(self.model_class)
        
        filter_conditions = []
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                filter_conditions.append(getattr(self.model_class, key) == value)
        
        if filter_conditions:
            query = query.where(and_(*filter_conditions))
            
        result = await self.session.execute(query)
        obj = result.scalar_one_or_none()
        
        if obj:
            return obj, False
        
        # Создаем новый объект
        create_data = {**filters}
        if defaults:
            create_data.update(defaults)
            
        new_obj = await self.create(create_data)
        return new_obj, True 