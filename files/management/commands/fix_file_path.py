from django.core.management.base import BaseCommand
from files.models import File
import os


class Command(BaseCommand):
    help = 'Исправляет путь к файлу в базе данных'

    def add_arguments(self, parser):
        parser.add_argument('code', type=str, help='Код файла')
        parser.add_argument('new_path', type=str, help='Новый путь к файлу')

    def handle(self, *args, **options):
        code = options['code']
        new_path = options['new_path']

        try:
            file_obj = File.objects.get(code=code)
            
            # Проверяем, существует ли файл по новому пути
            if os.path.exists(new_path):
                file_obj.file.name = new_path
                file_obj.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Путь к файлу {code} обновлен!')
                )
                self.stdout.write(f'Новый путь: {file_obj.file.name}')
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Файл {new_path} не найден!')
                )
                
        except File.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ Файл с кодом {code} не найден!')
            )
