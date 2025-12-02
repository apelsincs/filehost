from django.core.management.base import BaseCommand
from django.core.files import File
from files.models import File as FileModel
from django.utils import timezone
from datetime import timedelta
import os


class Command(BaseCommand):
    help = 'Создает постоянный файл с указанным кодом'

    def add_arguments(self, parser):
        parser.add_argument('code', type=str, help='Код файла')
        parser.add_argument('file_path', type=str, help='Путь к файлу на сервере')
        parser.add_argument('--filename', type=str, help='Имя файла (по умолчанию берется из пути)')
        parser.add_argument('--password', type=str, help='Пароль для защиты файла (необязательно)')

    def handle(self, *args, **options):
        code = options['code']
        file_path = options['file_path']
        filename = options.get('filename') or os.path.basename(file_path)
        password = options.get('password')

        # Проверяем, существует ли файл
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'Файл {file_path} не найден!')
            )
            return

        # Проверяем, не существует ли уже файл с таким кодом
        if FileModel.objects.filter(code=code).exists():
            self.stdout.write(
                self.style.ERROR(f'Файл с кодом {code} уже существует!')
            )
            return

        # Получаем размер файла
        file_size = os.path.getsize(file_path)

        # Создаем постоянный файл
        with open(file_path, 'rb') as f:
            django_file = File(f)
            
            file_obj = FileModel(
                code=code,
                filename=filename,
                file_size=file_size,
                is_permanent=True,  # Помечаем как постоянный
                is_protected=bool(password),
                password=password,
                expires_at=timezone.now() + timedelta(days=365*100),  # Устанавливаем дату истечения на 100 лет вперед
            )
            
            # Сохраняем файл
            file_obj.file.save(filename, django_file, save=True)

        self.stdout.write(
            self.style.SUCCESS(f'Постоянный файл {filename} создан с кодом {code}')
        )
        self.stdout.write(f'URL: http://0123.ru/{code}')
        if password:
            self.stdout.write(f'Пароль: {password}')