#!/usr/bin/env python
"""
Скрипт для очистки базы данных от удаленных файлов.
Удаляет файлы, которые:
1. Помечены как удаленные (is_deleted=True)
2. Физически отсутствуют на диске
3. Имеют отсутствующие QR коды

Использование:
    python cleanup_deleted_files.py [--dry-run] [--force] [--include-permanent]
"""

import os
import sys
import django
from django.conf import settings
from django.db import transaction

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'filehost.settings')
django.setup()

from files.models import File
import logging

logger = logging.getLogger(__name__)

def cleanup_deleted_files(dry_run=False, force=False, include_permanent=False):
    """Очищает базу данных от удаленных файлов"""
    
    print("🧹 Начинаем очистку базы данных от удаленных файлов...")
    
    # 1. Находим файлы, помеченные как удаленные
    soft_deleted_files = File.objects.filter(is_deleted=True)
    if not include_permanent:
        soft_deleted_files = soft_deleted_files.filter(is_permanent=False)
    
    print(f"📋 Найдено файлов, помеченных как удаленные: {soft_deleted_files.count()}")
    
    # 2. Находим файлы, которые физически отсутствуют на диске
    orphaned_files = []
    all_files = File.objects.all()
    if not include_permanent:
        all_files = all_files.filter(is_permanent=False)
        
    for file_obj in all_files:
        if file_obj.file and not os.path.exists(file_obj.file.path):
            orphaned_files.append(file_obj)
    
    print(f"📋 Найдено файлов, отсутствующих на диске: {len(orphaned_files)}")
    
    # 3. Находим QR коды, которые отсутствуют на диске
    orphaned_qr_codes = []
    for file_obj in all_files:
        if file_obj.qr_code and not os.path.exists(file_obj.qr_code.path):
            orphaned_qr_codes.append(file_obj)
    
    print(f"📋 Найдено QR кодов, отсутствующих на диске: {len(orphaned_qr_codes)}")
    
    # Объединяем все файлы для удаления
    files_to_delete = set()
    files_to_delete.update(soft_deleted_files)
    files_to_delete.update(orphaned_files)
    files_to_delete.update(orphaned_qr_codes)
    
    total_files = len(files_to_delete)
    
    if total_files == 0:
        print("✅ Нет файлов для удаления!")
        return True
    
    # Показываем детали
    print(f"\n📊 Детали файлов для удаления:")
    print(f"   • Помеченные как удаленные: {soft_deleted_files.count()}")
    print(f"   • Отсутствующие на диске: {len(orphaned_files)}")
    print(f"   • С отсутствующими QR кодами: {len(orphaned_qr_codes)}")
    print(f"   • Всего уникальных файлов: {total_files}")
    
    if dry_run:
        print("\n🔍 РЕЖИМ ПРОСМОТРА - файлы НЕ будут удалены")
        show_file_details(files_to_delete)
        return True
    
    # Подтверждение удаления
    if not force:
        print(f"\n⚠️  Вы собираетесь удалить {total_files} файлов из базы данных.")
        confirm = input("Продолжить? (yes/no): ")
        if confirm.lower() not in ['yes', 'y', 'да', 'д']:
            print("❌ Операция отменена пользователем")
            return False
    
    # Выполняем удаление
    print(f"\n🗑️  Удаляем {total_files} файлов...")
    
    deleted_count = 0
    errors = []
    
    with transaction.atomic():
        for file_obj in files_to_delete:
            try:
                # Логируем информацию о файле
                print(f"   Удаляем: {file_obj.code} - {file_obj.filename}")
                
                # Удаляем файл (это вызовет наш кастомный метод delete)
                file_obj.delete()
                deleted_count += 1
                
            except Exception as e:
                error_msg = f"Ошибка при удалении {file_obj.code}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                print(f"   ❌ {error_msg}")
    
    # Результаты
    print(f"\n📈 Результаты очистки:")
    print(f"   ✅ Успешно удалено: {deleted_count}")
    print(f"   ❌ Ошибок: {len(errors)}")
    
    if errors:
        print(f"\n🚨 Ошибки:")
        for error in errors:
            print(f"   • {error}")
    
    if deleted_count > 0:
        print(f"\n🎉 Очистка завершена! Удалено {deleted_count} файлов.")
        return True
    else:
        print("\n⚠️  Не удалось удалить ни одного файла.")
        return False

def show_file_details(files):
    """Показывает детали файлов для удаления"""
    print(f"\n📋 Детали файлов для удаления:")
    
    for file_obj in files:
        status = []
        if file_obj.is_deleted:
            status.append("помечен как удаленный")
        if file_obj.file and not os.path.exists(file_obj.file.path):
            status.append("файл отсутствует")
        if file_obj.qr_code and not os.path.exists(file_obj.qr_code.path):
            status.append("QR код отсутствует")
        
        status_str = ", ".join(status)
        print(f"   • {file_obj.code} - {file_obj.filename} ({status_str})")

def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Очистка базы данных от удаленных файлов')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Показать, какие файлы будут удалены, без фактического удаления')
    parser.add_argument('--force', action='store_true', 
                       help='Принудительно удалить все найденные записи без подтверждения')
    parser.add_argument('--include-permanent', action='store_true', 
                       help='Включить в очистку постоянные файлы (по умолчанию они исключены)')
    
    args = parser.parse_args()
    
    success = cleanup_deleted_files(
        dry_run=args.dry_run,
        force=args.force,
        include_permanent=args.include_permanent
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
