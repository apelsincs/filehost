from django.core.management.base import BaseCommand
from django.db import transaction
from files.models import File
import os
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Удаляет из базы данных файлы, которые помечены как удаленные или физически отсутствуют на диске'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать, какие файлы будут удалены, без фактического удаления',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно удалить все найденные записи без подтверждения',
        )
        parser.add_argument(
            '--include-permanent',
            action='store_true',
            help='Включить в очистку постоянные файлы (по умолчанию они исключены)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        include_permanent = options['include_permanent']
        
        self.stdout.write(
            self.style.SUCCESS('🧹 Начинаем очистку базы данных от удаленных файлов...')
        )
        
        # 1. Находим файлы, помеченные как удаленные
        soft_deleted_files = File.objects.filter(is_deleted=True)
        if not include_permanent:
            soft_deleted_files = soft_deleted_files.filter(is_permanent=False)
        
        self.stdout.write(f"📋 Найдено файлов, помеченных как удаленные: {soft_deleted_files.count()}")
        
        # 2. Находим файлы, которые физически отсутствуют на диске
        orphaned_files = []
        all_files = File.objects.all()
        if not include_permanent:
            all_files = all_files.filter(is_permanent=False)
            
        for file_obj in all_files:
            if file_obj.file and not os.path.exists(file_obj.file.path):
                orphaned_files.append(file_obj)
        
        self.stdout.write(f"📋 Найдено файлов, отсутствующих на диске: {len(orphaned_files)}")
        
        # 3. Находим QR коды, которые отсутствуют на диске
        orphaned_qr_codes = []
        for file_obj in all_files:
            if file_obj.qr_code and not os.path.exists(file_obj.qr_code.path):
                orphaned_qr_codes.append(file_obj)
        
        self.stdout.write(f"📋 Найдено QR кодов, отсутствующих на диске: {len(orphaned_qr_codes)}")
        
        # Объединяем все файлы для удаления
        files_to_delete = set()
        files_to_delete.update(soft_deleted_files)
        files_to_delete.update(orphaned_files)
        files_to_delete.update(orphaned_qr_codes)
        
        total_files = len(files_to_delete)
        
        if total_files == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ Нет файлов для удаления!')
            )
            return
        
        # Показываем детали
        self.stdout.write(f"\n📊 Детали файлов для удаления:")
        self.stdout.write(f"   • Помеченные как удаленные: {soft_deleted_files.count()}")
        self.stdout.write(f"   • Отсутствующие на диске: {len(orphaned_files)}")
        self.stdout.write(f"   • С отсутствующими QR кодами: {len(orphaned_qr_codes)}")
        self.stdout.write(f"   • Всего уникальных файлов: {total_files}")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n🔍 РЕЖИМ ПРОСМОТРА - файлы НЕ будут удалены')
            )
            self.show_file_details(files_to_delete)
            return
        
        # Подтверждение удаления
        if not force:
            self.stdout.write(f"\n⚠️  Вы собираетесь удалить {total_files} файлов из базы данных.")
            confirm = input("Продолжить? (yes/no): ")
            if confirm.lower() not in ['yes', 'y', 'да', 'д']:
                self.stdout.write(
                    self.style.WARNING('❌ Операция отменена пользователем')
                )
                return
        
        # Выполняем удаление
        self.stdout.write(f"\n🗑️  Удаляем {total_files} файлов...")
        
        deleted_count = 0
        errors = []
        
        with transaction.atomic():
            for file_obj in files_to_delete:
                try:
                    # Логируем информацию о файле
                    self.stdout.write(f"   Удаляем: {file_obj.code} - {file_obj.filename}")
                    
                    # Удаляем файл (это вызовет наш кастомный метод delete)
                    file_obj.delete()
                    deleted_count += 1
                    
                except Exception as e:
                    error_msg = f"Ошибка при удалении {file_obj.code}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    self.stdout.write(
                        self.style.ERROR(f"   ❌ {error_msg}")
                    )
        
        # Результаты
        self.stdout.write(f"\n📈 Результаты очистки:")
        self.stdout.write(f"   ✅ Успешно удалено: {deleted_count}")
        self.stdout.write(f"   ❌ Ошибок: {len(errors)}")
        
        if errors:
            self.stdout.write(f"\n🚨 Ошибки:")
            for error in errors:
                self.stdout.write(f"   • {error}")
        
        if deleted_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\n🎉 Очистка завершена! Удалено {deleted_count} файлов.')
            )
        else:
            self.stdout.write(
                self.style.WARNING('\n⚠️  Не удалось удалить ни одного файла.')
            )

    def show_file_details(self, files):
        """Показывает детали файлов для удаления"""
        self.stdout.write(f"\n📋 Детали файлов для удаления:")
        
        for file_obj in files:
            status = []
            if file_obj.is_deleted:
                status.append("помечен как удаленный")
            if file_obj.file and not os.path.exists(file_obj.file.path):
                status.append("файл отсутствует")
            if file_obj.qr_code and not os.path.exists(file_obj.qr_code.path):
                status.append("QR код отсутствует")
            
            status_str = ", ".join(status)
            self.stdout.write(
                f"   • {file_obj.code} - {file_obj.filename} ({status_str})"
            )
