# Telegram Бот Администратора Канала

Многофункциональный Telegram-бот для эффективного администрирования каналов и управления контентом с использованием ИИ-генерации текстов.

![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)
![Python](https://img.shields.io/badge/Python-3.9+-green?logo=python)
![aiogram](https://img.shields.io/badge/aiogram-3.10.0-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)

## 📋 Оглавление

- [Функциональность](#-функциональность)
- [Технические характеристики](#-технические-характеристики)
- [Установка и настройка](#-установка-и-настройка)
- [Запуск в Docker](#-запуск-в-docker)
- [Структура проекта](#-структура-проекта)
- [Использование](#-использование)
- [Работа с постами и ИИ](#-работа-с-постами-и-ии)
- [Управление пользователями и ролями](#-управление-пользователями-и-ролями)
- [Управление каналами](#-управление-каналами)
- [Расширение функциональности](#-расширение-функциональности)
- [Примечания разработчика](#-примечания-разработчика)
- [Лицензия](#-лицензия)

## 🚀 Функциональность

### Основные возможности:

- **Администрирование каналов**
  - Управление публикациями
  - Настройка прав доступа

- **Управление контентом**
  - CRUD операции с постами
  - Редактирование и удаление сообщений
  - Отложенная публикация
  - Автоматическая публикация в канал
  
- **Генерация контента с использованием ИИ**
  - Создание текстов постов с помощью AI
  - Автоматическая генерация заголовков
  - Генерация релевантных хештегов
  
- **Управление ролями**
  - Назначение администраторов
  - Управление контент-менеджерами
  - Детальный аудит изменений ролей

- **Расширенная безопасность**
  - Аутентификация пользователей
  - Валидация ввода
  - Защита от спама
  - Безопасное хранение токенов

## 💻 Технические характеристики

### Стек технологий:

- **Основной язык**: Python 3.9+
- **Telegram API**: aiogram 3.10.0
- **База данных**: PostgreSQL с асинхронным ORM (SQLAlchemy)
- **Миграции**: Alembic
- **Работа с ИИ**: Custom API интеграция
- **Конфигурация**: python-dotenv, pydantic-settings
- **Логирование**: Стандартная библиотека logging
- **Асинхронные операции**: asyncio, aiohttp

### Паттерны проектирования:

- **SOLID** принципы
- **Репозиторий** (для работы с данными)
- **Сервисный слой** (для бизнес-логики)
- **Фабрика** (для клавиатур)
- **FSM** (Конечный автомат состояний)
- **Медиатор** (для межмодульного взаимодействия)

## 🔧 Установка и настройка

### Предварительные требования:

- Python 3.9 или выше
- PostgreSQL 12 или выше
- Токен Telegram бота (можно получить у [@BotFather](https://t.me/BotFather))
- API ключ для генерации текста (опционально)

### Шаги по установке:

1. **Клонировать репозиторий**:
   ```bash
   git clone https://github.com/LAV76/admin_bot.git
   cd admin_chat
   ```

2. **Создать виртуальное окружение**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # для Linux/Mac
   venv\Scripts\activate  # для Windows
   ```

3. **Установить зависимости**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Настроить переменные окружения**:
   Создайте файл `.env` в корне проекта со следующим содержимым:
   ```
   # Настройки бота
   API_TOKEN=<ваш-токен-телеграм-бота>
   ADMIN_ID=<ваш-id-администратора>
   CHANNEL_ID=<id-вашего-канала>
   
   # Настройка API для ИИ
   API_KEY=<ключ-api-для-генерации-текста>
   
   # Настройки базы данных
   DB_USER=postgres
   DB_PASS=<ваш-пароль>
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=tgbot_admin
   
   # Дополнительные настройки
   NOTIFICATION_ENABLED=True
   ACTIVE_MODE=True
   CACHE_TTL=3600
   ```

5. **Настроить базу данных**:
   ```bash
   python scripts/create_db_and_tables.py
   ```

6. **Запустить миграции**:
   ```bash
   alembic upgrade head
   ```

7. **Запустить бота**:
   ```bash
   python main.py
   ```

### Настройка администратора:

При первом запуске бота автоматически создается администратор с ID, указанным в переменной `ADMIN_ID`. Убедитесь, что вы правильно указали ID администратора в файле `.env`.

## 📂 Структура проекта

```
admin_chat/
├── alembic/               # Файлы миграций
├── app/                   # Основная логика приложения
│   ├── core/              # Базовые компоненты
│   │   ├── config.py      # Конфигурация
│   │   ├── decorators.py  # Декораторы
│   │   └── utils.py       # Утилиты
│   ├── db/                # Работа с базой данных
│   │   ├── engine.py      # Настройка подключения
│   │   ├── models/        # Модели данных
│   │   └── repositories/  # Репозитории
│   ├── services/          # Бизнес-логика
│   └── states/            # Состояния FSM
├── handlers/              # Обработчики сообщений
│   ├── admin/             # Админ-панель
│   │   ├── channels.py    # Работа с каналами
│   │   ├── create_post.py # Создание постов
│   │   ├── manage_posts.py# Управление постами
│   │   ├── post_states.py # Состояния постов
│   │   └── roles.py       # Управление ролями
│   └── __init__.py        # Инициализация
├── keyboards/             # Клавиатуры
│   └── admin/             # Админ-клавиатуры
├── middlewares/           # Промежуточные обработчики
│   ├── anti_spam.py       # Защита от спама
│   └── role_checker.py    # Проверка ролей
├── migrations/            # SQL-миграции
│   └── versions/          # Версии миграций
├── scripts/               # Вспомогательные скрипты
│   └── create_db_and_tables.py  # Создание БД
├── utils/                 # Утилиты
│   ├── ai_service.py      # Сервис ИИ
│   ├── logger.py          # Настройка логгирования
│   └── notifications.py   # Работа с уведомлениями
├── .env                   # Переменные окружения
├── main.py                # Точка входа
├── requirements.txt       # Зависимости
└── README.md              # Документация
```

## 🎮 Использование

### Основные команды бота:

- `/start` - Начало работы с ботом
- `/help` - Справка по командам
- `/admin` - Доступ к админ-панели (только для администраторов)

### Основные разделы админ-панели:

1. **Управление ролями** - Добавление/удаление администраторов и контент-менеджеров
2. **Управление постами** - Создание, редактирование, публикация постов
3. **Управление каналами** - Добавление и настройка каналов для публикации

## 📝 Работа с постами и ИИ

### Создание поста:

1. Выберите опцию "Управление постами" в меню администратора
2. Нажмите кнопку "Создать пост"
3. У вас есть два варианта создания поста:
   - **Ручное создание**: последовательно введите название, описание, добавьте изображение (опционально) и теги
   - **Генерация через ИИ**: нажмите кнопку "Сгенерировать AI" и следуйте инструкциям

### Генерация контента с помощью ИИ:

1. В процессе создания поста нажмите кнопку "🤖 Сгенерировать AI"
2. Введите тему или описание желаемого поста (например, "5 способов повысить продуктивность")
3. Дождитесь генерации контента (это может занять несколько секунд)
4. После успешной генерации вы получите:
   - Сгенерированный заголовок поста
   - Текст поста (до 1000 символов)
   - Набор релевантных хештегов
5. Вы можете:
   - Принять результат и продолжить
   - Сгенерировать новую версию
   - Отменить генерацию и вернуться к ручному созданию

### Редактирование поста:

1. В разделе "Управление постами" выберите нужный пост
2. Нажмите кнопку "Редактировать"
3. Измените необходимые поля
4. Сохраните изменения

### Публикация поста:

1. Выберите пост для публикации
2. Нажмите кнопку "Опубликовать"
3. Выберите канал для публикации
4. Подтвердите публикацию

## 👥 Управление пользователями и ролями

### Доступные роли:

- **Администратор** - полный доступ ко всем функциям бота
- **Контент-менеджер** - управление постами без доступа к настройкам и ролям

### Добавление пользователя:

1. В админ-панели выберите "Управление ролями"
2. Нажмите "Добавить пользователя"
3. Введите Telegram ID пользователя или его @username
4. Если пользователь не найден, вы можете создать его вручную
5. Выберите роль для пользователя

### Удаление пользователя:

1. В разделе "Управление ролями" выберите "Удалить пользователя"
2. Выберите пользователя для удаления
3. Подтвердите действие

### Назначение роли:

1. В разделе "Управление ролями" выберите "Добавить роль"
2. Введите ID или @username пользователя
3. Выберите роль из списка доступных
4. Подтвердите добавление роли

### Просмотр истории ролей:

1. В разделе "Управление ролями" выберите "История изменений"
2. Просмотрите историю назначений и удалений ролей с указанием времени и администратора

## 📢 Управление каналами

### Добавление канала:

1. В админ-панели выберите "Управление каналами"
2. Нажмите "Добавить канал"
3. Введите @username канала или его ID
4. Убедитесь, что бот добавлен в канал как администратор
5. Подтвердите добавление канала

### Настройка канала по умолчанию:

1. В разделе "Управление каналами" выберите нужный канал
2. Нажмите "Установить по умолчанию"
3. Теперь этот канал будет автоматически выбираться при публикации

### Удаление канала:

1. В разделе "Управление каналами" выберите нужный канал
2. Нажмите "Удалить канал"
3. Подтвердите удаление

## 🔄 Расширение функциональности

### Добавление новых ролей:

Для добавления новой роли необходимо:

1. Добавить новую роль в `app/db/models/users.py`
2. Обновить функцию `check_user_role` в `db_handlers/user_role/manage_roles.py`
3. Создать миграцию с помощью Alembic
4. Обновить интерфейс управления ролями в `handlers/admin/roles.py`

### Настройка ИИ-генерации:

Для изменения параметров генерации контента:

1. Отредактируйте промпты в `utils/ai_service.py`
2. При необходимости измените модель ИИ в методе `__init__` класса `AIService`
3. Настройте дополнительные параметры в запросе к API

### Создание новых состояний FSM:

Для добавления новых шагов при создании поста:

1. Добавьте новые состояния в `handlers/admin/post_states.py`
2. Создайте обработчики для новых состояний в соответствующих файлах
3. Обновите клавиатуры и переходы между состояниями

## 📝 Примечания разработчика

### Лучшие практики:

- **Логирование**: используйте функцию `logger` для отслеживания операций
- **Обработка ошибок**: всегда оборачивайте потенциально опасный код в блоки try-except
- **Валидация ввода**: проверяйте корректность ввода пользователя
- **Транзакции**: используйте транзакции при работе с БД для обеспечения целостности данных

### Известные проблемы:

- При большом количестве постов возможны задержки при загрузке списка
- Пользователь должен запустить бота для добавления его в систему
- Возможны проблемы при генерации контента, если API недоступен
- При закрытии соединения с базой данных может возникать ошибка CancelledError

### Будущие улучшения:

- Добавление веб-интерфейса для администрирования
- Интеграция с другими платформами (Instagram, Facebook)
- Расширенная аналитика по постам и активности
- Система модерации комментариев
- Расширенная генерация медиа-контента через ИИ

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. Подробности в файле LICENSE.

## 🐳 Запуск в Docker

Проект полностью готов к запуску в Docker. Для этого предусмотрено два варианта: с встроенной базой данных PostgreSQL или с использованием внешней базы данных.

### Предварительные требования:

- Docker и Docker Compose
- Файл `.env` в корневой директории проекта

### Вариант 1: С встроенной базой данных

1. **Настройте переменные окружения**

   Убедитесь, что в файле `.env` указаны необходимые параметры:
   ```
   # Настройки бота
   API_TOKEN=<ваш-токен-телеграм-бота>
   ADMIN_ID=<ваш-id-администратора>
   CHANNEL_ID=<id-вашего-канала>
   
   # Настройка API для ИИ
   API_KEY=<ключ-api-для-генерации-текста>
   
   # Настройки базы данных
   DB_USER=postgres
   DB_PASS=<ваш-пароль>
   DB_HOST=postgres
   DB_PORT=5432
   DB_NAME=tgbot_admin
   ```

2. **Запустите контейнеры**

   ```bash
   docker-compose up -d
   ```

   Это создаст и запустит два контейнера:
   - `telegram_admin_bot` - контейнер с ботом
   - `telegram_bot_postgres` - контейнер с PostgreSQL

   База данных будет сохранена в Docker volume `telegram_bot_postgres_data`.

3. **Проверьте логи**

   ```bash
   docker logs -f telegram_admin_bot
   ```

### Вариант 2: С внешней базой данных

Если у вас уже есть работающая база данных PostgreSQL, вы можете использовать её:

1. **Настройте переменные окружения**

   В файле `.env` укажите параметры подключения к вашей базе:
   ```
   # Настройки бота
   API_TOKEN=<ваш-токен-телеграм-бота>
   ADMIN_ID=<ваш-id-администратора>
   CHANNEL_ID=<id-вашего-канала>
   
   # Настройка API для ИИ
   API_KEY=<ключ-api-для-генерации-текста>
   
   # Настройки базы данных
   DB_USER=<пользователь-бд>
   DB_PASS=<пароль>
   DB_HOST=<адрес-хоста-бд>
   DB_PORT=5432
   DB_NAME=tgbot_admin
   ```

2. **Запустите контейнер с ботом**

   ```bash
   docker-compose -f docker-compose.external-db.yml up -d
   ```

   Это создаст и запустит только контейнер с ботом, который будет подключаться к внешней базе данных.

### Управление контейнерами

- **Остановка контейнеров**
  ```bash
  docker-compose down
  ```

- **Остановка и удаление всех данных**
  ```bash
  docker-compose down -v
  ```

- **Пересборка образа**
  ```bash
  docker-compose build --no-cache
  ```

- **Просмотр логов**
  ```bash
  docker logs -f telegram_admin_bot
  ```

## 🔄 Часто встречающиеся проблемы при использовании Docker

### Проблема: Бот запускается, но не отвечает на команды

**Причина**: Скорее всего, проблема в недействительном токене Telegram API или неправильном ID администратора.

**Решение**:
1. Убедитесь, что вы заменили тестовые значения в файле `.env` на действительные:
   ```
   API_TOKEN=<ваш-настоящий-токен-от-BotFather>
   ADMIN_ID=<ваш-настоящий-Telegram-ID>
   CHANNEL_ID=<настоящий-ID-вашего-канала>
   ```
2. Перезапустите контейнер:
   ```bash
   docker-compose down
   docker-compose up -d
   ```
3. Проверьте логи на наличие ошибок:
   ```bash
   docker logs telegram_admin_bot
   ```

### Проблема: Ошибка подключения к базе данных

**Причина**: Неправильные параметры подключения к PostgreSQL.

**Решение**:
1. Для встроенной базы данных убедитесь, что в `.env` файле:
   ```
   DB_HOST=postgres
   DB_PASS=postgres  # Такой же пароль, как установлен в docker-compose.yml
   ```
2. Проверьте, что контейнер базы данных запущен:
   ```bash
   docker ps | grep postgres
   ```
3. Перезапустите оба контейнера:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Проблема: Контейнер Docker не запускается

**Причина**: Проблемы с Docker Engine или конфигурацией.

**Решение**:
1. Убедитесь, что Docker Desktop запущен
2. Перезапустите Docker Desktop
3. Проверьте соответствие версий Docker Compose:
   ```bash
   docker-compose --version
   ```
4. Попробуйте запустить с подробными логами:
   ```bash
   docker-compose --verbose up -d
   ```

### Проблема: Бот запускается, но не может создать таблицы в базе данных

**Причина**: Проблемы с миграциями или правами доступа к базе данных.

**Решение**:
1. Проверьте, что миграции выполняются корректно:
   ```bash
   docker exec -it telegram_admin_bot alembic upgrade head
   ```
2. Проверьте права пользователя базы данных:
   ```bash
   docker exec -it telegram_bot_postgres psql -U postgres -d tgbot_admin -c "SELECT current_user;"
   ```

---

© 2025 Telegram Bot Admin. Разработано с ❤️ для эффективного управления контентом. 
