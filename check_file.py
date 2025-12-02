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

# Проверяем файл с кодом 5711
try:
    file_obj = File.objects.get(code='5711')
    print(f"Файл найден:")
    print(f"  Код: {file_obj.code}")
    print(f"  Имя файла: {file_obj.filename}")
    print(f"  Размер: {file_obj.file_size} байт")
    print(f"  Постоянный: {file_obj.is_permanent}")
    print(f"  Защищен паролем: {file_obj.is_protected}")
    print(f"  Удален: {file_obj.is_deleted}")
    print(f"  Истекает: {file_obj.expires_at}")
    print(f"  Путь к файлу: {file_obj.file.path}")
    print(f"  Файл существует: {os.path.exists(file_obj.file.path)}")
    
    # Проверяем альтернативный путь
    alt_path = "/var/www/filehost/demo_files/uploads/catalog_moscow.pdf"
    print(f"  Альтернативный путь: {alt_path}")
    print(f"  Альтернативный файл существует: {os.path.exists(alt_path)}")
    
except File.DoesNotExist:
    print("Файл с кодом 5711 не найден в базе данных")
except Exception as e:
    print(f"Ошибка: {e}")
