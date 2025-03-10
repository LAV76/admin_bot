import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем значение ADMIN_ID
admin_id = os.getenv("ADMIN_ID")
print(f"ADMIN_ID из .env файла: {admin_id}")

# Проверяем, является ли значение числом
if admin_id and admin_id.isdigit():
    print(f"ADMIN_ID как число: {int(admin_id)}")
else:
    print(f"ADMIN_ID не является числом или не задан") 