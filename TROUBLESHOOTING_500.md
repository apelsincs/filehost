# 🔍 Диагностика ошибки 500 на www.0123.ru

## 📋 Быстрая диагностика

### 1. Проверка статуса сервисов

```bash
# Проверьте статус всех сервисов
systemctl status filehost
systemctl status nginx
systemctl status postgresql
systemctl status redis

# Если какой-то сервис не запущен, запустите его:
systemctl start filehost
systemctl start nginx
systemctl start postgresql
systemctl start redis
```

### 2. Проверка логов Django/Gunicorn

```bash
# Логи Gunicorn через systemd
journalctl -u filehost -n 100 --no-pager

# Логи Django
tail -n 100 /var/www/filehost/logs/django.log

# Логи Gunicorn (если настроены отдельные файлы)
tail -n 100 /var/log/gunicorn/error.log
```

**Что искать:**
- Ошибки подключения к базе данных
- Отсутствующие переменные окружения (SECRET_KEY, DATABASE_URL и т.д.)
- Ошибки импорта модулей
- Проблемы с правами доступа к файлам

### 3. Проверка логов Nginx

```bash
# Ошибки Nginx
tail -n 100 /var/log/nginx/error.log
tail -n 100 /var/log/nginx/filehost_error.log

# Access логи (для понимания, какие запросы приходят)
tail -n 50 /var/log/nginx/filehost_access.log
```

**Что искать:**
- Ошибки подключения к upstream (gunicorn)
- Проблемы с SSL сертификатами
- Ошибки 502 Bad Gateway (означает, что gunicorn не отвечает)

### 4. Проверка переменных окружения

```bash
# Проверьте наличие .env файла
ls -la /var/www/filehost/.env

# Проверьте содержимое (осторожно, не выводите пароли в терминал)
cat /var/www/filehost/.env | grep -v PASSWORD

# Проверьте, что SECRET_KEY установлен
grep SECRET_KEY /var/www/filehost/.env

# Проверьте ALLOWED_HOSTS (должен содержать www.0123.ru)
grep ALLOWED_HOSTS /var/www/filehost/.env
```

**Критически важно:**
- `SECRET_KEY` должен быть установлен и не быть значением по умолчанию
- `ALLOWED_HOSTS` должен содержать `www.0123.ru` и `0123.ru`
- `DATABASE_URL` или `DB_*` переменные должны быть правильно настроены
- `SITE_BASE_URL` должен быть `https://www.0123.ru` (если используется HTTPS)

### 5. Проверка подключения к базе данных

```bash
# Подключитесь к базе данных
sudo -u postgres psql -d filehost

# Или если используется другой пользователь:
psql -U filehost_user -d filehost -h localhost

# Проверьте, что таблицы существуют
\dt

# Выйдите из psql
\q
```

**Если не можете подключиться:**
```bash
# Проверьте, запущен ли PostgreSQL
systemctl status postgresql

# Проверьте логи PostgreSQL
tail -n 50 /var/log/postgresql/postgresql-*.log
```

### 6. Проверка подключения к Redis

```bash
# Проверьте подключение к Redis
redis-cli ping
# Должен вернуть: PONG

# Если не работает:
systemctl status redis
systemctl start redis
```

### 7. Проверка прав доступа к файлам

```bash
# Проверьте права на директорию проекта
ls -la /var/www/filehost/

# Проверьте права на логи
ls -la /var/www/filehost/logs/

# Проверьте права на media и staticfiles
ls -la /var/www/filehost/media/
ls -la /var/www/filehost/staticfiles/

# Если права неправильные, исправьте:
sudo chown -R www-data:www-data /var/www/filehost
sudo chmod -R 755 /var/www/filehost
sudo chmod -R 775 /var/www/filehost/media
sudo chmod -R 775 /var/www/filehost/logs
```

### 8. Проверка конфигурации Nginx

```bash
# Проверьте синтаксис конфигурации Nginx
nginx -t

# Проверьте, что конфигурация активна
ls -la /etc/nginx/sites-enabled/

# Проверьте, что server_name содержит правильный домен
grep server_name /etc/nginx/sites-available/filehost
```

**Важно:** В конфигурации Nginx должен быть указан `server_name www.0123.ru 0123.ru;`

### 9. Проверка SSL сертификата (если используется HTTPS)

```bash
# Проверьте наличие SSL сертификата
ls -la /etc/ssl/certs/ | grep 0123
ls -la /etc/ssl/private/ | grep 0123

# Или если используется Let's Encrypt:
ls -la /etc/letsencrypt/live/www.0123.ru/

# Проверьте срок действия сертификата
sudo certbot certificates
```

### 10. Тест запуска Django напрямую

```bash
# Перейдите в директорию проекта
cd /var/www/filehost

# Активируйте виртуальное окружение
source venv/bin/activate

# Попробуйте запустить Django проверку
python manage.py check --settings=filehost.settings_prod

# Попробуйте запустить миграции (dry-run)
python manage.py migrate --settings=filehost.settings_prod --plan

# Попробуйте запустить shell
python manage.py shell --settings=filehost.settings_prod
# В shell попробуйте:
# from django.conf import settings
# print(settings.ALLOWED_HOSTS)
# print(settings.DATABASES)
```

## 🔧 Частые проблемы и решения

### Проблема 1: SECRET_KEY не установлен

**Симптомы:** Ошибка в логах о SECRET_KEY

**Решение:**
```bash
cd /var/www/filehost
source venv/bin/activate
SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
systemctl restart filehost
```

### Проблема 2: ALLOWED_HOSTS не содержит домен

**Симптомы:** Ошибка "DisallowedHost" в логах

**Решение:**
```bash
# Отредактируйте .env файл
nano /var/www/filehost/.env

# Обновите ALLOWED_HOSTS:
ALLOWED_HOSTS=www.0123.ru,0123.ru,localhost,127.0.0.1

# Перезапустите сервис
systemctl restart filehost
```

### Проблема 3: База данных недоступна

**Симптомы:** Ошибки подключения к PostgreSQL в логах

**Решение:**
```bash
# Проверьте, запущен ли PostgreSQL
systemctl status postgresql
systemctl start postgresql

# Проверьте подключение
sudo -u postgres psql -c "\l" | grep filehost

# Если база не существует, создайте её:
sudo -u postgres createdb filehost
sudo -u postgres createuser filehost_user
sudo -u postgres psql -c "ALTER USER filehost_user WITH PASSWORD 'your-password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE filehost TO filehost_user;"

# Выполните миграции
cd /var/www/filehost
source venv/bin/activate
python manage.py migrate --settings=filehost.settings_prod
```

### Проблема 4: Redis недоступен

**Симптомы:** Ошибки подключения к Redis в логах

**Решение:**
```bash
systemctl status redis
systemctl start redis
systemctl enable redis

# Проверьте подключение
redis-cli ping
```

### Проблема 5: Статические файлы не собраны

**Симптомы:** CSS/JS не загружаются, ошибки 404 для статики

**Решение:**
```bash
cd /var/www/filehost
source venv/bin/activate
python manage.py collectstatic --noinput --settings=filehost.settings_prod
sudo chown -R www-data:www-data staticfiles/
```

### Проблема 6: Gunicorn не запускается

**Симптомы:** `systemctl status filehost` показывает ошибку

**Решение:**
```bash
# Проверьте логи
journalctl -u filehost -n 50

# Проверьте конфигурацию gunicorn
cat /var/www/filehost/gunicorn.conf.py

# Попробуйте запустить вручную для диагностики
cd /var/www/filehost
source venv/bin/activate
gunicorn filehost.wsgi:application --config gunicorn.conf.py --settings=filehost.settings_prod
```

### Проблема 7: Nginx не может подключиться к Gunicorn

**Симптомы:** Ошибка 502 Bad Gateway

**Решение:**
```bash
# Проверьте, что Gunicorn слушает на правильном порту
netstat -tlnp | grep 8000
# или
ss -tlnp | grep 8000

# Проверьте конфигурацию Nginx
grep "proxy_pass" /etc/nginx/sites-available/filehost

# Убедитесь, что upstream указывает на правильный адрес
grep "upstream" /etc/nginx/sites-available/filehost
```

### Проблема 8: Проблемы с HTTPS/SSL

**Симптомы:** Ошибки SSL в логах Nginx

**Решение:**
```bash
# Если используете Let's Encrypt, обновите сертификат
sudo certbot renew

# Проверьте конфигурацию Nginx для HTTPS
grep -A 5 "listen 443" /etc/nginx/sites-available/filehost

# Убедитесь, что в .env установлено:
# USE_HTTPS=True
# SITE_BASE_URL=https://www.0123.ru
```

## 🚀 Быстрое исправление (после диагностики)

После того, как вы нашли проблему, выполните:

```bash
# 1. Исправьте проблему (в зависимости от найденной ошибки)

# 2. Перезапустите все сервисы
systemctl restart postgresql
systemctl restart redis
systemctl restart filehost
systemctl restart nginx

# 3. Проверьте статус
systemctl status filehost
systemctl status nginx

# 4. Проверьте логи на наличие новых ошибок
tail -f /var/www/filehost/logs/django.log
tail -f /var/log/nginx/filehost_error.log
```

## 📞 Дополнительная диагностика

Если проблема не решена, соберите следующую информацию:

```bash
# Создайте файл с диагностической информацией
cat > /tmp/diagnostic.txt << EOF
=== System Info ===
$(uname -a)
$(date)

=== Service Status ===
$(systemctl status filehost --no-pager -l)
$(systemctl status nginx --no-pager -l)
$(systemctl status postgresql --no-pager -l)
$(systemctl status redis --no-pager -l)

=== Recent Django Logs ===
$(tail -n 50 /var/www/filehost/logs/django.log)

=== Recent Gunicorn Logs ===
$(journalctl -u filehost -n 50 --no-pager)

=== Recent Nginx Error Logs ===
$(tail -n 50 /var/log/nginx/filehost_error.log)

=== Environment Variables (without passwords) ===
$(grep -v PASSWORD /var/www/filehost/.env)

=== Database Connection Test ===
$(sudo -u postgres psql -d filehost -c "\conninfo" 2>&1)

=== Redis Connection Test ===
$(redis-cli ping 2>&1)

=== Port Status ===
$(netstat -tlnp | grep -E ':(80|443|8000|5432|6379)')
EOF

# Просмотрите файл
cat /tmp/diagnostic.txt
```

---

**💡 Совет:** Начните с проверки логов (шаг 2 и 3) - они обычно сразу показывают причину ошибки 500.

