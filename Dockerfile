FROM python:3.10-slim

WORKDIR /app

# Устанавливаем дополнительные пакеты для отладки
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Создаем директорию для логов
RUN mkdir -p logs && chmod 777 logs

# Добавим скрипт инициализации для ожидания готовности БД
COPY scripts/check_connections.py /app/scripts/
RUN chmod +x /app/scripts/check_connections.py

# Устанавливаем CMD без использования скрипта проверки,
# так как он может блокировать запуск бота
CMD ["python", "main.py"] 