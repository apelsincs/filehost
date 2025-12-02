from django.db import models
from django.utils import timezone
from django.conf import settings
import os
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image


class File(models.Model):
    """
    Модель для хранения информации о загруженных файлах.
    Поддерживает автоматическую генерацию QR кодов, защиту паролем
    и связывание с анонимными сессиями пользователей.
    """
    
    # Основные поля файла
    file = models.FileField(upload_to='uploads/', verbose_name='Файл')
    filename = models.CharField(max_length=255, verbose_name='Имя файла')
    file_size = models.BigIntegerField(verbose_name='Размер файла (байт)')
    
    # Идентификация и доступ
    code = models.CharField(max_length=10, unique=True, verbose_name='Код файла')
    password = models.CharField(max_length=128, blank=True, null=True, verbose_name='Пароль')
    is_protected = models.BooleanField(default=False, verbose_name='Защищен паролем')
    
    # Анонимная сессия пользователя
    session_id = models.CharField(max_length=64, blank=True, null=True, verbose_name='ID анонимной сессии')
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    expires_at = models.DateTimeField(verbose_name='Дата истечения')
    
    # QR код
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True, verbose_name='QR код')
    
    # Статистика
    download_count = models.PositiveIntegerField(default=0, verbose_name='Количество скачиваний')
    last_downloaded = models.DateTimeField(blank=True, null=True, verbose_name='Последнее скачивание')
    
    # Флаг удаления (для подсчета всех загруженных файлов)
    is_deleted = models.BooleanField(default=False, verbose_name='Файл удален')
    
    # Флаг постоянного файла (никогда не удаляется)
    is_permanent = models.BooleanField(default=False, verbose_name='Постоянный файл')
    
    # Сжатая версия PDF для быстрого отображения
    compressed_pdf = models.FileField(upload_to='compressed_pdfs/', blank=True, null=True, verbose_name='Сжатый PDF')
    compressed_pdf_size = models.BigIntegerField(blank=True, null=True, verbose_name='Размер сжатого PDF (байт)')
    
    class Meta:
        verbose_name = 'Файл'
        verbose_name_plural = 'Файлы'
        ordering = ['-created_at']
        # Индексы для оптимизации запросов
        indexes = [
            models.Index(fields=['session_id', 'created_at']),
            models.Index(fields=['session_id', 'expires_at']),
            models.Index(fields=['code']),  # Для быстрого поиска по коду
            models.Index(fields=['is_deleted', 'expires_at']),  # Для очистки истекших файлов
            models.Index(fields=['download_count']),  # Для популярных файлов
            models.Index(fields=['created_at']),  # Для сортировки по дате
            models.Index(fields=['file_size']),  # Для фильтрации по размеру
            models.Index(fields=['is_protected']),  # Для защищенных файлов
        ]
    
    def __str__(self):
        return f"{self.code} - {self.filename}"
    
    def save(self, *args, **kwargs):
        """Переопределяем save для автоматической генерации QR кода"""
        if not self.pk:  # Только при создании нового файла
            self.generate_qr_code()
        super().save(*args, **kwargs)
    
    def generate_qr_code(self):
        """Генерирует QR код со ссылкой на файл"""
        from django.urls import reverse
        # Используем SITE_BASE_URL из настроек и корректный namespaced url
        base = getattr(settings, 'SITE_BASE_URL', 'http://localhost:8000')
        file_url = f"{base}{reverse('files:file_detail', kwargs={'code': self.code})}"
        
        # Генерируем QR код
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=settings.QR_CODE_SIZE,
            border=4,
        )
        qr.add_data(file_url)
        qr.make(fit=True)
        
        # Создаем изображение
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Сохраняем в BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Сохраняем как ImageField
        self.qr_code.save(f'qr_{self.code}.png', ContentFile(buffer.getvalue()), save=False)
    
    def get_file_size_mb(self):
        """Возвращает размер файла в мегабайтах"""
        return round(self.file_size / (1024 * 1024), 2)
    
    def is_expired(self):
        """Проверяет, истек ли срок действия файла"""
        # Постоянные файлы никогда не истекают
        if self.is_permanent:
            return False
        return timezone.now() > self.expires_at
    
    def increment_download_count(self):
        """Увеличивает счетчик скачиваний"""
        self.download_count += 1
        self.last_downloaded = timezone.now()
        self.save(update_fields=['download_count', 'last_downloaded'])
    
    def get_file_type(self):
        """Определяет тип файла на основе расширения"""
        import mimetypes
        
        # Получаем расширение файла
        _, ext = os.path.splitext(self.filename.lower())
        
        # Определяем MIME тип
        mime_type, _ = mimetypes.guess_type(self.filename)
        
        # Категории файлов
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico']:
            return 'image'
        elif ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v']:
            return 'video'
        elif ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a']:
            return 'audio'
        elif ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt']:
            return 'document'
        elif ext in ['.xls', '.xlsx', '.csv', '.ods']:
            return 'spreadsheet'
        elif ext in ['.ppt', '.pptx', '.odp']:
            return 'presentation'
        elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2']:
            return 'archive'
        elif ext in ['.py', '.js', '.html', '.css', '.php', '.java', '.cpp', '.c', '.h']:
            return 'code'
        elif ext in ['.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm']:
            return 'executable'
        else:
            return 'other'
    
    def get_file_type_icon(self):
        """Возвращает иконку FontAwesome для типа файла"""
        file_type = self.get_file_type()
        
        icon_map = {
            'image': 'fas fa-image',
            'video': 'fas fa-video',
            'audio': 'fas fa-music',
            'document': 'fas fa-file-alt',
            'spreadsheet': 'fas fa-file-excel',
            'presentation': 'fas fa-file-powerpoint',
            'archive': 'fas fa-file-archive',
            'code': 'fas fa-file-code',
            'executable': 'fas fa-cog',
            'other': 'fas fa-file'
        }
        
        return icon_map.get(file_type, 'fas fa-file')
    
    def get_file_type_name(self):
        """Возвращает человекочитаемое название типа файла"""
        file_type = self.get_file_type()
        
        name_map = {
            'image': 'Изображение',
            'video': 'Видео',
            'audio': 'Аудио',
            'document': 'Документ',
            'spreadsheet': 'Таблица',
            'presentation': 'Презентация',
            'archive': 'Архив',
            'code': 'Код',
            'executable': 'Программа',
            'other': 'Файл'
        }
        
        return name_map.get(file_type, 'Файл')
    
    def get_compressed_pdf_size_mb(self):
        """Возвращает размер сжатого PDF в мегабайтах"""
        if self.compressed_pdf_size:
            return round(self.compressed_pdf_size / (1024 * 1024), 2)
        return 0
    
    def has_compressed_pdf(self):
        """Проверяет, есть ли сжатая версия PDF"""
        return bool(self.compressed_pdf and self.compressed_pdf_size)
    
    def get_compression_ratio(self):
        """Возвращает коэффициент сжатия в процентах"""
        if not self.has_compressed_pdf() or not self.file_size:
            return 0
        
        original_size = self.file_size
        compressed_size = self.compressed_pdf_size
        
        if compressed_size >= original_size:
            return 0
        
        return round((1 - compressed_size / original_size) * 100, 1)
    
    def get_file_type_color(self):
        """Возвращает цвет для типа файла (Bootstrap классы)"""
        file_type = self.get_file_type()
        
        color_map = {
            'image': 'text-info',
            'video': 'text-danger',
            'audio': 'text-warning',
            'document': 'text-primary',
            'spreadsheet': 'text-success',
            'presentation': 'text-warning',
            'archive': 'text-secondary',
            'code': 'text-dark',
            'executable': 'text-danger',
            'other': 'text-muted'
        }
        
        return color_map.get(file_type, 'text-muted')
    
    def get_remaining_time(self):
        """Возвращает оставшееся время жизни файла"""
        if self.is_expired():
            return "Файл истек"
        
        remaining = self.expires_at - timezone.now()
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        
        if hours > 0:
            return f"{hours}ч {minutes}м"
        else:
            return f"{minutes}м"
    
    def delete(self, *args, **kwargs):
        """Удаляет физический файл и запись из базы данных"""
        # Постоянные файлы не удаляются
        if self.is_permanent:
            return
        
        # Удаляем физические файлы
        if self.file:
            try:
                if os.path.isfile(self.file.path):
                    os.remove(self.file.path)
            except (OSError, IOError) as e:
                # Логируем ошибку, но не прерываем удаление
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Не удалось удалить файл {self.file.path}: {e}")
        
        if self.qr_code:
            try:
                if os.path.isfile(self.qr_code.path):
                    os.remove(self.qr_code.path)
            except (OSError, IOError) as e:
                # Логируем ошибку, но не прерываем удаление
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Не удалось удалить QR код {self.qr_code.path}: {e}")
        
        if self.compressed_pdf:
            try:
                if os.path.isfile(self.compressed_pdf.path):
                    os.remove(self.compressed_pdf.path)
            except (OSError, IOError) as e:
                # Логируем ошибку, но не прерываем удаление
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Не удалось удалить сжатый PDF {self.compressed_pdf.path}: {e}")
        
        # Полностью удаляем запись из базы данных для освобождения кода
        super().delete(*args, **kwargs)
