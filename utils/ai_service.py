import os
import logging
from typing import Optional
import aiohttp
import asyncio
import json
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настраиваем логгер
logger = logging.getLogger("ai_service")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

class AIService:
    """Сервис для работы с AI для генерации контента"""
    
    def __init__(self):
        """Инициализация API ключа и клиента"""
        self.api_key = os.getenv("API_KEY")
        self.base_url = "https://api.sree.shop/v1/chat/completions"
        self.model = "gpt-4o"  # Можно настроить через параметры
        
        # Проверка наличия API ключа
        if not self.api_key:
            logger.warning("API_KEY не найден в переменных окружения!")
    
    async def generate_text(self, prompt: str, model: Optional[str] = None) -> str:
        """
        Генерирует текст с помощью AI модели через прямой HTTP запрос
        
        Args:
            prompt: Текст запроса для AI
            model: Название модели (если не указано, используется self.model)
            
        Returns:
            str: Сгенерированный текст
        """
        try:
            # Используем модель по умолчанию, если не указана другая
            model_to_use = model or self.model
            
            # Формируем данные запроса
            payload = {
                "model": model_to_use,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Отправка запроса к API с промтом длиной {len(prompt)} символов")
            
            # Выполняем асинхронный HTTP запрос
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=120  # Увеличенный таймаут для долгих запросов
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        generated_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        logger.info(f"Получен ответ от API длиной {len(generated_text)} символов")
                        return generated_text
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка API: статус {response.status}, ответ: {error_text}")
                        return f"Ошибка API: {response.status}"
            
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка HTTP при генерации текста: {e}", exc_info=True)
            return f"Ошибка соединения: {str(e)}"
        except asyncio.TimeoutError:
            logger.error("Превышен таймаут ожидания ответа от API", exc_info=True)
            return "Превышен таймаут ожидания ответа от API"
        except json.JSONDecodeError:
            logger.error("Ошибка декодирования JSON ответа", exc_info=True)
            return "Ошибка декодирования ответа от API"
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при генерации текста: {e}", exc_info=True)
            return f"Произошла ошибка при генерации текста: {str(e)}"
    
    async def generate_post_content(self, user_input: str) -> str:
        """
        Генерирует содержимое поста с определенным промтом
        
        Args:
            user_input: Текст от пользователя для генерации
            
        Returns:
            str: Сгенерированный текст поста
        """
        prompt = (
            "Ты — эксперт в копирайтинге и известный писатель. Твоя задача — написать текст для "
            "Telegram-канала не более 1000 знаков (включая пробелы), следуя рекомендациям из книги "
            "Максима Ильяхова «Пиши, сокращай» . Текст должен быть:\n\n"
            "Кратким и ёмким — убери лишние слова, оставь только суть.\n"
            "Легкодоступным — избегай сложных терминов, говори как с другом.\n"
            "Привлекательным — добавь эмоции, факты или интригу.\n"
            "Структурированным — используй подзаголовки, короткие абзацы, списки.\n"
            "С призывом к действию — подтолкни читателя к комментариям, подписке или переходу по ссылке.\n"
            "Пример темы: «Как перестать тратить время на рутину? 3 лайфхака, которые изменят ваш день» .\n\n"
            "Проверь текст на соответствие требованиям и уложись в лимит символов\n\n"
            f"Тема: {user_input}"
        )
        
        return await self.generate_text(prompt)
    
    async def generate_post_title(self, post_content: str) -> str:
        """
        Генерирует название поста на основе его содержимого
        
        Args:
            post_content: Содержимое поста
            
        Returns:
            str: Сгенерированное название
        """
        prompt = (
            "Ты — эксперт в копирайтинге и создании вирусных заголовков. Придумай название для "
            "Telegram-поста на основе текста ниже, следуя правилам:\n\n"
            "Коротко и ёмко — до 12 слов, упор на главную мысль.\n"
            "Эмоция и интрига — используй эмодзи, вопросы, цифры, «фишки» (например, «секреты», «лайфхаки»).\n"
            "Доступность — язык, как у разговора с другом (никакой академической сухости).\n"
            "Призыв к действию — намёк на пользу («успеть больше», «избежать ошибок»).\n"
            "Примеры структур:\n"
            "🔥 «Как перестать тратить время: 3 лайфхака для идеального дня»\n"
            "💡 «Знаете ли вы? Секреты гаджетов, которые экономят 5 часов в неделю»\n\n"
            f"Текст поста: {post_content}"
        )
        
        return await self.generate_text(prompt)
    
    async def generate_post_tags(self, post_content: str) -> str:
        """
        Генерирует хештеги для поста
        
        Args:
            post_content: Содержимое поста
            
        Returns:
            str: Сгенерированные хештеги
        """
        prompt = (
            "Ты — SMM-специалист и мастер вирального контента. Создай 7-10 коротких ключевых "
            "фраз для Telegram-поста на основе текста ниже, следуя правилам:\n\n"
            "Формат вывода — все фразы в одном предложении, разделённые пробелами "
            "(пример: Продуктивность Лайфхак Время).\n"
            "Краткость и ёмкость — до 3 слов в фразе (например, СоветДня).\n"
            "Релевантность — отражай ключевую тему поста (продуктивность, лайфхаки, саморазвитие и т.д.).\n"
            "SEO-оптимизация — используй популярные в нише ключевые слова (проверь тренды в TG).\n"
            "Микс форматов:\n"
            "— Основные (по теме): Продуктивность\n"
            "— Дополнительные (подтемы): ТаймМенеджмент\n"
            "— Трендовые (популярные в TG): Лайфхаки\n"
            "— Призывные (для вовлечения): СоветуйтеВКомментах\n"
            "Эмодзи — добавь в 1-2 фразы для привлечения внимания (например, 🔥ГорячиеСоветы).\n"
            "Пример результата:\n"
            "ПродуктивностьБезГраниц 💡ЛайфхакНаДень СаморазвитиеЛайт ВремяВДело.\n\n"
            "Проверь фразы на уникальность, длину (до 30 символов) и соответствие TG-аудитории\n\n"
            f"Текст поста: {post_content}"
        )
        
        return await self.generate_text(prompt) 