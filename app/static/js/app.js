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

// ---- Live Microphone Recording ----
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let speechRecognition = null;
let liveTranscript = '';

// ---- Continuous Listening Mode ----
let continuousMode = false;
let continuousRecognition = null;
let continuousSilenceTimer = null;
let continuousTranscript = '';

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

function toggleRecording() {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

async function startRecording() {
    const btn = document.getElementById('record-btn');
    const label = document.getElementById('record-label');
    const status = document.getElementById('record-status');

    // Disable continuous button while recording
    document.getElementById('continuous-btn').disabled = true;

    // Try browser speech recognition first (works in Chrome/Edge)
    if (SpeechRecognition) {
        try {
            speechRecognition = new SpeechRecognition();
            speechRecognition.continuous = true;
            speechRecognition.interimResults = true;
            speechRecognition.lang = 'en-US';
            liveTranscript = '';

            speechRecognition.onresult = (event) => {
                let final = '';
                let interim = '';
                for (let i = 0; i < event.results.length; i++) {
                    if (event.results[i].isFinal) {
                        final += event.results[i][0].transcript;
                    } else {
                        interim += event.results[i][0].transcript;
                    }
                }
                liveTranscript = final;
                status.textContent = final + (interim ? '...' + interim : '');
            };

            speechRecognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                if (event.error === 'not-allowed') {
                    status.textContent = 'Microphone permission denied.';
                    stopRecording();
                }
            };

            speechRecognition.onend = () => {
                if (isRecording) {
                    // Auto-restart if still recording (browser stops after silence)
                    try { speechRecognition.start(); } catch (e) {}
                }
            };

            speechRecognition.start();
            isRecording = true;
            btn.classList.add('recording');
            label.textContent = 'Stop';
            status.textContent = 'Listening...';
            updateStateUI({ state: 'LISTENING' });
            return;
        } catch (e) {
            console.warn('Speech recognition failed, falling back to MediaRecorder:', e);
        }
    }

    // Fallback: record raw audio with MediaRecorder (needs whisper.cpp for transcription)
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = async () => {
            stream.getTracks().forEach(t => t.stop());
            const blob = new Blob(audioChunks, { type: 'audio/webm' });
            await sendRecordedAudio(blob);
        };

        mediaRecorder.start();
        isRecording = true;
        btn.classList.add('recording');
        label.textContent = 'Stop';
        status.textContent = 'Recording audio... (needs whisper.cpp for transcription)';
        updateStateUI({ state: 'LISTENING' });
    } catch (e) {
        status.textContent = 'Microphone access denied or unavailable.';
        showResponse({ response: 'Could not access microphone: ' + e.message, processing_mode: 'LOCAL' });
    }
}

function stopRecording() {
    const btn = document.getElementById('record-btn');
    const label = document.getElementById('record-label');
    const status = document.getElementById('record-status');

    isRecording = false;
    btn.classList.remove('recording');
    label.textContent = 'Record';

    // Re-enable continuous button
    document.getElementById('continuous-btn').disabled = false;

    if (speechRecognition) {
        speechRecognition.stop();
        speechRecognition = null;

        if (liveTranscript.trim()) {
            status.textContent = 'Sending: "' + liveTranscript.trim() + '"';
            sendTranscribedText(liveTranscript.trim());
        } else {
            status.textContent = 'No speech detected.';
            updateStateUI({ state: 'ARMED' });
        }
        return;
    }

    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        status.textContent = 'Processing...';
        mediaRecorder.stop();
    } else {
        updateStateUI({ state: 'ARMED' });
    }
}

async function sendTranscribedText(text) {
    const status = document.getElementById('record-status');
    try {
        updateStateUI({ state: 'REASONING_LOCAL' });
        status.textContent = 'Processing: "' + text + '"...';

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000);

        const res = await fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
            signal: controller.signal,
        });
        clearTimeout(timeoutId);
        const data = await res.json();
        addToHistory(text, data);
        if (!continuousMode) {
            status.textContent = '';
        }
        await refreshData();
        return data;
    } catch (e) {
        if (e.name === 'AbortError') {
            addToHistory(text, { response: 'Request timed out. The AI model may be slow — try a shorter command.', processing_mode: 'LOCAL' });
        } else {
            addToHistory(text, { response: 'Error: ' + e.message, processing_mode: 'LOCAL' });
        }
        if (!continuousMode) {
            status.textContent = '';
        }
        updateStateUI({ state: 'ARMED' });
        return null;
    }
}

async function sendRecordedAudio(blob) {
    const status = document.getElementById('record-status');
    const file = new File([blob], 'recording.webm', { type: 'audio/webm' });

    try {
        updateStateUI({ state: 'TRANSCRIBING' });
        const data = await API.postFile('/api/audio', file);
        if (data.transcription) {
            addToHistory(data.transcription, {
                response: data.response || data.error || '',
                processing_mode: data.processing_mode || 'LOCAL',
                state: data.state,
            });
        } else if (data.detail) {
            addToHistory(null, { response: data.detail, processing_mode: 'LOCAL' });
        } else {
            addToHistory(null, data);
        }
        status.textContent = '';
        await refreshData();
    } catch (e) {
        addToHistory(null, { response: 'Audio error: ' + e.message, processing_mode: 'LOCAL' });
        status.textContent = '';
    }
}

// ---- Continuous Listening Mode ----
function toggleContinuous() {
    if (continuousMode) {
        stopContinuousListening();
    } else {
        startContinuousListening();
    }
}

function startContinuousListening() {
    if (!SpeechRecognition) {
        const status = document.getElementById('record-status');
        status.textContent = 'Continuous mode requires Chrome or Edge (SpeechRecognition API).';
        return;
    }

    // Disable the manual record button
    const recordBtn = document.getElementById('record-btn');
    const contBtn = document.getElementById('continuous-btn');
    const status = document.getElementById('record-status');

    continuousMode = true;
    recordBtn.disabled = true;
    contBtn.textContent = 'Continuous: On';
    contBtn.classList.add('active');
    status.textContent = 'Listening...';
    updateStateUI({ state: 'LISTENING' });

    continuousTranscript = '';
    initContinuousRecognition();
}

function initContinuousRecognition() {
    if (!continuousMode) return;

    continuousRecognition = new SpeechRecognition();
    continuousRecognition.continuous = true;
    continuousRecognition.interimResults = true;
    continuousRecognition.lang = 'en-US';

    let finalTranscript = '';

    continuousRecognition.onresult = (event) => {
        let interim = '';
        finalTranscript = '';
        for (let i = 0; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript;
            } else {
                interim += event.results[i][0].transcript;
            }
        }

        const status = document.getElementById('record-status');
        status.textContent = (finalTranscript + (interim ? ' ...' + interim : '')) || 'Listening...';

        // Reset silence timer whenever we get new results
        if (continuousSilenceTimer) {
            clearTimeout(continuousSilenceTimer);
            continuousSilenceTimer = null;
        }

        // If we have a final transcript, start a silence timer
        if (finalTranscript.trim()) {
            continuousSilenceTimer = setTimeout(() => {
                // Silence detected after final results - send the text
                const textToSend = finalTranscript.trim();
                finalTranscript = '';
                continuousTranscript = '';

                if (textToSend && continuousMode) {
                    // Stop current recognition before sending
                    try { continuousRecognition.stop(); } catch (e) {}

                    const status = document.getElementById('record-status');
                    status.textContent = 'Processing...';
                    updateStateUI({ state: 'REASONING_LOCAL' });

                    sendTranscribedText(textToSend).then(() => {
                        if (continuousMode) {
                            restartContinuousListening();
                        }
                    });
                }
            }, 2000);
        }
    };

    continuousRecognition.onend = () => {
        // Browser sometimes stops recognition on its own
        if (continuousMode) {
            // If we have pending final text and a silence timer, let it fire
            if (!continuousSilenceTimer) {
                // No pending text, just restart
                setTimeout(() => {
                    if (continuousMode) {
                        try {
                            initContinuousRecognition();
                        } catch (e) {
                            console.error('Failed to restart continuous recognition:', e);
                        }
                    }
                }, 300);
            }
        }
    };

    continuousRecognition.onerror = (event) => {
        console.error('Continuous recognition error:', event.error);
        if (event.error === 'not-allowed') {
            const status = document.getElementById('record-status');
            status.textContent = 'Microphone permission denied.';
            stopContinuousListening();
            return;
        }
        // For other errors, restart if still in continuous mode
        if (continuousMode) {
            setTimeout(() => {
                if (continuousMode) {
                    initContinuousRecognition();
                }
            }, 500);
        }
    };

    try {
        continuousRecognition.start();
    } catch (e) {
        console.error('Failed to start continuous recognition:', e);
        setTimeout(() => {
            if (continuousMode) {
                initContinuousRecognition();
            }
        }, 500);
    }
}

function restartContinuousListening() {
    if (!continuousMode) return;
    const status = document.getElementById('record-status');
    status.textContent = 'Listening...';
    updateStateUI({ state: 'LISTENING' });
    continuousTranscript = '';
    // Small delay before restarting to avoid rapid start/stop
    setTimeout(() => {
        if (continuousMode) {
            initContinuousRecognition();
        }
    }, 500);
}

function stopContinuousListening() {
    continuousMode = false;

    if (continuousSilenceTimer) {
        clearTimeout(continuousSilenceTimer);
        continuousSilenceTimer = null;
    }

    if (continuousRecognition) {
        try { continuousRecognition.stop(); } catch (e) {}
        continuousRecognition = null;
    }

    continuousTranscript = '';

    const recordBtn = document.getElementById('record-btn');
    const contBtn = document.getElementById('continuous-btn');
    const status = document.getElementById('record-status');

    recordBtn.disabled = false;
    contBtn.textContent = 'Continuous: Off';
    contBtn.classList.remove('active');
    status.textContent = '';
    updateStateUI({ state: 'ARMED' });
}

// ---- Audio File Upload ----
async function uploadAudio() {
    const fileInput = document.getElementById('audio-file');
    const file = fileInput.files[0];
    if (!file) {
        showResponse({ response: 'Please select an audio file first.', processing_mode: 'LOCAL' });
        return;
    }

    const spinner = document.getElementById('audio-spinner');
    spinner.classList.add('active');

    try {
        const data = await API.postFile('/api/audio', file);
        if (data.detail) {
            addToHistory(null, { response: data.detail, processing_mode: 'LOCAL' });
        } else if (data.transcription) {
            addToHistory(data.transcription, {
                response: data.response || data.error || '',
                processing_mode: data.processing_mode || 'LOCAL',
                state: data.state,
            });
        } else {
            addToHistory(null, data);
        }
        await refreshData();
    } catch (e) {
        addToHistory(null, { response: 'Audio upload error: ' + e.message, processing_mode: 'LOCAL' });
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

// ---- State Management ----
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

let ttsEnabled = false;

function toggleTTS() {
    ttsEnabled = !ttsEnabled;
    document.getElementById('tts-btn').textContent = ttsEnabled ? 'TTS: On' : 'TTS: Off';
}

function speakResponse(text) {
    if (!ttsEnabled || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
}

function addToHistory(userText, data) {
    const history = document.getElementById('conversation-history');
    const empty = document.getElementById('conversation-empty');
    if (empty) empty.remove();

    const msg = document.createElement('div');
    msg.className = 'chat-message';

    if (userText) {
        const userBubble = document.createElement('div');
        userBubble.className = 'chat-bubble chat-user';
        userBubble.textContent = userText;
        msg.appendChild(userBubble);
    }

    const companionBubble = document.createElement('div');
    companionBubble.className = 'chat-bubble chat-companion';
    companionBubble.textContent = data.response || data.error || 'No response.';
    msg.appendChild(companionBubble);

    const meta = document.createElement('div');
    meta.className = 'chat-meta';

    const badge = document.createElement('span');
    if (data.processing_mode === 'ONLINE_LOOKUP') {
        badge.textContent = 'ONLINE LOOKUP';
        badge.className = 'processing-badge badge-online';
    } else {
        badge.textContent = 'LOCAL';
        badge.className = 'processing-badge badge-local';
    }
    meta.appendChild(badge);

    const timestamp = document.createElement('span');
    timestamp.textContent = new Date().toLocaleTimeString();
    meta.appendChild(timestamp);

    msg.appendChild(meta);
    history.appendChild(msg);

    history.scrollTop = history.scrollHeight;

    if (data.state) {
        updateStateUI({ state: data.state });
    }

    speakResponse(data.response || data.error || '');
}

function showResponse(data) {
    addToHistory(null, data);
}

function clearHistory() {
    const history = document.getElementById('conversation-history');
    history.innerHTML = '<div class="empty-state" id="conversation-empty">Start a conversation with your companion.</div>';
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
        addToHistory(text, data);
        input.value = '';
        await refreshData();
    } catch (e) {
        addToHistory(text, { response: 'Error: ' + e.message, processing_mode: 'LOCAL' });
    } finally {
        spinner.classList.remove('active');
        btn.disabled = false;
    }
}

// ---- Data Loading ----
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

    // Check if speech recognition is available
    const status = document.getElementById('record-status');
    if (!SpeechRecognition && !navigator.mediaDevices) {
        status.textContent = 'Audio not supported in this browser.';
        document.getElementById('record-btn').disabled = true;
        document.getElementById('continuous-btn').disabled = true;
    } else if (!SpeechRecognition) {
        // Continuous mode requires SpeechRecognition API
        document.getElementById('continuous-btn').disabled = true;
        document.getElementById('continuous-btn').title = 'Requires Chrome or Edge';
    }
});
