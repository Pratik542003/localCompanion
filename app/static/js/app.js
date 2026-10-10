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

// Microphone samples are sent only to this application's local Whisper server.
let capture = null;
let captureGeneration = 0;
let isRecording = false;
let continuousMode = false;
let voiceBusy = false;
let voiceRequest = null;
let ttsPlaying = false;
const voiceQueue = [];
const MAX_PENDING_UTTERANCES = 4;
const SPEECH_THRESHOLD = 0.010;
const END_PAUSE_SECONDS = 0.55;

function listeningStatus() {
    if (ttsPlaying) return 'Speaking reply. Listening resumes when it finishes.';
    if (voiceBusy) return `Listening locally. Processing previous command${voiceQueue.length ? `; ${voiceQueue.length} waiting` : ''}...`;
    return 'Listening locally. Speak, then pause.';
}
function trimTrailingSilence(chunks, sampleRate, silence) {
    let remove = Math.max(0, Math.floor((silence - 0.15) * sampleRate));
    const result = chunks.slice();
    while (result.length && remove > 0) {
        const last = result[result.length - 1];
        if (last.length <= remove) { remove -= last.length; result.pop(); }
        else { result[result.length - 1] = last.subarray(0, last.length - remove); remove = 0; }
    }
    return result;
}
function submitUtterance(blob, generation) {
    if (currentState.muted || generation !== captureGeneration) return;
    if (voiceBusy) {
        if (voiceQueue.length >= MAX_PENDING_UTTERANCES) {
            voiceStatus('Speech queue is full. Wait for a reply, then repeat your last command.');
            return;
        }
        voiceQueue.push({ blob, generation });
        voiceStatus(listeningStatus());
        return;
    }
    sendRecordedAudio(blob, generation);
}

function voiceStatus(text) { document.getElementById('record-status').textContent = text; }
function voiceControls() {
    document.getElementById('record-label').textContent = isRecording ? 'Stop' : 'Record';
    document.getElementById('record-btn').classList.toggle('recording', isRecording);
    document.getElementById('record-btn').disabled = currentState.muted || continuousMode || voiceBusy;
    document.getElementById('continuous-btn').disabled = currentState.muted || isRecording;
    document.getElementById('continuous-btn').textContent = continuousMode ? 'Continuous: On' : 'Continuous: Off';
    document.getElementById('continuous-btn').classList.toggle('active', continuousMode);
}
function encodeWav(chunks, sampleRate) {
    const size = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const samples = new Float32Array(size);
    let offset = 0;
    for (const chunk of chunks) { samples.set(chunk, offset); offset += chunk.length; }
    const count = Math.floor(size * 16000 / sampleRate);
    const buffer = new ArrayBuffer(44 + count * 2);
    const view = new DataView(buffer);
    const word = (at, text) => [...text].forEach((ch, i) => view.setUint8(at + i, ch.charCodeAt(0)));
    word(0, 'RIFF'); view.setUint32(4, 36 + count * 2, true); word(8, 'WAVE');
    word(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
    view.setUint16(22, 1, true); view.setUint32(24, 16000, true);
    view.setUint32(28, 32000, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
    word(36, 'data'); view.setUint32(40, count * 2, true);
    for (let i = 0; i < count; i++) {
        const position = i * sampleRate / 16000;
        const left = Math.floor(position), fraction = position - left;
        const value = Math.max(-1, Math.min(1, samples[left] * (1 - fraction) + (samples[left + 1] ?? samples[left]) * fraction));
        view.setInt16(44 + i * 2, value < 0 ? value * 32768 : value * 32767, true);
    }
    return new Blob([buffer], { type: 'audio/wav' });
}
function releaseCapture(session) {
    if (!session) return;
    session.stream?.getTracks().forEach(track => track.stop());
    if (session.node) { session.node.port.onmessage = null; session.node.disconnect(); }
    session.source?.disconnect();
    if (session.context && session.context.state !== 'closed') session.context.close().catch(() => {});
}
function stopAllVoice() {
    captureGeneration++;
    releaseCapture(capture); capture = null;
    isRecording = false; continuousMode = false;
    voiceRequest?.abort(); voiceRequest = null;
    voiceBusy = false;
    voiceQueue.length = 0;
    cancelSpeech();
    voiceControls();
}
async function beginCapture(continuous) {
    if (currentState.muted || capture || voiceBusy) return;
    const generation = ++captureGeneration;
    const session = { chunks: [], duration: 0, voiced: 0, silence: 0, preRoll: [] };
    capture = session;
    isRecording = !continuous; continuousMode = continuous; voiceControls();
    voiceStatus('Checking local speech service...');
    try {
        const services = await API.get('/api/voice');
        if (generation !== captureGeneration || capture !== session) return;
        if (!services.speech_to_text) throw new Error('Local speech service is unavailable. Start start-qwen.bat, then retry.');
        session.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 } });
        if (generation !== captureGeneration || capture !== session || currentState.muted) { releaseCapture(session); return; }
        session.context = new (window.AudioContext || window.webkitAudioContext)();
        await session.context.audioWorklet.addModule('/static/js/audio-capture-worklet.js');
        if (generation !== captureGeneration || capture !== session) { releaseCapture(session); return; }
        session.source = session.context.createMediaStreamSource(session.stream);
        session.node = new AudioWorkletNode(session.context, 'companion-capture');
        session.node.port.onmessage = event => {
            if (capture !== session || currentState.muted || ttsPlaying) return;
            const samples = event.data;
            const seconds = samples.length / session.context.sampleRate;
            if (!continuous) {
                session.chunks.push(samples); session.duration += seconds;
                if (session.duration >= 30) stopRecording();
                return;
            }
            const rms = Math.sqrt(samples.reduce((sum, v) => sum + v * v, 0) / samples.length);
            if (!session.chunks.length && rms < SPEECH_THRESHOLD) {
                session.preRoll.push(samples);
                if (session.preRoll.length > Math.ceil(session.context.sampleRate * 0.2 / samples.length)) session.preRoll.shift();
                return;
            }
            if (!session.chunks.length) { session.chunks.push(...session.preRoll); session.preRoll = []; }
            session.chunks.push(samples); session.duration += seconds;
            if (rms >= SPEECH_THRESHOLD) { session.voiced += seconds; session.silence = 0; }
            else session.silence += seconds;
            if (session.silence >= END_PAUSE_SECONDS || session.duration >= 15) {
                const chunks = trimTrailingSilence(session.chunks, session.context.sampleRate, session.silence);
                const voiced = session.voiced;
                session.chunks = []; session.duration = 0; session.voiced = 0; session.silence = 0;
                if (voiced >= 0.18) submitUtterance(encodeWav(chunks, session.context.sampleRate), generation);
            }
        };
        session.source.connect(session.node); session.node.connect(session.context.destination);
        await session.context.resume();
        if (generation !== captureGeneration || capture !== session) { releaseCapture(session); return; }
        voiceStatus(continuous ? 'Listening locally. Speak, then pause.' : 'Recording locally. Speak, then click Stop.');
    } catch (error) {
        if (generation !== captureGeneration) { releaseCapture(session); return; }
        stopAllVoice();
        voiceStatus(error.name === 'NotAllowedError' ? 'Allow microphone access for localhost in your browser and Windows settings.' : error.message);
    }
}
function toggleRecording() { if (isRecording) stopRecording(); else beginCapture(false); }
function stopRecording() {
    const session = capture;
    if (!session || !isRecording) return;
    const generation = captureGeneration;
    capture = null; isRecording = false; releaseCapture(session); voiceControls();
    if (session.chunks.length) sendRecordedAudio(encodeWav(session.chunks, session.context.sampleRate), generation);
    else voiceStatus('No audio captured. Click Record and speak before clicking Stop.');
}
function toggleContinuous() { if (continuousMode) stopContinuousListening(); else beginCapture(true); }
function stopContinuousListening() { stopAllVoice(); voiceStatus('Continuous listening stopped.'); }
async function sendRecordedAudio(blob, generation = captureGeneration) {
    if (currentState.muted || voiceBusy || generation !== captureGeneration) return;
    const controller = new AbortController(); voiceRequest = controller; voiceBusy = true; voiceControls();
    voiceStatus(continuousMode ? listeningStatus() : 'Transcribing locally...');
    const timeout = setTimeout(() => controller.abort(), 240000);
    let failed = false;
    try {
        const form = new FormData(); form.append('file', new File([blob], 'recording.wav', { type: 'audio/wav' }));
        const response = await fetch('/api/audio', { method: 'POST', body: form, signal: controller.signal });
        const data = await response.json();
        if (generation !== captureGeneration || currentState.muted) return;
        if (!response.ok) throw new Error(data.detail || data.error || 'Local transcription failed.');
        addToHistory(data.transcription || null, { ...data, response: data.response || data.error });
        // Updating the dashboard must not prevent the next utterance from processing.
        refreshData().catch(console.error);
    } catch (error) {
        failed = true;
        if (generation === captureGeneration && !currentState.muted) voiceStatus(error.name === 'AbortError' ? 'Local speech request timed out. Try a shorter recording.' : error.message);
    } finally {
        clearTimeout(timeout);
        if (voiceRequest === controller) {
            voiceRequest = null; voiceBusy = false; voiceControls();
            const next = voiceQueue.shift();
            if (next && next.generation === captureGeneration && !currentState.muted) sendRecordedAudio(next.blob, next.generation);
            else {
                if (continuousMode && !failed && !controller.signal.aborted) voiceStatus(listeningStatus());
                drainSpeech();
            }
        }
    }
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
    const displayState = currentState.muted ? 'MUTED' : ttsPlaying ? 'SPEAKING' : capture && currentState.state === 'ARMED' ? 'LISTENING' : currentState.state;
    const color = STATE_COLORS[displayState] || STATE_COLORS.ARMED;

    dot.style.background = color;
    badge.style.borderColor = color;
    stateText.textContent = displayState;

    const muteBtn = document.getElementById('mute-btn');
    if (currentState.muted) {
        if (capture || voiceRequest || speechRequest) stopAllVoice();
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
    if (!currentState.muted) { stopAllVoice(); voiceStatus('Microphone stopped.'); }
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
    if (!ttsEnabled) cancelSpeech();
    document.getElementById('tts-btn').textContent = ttsEnabled ? 'TTS: On' : 'TTS: Off';
}

let speechAudio = null;
let speechRequest = null;
let speechUrl = null;
const speechQueue = [];
function cancelSpeech(clearQueue = true) {
    if (clearQueue) speechQueue.length = 0;
    speechRequest?.abort(); speechRequest = null;
    if (speechAudio) { speechAudio.pause(); speechAudio.src = ''; speechAudio = null; }
    if (speechUrl) { URL.revokeObjectURL(speechUrl); speechUrl = null; }
    ttsPlaying = false;
    if (continuousMode && !currentState.muted) voiceStatus(listeningStatus());
}
function speakResponse(text) {
    if (!ttsEnabled || currentState.muted || !text) return;
    speechQueue.push(text.slice(0, 4000));
    drainSpeech();
}
async function drainSpeech() {
    if (!ttsEnabled || currentState.muted || speechRequest || !speechQueue.length) return;
    // Defer replies while commands are processing instead of silently discarding them.
    if (continuousMode && (voiceBusy || voiceQueue.length)) return;
    const text = speechQueue.shift();
    const controller = new AbortController(); speechRequest = controller;
    const timeout = setTimeout(() => controller.abort(), 60000);
    try {
        const response = await fetch('/api/tts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }), signal: controller.signal });
        if (!response.ok) { const data = await response.json(); throw new Error(data.detail || 'Local voice output failed.'); }
        const blob = await response.blob();
        if (speechRequest !== controller || currentState.muted) return;
        if (continuousMode && (voiceQueue.length || voiceBusy)) {
            speechQueue.unshift(text);
            cancelSpeech(false);
            return;
        }
        ttsPlaying = true;
        if (continuousMode) voiceStatus(listeningStatus());
        if (capture) { capture.chunks = []; capture.preRoll = []; capture.duration = 0; capture.voiced = 0; capture.silence = 0; }
        speechUrl = URL.createObjectURL(blob); speechAudio = new Audio(speechUrl);
        speechAudio.onended = () => {
            if (speechRequest === controller) { cancelSpeech(false); drainSpeech(); }
        };
        speechAudio.onerror = () => {
            if (speechRequest === controller) { cancelSpeech(false); voiceStatus('Could not play the local voice response.'); drainSpeech(); }
        };
        await speechAudio.play();
    } catch (error) {
        if (speechRequest === controller) {
            cancelSpeech(false);
            if (error.name !== 'AbortError') voiceStatus(error.name === 'NotAllowedError' ? 'Browser blocked audio playback. Turn TTS off and on, then try again.' : error.message);
            drainSpeech();
        }
    } finally { clearTimeout(timeout); }
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

async function clearHistory() {
    try {
        const result = await API.post('/api/conversation/clear');
        if (!result.success) throw new Error(result.detail || 'Could not clear conversation');
    } catch (e) {
        alert(e.message);
        return;
    }
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

    if (!navigator.mediaDevices?.getUserMedia || !(window.AudioContext || window.webkitAudioContext)) {
        voiceStatus('Microphone requires a browser with audio support. Open http://localhost:8000.');
        document.getElementById('record-btn').disabled = true;
        document.getElementById('continuous-btn').disabled = true;
    }
});
window.addEventListener('pagehide', stopAllVoice);
