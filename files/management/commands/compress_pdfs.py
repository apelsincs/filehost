from django.core.management.base import BaseCommand
from django.db import transaction
from files.models import File
from files.pdf_utils import compress_pdf, should_compress_pdf, get_pdf_info
import os
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Сжимает PDF файлы для быстрого веб-отображения'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать, какие PDF файлы будут сжаты, без фактического сжатия',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно сжать все PDF файлы, даже если уже есть сжатые версии',
        )
        parser.add_argument(
            '--max-size',
            type=int,
            default=10,
            help='Максимальный размер PDF в МБ для сжатия (по умолчанию 10)',
        )
        parser.add_argument(
            '--quality',
            type=int,
            default=75,
            help='Качество сжатия от 1 до 100 (по умолчанию 75)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        max_size_mb = options['max_size']
        quality = options['quality']
        
        self.stdout.write(
            self.style.SUCCESS('🗜️  Начинаем сжатие PDF файлов...')
        )
        
        # Находим PDF файлы для сжатия
        pdf_files = File.objects.filter(
            filename__iendswith='.pdf',
            is_deleted=False
        )
        
        if not force:
            # Исключаем файлы, у которых уже есть сжатые версии
            pdf_files = pdf_files.filter(compressed_pdf__isnull=True)
        
        files_to_compress = []
        
        for file_obj in pdf_files:
            if os.path.exists(file_obj.file.path):
                if should_compress_pdf(file_obj.file.path, max_size_mb):
                    files_to_compress.append(file_obj)
        
        total_files = len(files_to_compress)
        
        if total_files == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ Нет PDF файлов для сжатия!')
            )
            return
        
        self.stdout.write(f"📋 Найдено PDF файлов для сжатия: {total_files}")
        self.stdout.write(f"⚙️  Параметры: max_size={max_size_mb}MB, quality={quality}")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n🔍 РЕЖИМ ПРОСМОТРА - файлы НЕ будут сжаты')
            )
            self.show_file_details(files_to_compress)
            return
        
        # Выполняем сжатие
        self.stdout.write(f"\n🗜️  Сжимаем {total_files} PDF файлов...")
        
        compressed_count = 0
        errors = []
        total_original_size = 0
        total_compressed_size = 0
        
        with transaction.atomic():
            for file_obj in files_to_compress:
                try:
                    original_size = file_obj.file_size
                    total_original_size += original_size
                    
                    self.stdout.write(f"   Сжимаем: {file_obj.code} - {file_obj.filename}")
                    
                    # Сжимаем PDF
                    success, compressed_path, compressed_size = compress_pdf(
                        file_obj.file.path,
                        quality=quality,
                        max_size_mb=max_size_mb
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
                        
                        total_compressed_size += compressed_size
                        compressed_count += 1
                        
                        # Удаляем временный файл
                        if compressed_path != file_obj.file.path:
                            os.remove(compressed_path)
                        
                        # Показываем результат
                        original_mb = original_size / (1024 * 1024)
                        compressed_mb = compressed_size / (1024 * 1024)
                        ratio = file_obj.get_compression_ratio()
                        
                        self.stdout.write(
                            f"     ✅ {original_mb:.1f}MB → {compressed_mb:.1f}MB ({ratio}% сжатие)"
                        )
                    else:
                        self.stdout.write(f"     ❌ Не удалось сжать")
                        errors.append(f"Не удалось сжать {file_obj.code}")
                        
                except Exception as e:
                    error_msg = f"Ошибка при сжатии {file_obj.code}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    self.stdout.write(
                        self.style.ERROR(f"     ❌ {error_msg}")
                    )
        
        # Результаты
        self.stdout.write(f"\n📈 Результаты сжатия:")
        self.stdout.write(f"   ✅ Успешно сжато: {compressed_count}")
        self.stdout.write(f"   ❌ Ошибок: {len(errors)}")
        
        if compressed_count > 0:
            total_original_mb = total_original_size / (1024 * 1024)
            total_compressed_mb = total_compressed_size / (1024 * 1024)
            total_saved_mb = total_original_mb - total_compressed_mb
            total_ratio = (1 - total_compressed_size / total_original_size) * 100
            
            self.stdout.write(f"   📊 Общий размер: {total_original_mb:.1f}MB → {total_compressed_mb:.1f}MB")
            self.stdout.write(f"   💾 Сэкономлено: {total_saved_mb:.1f}MB ({total_ratio:.1f}%)")
        
        if errors:
            self.stdout.write(f"\n🚨 Ошибки:")
            for error in errors:
                self.stdout.write(f"   • {error}")
        
        if compressed_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\n🎉 Сжатие завершено! Обработано {compressed_count} файлов.')
            )
        else:
            self.stdout.write(
                self.style.WARNING('\n⚠️  Не удалось сжать ни одного файла.')
            )

    def show_file_details(self, files):
        """Показывает детали файлов для сжатия"""
        self.stdout.write(f"\n📋 Детали PDF файлов для сжатия:")
        
        for file_obj in files:
            original_mb = file_obj.file_size / (1024 * 1024)
            self.stdout.write(
                f"   • {file_obj.code} - {file_obj.filename} ({original_mb:.1f}MB)"
            )
