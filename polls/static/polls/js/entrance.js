function getCSRFToken() {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, 10) === 'csrftoken=') {
                cookieValue = decodeURIComponent(cookie.substring(10));
                break;
            }
        }
    }
    return cookieValue;
}

const tabs = document.querySelectorAll('.tab-btn');
const loginPanel = document.getElementById('login-form');
const registerPanel = document.getElementById('register-form');

tabs.forEach(btn => {
    btn.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        btn.classList.add('active');

        if (btn.dataset.tab === 'login') {
            loginPanel.style.display = 'flex';
            registerPanel.style.display = 'none';
            clearAllLoginErrors();
        } else {
            loginPanel.style.display = 'none';
            registerPanel.style.display = 'flex';
            clearAllRegisterErrors();
        }
    });
});

function setAuthToken(token, user) {
    localStorage.setItem('auth_token', token);
    localStorage.setItem('user', JSON.stringify(user));
}

function showFieldError(elementId, message) {
    const errorSpan = document.getElementById(elementId);
    if (errorSpan) {
        errorSpan.textContent = message;
        errorSpan.style.display = 'block';
    }
    const inputId = elementId.replace('-error', '');
    const input = document.getElementById(inputId);
    if (input) {
        input.style.borderColor = '#ff5252';
        input.style.backgroundColor = '#fff0f0';
    }
}

function clearFieldError(elementId) {
    const errorSpan = document.getElementById(elementId);
    if (errorSpan) {
        errorSpan.textContent = '';
        errorSpan.style.display = 'none';
    }
    const inputId = elementId.replace('-error', '');
    const input = document.getElementById(inputId);
    if (input) {
        input.style.borderColor = '';
        input.style.backgroundColor = '';
    }
}

function showGeneralError(formType, message) {
    const errorDiv = document.getElementById(`${formType}-general-error`);
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }
}

function clearAllLoginErrors() {
    clearFieldError('username-error');
    clearFieldError('password-error');
    const generalError = document.getElementById('login-general-error');
    if (generalError) generalError.style.display = 'none';
}

function clearAllRegisterErrors() {
    clearFieldError('r_username-error');
    clearFieldError('email-error');
    clearFieldError('r_password-error');
    clearFieldError('r2_password-error');
    const generalError = document.getElementById('register-general-error');
    if (generalError) generalError.style.display = 'none';
}

function validateLoginForm() {
    const username = document.getElementById('username');
    const password = document.getElementById('password');
    let isValid = true;

    clearAllLoginErrors();

    const usernameRegex = /^[a-zA-Z0-9_]{5,20}$/;
    if (!usernameRegex.test(username.value)) {
        showFieldError('username-error', 'Логин должен содержать 5-20 символов (латиница, цифры, _)');
        isValid = false;
    }

    if (password.value.length < 7) {
        showFieldError('password-error', 'Пароль должен содержать минимум 7 символов');
        isValid = false;
    }

    return isValid;
}

function validateRegisterForm() {
    const username = document.getElementById('r_username');
    const email = document.getElementById('email');
    const password = document.getElementById('r_password');
    const password2 = document.getElementById('r2_password');
    let isValid = true;

    clearAllRegisterErrors();

    const usernameRegex = /^[a-zA-Z0-9_]{5,20}$/;
    if (!usernameRegex.test(username.value)) {
        showFieldError('r_username-error', 'Логин должен содержать 5-20 символов (латиница, цифры, _)');
        isValid = false;
    }

    const emailRegex = /^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/i;
    if (!emailRegex.test(email.value)) {
        showFieldError('email-error', 'Введите корректный email (пример: user@example.com)');
        isValid = false;
    }

    if (password.value.length < 7) {
        showFieldError('r_password-error', 'Пароль должен содержать минимум 7 символов');
        isValid = false;
    }

    if (password.value !== password2.value) {
        showFieldError('r2_password-error', 'Пароли не совпадают');
        isValid = false;
    }

    return isValid;
}

const loginInputs = ['username', 'password'];
loginInputs.forEach(id => {
    const input = document.getElementById(id);
    if (input) {
        input.addEventListener('input', () => {
            clearFieldError(`${id}-error`);
        });
    }
});

const registerInputs = ['r_username', 'email', 'r_password', 'r2_password'];
registerInputs.forEach(id => {
    const input = document.getElementById(id);
    if (input) {
        input.addEventListener('input', () => {
            clearFieldError(`${id}-error`);
        });
    }
});

document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!validateLoginForm()) {
        return;
    }

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch('/api/login/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (response.ok) {
            setAuthToken(data.token, { id: data.user_id, username: data.username, email: data.email });
            window.location.href = '/polls/';
        } else {
            showGeneralError('login', data.error || 'Неверное имя пользователя или пароль');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showGeneralError('login', 'Ошибка подключения к серверу');
    }
});


document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!validateRegisterForm()) {
        return;
    }

    const username = document.getElementById('r_username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('r_password').value;
    const password2 = document.getElementById('r2_password').value;

    try {
        const response = await fetch('/api/register/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({ username, email, password, password2 })
        });

        const data = await response.json();

        if (response.ok) {
            setAuthToken(data.token, { id: data.user_id, username: data.username, email: data.email });
            window.location.href = '/polls/';
        } else {
            let errorMessage = '';
            if (typeof data === 'object') {
                errorMessage = Object.values(data).flat().join(', ');
            } else {
                errorMessage = data.error || 'Ошибка при регистрации';
            }
            showGeneralError('register', errorMessage);
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showGeneralError('register', 'Ошибка подключения к серверу');
    }
});