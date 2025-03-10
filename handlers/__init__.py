# Пустой файл для обозначения пакета

from aiogram import Dispatcher, Router
from utils.logger import setup_logger

# Импортируем все роутеры
from .common.start import router as start_router
from .common.help import router as help_router
from .admin.menu import router as menu_router
from .admin.posts import router as posts_router
from .admin.roles import router as roles_router
from .admin.settings import router as settings_router
from .admin.create_post import router as create_post_router
from .admin.manage_posts import router as manage_posts_router
from .admin.channels import router as channels_router

logger = setup_logger()

def register_all_handlers(dp: Dispatcher) -> None:
    """Регистрация всех обработчиков"""
    # Создаем основной роутер
    main_router = Router()
    
    # Список всех роутеров
    routers = [
        start_router,
        help_router,
        menu_router,
        posts_router,
        roles_router,
        settings_router,
        create_post_router,
        manage_posts_router,
        channels_router
    ]
    
    # Подключаем все роутеры к основному
    for router in routers:
        try:
            main_router.include_router(router)
            logger.debug(f"Зарегистрирован роутер: {router.__class__.__name__}")
        except RuntimeError as e:
            logger.warning(f"Ошибка при регистрации роутера: {e}")
    
    # Подключаем основной роутер к диспетчеру
    try:
        dp.include_router(main_router)
        logger.info("Все обработчики успешно зарегистрированы")
    except RuntimeError as e:
        logger.error(f"Ошибка при подключении основного роутера: {e}")

def setup_routers() -> Router:
    """
    Настройка и подключение всех роутеров
    
    Returns:
        Router: Основной роутер с подключенными дочерними роутерами
    """
    router = Router()
    
    # Подключаем общие обработчики
    router.include_router(start_router)
    router.include_router(help_router)
    
    # Подключаем обработчики для администраторов
    router.include_router(roles_router)
    router.include_router(menu_router)
    router.include_router(posts_router)
    router.include_router(settings_router)
    router.include_router(create_post_router)
    router.include_router(manage_posts_router)
    router.include_router(channels_router)
    
    return router
