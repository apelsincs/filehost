# 🚀 Развертывание проекта на чистом Ubuntu сервере

Полное пошаговое руководство по развертыванию файлового хостинга на абсолютно новом сервере Ubuntu.

## 📋 Требования

- **ОС:** Ubuntu 20.04 LTS или новее (рекомендуется 22.04 LTS)
- **RAM:** Минимум 2GB (рекомендуется 4GB+)
- **CPU:** 2 ядра (рекомендуется 4+)
- **Диск:** 40GB+ SSD
- **Права:** Доступ root или sudo
- **Сеть:** Статический IP адрес

## 🎯 Шаг 1: Подготовка сервера

### 1.1 Подключение к серверу

```bash
ssh root@YOUR_SERVER_IP
# или
ssh user@YOUR_SERVER_IP
```

### 1.2 Обновление системы

```bash
# Обновить список пакетов
apt update

# Обновить установленные пакеты
apt upgrade -y

# Установить базовые утилиты
apt install -y git curl wget nano htop
```

### 1.3 Создание пользователя для приложения (опционально, но рекомендуется)

```bash
# Создать пользователя www-data если его нет
# Обычно он уже существует в Ubuntu
id www-data

# Если пользователя нет:
# useradd -r -s /bin/false www-data
```

## 🔧 Шаг 2: Установка системных зависимостей

### 2.1 Установка Python и инструментов разработки

```bash
apt install -y python3 python3-pip python3-venv python3-dev \
    build-essential libpq-dev libmagic1 \
    libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev \
    gettext gettext-base
```

**Проверка установки:**
```bash
python3 --version  # Должно быть 3.8+
pip3 --version
```

### 2.2 Установка PostgreSQL

```bash
# Установка PostgreSQL
apt install -y postgresql postgresql-contrib

# Запуск и включение в автозагрузку
systemctl start postgresql
systemctl enable postgresql

# Проверка статуса
systemctl status postgresql
```

### 2.3 Настройка PostgreSQL

```bash
# Переключиться на пользователя postgres
sudo -u postgres psql

# В консоли PostgreSQL выполнить:
CREATE DATABASE filehost;
CREATE USER filehost_user WITH PASSWORD 'ВАШ_НАДЕЖНЫЙ_ПАРОЛЬ';
ALTER ROLE filehost_user SET client_encoding TO 'utf8';
ALTER ROLE filehost_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE filehost_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE filehost TO filehost_user;
ALTER USER filehost_user CREATEDB;
\q

# ВАЖНО: Выдать права на схему public (требуется для PostgreSQL 15+)
sudo -u postgres psql -d filehost << EOF
GRANT ALL ON SCHEMA public TO filehost_user;
GRANT CREATE ON SCHEMA public TO filehost_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO filehost_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO filehost_user;
\q
EOF

# Проверка подключения
sudo -u postgres psql -d filehost -c "SELECT version();"
```

### 2.4 Установка Redis

```bash
# Установка Redis
apt install -y redis-server

# Настройка Redis
sed -i 's/^# maxmemory <bytes>/maxmemory 256mb/' /etc/redis/redis.conf
sed -i 's/^# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf

# Запуск и включение в автозагрузку
systemctl start redis-server
systemctl enable redis-server

# Проверка статуса
systemctl status redis-server

# Проверка подключения
redis-cli ping  # Должно вернуть PONG
```

### 2.5 Установка Nginx

```bash
# Установка Nginx
apt install -y nginx

# Запуск и включение в автозагрузку
systemctl start nginx
systemctl enable nginx

# Проверка статуса
systemctl status nginx

# Проверка веб-сервера (откройте в браузере IP сервера)
curl http://localhost
```

### 2.6 Установка дополнительных инструментов безопасности

```bash
# Установка UFW (файрвол)
apt install -y ufw

# Установка Fail2ban (защита от брутфорса)
apt install -y fail2ban

# Запуск fail2ban
systemctl start fail2ban
systemctl enable fail2ban
```

## 📥 Шаг 3: Получение кода проекта

### 3.1 Создание директории для проекта

```bash
# Создать директорию
mkdir -p /var/www/filehost

# Установить права
chown www-data:www-data /var/www/filehost
```

### 3.2 Клонирование проекта

**Вариант 1: Из Git репозитория**

```bash
cd /var/www
git clone https://github.com/YOUR_USERNAME/filehost.git filehost
# или
git clone YOUR_REPO_URL filehost

cd filehost
chown -R www-data:www-data /var/www/filehost
```

**Вариант 2: Загрузка через SCP**

На локальной машине:
```bash
cd /path/to/your/project
tar -czf filehost.tar.gz --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' .
scp filehost.tar.gz root@YOUR_SERVER_IP:/tmp/
```

На сервере:
```bash
cd /var/www/filehost
tar -xzf /tmp/filehost.tar.gz
rm /tmp/filehost.tar.gz
chown -R www-data:www-data /var/www/filehost
```

**Вариант 3: Копирование вручную**

Просто скопируйте все файлы проекта в `/var/www/filehost/`

## 🐍 Шаг 4: Настройка Python окружения

### 4.1 Создание виртуального окружения

```bash
cd /var/www/filehost

# Создать виртуальное окружение
python3 -m venv venv

# Установить права
chown -R www-data:www-data venv
```

### 4.2 Активация окружения и установка зависимостей

```bash
# Активировать окружение
source venv/bin/activate

# Обновить pip
pip install --upgrade pip

# Установить production зависимости
pip install -r requirements-prod.txt

# Проверка установки
pip list | grep Django
pip list | grep gunicorn
```

## ⚙️ Шаг 5: Настройка Django

### 5.1 Создание .env файла

```bash
cd /var/www/filehost

# Скопировать пример файла
cp env.production .env

# Открыть для редактирования
nano .env
```

**Содержимое .env файла (заполните реальными значениями):**

```env
# Django настройки
DEBUG=False
SECRET_KEY=ВАШ_СУПЕР_СЕКРЕТНЫЙ_КЛЮЧ_СГЕНЕРИРУЙТЕ_ЕГО

# Разрешенные хосты (укажите IP или домен)
ALLOWED_HOSTS=YOUR_SERVER_IP,localhost,127.0.0.1

# База данных PostgreSQL
DB_NAME=filehost
DB_USER=filehost_user
DB_PASSWORD=ВАШ_ПАРОЛЬ_ОТ_POSTGRESQL
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://127.0.0.1:6379/1

# Настройки файлов
MAX_FILE_SIZE=26214400
FILE_EXPIRY_HOURS=24
QR_CODE_SIZE=10

# Безопасность
USE_HTTPS=False  # Измените на True после настройки SSL
SITE_BASE_URL=http://YOUR_SERVER_IP  # Измените на домен когда будет готов

# CSRF (укажите домен когда будет готов)
CSRF_TRUSTED_ORIGINS=http://YOUR_SERVER_IP

# Опционально: Email для уведомлений
ALERT_EMAIL=admin@your-domain.com
LOG_LEVEL=WARNING
```

### 5.2 Генерация SECRET_KEY

```bash
# В активированном виртуальном окружении
source venv/bin/activate

python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Скопируйте сгенерированный ключ и вставьте в `.env` файл вместо `ВАШ_СУПЕР_СЕКРЕТНЫЙ_КЛЮЧ_СГЕНЕРИРУЙТЕ_ЕГО`

### 5.3 Установка прав на .env файл

```bash
chown www-data:www-data .env
chmod 600 .env  # Только владелец может читать
```

### 5.4 Создание директорий для логов и медиа

```bash
cd /var/www/filehost

# Создать директории
mkdir -p logs media/uploads media/qr_codes staticfiles

# Установить права
chown -R www-data:www-data logs media staticfiles
chmod -R 755 media
chmod -R 755 logs
```

### 5.5 Применение миграций базы данных

```bash
cd /var/www/filehost
source venv/bin/activate

# Применить миграции
python manage.py migrate --settings=filehost.settings_prod

# Проверка успешности
python manage.py showmigrations --settings=filehost.settings_prod
```

### 5.6 Создание суперпользователя (опционально, для админки)

```bash
python manage.py createsuperuser --settings=filehost.settings_prod
```

### 5.7 Сбор статических файлов

```bash
python manage.py collectstatic --noinput --settings=filehost.settings_prod

# Проверка
ls -la staticfiles/
```

### 5.8 Компиляция переводов (если используются)

```bash
# Сгенерировать файлы переводов (если нужно)
python manage.py makemessages -l ru --settings=filehost.settings_prod
python manage.py makemessages -l en --settings=filehost.settings_prod

# Скомпилировать переводы
python manage.py compilemessages --settings=filehost.settings_prod
```

## 🔧 Шаг 6: Настройка Gunicorn

### 6.1 Создание директорий для логов

```bash
mkdir -p /var/log/gunicorn
chown www-data:www-data /var/log/gunicorn
```

### 6.2 Проверка конфигурации Gunicorn

```bash
cd /var/www/filehost

# Проверить наличие файла gunicorn.conf.py
ls -la gunicorn.conf.py

# Просмотреть конфигурацию
cat gunicorn.conf.py
```

### 6.3 Тестовый запуск Gunicorn (опционально)

```bash
cd /var/www/filehost
source venv/bin/activate

# Запустить вручную для проверки
gunicorn --config gunicorn.conf.py filehost.wsgi:application

# Если всё работает, остановите (Ctrl+C)
```

## 🎯 Шаг 7: Настройка Celery (для фоновых задач)

### 7.1 Создание директорий для Celery

```bash
mkdir -p /var/log/celery /var/run/celery
chown www-data:www-data /var/log/celery /var/run/celery
```

### 7.2 Проверка конфигурации Celery

```bash
cd /var/www/filehost

# Проверить наличие файла filehost/celery.py
ls -la filehost/celery.py

# Проверить наличие файла files/tasks.py
ls -la files/tasks.py
```

## ⚙️ Шаг 8: Настройка systemd сервисов

### 8.1 Копирование файлов сервисов

```bash
cd /var/www/filehost

# Копировать файлы сервисов
cp filehost.service /etc/systemd/system/
cp celery.service /etc/systemd/system/
cp celerybeat.service /etc/systemd/system/

# Установить права
chmod 644 /etc/systemd/system/filehost.service
chmod 644 /etc/systemd/system/celery.service
chmod 644 /etc/systemd/system/celerybeat.service
```

### 8.2 Проверка и редактирование сервисных файлов

**Важно:** Проверьте пути в файлах сервисов. Они должны указывать на `/var/www/filehost`

```bash
# Проверить файл filehost.service
cat /etc/systemd/system/filehost.service | grep WorkingDirectory
cat /etc/systemd/system/filehost.service | grep ExecStart

# Должно быть:
# WorkingDirectory=/var/www/filehost
# ExecStart=/var/www/filehost/venv/bin/gunicorn ...
```

Если пути отличаются, отредактируйте файлы:

```bash
nano /etc/systemd/system/filehost.service
nano /etc/systemd/system/celery.service
nano /etc/systemd/system/celerybeat.service
```

### 8.3 Перезагрузка systemd и включение сервисов

```bash
# Перезагрузить конфигурацию systemd
systemctl daemon-reload

# Включить сервисы в автозагрузку
systemctl enable filehost
systemctl enable celery
systemctl enable celerybeat

# Проверка статуса перед запуском
systemctl status filehost
systemctl status celery
systemctl status celerybeat
```

### 8.4 Запуск сервисов

```bash
# Запустить сервисы
systemctl start filehost
systemctl start celery
systemctl start celerybeat

# Проверить статус
systemctl status filehost
systemctl status celery
systemctl status celerybeat
```

### 8.5 Проверка логов

```bash
# Логи Django/Gunicorn
journalctl -u filehost -f

# Логи Celery worker
journalctl -u celery -f

# Логи Celery beat
journalctl -u celerybeat -f

# Логи Django (файл)
tail -f /var/www/filehost/logs/django.log
```

## 🌐 Шаг 9: Настройка Nginx

### 9.1 Копирование конфигурации Nginx

```bash
cd /var/www/filehost

# Копировать конфигурацию
cp nginx.conf /etc/nginx/sites-available/filehost

# Создать символическую ссылку
ln -sf /etc/nginx/sites-available/filehost /etc/nginx/sites-enabled/

# Удалить дефолтный сайт
rm -f /etc/nginx/sites-enabled/default
```

### 9.2 Редактирование конфигурации Nginx

```bash
nano /etc/nginx/sites-available/filehost
```

**Важно изменить:**
- `YOUR_SERVER_IP` на реальный IP адрес сервера или доменное имя
- Проверить пути к статическим файлам и медиа

Найти и заменить:
```bash
# Найти IP сервера
curl ifconfig.me

# Заменить в конфигурации
sed -i 's/YOUR_SERVER_IP/ВАШ_РЕАЛЬНЫЙ_IP/g' /etc/nginx/sites-available/filehost
```

### 9.3 Проверка конфигурации Nginx

```bash
# Проверка синтаксиса
nginx -t

# Если ошибок нет, перезапустить
systemctl restart nginx

# Проверка статуса
systemctl status nginx
```

### 9.4 Проверка работы Nginx

```bash
# Проверка логов
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log

# Проверка подключения
curl -I http://localhost
curl -I http://YOUR_SERVER_IP
```

## 🔒 Шаг 10: Настройка безопасности

### 10.1 Настройка файрвола (UFW)

```bash
# Разрешить SSH (важно сделать первым!)
ufw allow ssh
ufw allow 22/tcp  # Альтернативный способ

# Разрешить HTTP
ufw allow 80/tcp

# Разрешить HTTPS (для будущего SSL)
ufw allow 443/tcp

# Включить файрвол
ufw --force enable

# Проверка статуса
ufw status verbose
```

**⚠️ ВАЖНО:** Убедитесь, что SSH доступ разрешен, иначе можете потерять доступ к серверу!

### 10.2 Настройка Fail2ban

```bash
# Проверка статуса
systemctl status fail2ban

# Проверка заблокированных IP
fail2ban-client status sshd

# Настройка для защиты SSH (базовая конфигурация уже есть)
# Для дополнительной защиты Django/Nginx создайте конфиг
nano /etc/fail2ban/jail.local
```

**Содержимое `/etc/fail2ban/jail.local`:**
```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s
```

Перезапустить fail2ban:
```bash
systemctl restart fail2ban
```

## ✅ Шаг 11: Финальная проверка

### 11.1 Проверка всех сервисов

```bash
# Статус всех сервисов
systemctl status filehost
systemctl status celery
systemctl status celerybeat
systemctl status nginx
systemctl status postgresql
systemctl status redis-server
systemctl status fail2ban
```

Все сервисы должны быть `active (running)`.

### 11.2 Проверка веб-сайта

```bash
# Проверка через curl
curl -I http://YOUR_SERVER_IP

# Должен вернуться HTTP 200 OK
```

Откройте в браузере: `http://YOUR_SERVER_IP`

### 11.3 Проверка работы основных функций

1. **Главная страница:** Должна загрузиться форма загрузки файла
2. **Загрузка файла:** Попробуйте загрузить тестовый файл
3. **Просмотр файла:** После загрузки должна открыться страница с файлом
4. **Скачивание:** Кнопка скачивания должна работать

### 11.4 Проверка логов на ошибки

```bash
# Django логи
tail -50 /var/www/filehost/logs/django.log

# Gunicorn логи
journalctl -u filehost -n 50

# Nginx логи
tail -50 /var/log/nginx/error.log

# Celery логи
journalctl -u celery -n 50
```

## 🎯 Шаг 12: Настройка домена и SSL (когда домен будет готов)

### 12.1 Настройка DNS

В панели управления доменом добавьте A-запись:
```
A    @    YOUR_SERVER_IP
A    www  YOUR_SERVER_IP
```

### 12.2 Обновление .env файла

```bash
cd /var/www/filehost
nano .env
```

Обновите:
```env
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,YOUR_SERVER_IP
SITE_BASE_URL=https://yourdomain.com
USE_HTTPS=True
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 12.3 Установка SSL сертификата (Let's Encrypt)

```bash
# Установка Certbot
apt install -y certbot python3-certbot-nginx

# Получение сертификата
certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Автоматическое обновление
systemctl enable certbot.timer
systemctl start certbot.timer
```

### 12.4 Обновление Nginx конфигурации

Certbot автоматически обновит конфигурацию Nginx. Проверьте:

```bash
nginx -t
systemctl restart nginx
systemctl restart filehost
```

## 📊 Шаг 13: Настройка резервного копирования

### 13.1 Скрипт резервного копирования базы данных

```bash
nano /usr/local/bin/backup-filehost.sh
```

**Содержимое:**
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/filehost"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="filehost"
DB_USER="filehost_user"

mkdir -p $BACKUP_DIR

# Бэкап базы данных
pg_dump -U $DB_USER -h localhost $DB_NAME | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Бэкап медиа файлов
tar -czf $BACKUP_DIR/media_$DATE.tar.gz -C /var/www/filehost media/

# Удаление старых бэкапов (старше 30 дней)
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $DATE"
```

Сделать исполняемым:
```bash
chmod +x /usr/local/bin/backup-filehost.sh
```

### 13.2 Настройка cron для автоматических бэкапов

```bash
crontab -e
```

Добавить:
```
# Бэкап каждый день в 3:00 ночи
0 3 * * * /usr/local/bin/backup-filehost.sh >> /var/log/filehost-backup.log 2>&1
```

## 🔧 Шаг 14: Полезные команды для управления

### 14.1 Управление сервисами

```bash
# Перезапуск всех сервисов
systemctl restart filehost celery celerybeat nginx

# Проверка статуса
systemctl status filehost

# Просмотр логов
journalctl -u filehost -f

# Остановка сервисов
systemctl stop filehost celery celerybeat
```

### 14.2 Обновление кода

```bash
cd /var/www/filehost

# Если используется Git
git pull origin master

# Активировать окружение
source venv/bin/activate

# Обновить зависимости
pip install -r requirements-prod.txt

# Применить миграции
python manage.py migrate --settings=filehost.settings_prod

# Собрать статические файлы
python manage.py collectstatic --noinput --settings=filehost.settings_prod

# Перезапустить сервисы
systemctl restart filehost celery celerybeat
```

### 14.3 Работа с базой данных

```bash
# Подключение к базе
sudo -u postgres psql -d filehost

# Создание бэкапа
pg_dump -U filehost_user -h localhost filehost > backup.sql

# Восстановление из бэкапа
psql -U filehost_user -h localhost filehost < backup.sql
```

## 🆘 Устранение неполадок

### Проблема: Сервисы не запускаются

```bash
# Проверить логи
journalctl -u filehost -n 100
journalctl -u celery -n 100

# Проверить права доступа
ls -la /var/www/filehost/
ls -la /var/www/filehost/venv/

# Проверить .env файл
cat /var/www/filehost/.env

# Проверить конфигурацию сервисов
cat /etc/systemd/system/filehost.service
```

### Проблема: База данных недоступна

```bash
# Проверить статус PostgreSQL
systemctl status postgresql

# Проверить подключение
sudo -u postgres psql -d filehost -c "SELECT 1;"

# Проверить права пользователя
sudo -u postgres psql -c "\du filehost_user"
```

### Проблема: Redis недоступен

```bash
# Проверить статус
systemctl status redis-server

# Проверить подключение
redis-cli ping

# Проверить конфигурацию
cat /etc/redis/redis.conf | grep -E "bind|port"
```

### Проблема: Nginx не работает

```bash
# Проверить синтаксис
nginx -t

# Проверить логи
tail -50 /var/log/nginx/error.log

# Проверить порты
netstat -tlnp | grep :80
```

### Проблема: Статические файлы не загружаются

```bash
# Проверить директорию
ls -la /var/www/filehost/staticfiles/

# Проверить права
chown -R www-data:www-data /var/www/filehost/staticfiles/

# Пересобрать статические файлы
cd /var/www/filehost
source venv/bin/activate
python manage.py collectstatic --noinput --settings=filehost.settings_prod
```

## 📋 Чек-лист развертывания

- [ ] Сервер обновлен и готов
- [ ] Установлены все системные пакеты
- [ ] PostgreSQL установлен и настроен
- [ ] Redis установлен и настроен
- [ ] Nginx установлен
- [ ] Проект скопирован на сервер
- [ ] Python виртуальное окружение создано
- [ ] Зависимости установлены
- [ ] .env файл создан и настроен
- [ ] База данных создана и миграции применены
- [ ] Статические файлы собраны
- [ ] Gunicorn настроен
- [ ] Celery настроен
- [ ] systemd сервисы настроены и запущены
- [ ] Nginx настроен и работает
- [ ] Файрвол настроен
- [ ] Fail2ban настроен
- [ ] Все сервисы работают
- [ ] Сайт доступен по IP
- [ ] Основные функции работают
- [ ] Логи проверены на ошибки
- [ ] Резервное копирование настроено

## 🎉 Готово!

Ваш файловый хостинг успешно развернут на Ubuntu сервере!

**Основные URL:**
- Главная: `http://YOUR_SERVER_IP/`
- Админка: `http://YOUR_SERVER_IP/admin/` (если создан суперпользователь)

**Следующие шаги:**
1. Настроить домен и SSL (когда домен будет готов)
2. Настроить мониторинг (опционально)
3. Настроить автоматические обновления безопасности

**Полезные ссылки:**
- Логи Django: `/var/www/filehost/logs/django.log`
- Логи Gunicorn: `journalctl -u filehost -f`
- Логи Nginx: `/var/log/nginx/error.log`

Удачи! 🚀

