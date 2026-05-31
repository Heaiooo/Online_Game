function getAuthToken() {
    return localStorage.getItem('auth_token');
}

function logout() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    window.location.href = '/polls/entrance/';
}

async function loadProfile() {
    const token = getAuthToken();

    if (!token) {
        window.location.href = '/polls/entrance/';
        return;
    }

    try {
        const response = await fetch('/api/profile/stats/', {
            headers: {
                'Authorization': `Token ${token}`
            }
        });

        if (response.ok) {
            const data = await response.json();

            document.getElementById('username').textContent = data.username;
            document.getElementById('email').textContent = data.email;
            document.getElementById('user_id').textContent = data.user_id;
            document.getElementById('games-played').textContent = data.games_played;
            document.getElementById('games-won').textContent = data.games_won;
            document.getElementById('winrate').textContent = `${data.winrate}%`;

            document.getElementById('profile-loading').style.display = 'none';
            document.getElementById('profile-content').style.display = 'block';
        } else if (response.status === 401) {
            logout();
        } else {
            document.getElementById('profile-loading').textContent = 'Ошибка загрузки профиля';
        }
    } catch (error) {
        console.error('Ошибка:', error);
        document.getElementById('profile-loading').textContent = 'Ошибка подключения к серверу';
    }
}

document.getElementById('logoutBtn').addEventListener('click', logout);

loadProfile();