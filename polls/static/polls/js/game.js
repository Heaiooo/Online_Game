const gameId = document.getElementById('game-id')?.value;
let currentPlayerTeam = null;
let currentPlayerRole = null;
let currentTurnTeam = null;
let currentTurnPhase = null;
let socket = null;
let wsConnected = false;

function getToken() {
    return localStorage.getItem('auth_token');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

if (!getToken()) {
    window.location.href = '/polls/entrance/';
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
            return null;
        }

        if (response.ok) {
            const data = await response.json();
            handleGameUpdate(data);
            return data;
        }

    } catch (error) {
        console.error('Ошибка загрузки статуса:', error);
    }
    return null;
}

function handleGameUpdate(data) {
    console.log(data);
    document.getElementById('blue-score').textContent = data.blue_score;
    document.getElementById('red-score').textContent = data.red_score;

    currentTurnTeam = data.current_turn_team;
    currentTurnPhase = data.turn_phase;

    if (currentTurnTeam) {
        const turnLabel = document.querySelector('.turn-label');
        const teamText = currentTurnTeam === 'blue' ? 'синих' : 'красных';
        const phaseText = currentTurnPhase === 'hint'
            ? 'ассоциатор пишет подсказку'
            : 'десоциаторы угадывают слова';
        turnLabel.textContent = `Ход ${teamText} (${phaseText})`;
        turnLabel.className = `turn-label ${currentTurnTeam}`;
    }

    const allPlayers = [...(data.blue_team || []), ...(data.red_team || [])];
    const currentUsername = JSON.parse(localStorage.getItem('user') || '{}').username;
    const currentUser = allPlayers.find(p => p.username === currentUsername);

    if (currentUser) {
        currentPlayerTeam = currentUser.team;
        currentPlayerRole = currentUser.role;

        const teamName = currentPlayerTeam === 'blue' ? 'Синие' : 'Красные';
        const chatTeamName = document.getElementById('chat-team-name');
        if (chatTeamName) {
            chatTeamName.textContent = teamName;
            chatTeamName.style.color = currentPlayerTeam === 'blue' ? '#6b9eff' : '#ff7070';
        }

        const roleBadge = document.getElementById('chat-role-badge');
        if (roleBadge) {
            if (currentPlayerRole === 'associator') {
                roleBadge.textContent = 'Ассоциатор';
                roleBadge.className = 'chat-role-badge associator';
            } else {
                roleBadge.textContent = 'Десоциатор';
                roleBadge.className = 'chat-role-badge disassociator';
            }
        }
    }

    if (data.status === 'finished') {
        showGameOverModal(data);
    }

    updateUIByRole(currentPlayerRole, currentTurnTeam, currentPlayerTeam, currentTurnPhase);
}

function updateUIByRole(role, turnTeam, playerTeam, turnPhase) {
    const isMyTeamTurn = (turnTeam === playerTeam);
    const isAssociator = (role === 'associator');
    const isDisassociator = (role === 'disassociator');

    const chatInputArea = document.getElementById('chat-input-area');
    const chatReadonlyMessage = document.getElementById('chat-readonly-message');
    const endTurnBtn = document.getElementById('end-turn-btn');

    if (isAssociator && isMyTeamTurn && turnPhase === 'hint') {
        if (chatInputArea) chatInputArea.style.display = 'flex';
        if (chatReadonlyMessage) chatReadonlyMessage.style.display = 'none';
        if (endTurnBtn) endTurnBtn.style.display = 'none';
    }
    else if (isDisassociator && isMyTeamTurn && turnPhase === 'guess') {
        if (chatInputArea) chatInputArea.style.display = 'none';
        if (chatReadonlyMessage) chatReadonlyMessage.style.display = 'block';
        if (endTurnBtn) endTurnBtn.style.display = 'block';
    }
    else {
        if (chatInputArea) chatInputArea.style.display = 'none';
        if (chatReadonlyMessage) chatReadonlyMessage.style.display = 'block';
        if (endTurnBtn) endTurnBtn.style.display = 'none';
    }
}

async function loadBoard() {
    console.trace('loadBoard called from:');
    try {
        const response = await fetch(`/api/game/board/${gameId}/`, {
            headers: { 'Authorization': `Token ${getToken()}` }
        });

        if (response.ok) {
            const cards = await response.json();
            renderBoard(cards);
        }
    } catch (error) {
        console.error('Ошибка:', error);
    }
}

function renderBoard(cards) {
    const boardContainer = document.getElementById('game-board');
    const isAssociator = (currentPlayerRole === 'associator');
    const isDisassociator = (currentPlayerRole === 'disassociator');
    const isMyTurn = (currentTurnTeam === currentPlayerTeam);
    const canGuess = (currentPlayerRole === 'disassociator' && isMyTurn && currentTurnPhase === 'guess');

    const grid = document.createElement('div');
    grid.className = 'board-grid';

    cards.sort((a, b) => a.order_position - b.order_position);

    cards.forEach(card => {
        const cardDiv = document.createElement('div');
        cardDiv.className = 'card';
        if (card.is_flipped) {
            cardDiv.classList.add('flipped');
        }

        if (!card.is_flipped && card.color && isAssociator) {
            cardDiv.classList.add(`card-${card.color}`);
        }

        cardDiv.textContent = card.word;
        cardDiv.dataset.id = card.id;

        if (canGuess && !card.is_flipped) {
            cardDiv.addEventListener('click', () => guessCard(card.id));
            cardDiv.style.cursor = 'pointer';
        } else {
            cardDiv.style.cursor = 'default';
        }
        grid.appendChild(cardDiv);
    });

    boardContainer.innerHTML = '';
    boardContainer.appendChild(grid);
}

async function guessCard(cardId) {
    if (socket && wsConnected) {
        socket.send(JSON.stringify({
            type: 'guess',
            card_id: cardId
        }));
        return;
    }
}

async function sendChatMessage() {
    const messageInput = document.getElementById('chat-input');
    const message = messageInput?.value.trim();
    if (!message) return;

    if (socket && wsConnected) {
        socket.send(JSON.stringify({
            type: 'chat_message',
            message: message
        }));
        messageInput.value = '';
        return;
    }
}

async function endTurn() {
    if (socket && wsConnected) {
        socket.send(JSON.stringify({
            type: 'end_turn'
        }));
        return;
    }
}

async function loadChatMessages() {
    try {
        const response = await fetch(`/api/game/chat/${gameId}/`, {
            headers: { 'Authorization': `Token ${getToken()}` }
        });

        if (response.ok) {
            const messages = await response.json();
            const container = document.getElementById('chat-messages');
            if (!container) return;

            const currentUsername = JSON.parse(localStorage.getItem('user') || '{}').username;

            if (messages.length === 0) {
                container.innerHTML = '<div class="system-message">Нет сообщений. Ассоциатор, напишите подсказку!</div>';
                return;
            }

            container.innerHTML = messages.map(msg => `
                <div class="message ${msg.username === currentUsername ? 'own' : ''}">
                    <strong>${escapeHtml(msg.username)}</strong>: ${escapeHtml(msg.message)}
                </div>
            `).join('');

            container.scrollTop = container.scrollHeight;
        }
    } catch (error) {
        console.error('Ошибка загрузки чата:', error);
    }
}

function addChatMessage(username, message) {
    const container = document.getElementById('chat-messages');
    if (!container) return;

    const currentUsername = JSON.parse(localStorage.getItem('user') || '{}').username;

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${username === currentUsername ? 'own' : ''}`;
    messageDiv.innerHTML = `<strong>${escapeHtml(username)}</strong>: ${escapeHtml(message)}`;
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

function connectWebSocket() {
    console.log('Connecting WebSocket...');
    const token = getToken();
    if (!token) return;

    const wsUrl = `ws://${window.location.host}/ws/game/${gameId}/?token=${token}`;
    socket = new WebSocket(wsUrl);

    socket.onopen = function() {
        console.log('WebSocket подключен');
        wsConnected = true;
    };

    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log('WebSocket сообщение:', data);

        if (data.type === 'game_update') {
            handleGameUpdate(data.data);
            renderBoard(data.data.cards);
        } else if (data.type === 'chat_message') {
            addChatMessage(data.data.username, data.data.message);
        }
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
    await loadGameStatus();
    await loadBoard();
    await loadChatMessages();

    connectWebSocket();

    document.getElementById('chat-send-btn')?.addEventListener('click', sendChatMessage);
    document.getElementById('end-turn-btn')?.addEventListener('click', endTurn);
    document.getElementById('chat-input')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });
});


function showGameOverModal(data) {

    const modal = document.getElementById('game-over-modal');

    const winnerText = document.getElementById('winner-text');

    if (data.winner_team === 'blue' && currentPlayerTeam === "blue") {
        winnerText.textContent = 'Статус игры: ПОБЕДА';
    } else if (data.winner_team === 'red' && currentPlayerTeam === "red") {
        winnerText.textContent = 'Статус игры: ПОБЕДА';
    } else {
        winnerText.textContent = 'Статус игры: ПОРАЖЕНИЕ';
    }

    document.getElementById('final-blue-score').textContent =
        data.blue_score ?? 0;

    document.getElementById('final-red-score').textContent =
        data.red_score ?? 0;

    modal.classList.remove('hidden');
}