#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'filehost.settings')
django.setup()

from files.models import File
from django.utils import timezone
from datetime import timedelta

def create_permanent_file():
    """Создает постоянный файл с кодом 5711 на сервере"""
    
    # Путь к файлу на сервере
    file_path = '/var/www/filehost/demo_files/uploads/catalog_moscow.pdf'
    
    # Проверяем, существует ли файл
    if not os.path.exists(file_path):
        print(f"Ошибка: Файл {file_path} не найден!")
        return False
    
    # Получаем размер файла
    file_size = os.path.getsize(file_path)
    
    # Проверяем, не существует ли уже файл с таким кодом
    existing_file = File.objects.filter(code='5711').first()
    if existing_file:
        # Обновляем существующий файл как постоянный
        existing_file.is_permanent = True
        existing_file.file.name = 'demo_files/uploads/catalog_moscow.pdf'
        existing_file.save()
        print(f"Существующий файл обновлен как постоянный!")
        print(f"Код: {existing_file.code}")
        print(f"Имя файла: {existing_file.filename}")
        print(f"Размер: {existing_file.get_file_size_mb()} МБ")
        print(f"Постоянный: {existing_file.is_permanent}")
        print(f"URL: http://0123.ru/{existing_file.code}")
        return True
    
    # Создаем новый постоянный файл
    permanent_file = File.objects.create(
        filename='catalog_moscow.pdf',
        file_size=file_size,
        code='5711',
        is_protected=False,
        session_id=None,  # Постоянный файл не привязан к сессии
        expires_at=timezone.now() + timedelta(days=36500),  # 100 лет (практически бесконечно)
        is_permanent=True,  # Помечаем как постоянный
        download_count=0
    )
    
    # Устанавливаем путь к файлу
    permanent_file.file.name = 'demo_files/uploads/catalog_moscow.pdf'
    permanent_file.save()
    
    print(f"Постоянный файл создан успешно!")
    print(f"Код: {permanent_file.code}")
    print(f"Имя файла: {permanent_file.filename}")
    print(f"Размер: {permanent_file.get_file_size_mb()} МБ")
    print(f"Постоянный: {permanent_file.is_permanent}")
    print(f"URL: http://0123.ru/{permanent_file.code}")
    
    return True

if __name__ == '__main__':
    create_permanent_file()
