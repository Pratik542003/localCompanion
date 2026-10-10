const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
module.exports = async function () {
    const elements = new Map();
    const element = id => {
        if (!elements.has(id)) elements.set(id, { textContent: '', disabled: false, style: {}, classList: { add(){}, remove(){}, toggle(){} }, value: '', addEventListener(){} });
        return elements.get(id);
    };
    const tracks = [];
    const contexts = [];
    const nodes = [];
    const requests = [];
    let pendingMicrophone = null;
    class FakeContext {
        constructor() { this.sampleRate = 48000; this.state = 'running'; this.audioWorklet = { addModule: async () => {} }; contexts.push(this); }
        createMediaStreamSource() { return { connect(){}, disconnect(){} }; }
        async resume() {}
        async close() { this.state = 'closed'; }
    }
    class FakeNode {
        constructor() { this.port = {}; nodes.push(this); }
        connect() {} disconnect() {}
    }
    const sandbox = {
        window: { AudioContext: FakeContext, addEventListener(){} },
        navigator: { mediaDevices: { getUserMedia: async () => {
            if (pendingMicrophone) return pendingMicrophone;
            const track = { stopped: false, stop(){ this.stopped = true; } }; tracks.push(track);
            return { getTracks: () => [track] };
        } } },
        document: { getElementById: element, addEventListener(){} },
        AudioWorkletNode: FakeNode, Blob, File, FormData, AbortController, URL,
        console, setTimeout, clearTimeout, setInterval(){},
        fetch: async (url, options) => {
            requests.push({ url, options });
            if (url === '/api/voice') return { json: async () => ({ speech_to_text: true }) };
            if (url === '/api/audio') return { ok: true, json: async () => ({ transcription: 'hello', response: 'Hi!', state: 'ARMED' }) };
            if (url === '/api/mute') return { json: async () => ({ muted: true, state: 'MUTED' }) };
            return { json: async () => ({ muted: false, state: 'ARMED' }) };
        },
    };
    const ctx = vm.createContext(sandbox);
    const source = fs.readFileSync(path.join(__dirname, '../app/static/js/app.js'), 'utf8');
    assert(!/SpeechRecognition|speechSynthesis/.test(source), 'No browser cloud speech APIs');
    vm.runInContext(source, ctx);
    vm.runInContext('addToHistory = () => {}; refreshData = async () => {};', ctx);
    const tick = () => new Promise(resolve => setImmediate(resolve));
    await vm.runInContext('beginCapture(false)', ctx);
    nodes.at(-1).port.onmessage({ data: new Float32Array(4800).fill(0.3) });
    vm.runInContext('stopRecording()', ctx);
    await tick(); await tick();
    const audio = requests.find(r => r.url === '/api/audio');
    assert(audio, 'Manual recording sent to local endpoint');
    const bytes = new DataView(await audio.options.body.get('file').arrayBuffer());
    assert.equal(bytes.getUint32(24, true), 16000);
    assert.equal(bytes.getUint16(22, true), 1);
    assert.equal(bytes.getUint16(34, true), 16);
    assert.equal(bytes.getUint32(40, true), 3200);
    assert(tracks[0].stopped && contexts[0].state === 'closed', 'Stop releases microphone');
    await vm.runInContext('beginCapture(true)', ctx);
    const callback = nodes.at(-1).port.onmessage;
    for (let i = 0; i < 4; i++) callback({ data: new Float32Array(4800).fill(0.15) });
    for (let i = 0; i < 11; i++) callback({ data: new Float32Array(4800) });
    await tick(); await tick();
    assert.equal(requests.filter(r => r.url === '/api/audio').length, 2, 'One utterance sent after a pause');
    // Hold the server response to reproduce speaking again during processing.
    const originalFetch = sandbox.fetch;
    const waiting = [];
    sandbox.fetch = async (url, options) => {
        if (url !== '/api/audio') return originalFetch(url, options);
        requests.push({ url, options });
        return new Promise(resolve => waiting.push(resolve));
    };
    const speakAndPause = () => {
        for (let i = 0; i < 3; i++) callback({ data: new Float32Array(4800).fill(0.012) });
        for (let i = 0; i < 6; i++) callback({ data: new Float32Array(4800) });
    };
    const requestsBeforeQueue = requests.filter(r => r.url === '/api/audio').length;
    speakAndPause(); speakAndPause(); speakAndPause();
    assert.equal(waiting.length, 1, 'Only one speech request is in flight');
    assert.equal(vm.runInContext('voiceQueue.length', ctx), 2, 'Speech during processing is queued, not lost');
    const trimmed = requests.at(-1).options.body.get('file');
    assert(trimmed.size < 44 + 0.8 * 32000, 'Long trailing silence is not sent to Whisper');
    // Slow dashboard refresh cannot delay starting the next queued command.
    vm.runInContext('refreshData = () => new Promise(() => {})', ctx);
    waiting[0]({ ok: true, json: async () => ({ transcription: 'first', response: 'Saved' }) });
    await tick(); await tick();
    assert.equal(waiting.length, 2, 'Next utterance starts as soon as the response arrives');
    assert.equal(vm.runInContext('voiceQueue.length', ctx), 1);
    await vm.runInContext('toggleMute()', ctx);
    assert(tracks.every(track => track.stopped), 'Mute stops every microphone track');
    assert(contexts.every(context => context.state === 'closed'), 'Mute closes audio contexts');
    assert.equal(vm.runInContext('voiceQueue.length', ctx), 0, 'Mute clears pending speech');
    waiting[1]({ ok: true, json: async () => ({ transcription: 'late', response: 'Saved' }) });
    await tick(); await tick();
    assert.equal(waiting.length, 2, 'Muted queued speech never resumes');
    sandbox.fetch = originalFetch;
    const before = requests.filter(r => r.url === '/api/audio').length;
    callback({ data: new Float32Array(48000).fill(0.2) });
    assert.equal(requests.filter(r => r.url === '/api/audio').length, before, 'No recording after mute');
    vm.runInContext('currentState.muted = false', ctx);
    let resolveMicrophone;
    pendingMicrophone = new Promise(resolve => { resolveMicrophone = resolve; });
    const starting = vm.runInContext('beginCapture(false)', ctx);
    await tick();
    vm.runInContext('stopRecording()', ctx);
    const lateTrack = { stopped: false, stop(){ this.stopped = true; } };
    resolveMicrophone({ getTracks: () => [lateTrack] });
    await starting;
    assert(lateTrack.stopped, 'Stopping while permission is pending releases the late microphone');
    const playbacks = [];
    sandbox.Audio = class {
        constructor(url) { this.src = url; this.paused = false; playbacks.push(this); }
        async play() {}
        pause() { this.paused = true; }
    };
    const previousFetch = sandbox.fetch;
    sandbox.fetch = async (url, options) => url === '/api/tts'
        ? { ok: true, blob: async () => new Blob(['RIFFtest'], { type: 'audio/wav' }) }
        : previousFetch(url, options);
    vm.runInContext('ttsEnabled = true; continuousMode = true; voiceBusy = true; capture = { voiced: 0.2, chunks: [], preRoll: [] }', ctx);
    vm.runInContext("speakResponse('First reply'); speakResponse('Second reply')", ctx);
    await tick();
    assert.equal(playbacks.length, 0, 'Speech waits for command processing to finish');
    assert.equal(vm.runInContext('speechQueue.length', ctx), 2, 'Continuous replies are retained instead of skipped');
    vm.runInContext('voiceBusy = false; drainSpeech()', ctx);
    await tick(); await tick();
    assert.equal(playbacks.length, 1, 'Continuous mode plays the first retained reply');
    assert(vm.runInContext('ttsPlaying', ctx), 'Speech output suppresses microphone input');
    assert.equal(vm.runInContext('speechQueue.length', ctx), 1);
    playbacks[0].onended();
    await tick(); await tick();
    assert.equal(playbacks.length, 2, 'Second reply plays after the first finishes');
    assert.equal(vm.runInContext('speechQueue.length', ctx), 0);
    vm.runInContext("speakResponse('Third reply'); updateStateUI({ muted: true, state: 'MUTED' })", ctx);
    assert(playbacks[1].paused, 'Mute stops local speech playback');
    assert.equal(vm.runInContext('speechQueue.length', ctx), 0, 'Mute discards queued speech replies');
    assert(!vm.runInContext('ttsPlaying', ctx), 'Speech state clears after mute');
    const outputs = [];
    class Processor { constructor(){ this.port = { postMessage: samples => outputs.push(samples) }; } }
    let registered;
    const worklet = vm.createContext({ AudioWorkletProcessor: Processor, Float32Array, registerProcessor: (name, ctor) => { registered = ctor; } });
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../app/static/js/audio-capture-worklet.js'), 'utf8'), worklet);
    const silence = new Float32Array(128).fill(1);
    const processor = new registered();
    for (let i = 0; i < 8; i++) assert(processor.process([[new Float32Array(128).fill(0.2), new Float32Array(128).fill(0.6)]], [[silence]]));
    assert.equal(outputs.length, 1, 'Worklet batches eight render blocks into one browser message');
    assert.equal(outputs[0].length, 1024);
    assert(Math.abs(outputs[0][0] - 0.4) < 0.0001, 'Worklet captures mono microphone samples');
    assert(silence.every(value => value === 0), 'Worklet produces no microphone playback echo');
    console.log('PASS: PCM WAV recording, continuous pause detection, mute, permission race, local-only speech');
};
if (require.main === module) module.exports().catch(error => { console.error(error); process.exitCode = 1; });
