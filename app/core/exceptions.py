"""
Модуль содержит иерархию исключений приложения.

Определяет стандартизованные исключения, которые могут использоваться
по всему приложению для единообразной обработки ошибок.
"""
from typing import Optional, Any, Dict


class BotException(Exception):
    """Базовый класс для всех исключений бота.
    
    Предоставляет общую базовую функциональность для всех исключений
    приложения, включая хранение сообщения об ошибке и дополнительных данных.
    
    Attributes:
        message: Сообщение об ошибке.
        details: Дополнительные данные об ошибке (опционально).
    """
    
    def __init__(
        self, 
        message: str = "Произошла ошибка",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Инициализирует исключение.
        
        Args:
            message: Сообщение об ошибке.
            details: Словарь с дополнительной информацией об ошибке.
        """
        self.message: str = message
        self.details: Optional[Dict[str, Any]] = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """Возвращает строковое представление исключения.
        
        Returns:
            Строка с сообщением об ошибке.
        """
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message


class DatabaseError(BotException):
    """Исключение, связанное с ошибками базы данных.
    
    Возникает при проблемах с подключением к БД, выполнением запросов,
    нарушением целостности данных и т.д.
    """
    
    def __init__(
        self, 
        message: str = "Ошибка базы данных",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Инициализирует исключение.
        
        Args:
            message: Описание ошибки базы данных.
            details: Дополнительные данные об ошибке.
        """
        super().__init__(message, details)


class UserNotFoundError(BotException):
    """Исключение, когда пользователь не найден в системе.
    
    Возникает при попытке получить доступ к несуществующему пользователю.
    """
    
    def __init__(
        self, 
        user_id: Optional[int] = None,
        message: str = "Пользователь не найден",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Инициализирует исключение.
        
        Args:
            user_id: ID пользователя, который не был найден (опционально).
            message: Сообщение об ошибке.
            details: Дополнительные данные об ошибке.
        """
        if user_id is not None:
            message = f"Пользователь с ID {user_id} не найден"
            if not details:
                details = {}
            details["user_id"] = user_id
        
        super().__init__(message, details)


class RoleNotFoundError(BotException):
    """Исключение, когда роль не найдена в системе.
    
    Возникает при попытке получить доступ к несуществующей роли.
    """
    
    def __init__(
        self, 
        role_type: Optional[str] = None,
        message: str = "Роль не найдена",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Инициализирует исключение.
        
        Args:
            role_type: Название роли, которая не была найдена (опционально).
            message: Сообщение об ошибке.
            details: Дополнительные данные об ошибке.
        """
        if role_type is not None:
            message = f"Роль {role_type} не найдена"
            if not details:
                details = {}
            details["role_type"] = role_type
        
        super().__init__(message, details)


class PermissionDeniedError(BotException):
    """Исключение, когда у пользователя нет прав на действие.
    
    Возникает при попытке выполнить операцию, для которой
    у пользователя недостаточно прав.
    """
    
    def __init__(
        self, 
        user_id: Optional[int] = None,
        required_permission: Optional[str] = None,
        message: str = "Недостаточно прав для выполнения действия",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Инициализирует исключение.
        
        Args:
            user_id: ID пользователя, которому отказано в доступе (опционально).
            required_permission: Требуемое разрешение (опционально).
            message: Сообщение об ошибке.
            details: Дополнительные данные об ошибке.
        """
        if user_id is not None or required_permission is not None:
            if not details:
                details = {}
            
            if user_id is not None:
                details["user_id"] = user_id
            
            if required_permission is not None:
                details["required_permission"] = required_permission
                message = f"Недостаточно прав для выполнения действия. Требуется: {required_permission}"
        
        super().__init__(message, details)


class ConfigurationError(BotException):
    """Исключение, связанное с ошибками конфигурации.
    
    Возникает при проблемах с настройками или параметрами приложения.
    """
    
    def __init__(
        self, 
        config_key: Optional[str] = None,
        message: str = "Ошибка конфигурации",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Инициализирует исключение.
        
        Args:
            config_key: Ключ конфигурации, вызвавший проблему (опционально).
            message: Сообщение об ошибке.
            details: Дополнительные данные об ошибке.
        """
        if config_key is not None:
            message = f"Ошибка конфигурации для параметра '{config_key}'"
            if not details:
                details = {}
            details["config_key"] = config_key
        
        super().__init__(message, details)


class ValidationError(BotException):
    """Исключение, связанное с проверкой данных.
    
    Возникает при ошибках валидации пользовательского ввода, данных из БД и т.д.
    """
    
    def __init__(
        self, 
        field: Optional[str] = None,
        message: str = "Ошибка валидации данных",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Инициализирует исключение.
        
        Args:
            field: Поле, в котором произошла ошибка валидации (опционально).
            message: Сообщение об ошибке.
            details: Дополнительные данные об ошибке.
        """
        if field is not None:
            message = f"Ошибка валидации данных в поле '{field}'"
            if not details:
                details = {}
            details["field"] = field
        
        super().__init__(message, details)


class ExternalServiceError(BotException):
    """Исключение, связанное с внешними сервисами.
    
    Возникает при проблемах взаимодействия с API, внешними сервисами и т.д.
    """
    
    def __init__(
        self, 
        service_name: Optional[str] = None,
        message: str = "Ошибка внешнего сервиса",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Инициализирует исключение.
        
        Args:
            service_name: Название внешнего сервиса (опционально).
            message: Сообщение об ошибке.
            details: Дополнительные данные об ошибке.
        """
        if service_name is not None:
            message = f"Ошибка взаимодействия с сервисом '{service_name}'"
            if not details:
                details = {}
            details["service_name"] = service_name
        
        super().__init__(message, details) 