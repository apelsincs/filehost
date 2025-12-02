// Основной JavaScript для 0123.ru

class MaterialFileUploader {
    constructor() {
        this.isUploading = false;
        this.uploadForm = null;
        this.uploadArea = null;
        this.fileInput = null;
        this.lastUploadedFileUrl = null;
        this.init();
    }

    init() {
        this.setupElements();
        this.setupEventListeners();
        this.setupDragAndDrop();
        this.setupAnimations();
    }

    setupElements() {
        this.uploadForm = document.getElementById('uploadForm');
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
    }

    setupEventListeners() {
        if (this.uploadArea) {
            this.uploadArea.addEventListener('click', () => this.fileInput?.click());
        }

        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }

        if (this.uploadForm) {
            this.uploadForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // Обработчик для чекбокса защиты файла
        const isProtectedCheckbox = document.getElementById('isProtected');
        const passwordField = document.getElementById('password');
        if (isProtectedCheckbox && passwordField) {
            isProtectedCheckbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    passwordField.required = true;
                    try { passwordField.placeholder = gettext('Введите пароль для защиты файла'); } catch (_) { passwordField.placeholder = 'Введите пароль для защиты файла'; }
                    passwordField.style.borderColor = '#dc3545';
                } else {
                    passwordField.required = false;
                    try { passwordField.placeholder = gettext('Защитить файл паролем'); } catch (_) { passwordField.placeholder = 'Защитить файл паролем'; }
                    passwordField.style.borderColor = '';
                    passwordField.value = '';
                }
            });
        }

        // Обработчики для кнопок копирования ссылок
        // this.setupCopyButtons(); // Убираем этот вызов, так как метод находится в другом классе
        
        // Обработчик для проверки уникальности кода
        // this.setupCodeValidation(); // Убираем этот вызов, так как метод находится в другом классе

        // Обработчик для drag and drop
        document.addEventListener('dragover', (e) => e.preventDefault());
        document.addEventListener('drop', (e) => e.preventDefault());
    }

    setupDragAndDrop() {
        if (!this.uploadArea) return;

        this.uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                this.uploadArea.classList.add('dragover');
        });

        this.uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
                this.uploadArea.classList.remove('dragover');
        });

        this.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            this.uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                        this.fileInput.files = files;
                this.handleFileSelect({ target: { files } });
            }
        });
    }

    setupAnimations() {
        // Анимация появления элементов при загрузке страницы
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-fade-in-up');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        // Наблюдаем за элементами для анимации
        document.querySelectorAll('.feature-card, .recent-file-card, .file-upload-section').forEach(el => {
            observer.observe(el);
        });
    }

    handleFileSelect(event) {
        const files = event.target.files;
        if (files.length === 0) return;

        const file = files[0];
        this.updateUploadArea(file);
        this.validateFile(file);
    }

    updateUploadArea(file) {
        if (!this.uploadArea) return;

        this.uploadArea.classList.add('has-file');
        
        const uploadText = this.uploadArea.querySelector('.upload-text');
        const uploadHint = this.uploadArea.querySelector('.upload-hint');
        
        if (uploadText) {
            try { uploadText.textContent = interpolate(gettext('Выбран файл: %s'), [file.name], true); } catch (_) { uploadText.textContent = `Выбран файл: ${file.name}`; }
        }
        
        if (uploadHint) {
            try { uploadHint.textContent = interpolate(gettext('Размер: %s'), [this.formatFileSize(file.size)], true); } catch (_) { uploadHint.textContent = `Размер: ${this.formatFileSize(file.size)}`; }
        }

        // Анимация появления
        this.uploadArea.classList.add('animate-scale-in');
    }

    validateFile(file) {
        const maxSize = 25 * 1024 * 1024; // 25MB
        const allowedTypes = [
            'image/', 'text/', 'application/pdf', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/zip', 'application/x-rar-compressed'
        ];

        let isValid = true;
        let errorMessage = '';

        // Проверка размера
        if (file.size > maxSize) {
            isValid = false;
            try { errorMessage = gettext('Файл слишком большой. Максимальный размер: 25MB'); } catch (_) { errorMessage = 'Файл слишком большой. Максимальный размер: 25MB'; }
        }

        // Проверка типа
        const isAllowedType = allowedTypes.some(type => file.type.startsWith(type));
        if (!isAllowedType && file.type !== '') {
            isValid = false;
            try { errorMessage = gettext('Неподдерживаемый тип файла'); } catch (_) { errorMessage = 'Неподдерживаемый тип файла'; }
        }

        if (!isValid) {
            this.showNotification(errorMessage, 'error');
            this.resetUploadForm();
        }
    }

    handleFormSubmit(event) {
        event.preventDefault();
        
        if (!this.fileInput.files.length) {
            try { this.showNotification(gettext('Пожалуйста, выберите файл'), 'warning'); } catch (_) { this.showNotification('Пожалуйста, выберите файл', 'warning'); }
            return;
        }

        // Собираем данные формы
        const formData = new FormData(this.uploadForm);
        this.uploadFile(formData);
    }

    async uploadFile(formData) {
        this.isUploading = true;
        this.showUploadProgress();

        try {
            const response = await fetch('/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            let result = {};
            try {
                result = await response.json();
            } catch (error) {
                // Non-JSON response
            }

            if (response.ok) {
                if (result.success === false) {
                    // Обрабатываем ошибки валидации
                    this.handleValidationErrors(result);
                } else {
                    this.showUploadSuccessModal(result);
                }
            } else {
                const errorMessage = result.error || (typeof gettext === 'function' ? gettext('Ошибка загрузки файла') : 'Ошибка загрузки файла');
                this.showNotification(errorMessage, 'error');
            }
        } catch (error) {
            this.showNotification(error.message || (typeof gettext === 'function' ? gettext('Ошибка загрузки') : 'Ошибка загрузки'), 'error');
        } finally {
            this.isUploading = false;
            this.hideUploadProgress();
        }
    }

    showUploadProgress() {
        // Создаем индикатор прогресса в Material Design стиле
        const progressContainer = document.createElement('div');
        progressContainer.className = 'upload-progress-container';
        const progressText = (typeof gettext === 'function' ? gettext('Загрузка файла...') : 'Загрузка файла...');
        progressContainer.innerHTML = `
            <div class="upload-progress">
                <div class="progress-indicator">
                    <div class="progress-circle"></div>
                </div>
                <div class="progress-text">${progressText}</div>
            </div>
        `;

        this.uploadArea.appendChild(progressContainer);
        this.uploadArea.classList.add('uploading');
    }

    hideUploadProgress() {
        const progressContainer = this.uploadArea.querySelector('.upload-progress-container');
        if (progressContainer) {
            progressContainer.remove();
        }
        this.uploadArea.classList.remove('uploading');
    }

    showUploadSuccessModal(result) {
        const modal = document.getElementById('uploadSuccessModal');
        const fileName = document.getElementById('modalFileName');
        const fileCode = document.getElementById('modalFileCode');
        const fileSize = document.getElementById('modalFileSize');
        const fileExpiry = document.getElementById('modalFileExpiry');
        const fileTypeIcon = document.getElementById('modalFileTypeIcon');
        const fileTypeBadge = document.getElementById('modalFileTypeBadge');
        
        // Заполняем информацию о файле
        if (fileName && result.filename) {
            fileName.textContent = result.filename;
        }
        
        if (fileCode && result.code) {
            fileCode.textContent = result.code;
        }
        
        if (fileSize && result.file_size) {
            const formattedSize = this.formatFileSize(result.file_size);
            fileSize.textContent = formattedSize;
        }
        
        if (fileExpiry && result.expires_at) {
            const expiryDate = new Date(result.expires_at);
            const formattedExpiry = expiryDate.toLocaleString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            fileExpiry.textContent = formattedExpiry;
        }
        
        // Показываем иконку типа файла
        if (fileTypeIcon && result.file_type_icon && result.file_type_name) {
            const iconElement = fileTypeIcon.querySelector('i');
            if (iconElement) {
                iconElement.className = result.file_type_icon + ' fa-4x text-primary mb-3';
            }
            
            // Показываем бейдж с названием типа файла
            if (fileTypeBadge) {
                fileTypeBadge.textContent = result.file_type_name;
            }
            
            fileTypeIcon.style.display = 'block';
        }
        
        this.lastUploadedFileUrl = result.url;
        
        const modalInstance = new bootstrap.Modal(modal);
        modalInstance.show();
        
        this.setupModalHandlers();
        
        // Обновляем список недавних файлов
        setTimeout(() => {
            this.updateRecentFiles();
        }, 500);
    }

    setupModalHandlers() {
        const goToFileBtn = document.getElementById('goToFileBtn');
        const uploadAnotherBtn = document.getElementById('uploadAnotherBtn');
        const copyLinkBtn = document.getElementById('copyLinkBtn');
        const downloadBtn = document.getElementById('downloadBtn');
        const modal = document.getElementById('uploadSuccessModal');
        
        if (goToFileBtn) {
            goToFileBtn.onclick = () => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                modalInstance.hide();
                
                if (this.lastUploadedFileUrl) {
                    window.location.href = this.lastUploadedFileUrl;
                }
            };
        }
        
        if (uploadAnotherBtn) {
            uploadAnotherBtn.onclick = () => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                modalInstance.hide();
                
                // Небольшая задержка для плавного закрытия модального окна
                setTimeout(() => {
                    // Перезагружаем главную страницу для обновления списка файлов
                    window.location.reload();
                }, 300);
            };
        }
        
        // Кнопка копирования ссылки
        if (copyLinkBtn) {
            copyLinkBtn.onclick = () => {
                if (this.lastUploadedFileUrl) {
                    if (typeof copyToClipboard === 'function') {
                        copyToClipboard(this.lastUploadedFileUrl, copyLinkBtn);
                    } else {
                        // Fallback копирование
                        if (navigator.clipboard && window.isSecureContext) {
                            navigator.clipboard.writeText(this.lastUploadedFileUrl).then(() => {
                                this.showNotification(typeof gettext==='function'? gettext('Ссылка скопирована в буфер обмена!') : 'Ссылка скопирована в буфер обмена!', 'success');
                            }).catch(() => {
                                this.showNotification(typeof gettext==='function'? gettext('Не удалось скопировать ссылку') : 'Не удалось скопировать ссылку', 'error');
                            });
                        } else {
                            // Fallback для старых браузеров
                            const textArea = document.createElement('textarea');
                            textArea.value = this.lastUploadedFileUrl;
                            textArea.style.position = 'fixed';
                            textArea.style.left = '-999999px';
                            textArea.style.top = '-999999px';
                            document.body.appendChild(textArea);
                            textArea.focus();
                            textArea.select();
                            
                            try {
                                document.execCommand('copy');
                                this.showNotification(typeof gettext==='function'? gettext('Ссылка скопирована в буфер обмена!') : 'Ссылка скопирована в буфер обмена!', 'success');
                            } catch (err) {
                                this.showNotification(typeof gettext==='function'? gettext('Не удалось скопировать ссылку') : 'Не удалось скопировать ссылку', 'error');
                            }
                            
                            document.body.removeChild(textArea);
                        }
                    }
                }
            };
        }
        
        // Кнопка скачивания файла
        if (downloadBtn) {
            downloadBtn.onclick = () => {
                if (this.lastUploadedFileUrl) {
                    // Извлекаем код файла из URL
                    const urlParts = this.lastUploadedFileUrl.split('/');
                    const fileCode = urlParts[urlParts.length - 2]; // Предпоследний элемент
                    
                    if (fileCode) {
                        const downloadUrl = `${window.location.origin}/files/${fileCode}/download/`;
                        window.open(downloadUrl, '_blank');
                    }
                }
            };
        }
    }

    resetUploadForm() {
        if (this.uploadForm) {
            this.uploadForm.reset();
        }
        
        if (this.uploadArea) {
            this.uploadArea.classList.remove('has-file');
            
            const uploadText = this.uploadArea.querySelector('.upload-text');
            const uploadHint = this.uploadArea.querySelector('.upload-hint');
            
            if (uploadText) {
                uploadText.textContent = (typeof gettext==='function'? gettext('Перетащите файл сюда или нажмите для выбора') : 'Перетащите файл сюда или нажмите для выбора');
            }
            
            if (uploadHint) {
                uploadHint.textContent = (typeof gettext==='function'? gettext('Максимальный размер: 25MB') : 'Максимальный размер: 25MB');
            }
        }
        
        if (this.fileInput) {
            this.fileInput.value = '';
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        
        const icon = this.getNotificationIcon(type);

        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas ${icon}"></i>
                <span>${message}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        // Добавляем в контейнер уведомлений
        let container = document.querySelector('.notification-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'notification-container';
            document.body.appendChild(container);
        }

        container.appendChild(notification);

        // Показываем уведомление
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);

        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
        }, 300);
        }, 5000);
    }

    getNotificationIcon(type) {
        const icons = {
            'success': 'fa-check-circle',
            'error': 'fa-exclamation-circle',
            'warning': 'fa-exclamation-triangle',
            'info': 'fa-info-circle'
        };
        return icons[type] || icons.info;
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // Метод для обработки ошибок валидации
    handleValidationErrors(result) {
        
        // Обрабатываем ошибки полей
        if (result.errors) {
            Object.keys(result.errors).forEach(fieldName => {
                const field = document.querySelector(`[name="${fieldName}"]`);
                if (field) {
                    // Показываем ошибку под полем
                    this.showFieldError(field, result.errors[fieldName][0]);
                    
                    // Если это ошибка кастомного кода, показываем popover
                    if (fieldName === 'custom_code') {
                        this.showCodeOccupiedPopover(field, result.errors[fieldName][0]);
                    }
                }
            });
        }
        
        // Обрабатываем общие ошибки
        if (result.non_field_errors && result.non_field_errors.length > 0) {
            this.showNotification(result.non_field_errors[0], 'error');
        }
    }
    
    // Метод для показа ошибки поля
    showFieldError(field, message) {
        // Убираем существующие ошибки
        const existingError = field.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
        
        // Создаем элемент ошибки
        const errorElement = document.createElement('div');
        errorElement.className = 'field-error text-danger mt-1';
        errorElement.innerHTML = `<small><i class="fas fa-exclamation-circle me-1"></i>${message}</small>`;
        
        // Добавляем после поля
        field.parentNode.appendChild(errorElement);
        
        // Подсвечиваем поле
        field.classList.add('is-invalid');
        
        // Убираем ошибку при вводе
        field.addEventListener('input', function() {
            errorElement.remove();
            field.classList.remove('is-invalid');
        }, { once: true });
    }
    
    // Метод для показа popover о занятом коде
    showCodeOccupiedPopover(inputElement, message) {
        // Убираем существующий popover
        const existingPopover = document.querySelector('.code-occupied-popover');
        if (existingPopover) {
            existingPopover.remove();
        }
        
        // Создаем popover
        const popover = document.createElement('div');
        popover.className = 'code-occupied-popover';
        popover.innerHTML = `
            <div class="popover-content">
                <div class="popover-header">
                    <i class="fas fa-exclamation-triangle text-warning"></i>
                    <span>Код уже занят</span>
                </div>
                <div class="popover-body">
                    ${message}
                </div>
            </div>
        `;
        
        // Позиционируем popover
        const rect = inputElement.getBoundingClientRect();
        popover.style.position = 'absolute';
        popover.style.top = `${rect.bottom + 5}px`;
        popover.style.left = `${rect.left}px`;
        popover.style.zIndex = '9999';
        
        // Добавляем в DOM
        document.body.appendChild(popover);
        
        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            if (popover.parentNode) {
                popover.remove();
            }
        }, 5000);
        
        // Скрываем при клике вне popover
        document.addEventListener('click', function hidePopover(e) {
            if (!popover.contains(e.target) && e.target !== inputElement) {
                popover.remove();
                document.removeEventListener('click', hidePopover);
            }
        });
    }
}

// Material Design анимации и эффекты
class MaterialAnimations {
    constructor() {
        this.init();
    }

    init() {
        this.setupRippleEffects();
        this.setupScrollAnimations();
        this.setupHoverEffects();
    }

    setupRippleEffects() {
        // Добавляем ripple эффект для кнопок
        document.addEventListener('click', (e) => {
            const button = e.target.closest('.btn, .theme-btn, .nav-link');
            if (button) {
                this.createRipple(e, button);
            }
        });
    }

    createRipple(event, element) {
        const ripple = document.createElement('span');
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;

        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');

        element.appendChild(ripple);

        setTimeout(() => {
            ripple.remove();
        }, 600);
    }

    setupScrollAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-fade-in-up');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        // Наблюдаем за элементами для анимации
        document.querySelectorAll('.feature-card, .recent-file-card, .file-upload-section').forEach(el => {
            observer.observe(el);
        });
    }

    setupHoverEffects() {
        // Добавляем hover эффекты для карточек
        document.querySelectorAll('.feature-card, .recent-file-card').forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-8px)';
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0)';
            });
        });
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Инициализируем Material Design загрузчик файлов
    window.mdFileUploader = new MaterialFileUploader();
    
    // Инициализируем Material Design анимации
    window.mdAnimations = new MaterialAnimations();
    
    // Инициализируем менеджер анонимных сессий
    window.mdSessionManager = new AnonymousSessionManager();
    
    // Инициализируем кнопки копирования ссылок для всех страниц
    setupGlobalCopyButtons();
    
    // Добавляем CSS для ripple эффекта
    const style = document.createElement('style');
    style.textContent = `
        .ripple {
            position: absolute;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            transform: scale(0);
            animation: ripple-animation 0.6s linear;
            pointer-events: none;
        }
        
        @keyframes ripple-animation {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
        
        .upload-progress-container {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.1);
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: inherit;
        }
        
        .upload-progress {
            text-align: center;
            color: var(--md-on-primary);
        }
        
        .progress-indicator {
            margin-bottom: var(--md-spacing-md);
        }
        
        .progress-circle {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-top: 3px solid var(--md-on-primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .progress-text {
            font-size: var(--md-font-size-body);
            font-weight: 500;
        }
        
        .uploading .upload-area {
            pointer-events: none;
        }
    `;
    document.head.appendChild(style);
    
    // Инициализируем менеджер согласия на cookies (с безопасным fallback)
    try {
        // Может бросить ReferenceError из-за TDZ, если класс объявлен ниже
        window.cookieConsentManager = new CookieConsentManager();
    } catch (e) {
        // Легковесная инициализация, если класс недоступен на момент вызова
        const banner = document.getElementById('cookie-consent-banner');
        const acceptBtn = document.getElementById('cookie-consent-accept');
        if (banner && acceptBtn && !document.cookie.includes('cookie_consent=')) {
            banner.style.display = 'block';
            acceptBtn.addEventListener('click', () => {
                const maxAge = 365 * 24 * 60 * 60; // 1 год
                document.cookie = `cookie_consent=yes; max-age=${maxAge}; path=/; SameSite=Lax`;
                banner.style.display = 'none';
            });
        }
    }
});

// Класс для управления анонимными сессиями
class AnonymousSessionManager {
    constructor() {
        this.cookieName = 'anonymous_session_id';
        this.init();
    }

    init() {
        this.checkSessionStatus();
        this.setupSessionInfo();
        this.setupCodeValidation();
    }

    checkSessionStatus() {
        const sessionId = this.getCookie(this.cookieName);
        if (sessionId) {
            document.body.classList.add('has-anonymous-session');
            this.showSessionInfo(sessionId);
        } else {
            document.body.classList.remove('has-anonymous-session');
            this.hideSessionInfo();
        }
    }

    setupSessionInfo() {
        // Создаем индикатор сессии в навигации
        // this.createSessionIndicator(); // Убрано по запросу пользователя
        
        // Добавляем обработчик для очистки сессии
        this.setupSessionControls();
    }

    createSessionIndicator() {
        const navbar = document.querySelector('.navbar-actions');
        if (!navbar) return;

        // Проверяем, не создан ли уже индикатор
        if (navbar.querySelector('.session-indicator')) return;

        const sessionIndicator = document.createElement('div');
        sessionIndicator.className = 'session-indicator';
        sessionIndicator.innerHTML = `
            <div class="session-info" title="Информация о сессии">
                <i class="fas fa-user-circle"></i>
                <span class="session-status">Анонимная сессия</span>
            </div>
            <button class="btn btn-sm btn-outline-secondary session-clear-btn" 
                    title="Очистить сессию" onclick="window.mdSessionManager.clearSession()">
                <i class="fas fa-sign-out-alt"></i>
            </button>
        `;

        navbar.appendChild(sessionIndicator);
    }

    showSessionInfo(sessionId) {
        const sessionIndicator = document.querySelector('.session-indicator');
        if (sessionIndicator) {
            sessionIndicator.style.display = 'flex';
            
            const status = sessionIndicator.querySelector('.session-status');
            if (status) {
                status.textContent = 'Сессия активна';
                status.className = 'session-status text-success';
            }
        }
    }

    hideSessionInfo() {
        const sessionIndicator = document.querySelector('.session-indicator');
        if (sessionIndicator) {
            sessionIndicator.style.display = 'none';
        }
    }

    setupSessionControls() {
        // Добавляем обработчик для очистки сессии
        document.addEventListener('click', (e) => {
            if (e.target.closest('.session-clear-btn')) {
                this.clearSession();
            }
        });
    }

    clearSession() {
        if (confirm('Вы уверены, что хотите очистить текущую сессию? Это приведет к потере доступа к вашим файлам.')) {
            this.deleteCookie(this.cookieName);
            document.body.classList.remove('has-anonymous-session');
            this.hideSessionInfo();
            
            // Показываем уведомление
            if (window.mdFileUploader) {
                window.mdFileUploader.showNotification(
                    'Сессия очищена. Загрузите новый файл для создания новой сессии.', 
                    'info'
                );
            }
            
            // Перезагружаем страницу для обновления данных
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        }
    }

    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    deleteCookie(name) {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
    }

    // Метод для проверки активности сессии
    isSessionActive() {
        return !!this.getCookie(this.cookieName);
    }
    
    // Метод для копирования ссылки в буфер обмена
    copyToClipboard(text) {
        if (navigator.clipboard && window.isSecureContext) {
            // Используем современный Clipboard API
            navigator.clipboard.writeText(text).then(() => {
                showNotification(typeof gettext==='function'? gettext('Ссылка скопирована в буфер обмена!') : 'Ссылка скопирована в буфер обмена!', 'success');
            }).catch(() => {
                fallbackCopyToClipboard(text);
            });
        } else {
            // Fallback для старых браузеров
            fallbackCopyToClipboard(text);
        }
    }
    
    // Fallback метод копирования
    fallbackCopyToClipboard(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
            showNotification(typeof gettext==='function'? gettext('Ссылка скопирована в буфер обмена!') : 'Ссылка скопирована в буфер обмена!', 'success');
        } catch (err) {
            showNotification(typeof gettext==='function'? gettext('Не удалось скопировать ссылку') : 'Не удалось скопировать ссылку', 'error');
        }
        
        document.body.removeChild(textArea);
    }
    
    // Метод для настройки кнопок копирования
    setupCopyButtons() {
        // Находим все кнопки копирования ссылок
        document.addEventListener('click', (e) => {
            if (e.target.closest('.copy-link-btn')) {
                const button = e.target.closest('.copy-link-btn');
                const url = button.getAttribute('data-url');
                if (url) {
                    // Используем глобальную функцию вместо this.copyToClipboard
                    copyToClipboard(url, button);
                }
            }
        });
    }
    
    // Метод для настройки валидации кода
    setupCodeValidation() {
        const customCodeInput = document.getElementById('customCode');
        if (customCodeInput) {
            let debounceTimer;
            
            customCodeInput.addEventListener('input', (e) => {
                const code = e.target.value.trim();
                
                // Очищаем предыдущий таймер
                clearTimeout(debounceTimer);
                
                // Убираем существующий popover и статус
                const existingPopover = document.querySelector('.code-occupied-popover');
                if (existingPopover) {
                    existingPopover.remove();
                }
                
                const codeStatus = document.getElementById('codeStatus');
                if (codeStatus) {
                    codeStatus.style.display = 'none';
                }
                
                // Проверяем код через 500ms после остановки ввода
                debounceTimer = setTimeout(async () => {
                    if (code.length > 0) {
                        const isAvailable = await this.checkCodeAvailability(code);
                        if (!isAvailable) {
                            this.showCodeOccupiedPopover(customCodeInput, 
                                typeof gettext === 'function' ? gettext('Этот код уже используется. Выберите другой.') : 'Этот код уже используется. Выберите другой.');
                            // Подсвечиваем поле как неверное
                            customCodeInput.classList.add('is-invalid');
                            
                            // Показываем статус занятости
                            const codeStatus = document.getElementById('codeStatus');
                            const codeStatusText = document.getElementById('codeStatusText');
                            if (codeStatus && codeStatusText) {
                                codeStatusText.textContent = typeof gettext === 'function' ? gettext('Код занят') : 'Код занят';
                                codeStatus.className = 'mt-2';
                                codeStatus.innerHTML = `<small class="text-danger"><i class="fas fa-times-circle me-1"></i><span id="codeStatusText">${codeStatusText.textContent}</span></small>`;
                                codeStatus.style.display = 'block';
                            }
                        } else {
                            // Убираем подсветку если код доступен
                            customCodeInput.classList.remove('is-invalid');
                            
                            // Показываем статус доступности
                            const codeStatus = document.getElementById('codeStatus');
                            const codeStatusText = document.getElementById('codeStatusText');
                            if (codeStatus && codeStatusText) {
                                codeStatusText.textContent = typeof gettext === 'function' ? gettext('Код доступен') : 'Код доступен';
                                codeStatus.className = 'mt-2';
                                codeStatus.innerHTML = `<small class="text-success"><i class="fas fa-check-circle me-1"></i><span id="codeStatusText">${codeStatusText.textContent}</span></small>`;
                                codeStatus.style.display = 'block';
                            }
                        }
                    } else {
                        // Если поле пустое, скрываем статус
                        const codeStatus = document.getElementById('codeStatus');
                        if (codeStatus) {
                            codeStatus.style.display = 'none';
                        }
                    }
                }, 500);
            });
        }
    }
    
    // Метод для проверки уникальности кода
    async checkCodeAvailability(code) {
        if (!code || code.length < 1) return true;
        
        try {
            const url = `/api/check-code/?code=${encodeURIComponent(code)}`;
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                return result.available;
            }
        } catch (error) {
            // Ошибка при проверке кода
        }
        
        return true; // По умолчанию считаем доступным
    }
    
    // Метод для показа popover о занятом коде
    showCodeOccupiedPopover(inputElement, message) {
        // Убираем существующий popover
        const existingPopover = document.querySelector('.code-occupied-popover');
        if (existingPopover) {
            existingPopover.remove();
        }
        
        // Создаем popover
        const popover = document.createElement('div');
        popover.className = 'code-occupied-popover';
        popover.innerHTML = `
            <div class="popover-content">
                <div class="popover-header">
                    <i class="fas fa-exclamation-triangle text-warning"></i>
                    <span>Код уже занят</span>
                </div>
                <div class="popover-body">
                    ${message}
                </div>
            </div>
        `;
        
        // Позиционируем popover
        const rect = inputElement.getBoundingClientRect();
        popover.style.position = 'absolute';
        popover.style.top = `${rect.bottom + 5}px`;
        popover.style.left = `${rect.left}px`;
        popover.style.zIndex = '9999';
        
        // Добавляем в DOM
        document.body.appendChild(popover);
        
        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            if (popover.parentNode) {
                popover.remove();
            }
        }, 5000);
        
        // Скрываем при клике вне popover
        document.addEventListener('click', function hidePopover(e) {
            if (!popover.contains(e.target) && e.target !== inputElement) {
                popover.remove();
                document.removeEventListener('click', hidePopover);
            }
        });
    }
    
    // Метод для обновления списка недавних файлов
    async updateRecentFiles() {
        try {
            // Просто перезагружаем страницу для обновления списка файлов
            // Это более надежно, чем парсинг HTML
            window.location.reload();
        } catch (error) {
            // Не удалось обновить список файлов
        }
    }
}

// Глобальная функция для копирования в буфер обмена
function copyToClipboard(text, button = null) {
    // Проверяем, что текст не пустой
    if (!text || text.trim() === '') {
        if (typeof showNotification === 'function') {
            showNotification(typeof gettext==='function'? gettext('Ошибка: нечего копировать') : 'Ошибка: нечего копировать', 'error');
        } else {
            alert(typeof gettext==='function'? gettext('Ошибка: нечего копировать') : 'Ошибка: нечего копировать');
        }
        return;
    }
    
    // Показываем анимацию на кнопке, если она передана
    if (button) {
        button.classList.add('copying');
        setTimeout(() => {
            button.classList.remove('copying');
        }, 600);
    }
    
    if (navigator.clipboard && window.isSecureContext) {
        // Используем современный Clipboard API
        navigator.clipboard.writeText(text).then(() => {
            if (typeof showNotification === 'function') {
                showNotification(typeof gettext==='function'? gettext('Ссылка скопирована в буфер обмена!') : 'Ссылка скопирована в буфер обмена!', 'success');
            } else {
                alert(typeof gettext==='function'? gettext('Ссылка скопирована в буфер обмена!') : 'Ссылка скопирована в буфер обмена!');
            }
        }).catch((error) => {
            fallbackCopyToClipboard(text, button);
        });
    } else {
        // Fallback для старых браузеров
        fallbackCopyToClipboard(text, button);
    }
}

// Fallback метод копирования
function fallbackCopyToClipboard(text, button = null) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    textArea.style.opacity = '0';
    textArea.style.pointerEvents = 'none';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            if (typeof showNotification === 'function') {
                showNotification(typeof gettext==='function'? gettext('Ссылка скопирована в буфер обмена!') : 'Ссылка скопирована в буфер обмена!', 'success');
            } else {
                alert(typeof gettext==='function'? gettext('Ссылка скопирована в буфер обмена!') : 'Ссылка скопирована в буфер обмена!');
            }
        } else {
            if (typeof showNotification === 'function') {
                showNotification(typeof gettext==='function'? gettext('Не удалось скопировать ссылку') : 'Не удалось скопировать ссылку', 'error');
            } else {
                alert(typeof gettext==='function'? gettext('Не удалось скопировать ссылку') : 'Не удалось скопировать ссылку');
            }
        }
    } catch (err) {
        if (typeof showNotification === 'function') {
            showNotification(typeof gettext==='function'? gettext('Не удалось скопировать ссылку') : 'Не удалось скопировать ссылку', 'error');
        } else {
            alert(typeof gettext==='function'? gettext('Не удалось скопировать ссылку') : 'Не удалось скопировать ссылку');
        }
    }
    
    document.body.removeChild(textArea);
}

// Глобальная функция для показа уведомлений
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    
    const icon = getNotificationIcon(type);

    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas ${icon}"></i>
            <span>${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;

    // Добавляем в контейнер уведомлений
    let container = document.querySelector('.notification-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'notification-container';
        document.body.appendChild(container);
    }

    container.appendChild(notification);

    // Показываем уведомление
    setTimeout(() => {
        notification.classList.add('show');
    }, 100);

    // Автоматически скрываем через 5 секунд
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 300);
    }, 5000);
}

// Глобальная функция для получения иконки уведомления
function getNotificationIcon(type) {
    const icons = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle'
    };
    return icons[type] || icons.info;
}

// Глобальная функция для скачивания QR кода
function downloadQRCode(imgElement) {
    if (!imgElement || !imgElement.src) {
        showNotification(typeof gettext==='function'? gettext('QR код не найден') : 'QR код не найден', 'error');
        return;
    }
    
    try {
        // Создаем временную ссылку для скачивания
        const link = document.createElement('a');
        link.href = imgElement.src;
        link.download = `qr_code_${Date.now()}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showNotification(typeof gettext==='function'? gettext('QR код скачивается...') : 'QR код скачивается...', 'success');
    } catch (error) {
        showNotification(typeof gettext==='function'? gettext('Не удалось скачать QR код') : 'Не удалось скачать QR код', 'error');
        console.error('Error downloading QR code:', error);
    }
}

// Делаем функцию доступной глобально
window.downloadQRCode = downloadQRCode;

// Глобальная функция для инициализации кнопок копирования на всех страницах
function setupGlobalCopyButtons() {
    console.log('setupGlobalCopyButtons: инициализация...');
    
    // Находим все кнопки копирования ссылок
    document.addEventListener('click', (e) => {
        if (e.target.closest('.copy-link-btn')) {
            console.log('Кнопка копирования нажата!');
            const button = e.target.closest('.copy-link-btn');
            const url = button.getAttribute('data-url');
            console.log('URL для копирования:', url);
            
            if (url && url.trim() !== '') {
                if (typeof copyToClipboard === 'function') {
                    console.log('Используем основную функцию copyToClipboard');
                    copyToClipboard(url, button);
                } else {
                    console.log('Основная функция недоступна, используем fallback');
                    // Fallback если основная функция недоступна
                    if (navigator.clipboard && window.isSecureContext) {
                        navigator.clipboard.writeText(url).then(() => {
                            if (typeof showNotification === 'function') {
                                showNotification(typeof gettext==='function'? gettext('Ссылка скопирована в буфер обмена!') : 'Ссылка скопирована в буфер обмена!', 'success');
                            } else {
                                alert(typeof gettext==='function'? gettext('Ссылка скопирована в буфер обмена!') : 'Ссылка скопирована в буфер обмена!');
                            }
                        }).catch(() => {
                            if (typeof showNotification === 'function') {
                                showNotification(typeof gettext==='function'? gettext('Не удалось скопировать ссылку') : 'Не удалось скопировать ссылку', 'error');
                            } else {
                                alert(typeof gettext==='function'? gettext('Не удалось скопировать ссылку') : 'Не удалось скопировать ссылку');
                            }
                        });
                    } else {
                        // Fallback для старых браузеров
                        const textArea = document.createElement('textarea');
                        textArea.value = url;
                        textArea.style.position = 'fixed';
                        textArea.style.left = '-999999px';
                        textArea.style.top = '-999999px';
                        document.body.appendChild(textArea);
                        textArea.focus();
                        textArea.select();
                        
                        try {
                            document.execCommand('copy');
                            if (typeof showNotification === 'function') {
                                showNotification(typeof gettext==='function'? gettext('Ссылка скопирована в буфер обмена!') : 'Ссылка скопирована в буфер обмена!', 'success');
                            } else {
                                alert(typeof gettext==='function'? gettext('Ссылка скопирована в буфер обмена!') : 'Ссылка скопирована в буфер обмена!');
                            }
                        } catch (err) {
                            if (typeof showNotification === 'function') {
                                showNotification(typeof gettext==='function'? gettext('Не удалось скопировать ссылку') : 'Не удалось скопировать ссылку', 'error');
                            } else {
                                alert(typeof gettext==='function'? gettext('Не удалось скопировать ссылку') : 'Не удалось скопировать ссылку');
                            }
                        }
                        
                        document.body.removeChild(textArea);
                    }
                }
            } else {
                console.error('URL пустой или не найден');
                if (typeof showNotification === 'function') {
                    showNotification(typeof gettext==='function'? gettext('Ошибка: ссылка не найдена') : 'Ошибка: ссылка не найдена', 'error');
                } else {
                    alert(typeof gettext==='function'? gettext('Ошибка: ссылка не найдена') : 'Ошибка: ссылка не найдена');
                }
            }
        }
    });
    
    // Проверяем, что кнопки найдены при инициализации
    const copyButtons = document.querySelectorAll('.copy-link-btn');
    if (copyButtons.length > 0) {
        console.log(`setupGlobalCopyButtons: найдено ${copyButtons.length} кнопок копирования`);
    } else {
        console.log('setupGlobalCopyButtons: кнопки копирования не найдены');
    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { MaterialFileUploader, MaterialAnimations, AnonymousSessionManager };
}

// Делаем функции доступными глобально
window.copyToClipboard = copyToClipboard;
window.fallbackCopyToClipboard = fallbackCopyToClipboard;
window.showNotification = showNotification;
window.getNotificationIcon = getNotificationIcon;
window.downloadQRCode = downloadQRCode;
window.setupGlobalCopyButtons = setupGlobalCopyButtons; 

// Класс менеджера согласия на cookies
class CookieConsentManager {
    constructor() {
        this.cookieName = 'cookie_consent';
        this.banner = document.getElementById('cookie-consent-banner');
        this.acceptBtn = document.getElementById('cookie-consent-accept');
        this.init();
    }

    init() {
        if (!this.banner || !this.acceptBtn) return;
        if (!this.getCookie(this.cookieName)) {
            this.banner.style.display = 'block';
        }
        this.acceptBtn.addEventListener('click', () => this.accept());
    }

    accept() {
        const maxAge = 365 * 24 * 60 * 60; // 1 год
        document.cookie = `${this.cookieName}=yes; max-age=${maxAge}; path=/; SameSite=Lax`;
        this.banner.style.display = 'none';
    }

    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }
}