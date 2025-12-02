#!/usr/bin/env python
import os
import sys
import django

# Добавляем путь к проекту
sys.path.append('/var/www/filehost')

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'filehost.settings_prod')
django.setup()

from files.models import File
from django.core.files import File as DjangoFile
from django.utils import timezone
from datetime import timedelta

# Параметры файла
code = '5711'
file_path = '/var/www/filehost/demo_files/uploads/catalog_moscow.pdf'
filename = 'catalog_moscow.pdf'

# Проверяем, существует ли файл
if not os.path.exists(file_path):
    print(f"Файл {file_path} не найден!")
    sys.exit(1)

# Проверяем, не существует ли уже файл с таким кодом
if File.objects.filter(code=code).exists():
    print(f"Файл с кодом {code} уже существует!")
    # Обновляем существующий файл
    file_obj = File.objects.get(code=code)
    file_obj.is_permanent = True
    file_obj.expires_at = timezone.now() + timedelta(days=365*100)  # 100 лет
    file_obj.save()
    print(f"Файл {code} обновлен как постоянный")
else:
    # Получаем размер файла
    file_size = os.path.getsize(file_path)
    
    # Создаем постоянный файл
    with open(file_path, 'rb') as f:
        django_file = DjangoFile(f)
        
        file_obj = File(
            code=code,
            filename=filename,
            file_size=file_size,
            is_permanent=True,  # Помечаем как постоянный
            is_protected=False,  # Без пароля
            expires_at=timezone.now() + timedelta(days=365*100),  # 100 лет
        )
        
        # Сохраняем файл
        file_obj.file.save(filename, django_file, save=True)
    
    print(f"Постоянный файл {filename} создан с кодом {code}")

print(f"URL: http://0123.ru/{code}")
print(f"Файл: {file_path}")
print(f"Размер: {os.path.getsize(file_path)} байт")