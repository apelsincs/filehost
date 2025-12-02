# ⚡ Быстрый старт на Ubuntu сервере

Краткая шпаргалка для быстрого развертывания проекта на чистом Ubuntu сервере.

## 🚀 Быстрое развертывание (10 минут)

### 1. Подготовка сервера

```bash
# Обновление системы
apt update && apt upgrade -y

# Установка базовых пакетов
apt install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib redis-server nginx \
    libpq-dev build-essential libmagic1 git curl wget \
    gettext gettext-base ufw fail2ban
```

### 2. Настройка PostgreSQL

```bash
# Создание базы и пользователя
sudo -u postgres psql << EOF
CREATE DATABASE filehost;
CREATE USER filehost_user WITH PASSWORD 'ПАРОЛЬ_ДЛЯ_БД';
GRANT ALL PRIVILEGES ON DATABASE filehost TO filehost_user;
ALTER USER filehost_user CREATEDB;
\q
EOF

# ВАЖНО: Выдать права на схему public (для PostgreSQL 15+)
sudo -u postgres psql -d filehost << EOF
GRANT ALL ON SCHEMA public TO filehost_user;
GRANT CREATE ON SCHEMA public TO filehost_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO filehost_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO filehost_user;
\q
EOF
```

### 3. Запуск сервисов

```bash
systemctl start postgresql redis-server nginx
systemctl enable postgresql redis-server nginx fail2ban
```

### 4. Настройка проекта

```bash
# Создание директории
mkdir -p /var/www/filehost
chown www-data:www-data /var/www/filehost

# Копирование проекта (замените на ваш способ)
cd /var/www/filehost
# git clone ... или scp ... или любой другой способ

# Создание виртуального окружения
python3 -m venv venv
chown -R www-data:www-data venv
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements-prod.txt
```

### 5. Создание .env файла

```bash
cd /var/www/filehost
cp env.production .env
nano .env  # Заполните все значения!
```

**Минимальный .env:**
```env
DEBUG=False
SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
ALLOWED_HOSTS=YOUR_SERVER_IP,localhost
DB_NAME=filehost
DB_USER=filehost_user
DB_PASSWORD=ВАШ_ПАРОЛЬ_БД
DB_HOST=localhost
REDIS_URL=redis://127.0.0.1:6379/1
```

### 6. Настройка Django

```bash
cd /var/www/filehost
source venv/bin/activate

# Создание директорий
mkdir -p logs media/uploads staticfiles
chown -R www-data:www-data logs media staticfiles

# Миграции
python manage.py migrate --settings=filehost.settings_prod

# Статические файлы
python manage.py collectstatic --noinput --settings=filehost.settings_prod

# Создание суперпользователя (опционально)
python manage.py createsuperuser --settings=filehost.settings_prod
```

### 7. Настройка сервисов

```bash
cd /var/www/filehost

# Создание директорий для логов
mkdir -p /var/log/gunicorn /var/log/celery /var/run/celery
chown www-data:www-data /var/log/gunicorn /var/log/celery /var/run/celery

# Копирование файлов сервисов
cp filehost.service celery.service celerybeat.service /etc/systemd/system/

# Перезагрузка systemd
systemctl daemon-reload
systemctl enable filehost celery celerybeat
systemctl start filehost celery celerybeat
```

### 8. Настройка Nginx

```bash
cd /var/www/filehost

# Копирование конфигурации
cp nginx.conf /etc/nginx/sites-available/filehost

# Замена IP адреса
SERVER_IP=$(curl -s ifconfig.me)
sed -i "s/YOUR_SERVER_IP/$SERVER_IP/g" /etc/nginx/sites-available/filehost

# Активация сайта
ln -sf /etc/nginx/sites-available/filehost /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Проверка и перезапуск
nginx -t
systemctl restart nginx
```

### 9. Настройка файрвола

```bash
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
```

### 10. Проверка

```bash
# Статус всех сервисов
systemctl status filehost celery celerybeat nginx postgresql redis-server

# Проверка сайта
curl -I http://YOUR_SERVER_IP
```

## 🔧 Основные команды

### Перезапуск сервисов
```bash
systemctl restart filehost celery celerybeat nginx
```

### Просмотр логов
```bash
# Django
tail -f /var/www/filehost/logs/django.log

# Gunicorn
journalctl -u filehost -f

# Celery
journalctl -u celery -f

# Nginx
tail -f /var/log/nginx/error.log
```

### Обновление кода
```bash
cd /var/www/filehost
source venv/bin/activate
git pull  # или другой способ обновления
pip install -r requirements-prod.txt
python manage.py migrate --settings=filehost.settings_prod
python manage.py collectstatic --noinput --settings=filehost.settings_prod
systemctl restart filehost celery celerybeat
```

### Резервное копирование БД
```bash
pg_dump -U filehost_user -h localhost filehost > backup_$(date +%Y%m%d).sql
```

## 🆘 Быстрое решение проблем

### Сервис не запускается
```bash
journalctl -u filehost -n 50  # Посмотреть логи
systemctl restart filehost    # Перезапустить
```

### База данных недоступна
```bash
systemctl restart postgresql
sudo -u postgres psql -d filehost -c "SELECT 1;"
```

### Nginx не работает
```bash
nginx -t              # Проверить конфигурацию
tail -50 /var/log/nginx/error.log  # Посмотреть ошибки
```

## 📋 Чек-лист

- [ ] Все сервисы установлены
- [ ] PostgreSQL настроен
- [ ] Redis запущен
- [ ] Проект скопирован
- [ ] .env файл создан
- [ ] Миграции применены
- [ ] Статические файлы собраны
- [ ] Сервисы запущены
- [ ] Nginx настроен
- [ ] Сайт доступен

**Готово!** 🎉

