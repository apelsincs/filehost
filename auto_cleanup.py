#!/usr/bin/env python
"""
Автоматический скрипт очистки для cron.
Удаляет только файлы, помеченные как удаленные (без физической проверки диска).
Безопасен для автоматического запуска.
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

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cleanup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def auto_cleanup():
    """Автоматическая очистка только файлов, помеченных как удаленные"""
    
    logger.info("🤖 Запуск автоматической очистки...")
    
    try:
        # Находим только файлы, помеченные как удаленные
        # Исключаем постоянные файлы для безопасности
        files_to_delete = File.objects.filter(
            is_deleted=True,
            is_permanent=False
        )
        
        count = files_to_delete.count()
        
        if count == 0:
            logger.info("✅ Нет файлов для автоматической очистки")
            return True
        
        logger.info(f"📋 Найдено {count} файлов для удаления")
        
        deleted_count = 0
        errors = []
        
        with transaction.atomic():
            for file_obj in files_to_delete:
                try:
                    logger.info(f"🗑️  Удаляем: {file_obj.code} - {file_obj.filename}")
                    file_obj.delete()
                    deleted_count += 1
                    
                except Exception as e:
                    error_msg = f"Ошибка при удалении {file_obj.code}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
        
        logger.info(f"📈 Результат: удалено {deleted_count} из {count} файлов")
        
        if errors:
            logger.warning(f"⚠️  Ошибок: {len(errors)}")
            for error in errors:
                logger.error(f"   • {error}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при очистке: {str(e)}")
        return False

if __name__ == "__main__":
    success = auto_cleanup()
    sys.exit(0 if success else 1)
