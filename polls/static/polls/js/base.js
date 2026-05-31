const dialog = document.getElementById('myDialog');
const openLink = document.getElementById('openLink');
const closeBtn = document.getElementById('closeBtn');

openLink.addEventListener('click', (event) => {
    event.preventDefault();
    dialog.showModal();
});

closeBtn.addEventListener('click', () => {
    dialog.close();
});


function updateNavigation() {
    const token = localStorage.getItem('auth_token');
    const navContainer = document.getElementById('nav-links');

    if (!navContainer) return;

    if (token) {
        let username = '';
        try {
            const user = JSON.parse(localStorage.getItem('user') || '{}');
            username = user.username || '';
        } catch (e) {}

        navContainer.innerHTML = `<a href="/polls/profile/">Профиль</a>`;

    } else {
        navContainer.innerHTML = `<a href="/polls/entrance/">Вход / Регистрация</a>`;
    }
}

document.addEventListener('DOMContentLoaded', updateNavigation);
window.updateNavigation = updateNavigation;