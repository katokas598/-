// Discord Bot Dashboard - JavaScript

// Анимация загрузки страницы
document.addEventListener('DOMContentLoaded', function() {
    const container = document.querySelector('.container');
    if (container) {
        container.style.opacity = '0';
        setTimeout(() => {
            container.style.transition = 'opacity 0.5s ease';
            container.style.opacity = '1';
        }, 100);
    }
});

// Обработка форм с анимацией
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="loading"></span> Загрузка...';
            submitBtn.style.opacity = '0.7';
        }
    });
});

// Валидация форм
function validateForm(form) {
    const inputs = form.querySelectorAll('input[required], textarea[required]');
    let valid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.style.borderColor = 'var(--danger)';
            valid = false;
        } else {
            input.style.borderColor = 'transparent';
        }
    });
    
    return valid;
}

// Тоггл переключателя
document.querySelectorAll('.toggle input').forEach(toggle => {
    toggle.addEventListener('change', function() {
        const label = this.closest('.toggle').nextElementSibling;
        if (label) {
            label.style.color = this.checked ? 'var(--success)' : 'var(--text-muted)';
        }
    });
});

// Предпросмотр сообщения
const messageTextarea = document.querySelector('textarea[name="message"]');
if (messageTextarea) {
    messageTextarea.addEventListener('input', function() {
        const preview = document.getElementById('preview-text');
        if (preview) {
            let text = this.value
                .replace(/{user}/g, '@User')
                .replace(/{username}/g, 'User')
                .replace(/{server}/g, 'Server Name')
                .replace(/{member_count}/g, '42');
            preview.textContent = text || 'Введите сообщение для предпросмотра';
        }
    });
}

// Удаление команд с подтверждением
document.querySelectorAll('a[href*="delete"]').forEach(link => {
    link.addEventListener('click', function(e) {
        if (!confirm('Вы уверены, что хотите удалить эту команду?')) {
            e.preventDefault();
        }
    });
});

// Анимация карточек при появлении
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.card, .stat-card').forEach(card => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    observer.observe(card);
});

// Обработка ошибок сети
window.addEventListener('online', function() {
    showNotification('Соединение восстановлено', 'success');
});

window.addEventListener('offline', function() {
    showNotification('Потеряно соединение с интернетом', 'error');
});

// Уведомления
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 15px 25px;
        background: var(--bg-secondary);
        border-left: 3px solid var(--${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'accent'});
        border-radius: 5px;
        color: var(--text-main);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Копирование в буфер обмена
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Скопировано в буфер обмена', 'success');
    }).catch(() => {
        showNotification('Ошибка копирования', 'error');
    });
}

// Добавляем классы для анимации
setTimeout(() => {
    document.querySelectorAll('.card, .stat-card').forEach((card, index) => {
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}, 100);
