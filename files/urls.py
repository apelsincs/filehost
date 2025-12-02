from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    # Главная страница
    path('', views.home, name='home'),
    
    # Поиск файлов
    path('search/', views.search_files, name='search_files'),
    
    # Последние файлы
    path('recent/', views.recent_files, name='recent_files'),
    
    # API для загрузки файлов
    path('api/upload/', views.api_upload, name='api_upload'),
    
    # Проверка доступности кода (ВАЖНО: должен быть перед <str:code>/)
    path('api/check-code/', views.check_code_availability, name='check_code_availability'),
    
    # Проверка поддержки предпросмотра
    path('api/preview-support/', views.check_preview_support, name='check_preview_support'),
    
    # Специальный маршрут для прямого просмотра PDF (например, /5711)
    path('<str:code>/', views.direct_pdf_view, name='direct_pdf_view'),
    
    # Просмотр файла по коду (детальная страница)
    path('<str:code>/detail/', views.file_detail, name='file_detail'),
    
    # Скачивание файла
    path('<str:code>/download/', views.download_file, name='download_file'),

    # Просмотр файла (inline)
    path('<str:code>/view/', views.view_file, name='view_file'),
    
    # Редактирование файла
    path('<str:code>/edit/', views.edit_file, name='edit_file'),
    
    # Удаление файла
    path('<str:code>/delete/', views.delete_file, name='delete_file'),
] 