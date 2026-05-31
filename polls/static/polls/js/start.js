function getToken() {
    return localStorage.getItem('auth_token');
}

function checkAuth() {
    const token = getToken();
    if (!token) {
        window.location.href = '/polls/entrance/';
        return false;
    }
    return token;
}

async function createLobby() {
    const token = checkAuth();
    if (!token) return;

    try {
        const response = await fetch('/api/game/create/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Token ${token}`
            }
        });

        const data = await response.json();

        if (response.ok) {
            window.location.href = `/polls/lobby/${data.game_id}/`;
        } else {
            alert(data.error || 'Ошибка создания игры');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Ошибка соединения с сервером');
    }
}

async function joinGame() {
    const token = checkAuth();
    const gameId = document.getElementById('join-game-id').value.trim().toUpperCase();

    if (!gameId) {
        showJoinError('Введите код игры');
        return;
    }

    try {
        const response = await fetch('/api/game/join/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Token ${token}`
            },
            body: JSON.stringify({ game_id: gameId })
        });

        const data = await response.json();

        if (response.ok) {
            window.location.href = `/polls/lobby/${gameId}/`;
        } else {
            showJoinError(data.error || 'Не удалось присоединиться к игре');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showJoinError('Ошибка соединения с сервером');
    }
}

function showJoinError(message) {
    const errorDiv = document.getElementById('join-error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 4000);
}

const j_dialog = document.getElementById('join-dialog');
const joinInput = document.getElementById('join-game-id');

document.getElementById('create-lobby-btn').addEventListener('click', createLobby);
document.getElementById('join-lobby-btn').addEventListener('click', () => {
    joinInput.value = '';
    j_dialog.showModal();
});

document.getElementById('confirm-join-btn').addEventListener('click', joinGame);
document.getElementById('cancel-join-btn').addEventListener('click', () => {
    j_dialog.close();
});

joinInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        joinGame();
    }
});

checkAuth();