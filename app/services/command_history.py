"""
Модуль для управления историей команд пользователя.

Предоставляет функциональность для:
- Записи истории команд пользователей
- Получения истории команд конкретного пользователя
- Получения наиболее популярных команд
- Анализа использования команд
- Экспорта истории команд в различные форматы
"""

import asyncio
import logging
import json
import functools
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta, timezone
from pathlib import Path
import csv
from io import StringIO

from app.core.logging import setup_logger
from app.core.config import config
from app.database.engine import get_pool
from app.models.roles import RoleModel
from app.services.access_control import get_access_control
from app.db.session import get_session
from app.core.exceptions import DatabaseError

logger = setup_logger("command_history")


class CommandHistory:
    """
    Класс для управления историей команд пользователя.
    
    Сохраняет историю команд пользователей в базе данных для:
    - Аналитики использования бота
    - Отладки ошибок
    - Обнаружения попыток взлома или злоупотребления ботом
    
    Реализует паттерн Singleton для обеспечения единственного экземпляра.
    """
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(CommandHistory, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Инициализация класса CommandHistory.
        Создает кеш и проверяет наличие необходимых таблиц в базе данных.
        """
        if not self._initialized:
            self._cache = {}
            asyncio.create_task(self._ensure_tables_exist())
            self._initialized = True
    
    async def _ensure_tables_exist(self) -> None:
        """
        Создает необходимые таблицы в базе данных, если они не существуют.
        """
        pool = await get_pool()
        
        # Создаем таблицу истории команд, если она еще не существует
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS command_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    command TEXT NOT NULL,
                    args TEXT NULL,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    success BOOLEAN NOT NULL DEFAULT TRUE,
                    error_message TEXT NULL,
                    execution_time DOUBLE PRECISION NULL,
                    chat_id BIGINT NULL,
                    message_id BIGINT NULL
                )
            """)
            
            # Создаем индексы для оптимизации запросов
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS command_history_user_id_idx
                ON command_history (user_id)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS command_history_command_idx
                ON command_history (command)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS command_history_timestamp_idx
                ON command_history (timestamp)
            """)
        
        logger.info("Таблица истории команд проверена и готова к использованию")
    
    async def log_command(
        self,
        user_id: int,
        command: str,
        args: Optional[Dict[str, Any]] = None,
        chat_id: Optional[int] = None,
        message_id: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        execution_time: Optional[float] = None
    ) -> int:
        """
        Записывает команду в историю.
        
        Args:
            user_id: ID пользователя, выполнившего команду
            command: Имя команды
            args: Аргументы команды
            chat_id: ID чата, в котором была вызвана команда
            message_id: ID сообщения с командой
            success: Успешно ли выполнилась команда
            error_message: Сообщение об ошибке, если команда не выполнилась
            execution_time: Время выполнения команды в секундах
            
        Returns:
            int: ID записи в истории
        """
        # Ждем завершения создания таблиц
        await self._create_tables_task
        
        # Преобразуем аргументы в JSON строку
        args_json = json.dumps(args, ensure_ascii=False) if args else None
        
        # Записываем в базу данных
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchrow("""
                INSERT INTO command_history 
                (user_id, command, args, chat_id, message_id, success, error_message, execution_time)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """, user_id, command, args_json, chat_id, message_id, success, error_message, execution_time)
            
            record_id = result['id']
        
        # Сбрасываем кэш аналитики, так как данные изменились
        async with self._lock:
            self._analytics_cache = {}
        
        logger.debug(
            f"Команда '{command}' от пользователя {user_id} записана в историю: "
            f"success={success}, id={record_id}"
        )
        
        return record_id
    
    async def get_user_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        commands: Optional[List[str]] = None,
        success: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает историю команд пользователя.
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество записей
            offset: Смещение для пагинации
            start_date: Начальная дата фильтрации
            end_date: Конечная дата фильтрации
            commands: Список команд для фильтрации
            success: Фильтр по успешности выполнения
            
        Returns:
            List[Dict[str, Any]]: Список записей истории
        """
        # Ждем завершения создания таблиц
        await self._create_tables_task
        
        # Формируем базовый SQL запрос
        sql = """
            SELECT 
                id, user_id, command, args, timestamp, 
                success, error_message, execution_time,
                chat_id, message_id
            FROM command_history
            WHERE user_id = $1
        """
        
        # Параметры запроса
        params = [user_id]
        param_index = 2
        
        # Добавляем фильтры в запрос
        if start_date:
            sql += f" AND timestamp >= ${param_index}"
            params.append(start_date)
            param_index += 1
        
        if end_date:
            sql += f" AND timestamp <= ${param_index}"
            params.append(end_date)
            param_index += 1
        
        if commands:
            placeholders = ", ".join([f"${i}" for i in range(param_index, param_index + len(commands))])
            sql += f" AND command IN ({placeholders})"
            params.extend(commands)
            param_index += len(commands)
        
        if success is not None:
            sql += f" AND success = ${param_index}"
            params.append(success)
            param_index += 1
        
        # Добавляем сортировку и пагинацию
        sql += f" ORDER BY timestamp DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.extend([limit, offset])
        
        # Выполняем запрос
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
        
        # Преобразуем результаты
        result = []
        for row in rows:
            # Преобразуем аргументы из JSON обратно в словарь
            args = json.loads(row['args']) if row['args'] else None
            
            result.append({
                'id': row['id'],
                'user_id': row['user_id'],
                'command': row['command'],
                'args': args,
                'timestamp': row['timestamp'],
                'success': row['success'],
                'error_message': row['error_message'],
                'execution_time': row['execution_time'],
                'chat_id': row['chat_id'],
                'message_id': row['message_id']
            })
        
        return result
    
    async def get_popular_commands(
        self,
        days: int = 30,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Получает список наиболее популярных команд.
        
        Args:
            days: Количество дней для анализа
            limit: Максимальное количество команд в результате
            
        Returns:
            List[Dict[str, Any]]: Список популярных команд с их статистикой
        """
        # Используем кэш, если данные уже были получены
        cache_key = f'popular_commands_{days}_{limit}'
        async with self._lock:
            if cache_key in self._analytics_cache:
                cache_entry = self._analytics_cache[cache_key]
                # Проверяем, не устарел ли кэш (5 минут)
                if datetime.now(timezone.utc) - cache_entry['timestamp'] < timedelta(minutes=5):
                    return cache_entry['data']
        
        # Ждем завершения создания таблиц
        await self._create_tables_task
        
        # Вычисляем дату начала периода
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Выполняем запрос
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    command,
                    COUNT(*) as total_count,
                    SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) as success_count,
                    COUNT(DISTINCT user_id) as unique_users,
                    AVG(execution_time) as avg_execution_time
                FROM command_history
                WHERE timestamp >= $1
                GROUP BY command
                ORDER BY total_count DESC
                LIMIT $2
            """, start_date, limit)
        
        # Преобразуем результаты
        result = []
        for row in rows:
            result.append({
                'command': row['command'],
                'total_count': row['total_count'],
                'success_count': row['success_count'],
                'error_count': row['total_count'] - row['success_count'],
                'success_rate': float(row['success_count']) / row['total_count'] if row['total_count'] > 0 else 0,
                'unique_users': row['unique_users'],
                'avg_execution_time': row['avg_execution_time']
            })
        
        # Сохраняем результат в кэше
        async with self._lock:
            self._analytics_cache[cache_key] = {
                'timestamp': datetime.now(timezone.utc),
                'data': result
            }
        
        return result
    
    async def get_command_usage_by_time(
        self,
        days: int = 7,
        interval: str = 'day'
    ) -> List[Dict[str, Any]]:
        """
        Получает статистику использования команд по времени.
        
        Args:
            days: Количество дней для анализа
            interval: Интервал группировки ('hour', 'day', 'week', 'month')
            
        Returns:
            List[Dict[str, Any]]: Статистика использования команд по времени
        """
        # Используем кэш, если данные уже были получены
        cache_key = f'usage_by_time_{days}_{interval}'
        async with self._lock:
            if cache_key in self._analytics_cache:
                cache_entry = self._analytics_cache[cache_key]
                # Проверяем, не устарел ли кэш (5 минут)
                if datetime.now(timezone.utc) - cache_entry['timestamp'] < timedelta(minutes=5):
                    return cache_entry['data']
        
        # Ждем завершения создания таблиц
        await self._create_tables_task
        
        # Вычисляем дату начала периода
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Определяем формат времени в зависимости от интервала
        time_format = {
            'hour': "YYYY-MM-DD HH24:00",
            'day': "YYYY-MM-DD",
            'week': "YYYY-IW",
            'month': "YYYY-MM"
        }.get(interval, "YYYY-MM-DD")
        
        # Выполняем запрос
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT 
                    TO_CHAR(timestamp, '{time_format}') as time_period,
                    command,
                    COUNT(*) as count
                FROM command_history
                WHERE timestamp >= $1
                GROUP BY time_period, command
                ORDER BY time_period, count DESC
            """, start_date)
        
        # Преобразуем результаты в структурированный формат
        periods = {}
        commands = set()
        
        for row in rows:
            period = row['time_period']
            command = row['command']
            count = row['count']
            
            if period not in periods:
                periods[period] = {}
            
            periods[period][command] = count
            commands.add(command)
        
        # Формируем итоговый результат
        result = []
        
        # Сортируем периоды
        sorted_periods = sorted(periods.keys())
        
        for period in sorted_periods:
            period_data = {'period': period}
            
            for command in commands:
                period_data[command] = periods[period].get(command, 0)
            
            # Добавляем общую сумму
            period_data['total'] = sum(periods[period].values())
            
            result.append(period_data)
        
        # Сохраняем результат в кэше
        async with self._lock:
            self._analytics_cache[cache_key] = {
                'timestamp': datetime.now(timezone.utc),
                'data': result
            }
        
        return result
    
    async def get_user_command_stats(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Получает статистику использования команд конкретным пользователем.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Dict[str, Any]: Статистика использования команд пользователем
        """
        # Ждем завершения создания таблиц
        await self._create_tables_task
        
        # Выполняем запрос
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Общая статистика
            total_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_commands,
                    COUNT(DISTINCT command) as unique_commands,
                    SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) as success_count,
                    MIN(timestamp) as first_command,
                    MAX(timestamp) as last_command,
                    AVG(execution_time) as avg_execution_time
                FROM command_history
                WHERE user_id = $1
            """, user_id)
            
            # Популярные команды пользователя
            popular_commands = await conn.fetch("""
                SELECT 
                    command,
                    COUNT(*) as count,
                    SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) as success_count
                FROM command_history
                WHERE user_id = $1
                GROUP BY command
                ORDER BY count DESC
                LIMIT 5
            """, user_id)
            
            # Статистика по дням недели
            weekday_stats = await conn.fetch("""
                SELECT 
                    EXTRACT(DOW FROM timestamp) as weekday,
                    COUNT(*) as count
                FROM command_history
                WHERE user_id = $1
                GROUP BY weekday
                ORDER BY weekday
            """, user_id)
            
            # Статистика по часам
            hour_stats = await conn.fetch("""
                SELECT 
                    EXTRACT(HOUR FROM timestamp) as hour,
                    COUNT(*) as count
                FROM command_history
                WHERE user_id = $1
                GROUP BY hour
                ORDER BY hour
            """, user_id)
        
        # Преобразуем результаты
        total_days = 0
        if total_stats['first_command'] and total_stats['last_command']:
            delta = total_stats['last_command'] - total_stats['first_command']
            total_days = delta.days + 1
        
        result = {
            'total_commands': total_stats['total_commands'],
            'unique_commands': total_stats['unique_commands'],
            'success_rate': (total_stats['success_count'] / total_stats['total_commands'] 
                            if total_stats['total_commands'] > 0 else 0),
            'first_command': total_stats['first_command'],
            'last_command': total_stats['last_command'],
            'days_active': total_days,
            'avg_commands_per_day': (total_stats['total_commands'] / total_days 
                                    if total_days > 0 else 0),
            'avg_execution_time': total_stats['avg_execution_time'],
            'popular_commands': [
                {
                    'command': row['command'],
                    'count': row['count'],
                    'success_rate': (row['success_count'] / row['count'] 
                                    if row['count'] > 0 else 0)
                }
                for row in popular_commands
            ],
            'weekday_stats': {
                row['weekday']: row['count'] for row in weekday_stats
            },
            'hour_stats': {
                row['hour']: row['count'] for row in hour_stats
            }
        }
        
        return result
    
    async def delete_user_history(self, user_id: int, admin_id: int) -> int:
        """
        Удаляет историю команд пользователя.
        
        Args:
            user_id: ID пользователя, историю которого удаляем
            admin_id: ID администратора, выполняющего операцию
            
        Returns:
            int: Количество удаленных записей
        """
        try:
            # Проверяем права администратора
            ac = await get_access_control()
            is_admin = await ac.check_user_role(admin_id, "admin")
            
            if not is_admin:
                logger.warning(f"Пользователь {admin_id} пытается удалить историю без прав администратора")
                return 0
            
            # Удаляем записи
            async with get_session() as session:
                query = text("""
                    DELETE FROM command_history
                    WHERE user_id = :user_id
                    RETURNING id
                """)
                
                result = await session.execute(query, {"user_id": user_id})
                deleted_ids = result.fetchall()
                await session.commit()
                
                count = len(deleted_ids)
                logger.info(f"Удалено {count} записей из истории пользователя {user_id}")
                return count
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при удалении истории команд пользователя {user_id}: {e}")
            return 0
    
    async def export_history_csv(
        self,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        admin_id: int = None
    ) -> Tuple[str, StringIO]:
        """
        Экспортирует историю команд в формат CSV.
        
        Args:
            user_id: ID пользователя (если None, то экспортируется история всех пользователей)
            start_date: Начальная дата диапазона (если None, то не ограничивается)
            end_date: Конечная дата диапазона (если None, то не ограничивается)
            admin_id: ID администратора, выполняющего экспорт
            
        Returns:
            Tuple[str, StringIO]: Имя файла и содержимое CSV
        """
        try:
            # Проверяем права доступа, если указан admin_id
            if admin_id:
                ac = await get_access_control()
                is_admin = await ac.check_user_role(admin_id, "admin")
                
                if not is_admin:
                    logger.warning(f"Пользователь {admin_id} пытается экспортировать историю без прав администратора")
                    raise PermissionError("Недостаточно прав для экспорта истории")
            
            # Формируем параметры запроса
            params = {}
            where_clauses = []
            
            if user_id:
                where_clauses.append("user_id = :user_id")
                params["user_id"] = user_id
                
            if start_date:
                where_clauses.append("created_at >= :start_date")
                params["start_date"] = start_date
                
            if end_date:
                where_clauses.append("created_at <= :end_date")
                params["end_date"] = end_date
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            # Выполняем запрос
            async with get_session() as session:
                query = text(f"""
                    SELECT 
                        id,
                        user_id,
                        command,
                        args,
                        chat_id,
                        message_id,
                        success,
                        error_message,
                        execution_time,
                        created_at
                    FROM command_history
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                """)
                
                result = await session.execute(query, params)
                records = result.fetchall()
            
            # Создаем CSV файл
            output = StringIO()
            
            # Записываем заголовок
            output.write("ID,User ID,Command,Arguments,Chat ID,Message ID,Success,Error Message,Execution Time (ms),Timestamp\n")
            
            # Записываем данные
            for record in records:
                id, user_id, command, args, chat_id, message_id, success, error_message, execution_time, created_at = record
                
                # Форматируем аргументы
                args_str = json.dumps(args) if args else ""
                args_str = args_str.replace('"', '""')  # Экранируем кавычки для CSV
                
                # Форматируем сообщение об ошибке
                error_msg = error_message.replace('"', '""') if error_message else ""
                
                # Форматируем время выполнения
                exec_time = f"{execution_time:.2f}" if execution_time is not None else ""
                
                # Записываем строку
                output.write(f'{id},{user_id},"{command}","{args_str}",{chat_id or ""},')
                output.write(f'{message_id or ""},{"1" if success else "0"},"{error_msg}",{exec_time},"{created_at}"\n')
            
            # Сбрасываем указатель на начало файла
            output.seek(0)
            
            # Формируем имя файла
            if user_id:
                filename = f"command_history_user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            else:
                filename = f"command_history_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            return filename, output
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при экспорте истории команд: {e}")
            raise DatabaseError(f"Ошибка при экспорте истории: {e}")
    
    async def clean_old_history(
        self,
        days: int = 90,
        admin_id: int = None
    ) -> int:
        """
        Очищает старую историю команд.
        
        Args:
            days: Количество дней, за которые сохранять историю (остальное удаляется)
            admin_id: ID администратора, выполняющего операцию
            
        Returns:
            int: Количество удаленных записей
        """
        try:
            # Проверяем права администратора, если указан
            if admin_id:
                ac = await get_access_control()
                is_admin = await ac.check_user_role(admin_id, "admin")
                
                if not is_admin:
                    logger.warning(f"Пользователь {admin_id} пытается очистить историю без прав администратора")
                    return 0
            
            # Вычисляем дату, старше которой нужно удалить записи
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Выполняем удаление
            async with get_session() as session:
                query = text("""
                    DELETE FROM command_history
                    WHERE created_at < :cutoff_date
                    RETURNING id
                """)
                
                result = await session.execute(query, {"cutoff_date": cutoff_date})
                deleted_ids = result.fetchall()
                await session.commit()
                
                count = len(deleted_ids)
                logger.info(f"Удалено {count} старых записей из истории команд")
                return count
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при очистке старой истории команд: {e}")
            return 0

    async def get_user_activity(
        self,
        days: int = 7,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение данных об активных пользователях за указанный период.
        
        Args:
            days: Количество дней для анализа
            start_date: Начальная дата периода (если указана, days игнорируется)
            end_date: Конечная дата периода (если не указана, используется текущая дата)
            
        Returns:
            Список словарей с информацией об активных пользователях
        """
        pool = await get_pool()
        
        # Определяем период
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        
        query = """
        SELECT 
            user_id,
            COUNT(*) as command_count
        FROM 
            command_history
        WHERE 
            timestamp BETWEEN $1 AND $2
        GROUP BY 
            user_id
        ORDER BY 
            command_count DESC
        """
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, start_date, end_date)
            
            result = []
            for row in rows:
                result.append({
                    "user_id": row["user_id"],
                    "command_count": row["command_count"]
                })
            
            return result

    async def get_success_rate(
        self,
        days: int = 7,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Получение данных об успешности выполнения команд за указанный период.
        
        Args:
            days: Количество дней для анализа
            start_date: Начальная дата периода (если указана, days игнорируется)
            end_date: Конечная дата периода (если не указана, используется текущая дата)
            
        Returns:
            Словарь с информацией об успешности выполнения команд
        """
        pool = await get_pool()
        
        # Определяем период
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        
        query = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN success = true THEN 1 ELSE 0 END) as success_count
        FROM 
            command_history
        WHERE 
            timestamp BETWEEN $1 AND $2
        """
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, start_date, end_date)
            
            total = row["total"] if row["total"] else 0
            success_count = row["success_count"] if row["success_count"] else 0
            
            success_rate = success_count / total if total > 0 else 0
            
            return {
                "total": total,
                "success_count": success_count,
                "success_rate": success_rate
            }

    async def get_average_execution_time(
        self,
        days: int = 7,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Получение данных о среднем времени выполнения команд за указанный период.
        
        Args:
            days: Количество дней для анализа
            start_date: Начальная дата периода (если указана, days игнорируется)
            end_date: Конечная дата периода (если не указана, используется текущая дата)
            
        Returns:
            Словарь с информацией о среднем времени выполнения команд
        """
        pool = await get_pool()
        
        # Определяем период
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        
        query = """
        SELECT 
            AVG(execution_time) as avg_time,
            MIN(execution_time) as min_time,
            MAX(execution_time) as max_time
        FROM 
            command_history
        WHERE 
            timestamp BETWEEN $1 AND $2
            AND execution_time IS NOT NULL
        """
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, start_date, end_date)
            
            return {
                "avg_time": row["avg_time"] if row["avg_time"] else 0,
                "min_time": row["min_time"] if row["min_time"] else 0,
                "max_time": row["max_time"] if row["max_time"] else 0
            }

    async def get_commands_detailed(
        self,
        days: int = 7,
        limit: int = 10,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение детальной информации о командах за указанный период.
        
        Args:
            days: Количество дней для анализа
            limit: Максимальное количество команд для возврата
            start_date: Начальная дата периода (если указана, days игнорируется)
            end_date: Конечная дата периода (если не указана, используется текущая дата)
            
        Returns:
            Список словарей с детальной информацией о командах
        """
        pool = await get_pool()
        
        # Определяем период
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        
        query = """
        WITH command_stats AS (
            SELECT 
                command,
                COUNT(*) as count,
                AVG(CASE WHEN success = true THEN 1.0 ELSE 0.0 END) as success_rate,
                SUM(CASE WHEN success = false THEN 1 ELSE 0 END) as error_count,
                AVG(execution_time) as avg_time,
                COUNT(DISTINCT user_id) as unique_users
            FROM 
                command_history
            WHERE 
                timestamp BETWEEN $1 AND $2
            GROUP BY 
                command
            ORDER BY 
                count DESC
            LIMIT $3
        )
        SELECT * FROM command_stats
        """
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, start_date, end_date, limit)
            
            result = []
            for row in rows:
                result.append({
                    "command": row["command"],
                    "count": row["count"],
                    "success_rate": row["success_rate"],
                    "error_count": row["error_count"],
                    "avg_time": row["avg_time"] if row["avg_time"] else 0,
                    "unique_users": row["unique_users"]
                })
            
            return result

    async def get_active_users(
        self,
        days: int = 7,
        limit: int = 20,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение информации об активных пользователях за указанный период.
        
        Args:
            days: Количество дней для анализа
            limit: Максимальное количество пользователей для возврата
            start_date: Начальная дата периода (если указана, days игнорируется)
            end_date: Конечная дата периода (если не указана, используется текущая дата)
            
        Returns:
            Список словарей с информацией об активных пользователях
        """
        pool = await get_pool()
        
        # Определяем период
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        
        query = """
        WITH user_stats AS (
            SELECT 
                user_id,
                COUNT(*) as command_count,
                AVG(CASE WHEN success = true THEN 1.0 ELSE 0.0 END) as success_rate,
                AVG(execution_time) as avg_time,
                MAX(timestamp) as last_active
            FROM 
                command_history
            WHERE 
                timestamp BETWEEN $1 AND $2
            GROUP BY 
                user_id
            ORDER BY 
                command_count DESC
            LIMIT $3
        ),
        user_commands AS (
            SELECT 
                user_id,
                command,
                COUNT(*) as cmd_count
            FROM 
                command_history
            WHERE 
                timestamp BETWEEN $1 AND $2
                AND user_id IN (SELECT user_id FROM user_stats)
            GROUP BY 
                user_id, command
        ),
        top_commands AS (
            SELECT 
                user_id,
                array_agg(command ORDER BY cmd_count DESC) FILTER (WHERE command IS NOT NULL) as commands
            FROM (
                SELECT 
                    user_id,
                    command,
                    cmd_count,
                    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY cmd_count DESC) as rn
                FROM 
                    user_commands
            ) t
            WHERE rn <= 3
            GROUP BY user_id
        )
        SELECT 
            us.user_id,
            us.command_count,
            us.success_rate,
            us.avg_time,
            us.last_active,
            tc.commands as top_commands
        FROM 
            user_stats us
        LEFT JOIN 
            top_commands tc ON us.user_id = tc.user_id
        ORDER BY 
            us.command_count DESC
        """
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, start_date, end_date, limit)
            
            result = []
            for row in rows:
                result.append({
                    "user_id": row["user_id"],
                    "command_count": row["command_count"],
                    "success_rate": row["success_rate"],
                    "avg_time": row["avg_time"] if row["avg_time"] else 0,
                    "last_active": row["last_active"],
                    "top_commands": row["top_commands"] if row["top_commands"] else []
                })
            
            return result

    async def get_user_activity_by_time(
        self,
        days: int = 7,
        interval: str = 'day',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение данных об активности пользователей по времени.
        
        Args:
            days: Количество дней для анализа
            interval: Интервал группировки (hour, day, week, month, total)
            start_date: Начальная дата периода (если указана, days игнорируется)
            end_date: Конечная дата периода (если не указана, используется текущая дата)
            
        Returns:
            Список словарей с информацией об активности пользователей по времени
        """
        pool = await get_pool()
        
        # Определяем период
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        
        # Определяем формат группировки по времени
        if interval == 'hour':
            time_format = "date_trunc('hour', timestamp)"
        elif interval == 'day':
            time_format = "date_trunc('day', timestamp)"
        elif interval == 'week':
            time_format = "date_trunc('week', timestamp)"
        elif interval == 'month':
            time_format = "date_trunc('month', timestamp)"
        elif interval == 'total':
            time_format = "NULL"
        else:
            time_format = "date_trunc('day', timestamp)"
        
        query = f"""
        SELECT 
            {time_format} as timestamp,
            COUNT(DISTINCT user_id) as count
        FROM 
            command_history
        WHERE 
            timestamp BETWEEN $1 AND $2
        GROUP BY 
            {time_format}
        ORDER BY 
            timestamp
        """
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, start_date, end_date)
            
            result = []
            for row in rows:
                result.append({
                    "timestamp": row["timestamp"] if row["timestamp"] else end_date,
                    "count": row["count"]
                })
            
            return result

    async def get_user_command_stats_by_command(
        self,
        user_id: int,
        days: int = 7,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение статистики использования команд конкретным пользователем.
        
        Args:
            user_id: ID пользователя
            days: Количество дней для анализа
            start_date: Начальная дата периода (если указана, days игнорируется)
            end_date: Конечная дата периода (если не указана, используется текущая дата)
            
        Returns:
            Список словарей со статистикой использования команд
        """
        pool = await get_pool()
        
        # Определяем период
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        
        query = """
        SELECT 
            command,
            COUNT(*) as count,
            AVG(CASE WHEN success = true THEN 1.0 ELSE 0.0 END) as success_rate,
            AVG(execution_time) as avg_time
        FROM 
            command_history
        WHERE 
            user_id = $1
            AND timestamp BETWEEN $2 AND $3
        GROUP BY 
            command
        ORDER BY 
            count DESC
        """
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, user_id, start_date, end_date)
            
            result = []
            for row in rows:
                result.append({
                    "command": row["command"],
                    "count": row["count"],
                    "success_rate": row["success_rate"],
                    "avg_time": row["avg_time"] if row["avg_time"] else 0
                })
            
            return result


# Создаем синглтон для истории команд
command_history = CommandHistory()


# Декоратор для логирования команд
def log_command(command_name: str):
    """
    Декоратор для логирования выполнения команд.
    
    Args:
        command_name: Имя команды
        
    Returns:
        Callable: Декоратор для функции
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update, *args, **kwargs):
            # Получаем информацию о пользователе
            user_id = None
            chat_id = None
            message_id = None
            
            if hasattr(update, 'from_user') and update.from_user:
                user_id = update.from_user.id
            elif hasattr(update, 'message') and hasattr(update.message, 'from_user'):
                user_id = update.message.from_user.id
            
            if hasattr(update, 'chat') and update.chat:
                chat_id = update.chat.id
            elif hasattr(update, 'message') and hasattr(update.message, 'chat'):
                chat_id = update.message.chat.id
            
            if hasattr(update, 'message_id'):
                message_id = update.message_id
            elif hasattr(update, 'message') and hasattr(update.message, 'message_id'):
                message_id = update.message.message_id
            
            # Извлекаем аргументы команды
            args_dict = {}
            if hasattr(update, 'text') and update.text:
                text_parts = update.text.split()
                if len(text_parts) > 1:
                    args_dict['args'] = text_parts[1:]
            
            # Записываем начало выполнения
            start_time = datetime.now(timezone.utc)
            
            # Выполняем команду
            success = True
            error_message = None
            try:
                result = await func(update, *args, **kwargs)
            except Exception as e:
                success = False
                error_message = str(e)
                logger.exception(f"Ошибка при выполнении команды {command_name}: {e}")
                raise
            finally:
                # Вычисляем время выполнения
                end_time = datetime.now(timezone.utc)
                execution_time = (end_time - start_time).total_seconds()
                
                # Логируем команду
                try:
                    await command_history.log_command(
                        user_id=user_id,
                        command=command_name,
                        args=args_dict,
                        chat_id=chat_id,
                        message_id=message_id,
                        success=success,
                        error_message=error_message,
                        execution_time=execution_time
                    )
                except Exception as log_error:
                    logger.error(f"Не удалось записать команду в историю: {log_error}")
            
            return result
        
        return wrapper
    
    return decorator 