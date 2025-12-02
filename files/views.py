from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404, JsonResponse, FileResponse
from django.contrib import messages
from django.utils.translation import gettext as _
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.urls import reverse
from django_ratelimit.decorators import ratelimit
from django.contrib.sitemaps import Sitemap
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.core.files.base import ContentFile
import random
import string
from datetime import timedelta
import os
import subprocess
import shutil
import mimetypes

from .models import File
from .forms import FileUploadForm, PasswordForm, FileEditForm
from .pdf_utils import compress_pdf, should_compress_pdf


def generate_unique_code():
    """
    Генерирует уникальный 6-значный числовой код для файла.
    """
    while True:
        # Генерируем код из 6 цифр
        code = ''.join(random.choices(string.digits, k=6))
        
        # Проверяем уникальность
        if not File.objects.filter(code=code).exists():
            return code


@ratelimit(key='ip', rate='10/m', method=['POST'])
def home(request):
    """
    Главная страница с формой загрузки файлов.
    """
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            
            # Возвращаем ошибки валидации для AJAX запросов
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors,
                    'non_field_errors': form.non_field_errors()
                })
        if form.is_valid():
            # Создаем новый файл
            file_instance = form.save(commit=False)
            
            # Устанавливаем имя файла и размер
            file_instance.filename = form.cleaned_data['file'].name
            file_instance.file_size = form.cleaned_data['file'].size
            
            # Генерируем или используем кастомный код
            custom_code = form.cleaned_data.get('custom_code')
            if custom_code:
                file_instance.code = custom_code
            else:
                file_instance.code = generate_unique_code()
            
            # Устанавливаем пароль и защиту
            password = form.cleaned_data.get('password')
            
            # Если есть пароль, то файл защищен
            if password:
                file_instance.password = make_password(password)
                file_instance.is_protected = True
            else:
                file_instance.is_protected = False
            
            # Связываем файл с анонимной сессией пользователя
            if hasattr(request, 'anonymous_session_id'):
                file_instance.session_id = request.anonymous_session_id
            
            # Устанавливаем время истечения (24 часа)
            file_instance.expires_at = timezone.now() + timedelta(hours=settings.FILE_EXPIRY_HOURS)
            
            # Сохраняем файл
            file_instance.save()
            
            # Если это PDF файл, пытаемся сжать его
            if file_instance.filename.lower().endswith('.pdf'):
                try:
                    if should_compress_pdf(file_instance.file.path, max_size_mb=10):
                        success, compressed_path, compressed_size = compress_pdf(
                            file_instance.file.path,
                            quality=75,
                            max_size_mb=10
                        )
                        
                        if success and compressed_path and compressed_size:
                            # Сохраняем сжатую версию
                            with open(compressed_path, 'rb') as f:
                                file_instance.compressed_pdf.save(
                                    f"compressed_{file_instance.filename}",
                                    ContentFile(f.read()),
                                    save=True
                                )
                            
                            file_instance.compressed_pdf_size = compressed_size
                            file_instance.save(update_fields=['compressed_pdf', 'compressed_pdf_size'])
                            
                            # Удаляем временный файл
                            if compressed_path != file_instance.file.path:
                                os.remove(compressed_path)
                            
                            # Логируем успешное сжатие
                            import logging
                            logger = logging.getLogger(__name__)
                            original_mb = file_instance.file_size / (1024 * 1024)
                            compressed_mb = compressed_size / (1024 * 1024)
                            ratio = (1 - compressed_size / file_instance.file_size) * 100
                            logger.info(f"PDF сжат: {file_instance.code} - {original_mb:.1f}MB → {compressed_mb:.1f}MB ({ratio:.1f}%)")
                except Exception as e:
                    # Логируем ошибку, но не прерываем загрузку
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Не удалось сжать PDF {file_instance.code}: {str(e)}")
            
            # Возвращаем JSON ответ для показа модального окна
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Добавляем отладочную информацию
                response_data = {
                    'success': True,
                    'code': file_instance.code,
                    'url': request.build_absolute_uri(
                        reverse('files:file_detail', kwargs={'code': file_instance.code})
                    ),
                    'download_url': request.build_absolute_uri(
                        reverse('files:download_file', kwargs={'code': file_instance.code})
                    ),
                    'qr_url': request.build_absolute_uri(file_instance.qr_code.url) if file_instance.qr_code else None,
                    'expires_at': file_instance.expires_at.isoformat(),
                    'file_size': file_instance.file_size,
                    'filename': file_instance.filename,
                    'session_id': file_instance.session_id,
                    'is_protected': file_instance.is_protected,
                    'file_type': file_instance.get_file_type(),
                    'file_type_name': file_instance.get_file_type_name(),
                    'file_type_icon': file_instance.get_file_type_icon(),
                    'debug_info': {
                        'custom_code_provided': bool(custom_code),
                        'password_provided': bool(password),
                        'has_session': hasattr(request, 'anonymous_session_id'),
                        'session_id_value': getattr(request, 'anonymous_session_id', None)
                    }
                }
                return JsonResponse(response_data)
            
            # Для обычных запросов показываем сообщение и перенаправляем
            messages.success(request, _('Файл успешно загружен! Код: %(code)s') % {'code': file_instance.code})
            return redirect('files:file_detail', code=file_instance.code)
    else:
        form = FileUploadForm()
    
    # Получаем последние загруженные файлы для отображения (с кешированием)
    # Показываем только файлы текущего пользователя (если есть session_id)
    if hasattr(request, 'anonymous_session_id') and request.anonymous_session_id:
        # Кешируем недавние файлы на 2 минуты
        cache_key = f'recent_files_{request.anonymous_session_id}'
        recent_files = cache.get(cache_key)
        
        if recent_files is None:
            recent_files = list(File.objects.filter(
                session_id=request.anonymous_session_id,
                expires_at__gt=timezone.now(),
                is_deleted=False
            ).order_by('-created_at')[:3])
            cache.set(cache_key, recent_files, 120)  # 2 минуты
    else:
        # Если session_id нет, показываем пустой список
        recent_files = []
    
    # Статистика для главной страницы (с кешированием)
    
    # Кешируем статистику на 5 минут
    cache_key = f'home_stats_{request.anonymous_session_id or "anonymous"}'
    cached_stats = cache.get(cache_key)
    
    if cached_stats is None:
        total_files = File.objects.count()  # Все файлы (включая удаленные)
        total_downloads = File.objects.aggregate(Sum('download_count')).get('download_count__sum') or 0
        
        cached_stats = {
            'total_files': total_files,
            'total_downloads': total_downloads,
        }
        cache.set(cache_key, cached_stats, 300)  # 5 минут
    else:
        total_files = cached_stats['total_files']
        total_downloads = cached_stats['total_downloads']
    active_files = File.objects.filter(expires_at__gt=timezone.now(), is_deleted=False).count()
    protected_files = File.objects.filter(is_protected=True, expires_at__gt=timezone.now(), is_deleted=False).count()
    
    # Количество загруженных файлов за сегодня
    today = timezone.now().date()
    today_files = File.objects.filter(
        created_at__date=today
    ).count()

    context = {
        'form': form,
        'recent_files': recent_files,
        'max_file_size_mb': settings.MAX_FILE_SIZE // (1024 * 1024),
        'expiry_hours': settings.FILE_EXPIRY_HOURS,
        'total_files': total_files,
        'total_downloads': total_downloads,
        'active_files': active_files,
        'protected_files': protected_files,
        'today_files': today_files,
    }
    
    return render(request, 'files/home.html', context)


def file_detail(request, code):
    """
    Страница просмотра файла по коду.
    """
    # Нормализуем код (верхний регистр, убираем пробелы)
    code = code.upper().strip()
    
    file_instance = get_object_or_404(File, code=code)
    
    # Проверяем, не удален ли файл
    if file_instance.is_deleted:
        raise Http404("Файл не найден")
    
    # Проверяем, не истек ли файл (постоянные файлы никогда не истекают)
    if not file_instance.is_permanent and file_instance.is_expired():
        messages.error(request, _('Файл истек и больше недоступен.'))
        return redirect('files:home')
    
    # Если файл защищен паролем, всегда запрашиваем пароль
    if file_instance.is_protected:
        if request.method == 'POST':
            password_form = PasswordForm(file_instance, request.POST)
            if password_form.is_valid():
                # Пароль верный — помечаем файл как авторизованный в текущей сессии
                authorized = request.session.get('authorized_files', {})
                authorized[file_instance.code] = True
                request.session['authorized_files'] = authorized
                request.session.modified = True
                # Продолжаем выполнение (покажем карточку файла)
            else:
                messages.error(request, _('Неверный пароль.'))
                return render(request, 'files/password_required.html', {
                    'file': file_instance,
                    'form': password_form
                })
        else:
            # Всегда показываем форму пароля для защищенных файлов
            password_form = PasswordForm(file_instance)
            return render(request, 'files/password_required.html', {
                'file': file_instance,
                'form': password_form
            })
    
    # На странице деталей не изменяем счетчик скачиваний
    
    context = {
        'file': file_instance,
        'file_url': request.build_absolute_uri(reverse('files:file_detail', kwargs={'code': file_instance.code})),
    }
    
    return render(request, 'files/file_detail.html', context)


@ratelimit(key='ip', rate='20/m', method=['GET'])
def download_file(request, code):
    """
    Скачивание файла по коду.
    """
    file_instance = get_object_or_404(File, code=code.upper())
    
    # Проверяем, не удален ли файл
    if file_instance.is_deleted:
        raise Http404("Файл не найден")
    
    # Проверяем, не истек ли файл (постоянные файлы никогда не истекают)
    if not file_instance.is_permanent and file_instance.is_expired():
        raise Http404("Файл истек")
    
    # Если файл защищен паролем, проверяем пароль/авторизацию
    if file_instance.is_protected:
        authorized = request.session.get('authorized_files', {})
        if not authorized.get(file_instance.code):
            # Дополнительно поддерживаем разовый доступ через параметр ?password=
            password = request.GET.get('password')
            if not password:
                # Перенаправляем на карточку файла для ввода пароля
                return redirect('files:file_detail', code=file_instance.code)
            from django.contrib.auth.hashers import check_password
            if not check_password(password, file_instance.password or ''):
                raise Http404(_('Неверный пароль'))
            # Разрешаем и запоминаем в сессии
            authorized[file_instance.code] = True
            request.session['authorized_files'] = authorized
            request.session.modified = True
    
    # Увеличиваем счетчик скачиваний
    file_instance.increment_download_count()

    # Потоковая отдача файла
    file_stream = file_instance.file.open('rb')
    response = FileResponse(file_stream, as_attachment=True, filename=file_instance.filename)
    response['Content-Length'] = file_instance.file_size
    return response


@ratelimit(key='ip', rate='20/m', method=['GET'])
def view_file(request, code):
    """
    Просмотр (inline) файла по коду. Для поддерживаемых браузером типов откроется предпросмотр.
    """
    file_instance = get_object_or_404(File, code=code.upper())
    
    # Базовые проверки
    if file_instance.is_deleted:
        raise Http404(_('Файл не найден'))
    if not file_instance.is_permanent and file_instance.is_expired():
        raise Http404(_('Файл истек'))

    # Защита паролем
    if file_instance.is_protected:
        authorized = request.session.get('authorized_files', {})
        if not authorized.get(file_instance.code):
            # Требуем ввод пароля на карточке файла
            return redirect('files:file_detail', code=file_instance.code)

    # Определяем стратегию предпросмотра
    _, ext = os.path.splitext(file_instance.filename.lower())
    doc_like_exts = {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp'}
    image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg', '.ico'}
    text_exts = {'.txt', '.csv', '.log', '.md', '.json', '.xml', '.html', '.css', '.js', '.py', '.php', '.java', '.cpp', '.c', '.h'}

    # Для PDF и изображений — отдаём как есть inline
    if ext == '.pdf' or ext in image_exts:
        # Для PDF используем сжатую версию, если она есть
        if ext == '.pdf' and file_instance.has_compressed_pdf():
            file_stream = file_instance.compressed_pdf.open('rb')
            response = FileResponse(file_stream, as_attachment=False, filename=file_instance.filename)
            response['Content-Length'] = file_instance.compressed_pdf_size
            response['Content-Type'] = 'application/pdf'
            # Добавляем заголовок, указывающий что это сжатая версия
            response['X-Compressed-PDF'] = 'true'
            response['X-Original-Size'] = str(file_instance.file_size)
            response['X-Compressed-Size'] = str(file_instance.compressed_pdf_size)
        else:
            file_stream = file_instance.file.open('rb')
            response = FileResponse(file_stream, as_attachment=False, filename=file_instance.filename)
            response['Content-Length'] = file_instance.file_size
            if ext == '.pdf':
                response['Content-Type'] = 'application/pdf'
        return response

    # Для текстовых файлов — показываем как plain text
    if ext in text_exts:
        try:
            file_stream = file_instance.file.open('r', encoding='utf-8')
            content = file_stream.read()
            file_stream.close()
            
            # Ограничиваем размер для предпросмотра (1MB)
            if len(content) > 1024 * 1024:
                content = content[:1024 * 1024] + "\n\n... (файл обрезан, размер превышает 1MB)"
            
            response = HttpResponse(content, content_type='text/plain; charset=utf-8')
            response['Content-Disposition'] = f'inline; filename="{file_instance.filename}"'
            return response
        except UnicodeDecodeError:
            # Если не удается декодировать как UTF-8, отдаем как бинарный
            file_stream = file_instance.file.open('rb')
            response = FileResponse(file_stream, as_attachment=False, filename=file_instance.filename)
            response['Content-Type'] = 'application/octet-stream'
            return response

    # Для офисных форматов — пробуем конвертировать в PDF (кэшируем)
    if ext in doc_like_exts:
        previews_dir = os.path.join(settings.MEDIA_ROOT, 'previews')
        os.makedirs(previews_dir, exist_ok=True)
        preview_pdf_path = os.path.join(previews_dir, f'{file_instance.code}.pdf')

        # Нужна повторная конвертация, если превью нет или исходник новее
        need_convert = True
        if os.path.exists(preview_pdf_path):
            try:
                src_mtime = os.path.getmtime(file_instance.file.path)
                pdf_mtime = os.path.getmtime(preview_pdf_path)
                need_convert = pdf_mtime < src_mtime
            except Exception:
                need_convert = True

        if need_convert:
            libreoffice = shutil.which('libreoffice') or shutil.which('soffice')
            if not libreoffice:
                # Нет LibreOffice — fallback: отдаём оригинал на скачивание
                return redirect('files:download_file', code=file_instance.code)
            try:
                # Конвертируем через LibreOffice в headless режиме
                subprocess.check_call([
                    libreoffice,
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', previews_dir,
                    file_instance.file.path,
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                return redirect('files:download_file', code=file_instance.code)

        # Отдаём PDF inline
        if os.path.exists(preview_pdf_path):
            preview_stream = open(preview_pdf_path, 'rb')
            response = FileResponse(preview_stream, as_attachment=False, filename=os.path.basename(preview_pdf_path))
            response['Content-Type'] = 'application/pdf'
            try:
                response['Content-Length'] = os.path.getsize(preview_pdf_path)
            except Exception:
                pass
            return response

    # Для остальных типов — пробуем отдать inline по mime, иначе скачивание
    file_stream = file_instance.file.open('rb')
    mime, _ = mimetypes.guess_type(file_instance.filename)
    response = FileResponse(file_stream, as_attachment=False, filename=file_instance.filename)
    if mime:
        response['Content-Type'] = mime
    try:
        response['Content-Length'] = file_instance.file_size
    except Exception:
        pass
    return response


def edit_file(request, code):
    """
    Редактирование информации о файле.
    """
    file_instance = get_object_or_404(File, code=code.upper())
    
    # Проверяем, не удален ли файл
    if file_instance.is_deleted:
        raise Http404("Файл не найден")
    
    # Проверяем, не истек ли файл
    if file_instance.is_expired():
        messages.error(request, _('Файл истек и больше недоступен для редактирования.'))
        return redirect('files:home')
    
    if request.method == 'POST':
        form = FileEditForm(request.POST, instance=file_instance)
        if form.is_valid():
            # Обновляем код если указан новый
            new_code = form.cleaned_data.get('new_code')
            if new_code:
                file_instance.code = new_code
                file_instance.generate_qr_code()  # Перегенерируем QR код
            
            # Обновляем пароль
            new_password = form.cleaned_data.get('new_password')
            if new_password is not None:  # Пустая строка означает убрать пароль
                if new_password:
                    file_instance.password = make_password(new_password)
                    file_instance.is_protected = True
                else:
                    file_instance.password = None
                    file_instance.is_protected = False
            
            file_instance.save()
            messages.success(request, _('Информация о файле обновлена!'))
            return redirect('files:file_detail', code=file_instance.code)
        else:
            # Возвращаем ошибки валидации для AJAX запросов
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors,
                    'non_field_errors': form.non_field_errors()
                })
    else:
        form = FileEditForm(instance=file_instance)
    
    context = {
        'file': file_instance,
        'form': form,
    }
    
    return render(request, 'files/edit_file.html', context)


def delete_file(request, code):
    """
    Удаление файла.
    """
    file_instance = get_object_or_404(File, code=code.upper())
    
    # Проверяем, не удален ли файл
    if file_instance.is_deleted:
        raise Http404("Файл не найден")
    
    # Проверяем, не истек ли файл
    if file_instance.is_expired():
        messages.error(request, _('Файл истек и больше недоступен для удаления.'))
        return redirect('files:home')
    
    if request.method == 'POST':
        # Используем наш кастомный метод удаления
        file_instance.delete()
        messages.success(request, _('Файл успешно удален!'))
        return redirect('files:home')
    
    context = {
        'file': file_instance,
    }
    
    return render(request, 'files/delete_file.html', context)


def check_code_availability(request):
    """
    Проверка доступности кода для файла.
    """
    code = request.GET.get('code', '').strip()
    
    if not code:
        return JsonResponse({'available': False, 'error': _('Код не указан')})
    
    # Проверяем, не занят ли код
    is_occupied = File.objects.filter(code=code).exists()
    
    return JsonResponse({
        'available': not is_occupied,
        'code': code,
        'occupied': is_occupied
    })


def check_preview_support(request):
    """
    Проверка поддержки предпросмотра файлов на сервере.
    """
    libreoffice_available = bool(shutil.which('libreoffice') or shutil.which('soffice'))
    
    return JsonResponse({
        'libreoffice_available': libreoffice_available,
        'supported_formats': {
            'office': ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp'],
            'images': ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg', 'ico'],
            'text': ['txt', 'csv', 'log', 'md', 'json', 'xml', 'html', 'css', 'js', 'py', 'php', 'java', 'cpp', 'c', 'h'],
            'pdf': ['pdf']
        }
    })


def direct_pdf_view(request, code):
    """
    Прямой просмотр PDF файла по коду (например, /5711).
    Если файл не PDF или защищен паролем, перенаправляет на детальную страницу.
    """
    # Нормализуем код (верхний регистр, убираем пробелы)
    code = code.upper().strip()
    
    file_instance = get_object_or_404(File, code=code)
    
    # Проверяем, не удален ли файл
    if file_instance.is_deleted:
        raise Http404('Файл не найден')
    
    # Проверяем, не истек ли файл (постоянные файлы никогда не истекают)
    if not file_instance.is_permanent and file_instance.is_expired():
        raise Http404('Файл истек')
    
    # Если файл защищен паролем, перенаправляем на детальную страницу
    if file_instance.is_protected:
        return redirect('files:file_detail', code=file_instance.code)
    
    # Проверяем, является ли файл PDF
    _, ext = os.path.splitext(file_instance.filename.lower())
    if ext != '.pdf':
        # Если не PDF, перенаправляем на детальную страницу
        return redirect('files:file_detail', code=file_instance.code)
    
    # Отдаем PDF файл напрямую для просмотра
    try:
        # Используем сжатую версию, если она есть
        if file_instance.has_compressed_pdf():
            file_stream = file_instance.compressed_pdf.open('rb')
            response = FileResponse(file_stream, as_attachment=False, filename=file_instance.filename)
            response['Content-Type'] = 'application/pdf'
            response['Content-Length'] = file_instance.compressed_pdf_size
            response['Content-Disposition'] = f'inline; filename="{file_instance.filename}"'
            response['X-Compressed-PDF'] = 'true'
            response['X-Original-Size'] = str(file_instance.file_size)
            response['X-Compressed-Size'] = str(file_instance.compressed_pdf_size)
        else:
            # Пытаемся открыть файл через Django FileField
            file_stream = file_instance.file.open('rb')
            response = FileResponse(file_stream, as_attachment=False, filename=file_instance.filename)
            response['Content-Type'] = 'application/pdf'
            response['Content-Length'] = file_instance.file_size
            response['Content-Disposition'] = f'inline; filename="{file_instance.filename}"'
        
        # Увеличиваем счетчик просмотров
        file_instance.increment_download_count()
        
        return response
    except (OSError, IOError):
        # Если файл не найден через FileField, пытаемся найти его напрямую
        file_path = file_instance.file.name
        
        # Если файл в папке demo_files, ищем его напрямую
        if file_path.startswith('demo_files/'):
            import os
            from django.conf import settings
            full_path = os.path.join(settings.BASE_DIR, file_path)
            
            if os.path.exists(full_path):
                with open(full_path, 'rb') as f:
                    response = FileResponse(f, as_attachment=False, filename=file_instance.filename)
                    response['Content-Type'] = 'application/pdf'
                    response['Content-Length'] = os.path.getsize(full_path)
                    response['Content-Disposition'] = f'inline; filename="{file_instance.filename}"'
                    
                    # Увеличиваем счетчик просмотров
                    file_instance.increment_download_count()
                    
                    return response
        
        # Для постоянных файлов пробуем найти по оригинальному пути
        if file_instance.is_permanent:
            # Пробуем несколько возможных путей
            possible_paths = [
                "/var/www/filehost/demo_files/uploads/catalog_moscow.pdf",
                os.path.join(settings.BASE_DIR, "demo_files/uploads/catalog_moscow.pdf"),
                os.path.join(settings.MEDIA_ROOT, "demo_files/uploads/catalog_moscow.pdf"),
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'rb') as f:
                        response = FileResponse(f, as_attachment=False, filename=file_instance.filename)
                        response['Content-Type'] = 'application/pdf'
                        response['Content-Length'] = os.path.getsize(path)
                        response['Content-Disposition'] = f'inline; filename="{file_instance.filename}"'
                        
                        # Увеличиваем счетчик просмотров
                        file_instance.increment_download_count()
                        
                        return response
        
        # Если файл не найден, показываем 404
        raise Http404('Файл не найден')


def search_files(request):
    """
    Поиск файлов по коду или имени.
    Показывает только файлы текущего пользователя.
    """
    query = request.GET.get('q', '').strip()
    
    if not query:
        return redirect('files:home')
    
    # Получаем только файлы текущего пользователя
    if hasattr(request, 'anonymous_session_id') and request.anonymous_session_id:
        # Ищем файлы по коду или имени только среди файлов пользователя
        files = File.objects.filter(
            Q(code__icontains=query) | Q(filename__icontains=query),
            session_id=request.anonymous_session_id,
            expires_at__gt=timezone.now(),
            is_deleted=False
        ).order_by('-created_at')
    else:
        # Если session_id нет, показываем пустой список
        files = File.objects.none()
    
    # Пагинация
    paginator = Paginator(files, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'query': query,
        'page_obj': page_obj,
        'files_count': files.count(),
        'has_session': hasattr(request, 'anonymous_session_id') and request.anonymous_session_id,
    }
    
    return render(request, 'files/search_results.html', context)


def recent_files(request):
    """
    Страница с последними загруженными файлами.
    Показывает только файлы текущего пользователя.
    """
    # Получаем только файлы текущего пользователя
    if hasattr(request, 'anonymous_session_id') and request.anonymous_session_id:
        files = File.objects.filter(
            session_id=request.anonymous_session_id,
            expires_at__gt=timezone.now(),
            is_deleted=False
        ).order_by('-created_at')
        
        # Проверяем, есть ли активные файлы
        has_files = files.exists()
    else:
        # Если session_id нет, показываем пустой список
        files = File.objects.none()
        has_files = False
    
    # Пагинация только если есть файлы
    if has_files:
        paginator = Paginator(files, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
    else:
        page_obj = None
    
    context = {
        'page_obj': page_obj,
        'has_session': hasattr(request, 'anonymous_session_id') and request.anonymous_session_id,
        'has_files': has_files,
        'total_files': files.count() if has_files else 0,
    }
    
    return render(request, 'files/recent_files.html', context)


@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(key='ip', rate='10/m', method=['POST'])
def api_upload(request):
    """
    API endpoint для загрузки файлов (для будущего развития).
    """
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Создаем файл аналогично обычной загрузке
            file_instance = form.save(commit=False)
            file_instance.filename = form.cleaned_data['file'].name
            file_instance.file_size = form.cleaned_data['file'].size
            
            custom_code = form.cleaned_data.get('custom_code')
            if custom_code:
                file_instance.code = custom_code
            else:
                file_instance.code = generate_unique_code()
            
            password = form.cleaned_data.get('password')
            if password:
                file_instance.password = make_password(password)
                file_instance.is_protected = True
            
            # Связываем файл с анонимной сессией пользователя
            if hasattr(request, 'anonymous_session_id'):
                file_instance.session_id = request.anonymous_session_id
            
            file_instance.expires_at = timezone.now() + timedelta(hours=settings.FILE_EXPIRY_HOURS)
            file_instance.save()
            
            return JsonResponse({
                'success': True,
                'code': file_instance.code,
                'url': request.build_absolute_uri(
                    reverse('files:file_detail', kwargs={'code': file_instance.code})
                ),
                'download_url': request.build_absolute_uri(
                    reverse('files:download_file', kwargs={'code': file_instance.code})
                ),
                'qr_url': request.build_absolute_uri(file_instance.qr_code.url) if file_instance.qr_code else None,
                'expires_at': file_instance.expires_at.isoformat(),
                'file_size': file_instance.file_size,
                'filename': file_instance.filename,
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


# Sitemap классы
class StaticViewSitemap(Sitemap):
    """
    Sitemap для статических страниц сайта.
    """
    changefreq = 'daily'
    priority = 0.9
    
    def items(self):
        return ['files:home', 'files:recent_files']
    
    def location(self, item):
        return reverse(item)


class FileSitemap(Sitemap):
    """
    Sitemap для публичных файлов (без паролей).
    """
    changefreq = 'daily'
    priority = 0.7
    
    def items(self):
        # Возвращаем только публичные файлы (без паролей), которые не истекли
        return File.objects.filter(
            is_protected=False,
            expires_at__gt=timezone.now(),
            is_deleted=False
        ).order_by('-created_at')[:1000]  # Ограничиваем количество для производительности
    
    def lastmod(self, obj):
        return obj.created_at
    
    def location(self, obj):
        return reverse('files:file_detail', kwargs={'code': obj.code})


# Словарь sitemaps для urls.py
sitemaps = {
    'static': StaticViewSitemap,
    'files': FileSitemap,
}


def robots_txt(request):
    """
    Возвращает robots.txt файл.
    """
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    
    content = render_to_string('robots.txt', {
        'domain': request.get_host(),
    })
    
    return HttpResponse(content, content_type='text/plain')


def sitemap_xml(request):
    """
    Возвращает sitemap.xml файл.
    """
    from django.http import HttpResponse
    from django.contrib.sites.models import Site
    
    try:
        site = Site.objects.get_current()
        domain = site.domain
    except Site.DoesNotExist:
        domain = '0123.ru'
    
    # Генерируем XML
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    # Статические страницы
    static_pages = [
        ('', '1.0', 'daily'),  # Главная страница
        ('/files/recent/', '0.8', 'daily'),  # Мои файлы
    ]
    
    for url, priority, changefreq in static_pages:
        xml += f'  <url>\n'
        xml += f'    <loc>https://{domain}{url}</loc>\n'
        xml += f'    <changefreq>{changefreq}</changefreq>\n'
        xml += f'    <priority>{priority}</priority>\n'
        xml += f'  </url>\n'
    
    # Публичные файлы (без паролей)
    public_files = File.objects.filter(
        is_protected=False,
        expires_at__gt=timezone.now(),
        is_deleted=False
    ).order_by('-created_at')[:1000]  # Ограничиваем количество
    
    for file in public_files:
        xml += f'  <url>\n'
        xml += f'    <loc>https://{domain}/files/{file.code}/</loc>\n'
        xml += f'    <lastmod>{file.created_at.strftime("%Y-%m-%d")}</lastmod>\n'
        xml += f'    <changefreq>daily</changefreq>\n'
        xml += f'    <priority>0.6</priority>\n'
        xml += f'  </url>\n'
    
    # Закрываем XML
    xml += '</urlset>'
    
    return HttpResponse(xml, content_type='application/xml')


# Error handlers
def error_400(request, exception):
    return render(request, '400.html', {'exception': exception}, status=400)


def error_403(request, exception):
    return render(request, '403.html', {'exception': exception}, status=403)


def error_404(request, exception):
    return render(request, '404.html', {'exception': exception}, status=404)


def error_500(request):
    return render(request, '500.html', status=500)


def redirect_to_direct_pdf(request, code):
    """
    Перенаправляет на прямой просмотр PDF файла.
    """
    return redirect('files:direct_pdf_view', code=code)
