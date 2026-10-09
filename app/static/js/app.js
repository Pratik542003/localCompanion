const API = {
    async get(url) {
        const res = await fetch(url);
        return res.json();
    },
    async post(url, body = {}) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        return res.json();
    },
    async postFile(url, file) {
        const form = new FormData();
        form.append('file', file);
        const res = await fetch(url, { method: 'POST', body: form });
        return res.json();
    },
    async del(url) {
        const res = await fetch(url, { method: 'DELETE' });
        return res.json();
    },
    async patch(url, body = {}) {
        const res = await fetch(url, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        return res.json();
    },
};

const STATE_COLORS = {
    MUTED: '#9E9E9E',
    ARMED: '#2196F3',
    LISTENING: '#4CAF50',
    TRANSCRIBING: '#FFEB3B',
    REASONING_LOCAL: '#9C27B0',
    ONLINE_LOOKUP: '#FF9800',
    SPEAKING: '#00BCD4',
    ERROR: '#F44336',
};

let currentState = { state: 'ARMED', muted: false, mode: 'demo' };

function updateStateUI(data) {
    currentState = { ...currentState, ...data };
    const dot = document.getElementById('state-dot');
    const badge = document.getElementById('state-badge');
    const stateText = document.getElementById('state-text');
    const color = STATE_COLORS[currentState.state] || STATE_COLORS.ARMED;

    dot.style.background = color;
    badge.style.borderColor = color;
    stateText.textContent = currentState.state;

    const muteBtn = document.getElementById('mute-btn');
    if (currentState.muted) {
        muteBtn.textContent = 'Unmute';
        muteBtn.classList.add('muted');
    } else {
        muteBtn.textContent = 'Mute';
        muteBtn.classList.remove('muted');
    }

    const modeSelect = document.getElementById('mode-select');
    if (data.mode) {
        modeSelect.value = data.mode;
    }
}

async function pollState() {
    try {
        const data = await API.get('/api/state');
        updateStateUI(data);
    } catch (e) {
        console.error('State poll failed:', e);
    }
}

async function toggleMute() {
    const url = currentState.muted ? '/api/unmute' : '/api/mute';
    const data = await API.post(url);
    updateStateUI(data);
    await pollState();
}

async function changeMode() {
    const mode = document.getElementById('mode-select').value;
    try {
        await API.post('/api/mode', { mode });
        currentState.mode = mode;
    } catch (e) {
        alert('Failed to change mode: ' + e.message);
    }
}

function showResponse(data) {
    const area = document.getElementById('response-area');
    const text = document.getElementById('response-text');
    const badge = document.getElementById('response-badge');

    area.classList.add('visible');

    if (data.processing_mode === 'ONLINE_LOOKUP') {
        badge.textContent = 'ONLINE LOOKUP';
        badge.className = 'processing-badge badge-online';
    } else {
        badge.textContent = 'LOCAL';
        badge.className = 'processing-badge badge-local';
    }

    text.textContent = data.response || data.error || 'No response.';

    if (data.state) {
        updateStateUI({ state: data.state });
    }
}

async function sendCommand() {
    const input = document.getElementById('command-input');
    const text = input.value.trim();
    if (!text) return;

    const spinner = document.getElementById('send-spinner');
    const btn = document.getElementById('send-btn');
    spinner.classList.add('active');
    btn.disabled = true;

    try {
        const data = await API.post('/api/command', { text });
        showResponse(data);
        input.value = '';
        await refreshData();
    } catch (e) {
        showResponse({ response: 'Error: ' + e.message, processing_mode: 'LOCAL' });
    } finally {
        spinner.classList.remove('active');
        btn.disabled = false;
    }
}

async function uploadAudio() {
    const fileInput = document.getElementById('audio-file');
    const file = fileInput.files[0];
    if (!file) return;

    const spinner = document.getElementById('audio-spinner');
    spinner.classList.add('active');

    try {
        const data = await API.postFile('/api/audio', file);
        if (data.transcription) {
            showResponse({
                response: `[Transcription: "${data.transcription}"]\n${data.response || data.error || ''}`,
                processing_mode: data.processing_mode || 'LOCAL',
                state: data.state,
            });
        } else {
            showResponse(data);
        }
        await refreshData();
    } catch (e) {
        showResponse({ response: 'Audio error: ' + e.message, processing_mode: 'LOCAL' });
    } finally {
        spinner.classList.remove('active');
        fileInput.value = '';
        document.getElementById('audio-filename').textContent = 'Choose audio file...';
    }
}

function handleAudioSelect() {
    const fileInput = document.getElementById('audio-file');
    const label = document.getElementById('audio-filename');
    if (fileInput.files.length > 0) {
        label.textContent = fileInput.files[0].name;
    } else {
        label.textContent = 'Choose audio file...';
    }
}

async function loadMemories() {
    const list = document.getElementById('memory-list');
    try {
        const data = await API.get('/api/memories');
        if (!data.memories || data.memories.length === 0) {
            list.innerHTML = '<div class="empty-state">No memories saved yet.</div>';
            return;
        }
        list.innerHTML = data.memories.map(m => `
            <div class="memory-item">
                <div class="memory-content">
                    ${escapeHtml(m.content)}
                    <div class="memory-meta">${m.created_at ? new Date(m.created_at).toLocaleString() : ''} &middot; ${m.source}</div>
                </div>
                <button class="delete-btn" onclick="deleteMemory(${m.id})">Delete</button>
            </div>
        `).join('');
    } catch (e) {
        list.innerHTML = '<div class="empty-state">Failed to load memories.</div>';
    }
}

async function deleteMemory(id) {
    await API.del(`/api/memories/${id}`);
    await loadMemories();
}

async function loadTasks() {
    const list = document.getElementById('task-list');
    try {
        const data = await API.get('/api/tasks');
        if (!data.tasks || data.tasks.length === 0) {
            list.innerHTML = '<div class="empty-state">No tasks yet.</div>';
            return;
        }
        list.innerHTML = data.tasks.map(t => `
            <div class="task-item">
                <div class="task-content">
                    ${escapeHtml(t.title)}
                    <div class="task-meta">
                        <span class="task-status ${t.status === 'completed' ? 'status-completed' : 'status-pending'}">${t.status}</span>
                        &middot; ${t.created_at ? new Date(t.created_at).toLocaleString() : ''}
                    </div>
                </div>
                ${t.status === 'pending' ? `<button class="complete-btn" onclick="completeTask(${t.id})">Complete</button>` : ''}
            </div>
        `).join('');
    } catch (e) {
        list.innerHTML = '<div class="empty-state">Failed to load tasks.</div>';
    }
}

async function completeTask(id) {
    await API.patch(`/api/tasks/${id}`, { status: 'completed' });
    await loadTasks();
}

async function loadNetworkEvents() {
    const list = document.getElementById('event-list');
    try {
        const data = await API.get('/api/network-events');
        if (!data.events || data.events.length === 0) {
            list.innerHTML = '<div class="empty-state">No network events recorded.</div>';
            return;
        }
        list.innerHTML = data.events.map(e => `
            <div class="event-item">
                <div class="event-provider">${escapeHtml(e.provider)}</div>
                <div class="event-detail">
                    ${escapeHtml(e.request_type)} &rarr; ${escapeHtml(e.destination)}
                    &middot; Query: ${escapeHtml(e.sanitized_query)}
                </div>
                <div class="event-meta">
                    <span class="${e.success ? 'event-success' : 'event-fail'}">${e.success ? 'Success' : 'Failed'}</span>
                    &middot; ${e.created_at ? new Date(e.created_at).toLocaleString() : ''}
                </div>
            </div>
        `).join('');
    } catch (e) {
        list.innerHTML = '<div class="empty-state">Failed to load network events.</div>';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

async function refreshData() {
    await Promise.all([
        pollState(),
        loadMemories(),
        loadTasks(),
        loadNetworkEvents(),
    ]);
}

document.addEventListener('DOMContentLoaded', () => {
    refreshData();
    setInterval(pollState, 3000);

    const input = document.getElementById('command-input');
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendCommand();
        }
    });
});
