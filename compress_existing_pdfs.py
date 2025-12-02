#!/usr/bin/env python
"""
Скрипт для сжатия существующих PDF файлов.
"""

import os
import sys
import django
from django.conf import settings

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'filehost.settings')
django.setup()

from files.models import File
from files.pdf_utils import compress_pdf, should_compress_pdf
from django.core.files.base import ContentFile

def compress_existing_pdfs():
    """Сжимает существующие PDF файлы"""
    print("🗜️  Сжатие существующих PDF файлов...")
    
    # Находим PDF файлы без сжатых версий
    pdf_files = File.objects.filter(
        filename__iendswith='.pdf',
        is_deleted=False,
        compressed_pdf__isnull=True
    )
    
    print(f"📋 Найдено PDF файлов: {pdf_files.count()}")
    
    compressed_count = 0
    errors = []
    
    for file_obj in pdf_files:
        try:
            if os.path.exists(file_obj.file.path):
                print(f"🗜️  Сжимаем: {file_obj.code} - {file_obj.filename}")
                
                # Проверяем, нужно ли сжимать
                if should_compress_pdf(file_obj.file.path, max_size_mb=10):
                    success, compressed_path, compressed_size = compress_pdf(
                        file_obj.file.path,
                        quality=75,
                        max_size_mb=10
                    )
                    
                    if success and compressed_path and compressed_size:
                        # Сохраняем сжатую версию
                        with open(compressed_path, 'rb') as f:
                            file_obj.compressed_pdf.save(
                                f"compressed_{file_obj.filename}",
                                ContentFile(f.read()),
                                save=True
                            )
                        
                        file_obj.compressed_pdf_size = compressed_size
                        file_obj.save(update_fields=['compressed_pdf', 'compressed_pdf_size'])
                        
                        original_mb = file_obj.file_size / (1024 * 1024)
                        compressed_mb = compressed_size / (1024 * 1024)
                        ratio = (1 - compressed_size / file_obj.file_size) * 100
                        
                        print(f"   ✅ {original_mb:.1f}MB → {compressed_mb:.1f}MB ({ratio:.1f}%)")
                        compressed_count += 1
                        
                        # Удаляем временный файл
                        if compressed_path != file_obj.file.path:
                            os.remove(compressed_path)
                    else:
                        print(f"   ❌ Не удалось сжать")
                        errors.append(f"Не удалось сжать {file_obj.code}")
                else:
                    print(f"   ℹ️  Сжатие не требуется")
            else:
                print(f"   ❌ Файл не найден: {file_obj.file.path}")
                errors.append(f"Файл не найден: {file_obj.code}")
                
        except Exception as e:
            error_msg = f"Ошибка при сжатии {file_obj.code}: {str(e)}"
            errors.append(error_msg)
            print(f"   ❌ {error_msg}")
    
    print(f"\n📈 Результаты:")
    print(f"   ✅ Сжато: {compressed_count}")
    print(f"   ❌ Ошибок: {len(errors)}")
    
    if errors:
        print(f"\n🚨 Ошибки:")
        for error in errors:
            print(f"   • {error}")
    
    return compressed_count > 0

if __name__ == "__main__":
    success = compress_existing_pdfs()
    sys.exit(0 if success else 1)
