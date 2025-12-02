"""
Утилиты для работы с PDF файлами, включая сжатие и оптимизацию.
"""

import os
import logging
from django.conf import settings
from django.core.files.base import ContentFile
from io import BytesIO

logger = logging.getLogger(__name__)

def compress_pdf(input_path, output_path=None, quality=75, max_size_mb=10):
    """
    Сжимает PDF файл для веб-отображения.
    
    Args:
        input_path (str): Путь к исходному PDF файлу
        output_path (str, optional): Путь для сохранения сжатого файла
        quality (int): Качество сжатия (1-100, по умолчанию 75)
        max_size_mb (int): Максимальный размер в МБ (по умолчанию 10)
    
    Returns:
        tuple: (успех, путь_к_файлу, размер_файла) или (False, None, 0)
    """
    try:
        import fitz  # PyMuPDF
        
        # Открываем исходный PDF
        doc = fitz.open(input_path)
        
        # Проверяем размер исходного файла
        original_size = os.path.getsize(input_path)
        original_size_mb = original_size / (1024 * 1024)
        
        logger.info(f"Сжимаем PDF: {input_path} (исходный размер: {original_size_mb:.2f} МБ)")
        
        # Если файл уже меньше максимального размера, возвращаем оригинал
        if original_size_mb <= max_size_mb:
            logger.info(f"PDF уже достаточно мал ({original_size_mb:.2f} МБ), сжатие не требуется")
            return True, input_path, original_size
        
        # Создаем новый документ для сжатой версии
        compressed_doc = fitz.open()
        
        # Копируем страницы с оптимизацией
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Получаем изображение страницы с пониженным качеством
            mat = fitz.Matrix(0.8, 0.8)  # Уменьшаем разрешение на 20%
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Конвертируем в изображение
            img_data = pix.tobytes("png")
            
            # Создаем новую страницу с изображением
            new_page = compressed_doc.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(page.rect, pixmap=pix)
        
        # Если не указан путь вывода, создаем временный файл
        if not output_path:
            output_path = input_path.replace('.pdf', '_compressed.pdf')
        
        # Сохраняем сжатый PDF
        compressed_doc.save(output_path, garbage=4, deflate=True, clean=True)
        compressed_doc.close()
        doc.close()
        
        # Проверяем размер сжатого файла
        compressed_size = os.path.getsize(output_path)
        compressed_size_mb = compressed_size / (1024 * 1024)
        
        # Вычисляем коэффициент сжатия
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        logger.info(f"PDF сжат: {compressed_size_mb:.2f} МБ (сжатие: {compression_ratio:.1f}%)")
        
        # Если сжатие не дало результата, возвращаем оригинал
        if compressed_size >= original_size:
            logger.warning("Сжатие не дало результата, используем оригинал")
            os.remove(output_path)
            return True, input_path, original_size
        
        return True, output_path, compressed_size
        
    except ImportError:
        logger.error("PyMuPDF не установлен. Установите: pip install PyMuPDF")
        return False, None, 0
    except Exception as e:
        logger.error(f"Ошибка при сжатии PDF {input_path}: {str(e)}")
        return False, None, 0

def create_pdf_thumbnail(pdf_path, thumbnail_path=None, size=(200, 200)):
    """
    Создает миниатюру для PDF файла.
    
    Args:
        pdf_path (str): Путь к PDF файлу
        thumbnail_path (str, optional): Путь для сохранения миниатюры
        size (tuple): Размер миниатюры (ширина, высота)
    
    Returns:
        tuple: (успех, путь_к_миниатюре) или (False, None)
    """
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        
        # Открываем PDF
        doc = fitz.open(pdf_path)
        
        # Получаем первую страницу
        page = doc[0]
        
        # Создаем изображение страницы
        mat = fitz.Matrix(0.5, 0.5)  # Уменьшаем для миниатюры
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Конвертируем в PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(BytesIO(img_data))
        
        # Изменяем размер
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Если не указан путь, создаем временный файл
        if not thumbnail_path:
            thumbnail_path = pdf_path.replace('.pdf', '_thumb.png')
        
        # Сохраняем миниатюру
        img.save(thumbnail_path, 'PNG', optimize=True)
        
        doc.close()
        
        logger.info(f"Создана миниатюра PDF: {thumbnail_path}")
        return True, thumbnail_path
        
    except ImportError:
        logger.error("PyMuPDF или Pillow не установлены")
        return False, None
    except Exception as e:
        logger.error(f"Ошибка при создании миниатюры PDF {pdf_path}: {str(e)}")
        return False, None

def get_pdf_info(pdf_path):
    """
    Получает информацию о PDF файле.
    
    Args:
        pdf_path (str): Путь к PDF файлу
    
    Returns:
        dict: Информация о PDF (количество страниц, размер, etc.)
    """
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(pdf_path)
        
        info = {
            'pages': len(doc),
            'size_bytes': os.path.getsize(pdf_path),
            'size_mb': os.path.getsize(pdf_path) / (1024 * 1024),
            'title': doc.metadata.get('title', ''),
            'author': doc.metadata.get('author', ''),
            'creator': doc.metadata.get('creator', ''),
            'producer': doc.metadata.get('producer', ''),
        }
        
        doc.close()
        return info
        
    except ImportError:
        logger.error("PyMuPDF не установлен")
        return {}
    except Exception as e:
        logger.error(f"Ошибка при получении информации о PDF {pdf_path}: {str(e)}")
        return {}

def should_compress_pdf(file_path, max_size_mb=10):
    """
    Определяет, нужно ли сжимать PDF файл.
    
    Args:
        file_path (str): Путь к PDF файлу
        max_size_mb (int): Максимальный размер в МБ
    
    Returns:
        bool: True если файл нужно сжать
    """
    try:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        return file_size_mb > max_size_mb
    except Exception:
        return False
