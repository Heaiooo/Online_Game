const gameId = document.getElementById('game-id')?.value;
let currentPlayerTeam = null;
let currentPlayerRole = null;
let socket = null;
let wsConnected = false;

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

async function loadGameStatus() {
    const token = getToken();
    if (!token) return null;

    try {
        const response = await fetch(`/api/game/status/${gameId}/`, {
            headers: { 'Authorization': `Token ${token}` }
        });

        if (response.status === 404) {
            window.location.href = '/polls/start/';
            return;
        }

        if (response.ok) {
            const data = await response.json();
            updateUI(data);
            return data;
        }

    } catch (error) {
        console.error('Ошибка загрузки статуса:', error);
    }
    return null;
}

function updateTeamUI(team, players) {
    const container = document.getElementById(`${team}-players`);
    const countSpan = document.getElementById(`${team}-count`);

    if (!container) return;

    countSpan.textContent = players.length;

    if (players.length === 0) {
        container.innerHTML = '<div class="empty-message">Нет игроков</div>';
        return;
    }

    container.innerHTML = players.map(p => {
        let roleText = '';
        let roleClass = '';

        if (p.role === 'associator') {
            roleText = 'Ассоциатор';
            roleClass = 'associator';
        } else if (p.role === 'disassociator') {
            roleText = 'Десоциатор';
            roleClass = 'disassociator';
        } else {
            roleText = 'Не выбрана';
            roleClass = 'none-role';
        }

        return `
            <div class="player-item">
                <span class="player-name">${escapeHtml(p.username)}</span>
                <span class="player-role ${roleClass}">${roleText}</span>
            </div>
        `;
    }).join('');
}

function chooseRole(role) {
    if (socket && wsConnected) {
        socket.send(JSON.stringify({
            type: 'choose_role',
            role: role
        }));
    } else {
        console.warn('WebSocket не подключён');
    }
}

function switchTeam(team) {
    if (socket && wsConnected) {
        socket.send(JSON.stringify({
            type: 'switch_team',
            team: team
        }));
    }
}

function startGame() {
    if (socket && wsConnected) {
        socket.send(JSON.stringify({
            type: 'start_game'
        }));
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateUI(data) {
    // Обновляем обе команды
    updateTeamUI('blue', data.blue_team);
    updateTeamUI('red', data.red_team);

    // Находим текущего игрока в обновлённых данных
    const allPlayers = [...data.blue_team, ...data.red_team];
    const currentUsername = JSON.parse(localStorage.getItem('user') || '{}').username;
    const currentUser = allPlayers.find(p => p.username === currentUsername);

    if (currentUser) {
        currentPlayerTeam = currentUser.team;
        currentPlayerRole = currentUser.role;

        // Обновляем информацию в localStorage (для отображения в навигации)
        const userData = JSON.parse(localStorage.getItem('user') || '{}');
        userData.team = currentUser.team;
        userData.role = currentUser.role;
        localStorage.setItem('user', JSON.stringify(userData));
    }

    // Показываем выбор роли (всегда показываем, если игра не началась)
    const roleSelection = document.getElementById('role-selection');
    const teamSwitch = document.getElementById('team-switch');

    if (data.status === 'waiting' && currentUser) {
        roleSelection.style.display = 'block';
        teamSwitch.style.display = 'block';
    } else if (data.status === 'active') {
        window.location.href = `/polls/game/${gameId}/`;
    }else {
        roleSelection.style.display = 'none';
        teamSwitch.style.display = 'none';
    }

    // Обновляем отображение ассоциаторов в UI (если есть такие элементы)
    const blueAssociatorSpan = document.getElementById('blue-associator');
    const redAssociatorSpan = document.getElementById('red-associator');
    if (blueAssociatorSpan) {
        const blueAssociator = data.blue_team.find(p => p.role === 'associator');
        blueAssociatorSpan.textContent = blueAssociator ? blueAssociator.username : 'не назначен';
    }
    if (redAssociatorSpan) {
        const redAssociator = data.red_team.find(p => p.role === 'associator');
        redAssociatorSpan.textContent = redAssociator ? redAssociator.username : 'не назначен';
    }

    // Проверяем готовность к старту
    const startContainer = document.getElementById('start-game-container');
    const waitingMessage = document.getElementById('waiting-message');

    const blueHasAssociator = data.blue_team.some(p => p.role === 'associator');
    const redHasAssociator = data.red_team.some(p => p.role === 'associator');
    const blueHasDisassociator = data.blue_team.some(p => p.role === 'disassociator');
    const redHasDisassociator = data.red_team.some(p => p.role === 'disassociator');
    const gameReady = blueHasAssociator && redHasAssociator && blueHasDisassociator && redHasDisassociator;

    if (currentUser && currentUser.role === 'associator' && data.status === 'waiting' && gameReady) {
        startContainer.style.display = 'block';
        waitingMessage.style.display = 'none';
    } else if (data.status === 'active') {
        window.location.href = `/polls/game/${gameId}/`;
    } else {
        startContainer.style.display = 'none';
        waitingMessage.style.display = 'block';
    }
}

function connectWebSocket() {
    console.log('Connecting WebSocket...');
    const token = getToken();
    if (!token) return;

    const wsUrl = `ws://${window.location.host}/ws/lobby/${gameId}/?token=${token}`;
    socket = new WebSocket(wsUrl);

    socket.onopen = function() {
        console.log('WebSocket подключен');
        wsConnected = true;
    };

    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log('WebSocket сообщение:', data);
        updateUI(data);
    };

    socket.onclose = function() {
        console.log('WebSocket отключен');
        wsConnected = false;
        setTimeout(connectWebSocket, 3000);
    };

    socket.onerror = function(error) {
        console.error('WebSocket ошибка:', error);
    };
}

document.addEventListener('DOMContentLoaded', async () => {
    if (!checkAuth()) return;

    await loadGameStatus();

    connectWebSocket();

    document.getElementById('role-associator')?.addEventListener('click', () => chooseRole('associator'));
    document.getElementById('role-disassociator')?.addEventListener('click', () => chooseRole('disassociator'));
    document.getElementById('role-none')?.addEventListener('click', () => chooseRole('none'));
    document.getElementById('switch-to-blue')?.addEventListener('click', () => switchTeam('blue'));
    document.getElementById('switch-to-red')?.addEventListener('click', () => switchTeam('red'));
    document.getElementById('start-game-btn')?.addEventListener('click', startGame);
});
