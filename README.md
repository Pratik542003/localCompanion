# Local Companion

A private, offline-first personal AI companion that runs entirely on your device. All reasoning happens locally — the only permitted online calls are for real-time factual lookups (weather), never for reasoning or decision-making.

## Start on this Windows computer

Double-click `scripts/start-qwen.bat`, or from the scripts folder run:

```powershell
.\start-qwen.bat
```

The launcher starts/reuses Qwen on port 8082, Whisper on 8081, and the dashboard on 8000. Piper runs locally when speech is requested. Open http://localhost:8000 and refresh the page after an update.

- **Record:** allow microphone access, speak, then click **Stop**.
- **Continuous: On:** speak and pause; each utterance is transcribed locally. Speech arriving during processing is queued in order (up to four waiting utterances). Listening pauses during speaker playback to avoid hearing its own reply and resumes afterward. No wake phrase is required.
- **TTS: On:** hear responses using the installed local Piper voice.
- **Mute:** immediately stops this page's microphone and speaker playback; the server rejects new commands and speech requests until unmuted. Unmuting does not silently restart recording.
- **Upload:** select a PCM WAV file, then click Upload. Other audio formats need conversion to WAV first.

Chat and voice work without internet after installation. Weather/news requests are separate online lookups with an ONLINE LOOKUP badge. Qwen and Whisper URLs are restricted to loopback addresses; browser network requests are restricted to this app's origin.

## Quick test conversation

1. `my name is Rishav` ? name is saved.
2. `what is my name?` ? `Your name is Rishav.`
3. `my meeting is Friday at 3 PM`
4. `my meeting is in Monday at 3 PM`
5. `when is my meeting?` ? `Your meeting is on Monday at 3 PM.`
6. `what is 4 + 6` ? `10`
7. `my favorite color is blue`
8. `what is my favorite color?` ? `Your favorite color is blue.`
9. `Explain photosynthesis in two sentences`
10. `Make that simpler` ? follows the previous explanation.
11. `add task buy groceries`, then `show tasks`, then `complete buy groceries`.

Repeat these using Record or Continuous mode. Test Mute while recording: your browser's microphone indicator should turn off. Turn TTS on to hear the replies. Actual microphone permissions and input volume must be checked on your computer.

## Verification

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe scripts/verify-local.py
# Optional, if Node.js is installed:
node tests/test_voice_ui.cjs
```

The live verification uses a temporary database and rejects external HTTP destinations. It checks real Qwen follow-ups, Piper WAV output, Whisper transcription, saved preferences, and mute. It does not alter your saved memories.

## Architecture

```
                    +------------------+
                    |   Web Dashboard  |
                    |  (HTML/CSS/JS)   |
                    +--------+---------+
                             |
                    +--------+---------+
                    |   FastAPI Server  |
                    |   (API Routes)    |
                    +--------+---------+
                             |
                    +--------+---------+
                    | Command Processor |
                    +--------+---------+
                             |
         +-------------------+-------------------+
         |                   |                   |
   +-----+------+    +------+------+    +-------+-------+
   |  Wake Word  |    |  Reasoning  |    |  Online       |
   |  Processor  |    |  Provider   |    |  Lookup       |
   +-------------+    +------+------+    +-------+-------+
                             |                   |
                      +------+------+    +-------+-------+
                      | Demo | LLM  |    | Weather       |
                      | Mode | Mode  |    | (wttr.in)     |
                      +------+------+    +---------------+
                             |
                    +--------+---------+
                    |   SQLite + FTS5  |
                    |  (memories,      |
                    |   tasks, events) |
                    +------------------+
```

### Data Flow

**Local requests** (memory, tasks):
```
User Input -> Wake Word Check -> Reasoning (local) -> SQLite -> Response [LOCAL]
```

**Online lookups** (weather, news):
```
User Input -> Wake Word Check -> Reasoning (local) -> wttr.in / Wikinews API -> Response [ONLINE_LOOKUP]
```

Only the location/topic parameter is sent online. No memories, tasks, conversation history, or personal information leaves the device.

### Hardware Abstraction Layer

All components are behind abstract interfaces so hardware can be swapped in later:

| Interface | Software Implementation | Future Hardware |
|-----------|------------------------|-----------------|
| `AudioInput` | `AudioFileInputAdapter` | `MicrophoneAudioInput` (USB/I2S mic) |
| `SpeechToText` | `WhisperCppSpeechToText` | Same (runs on-device) |
| `ReasoningProvider` | `DemoReasoningProvider` / `LlamaCppReasoningProvider` | Same (runs on-device) |
| `MemoryRepository` | `SQLiteMemoryRepository` | Same |
| `TextToSpeech` | `ConsoleTextToSpeech` / `PiperTextToSpeech` | `SpeakerOutput` (GPIO audio) |
| `MuteController` | `SoftwareMuteController` | `GpioMuteController` (physical switch) |
| `StatusIndicator` | `WebStatusIndicator` (state manager) | `GpioLedIndicator` (RGB LED) |
| `OnlineLookupProvider` | `WeatherLookupProvider` / `NewsLookupProvider` | Same |

## Privacy

- Raw audio is **never** permanently stored
- Temporary audio files are deleted after processing (even on failure)
- Local requests never trigger internet calls
- Cloud AI services are **prohibited** — no cloud LLM, STT, or TTS
- Online requests contain only minimum required factual parameters
- Secrets are read from environment variables
- Application logs do not contain complete personal memories
- All responses clearly indicate LOCAL or ONLINE_LOOKUP processing

## Application States

| State | Color | Description |
|-------|-------|-------------|
| MUTED | Grey (#9E9E9E) | Companion is muted, ignoring all input |
| ARMED | Blue (#2196F3) | Ready for input |
| LISTENING | Green (#4CAF50) | Actively listening |
| TRANSCRIBING | Yellow (#FFEB3B) | Converting audio to text |
| REASONING_LOCAL | Purple (#9C27B0) | Processing with local AI |
| ONLINE_LOOKUP | Amber (#FF9800) | Making approved online request |
| SPEAKING | Cyan (#00BCD4) | Delivering response |
| ERROR | Red (#F44336) | An error occurred |

## Installation

### Prerequisites

- Python 3.11 or newer

### Windows

```powershell
cd local-companion
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

### Linux

```bash
cd local-companion
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` to configure:
- `COMPANION_MODE` — `demo` (default) or `local_ai`
- `WAKE_WORD_ENABLED` — `false` (default); set `true` to require the wake phrase
- `LLAMA_CPP_URL` — URL of your llama.cpp server (for local_ai mode)
- `WEATHER_PROVIDER_URL` — Weather API URL (default: `https://wttr.in`)

## Starting the Application

```bash
python -m uvicorn app.main:app --reload
```

Then open http://localhost:8000 in your browser.

## Demo Mode

Demo mode works without any external AI models. It uses deterministic keyword matching to classify commands:

Demo mode also handles greetings and simple arithmetic, such as `what is 4 + 6`.
It is not a general conversational model. For explanations, writing, and follow-up
questions, select **Local AI Mode (conversation)** and run a local model server.
The mode selector changes the active provider immediately.

Local AI mode keeps the last six exchanges in memory for follow-up questions.
**Clear History** clears this conversation context; restarting the app also clears it.
Saved memories stay in SQLite. Recall answers directly using the latest matching
saved entry, for example: "Your meeting is on Monday at 3 PM."
It does not delete older memories or infer a calendar date from a weekday alone.

| Command Type | Example Keywords |
|-------------|-----------------|
| Save Memory | "remember", "save", "store", "note that" |
| Search Memory | "when is", "what is", "recall", "find" |
| Add Task | "add", "create task", "new task" |
| List Tasks | "show tasks", "list tasks", "pending tasks" |
| Complete Task | "mark", "complete", "finish", "done with" |
| Weather | "weather", "temperature", "forecast" |
| News | "news", "headlines", "latest news" |

### Example Commands

```
Hey Companion, remember that the client meeting is Friday at 3 PM
Hey Companion, when is the client meeting?
Hey Companion, add testing the credential flow to my task list
Hey Companion, show my pending tasks
Hey Companion, mark testing the credential flow as completed
Hey Companion, what is the weather in Bangalore?
Hey Companion, what's the latest news?
Hey Companion, write me a poem (unsupported — returns honest fallback)
```

## llama.cpp Integration (Local AI Mode)

1. Download and build [llama.cpp](https://github.com/ggerganov/llama.cpp)

2. Download a GGUF model (recommended for edge devices):
   - [Phi-3-mini-4k-instruct-q4](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf) (~2.3 GB)
   - [Gemma-2-2b-it-Q4_K_M](https://huggingface.co/google/gemma-2-2b-it-GGUF) (~1.5 GB)
   - [Llama-3.2-1B-Instruct-Q4_K_M](https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF) (~0.8 GB)

3. Start the llama.cpp server:
   ```bash
   ./llama-server -m model.gguf --port 8080 -c 2048
   ```

4. Configure Local Companion:
   ```env
   COMPANION_MODE=local_ai
   LLAMA_CPP_URL=http://localhost:8080
   ```

5. Start Local Companion:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

The companion sends messages and recent conversation to llama.cpp for local answers
and command routing. If the model is unavailable or returns an invalid result,
basic commands fall back to deterministic handling and general chat reports the
model issue.

## whisper.cpp Integration (Optional Speech-to-Text)

1. Download and build [whisper.cpp](https://github.com/ggerganov/whisper.cpp)

2. Download a Whisper model:
   ```bash
   ./models/download-ggml-model.sh base.en
   ```

3. Start the whisper.cpp server:
   ```bash
   ./server -m models/ggml-base.en.bin --port 8081
   ```

4. Configure:
   ```env
   WHISPER_CPP_URL=http://localhost:8081
   ```

5. Upload audio files through the dashboard's audio upload feature.

## Piper Integration (Optional Text-to-Speech)

1. Download [Piper](https://github.com/rhasspy/piper/releases)

2. Download a voice model from [Piper voices](https://rhasspy.github.io/piper-samples/)

3. Configure:
   ```env
   PIPER_BINARY_PATH=/path/to/piper
   PIPER_MODEL_PATH=/path/to/model.onnx
   ```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/state` | Current companion state |
| POST | `/api/mute` | Mute the companion |
| POST | `/api/unmute` | Unmute the companion |
| POST | `/api/command` | Process a text command |
| POST | `/api/audio` | Process an audio file |
| GET | `/api/memories` | List all memories |
| GET | `/api/memories/search?q=` | Search memories |
| DELETE | `/api/memories/{id}` | Soft-delete a memory |
| GET | `/api/tasks` | List all tasks |
| POST | `/api/tasks` | Create a task directly |
| PATCH | `/api/tasks/{id}` | Update task status |
| GET | `/api/network-events` | List network events |
| POST | `/api/mode` | Switch demo/local_ai mode |
| POST | `/api/conversation/clear` | Clear recent conversation context |

### Command Request/Response

```json
// Request
POST /api/command
{"text": "Hey Companion, add API testing to my task list"}

// Response
{
  "success": true,
  "action": "add_task",
  "processing_mode": "LOCAL",
  "response": "I've added \"API testing\" to your task list.",
  "state": "SPEAKING",
  "confidence": 0.92
}
```

## Project Structure

```
local-companion/
├── app/
│   ├── api/
│   │   └── routes.py              # FastAPI endpoint definitions
│   ├── core/
│   │   ├── config.py              # Application settings (Pydantic)
│   │   ├── state_manager.py       # Companion state management
│   │   ├── mute_controller.py     # Software mute/unmute
│   │   └── wake_word.py           # Wake phrase detection
│   ├── domain/
│   │   ├── models.py              # Pydantic models, enums
│   │   └── interfaces.py          # Abstract base classes
│   ├── services/
│   │   └── command_processor.py   # Command routing and execution
│   ├── repositories/
│   │   ├── database.py            # SQLite init, FTS5, connections
│   │   ├── memory_repo.py         # Memory CRUD with FTS5 search
│   │   ├── task_repo.py           # Task CRUD with fuzzy matching
│   │   ├── interaction_repo.py    # Interaction logging
│   │   └── network_event_repo.py  # Network event audit trail
│   ├── providers/
│   │   ├── reasoning/
│   │   │   ├── demo_provider.py   # Keyword-based classification
│   │   │   └── llama_provider.py  # llama.cpp integration
│   │   ├── speech_to_text/
│   │   │   └── whisper_provider.py # whisper.cpp integration
│   │   ├── text_to_speech/
│   │   │   ├── console_tts.py     # Console output (default)
│   │   │   └── piper_tts.py       # Piper TTS integration
│   │   ├── online_lookup/
│   │   │   ├── weather_provider.py # wttr.in weather lookup
│   │   │   └── news_provider.py    # Wikinews news lookup
│   │   └── hardware/
│   │       └── placeholders.py    # Future GPIO/hardware stubs
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/app.js
│   ├── templates/
│   │   └── dashboard.html
│   └── main.py                    # FastAPI app + lifespan
├── data/                          # SQLite database (auto-created)
├── docs/
│   ├── LLAMA_CPP_SETUP.md         # llama.cpp setup guide
│   ├── WHISPER_CPP_SETUP.md       # whisper.cpp setup guide
│   ├── PROJECT_SETUP.md           # Complete project setup
│   ├── DEMO_SCRIPT.md             # Live demo script
│   └── PRESENTATION.md            # Presentation slide content
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

## Current Limitations

- Demo mode uses keyword matching, not semantic understanding
- Microphone, continuous listening, and WAV uploads require the local whisper.cpp server; the launcher starts it.
- Continuous listening works while the dashboard is open and the browser has microphone permission. It stops on Mute, Continuous: Off, or leaving the page.
- Single-user design (no authentication)
- Hardware providers are placeholders. Physical switch, light, standalone audio, and target-device validation still require implementation.

## Future Raspberry Pi Integration Plan

The architecture is designed for a smooth transition to Raspberry Pi hardware:

1. **Physical mute switch** — Replace `SoftwareMuteController` with `GpioMuteController` reading a GPIO pin
2. **LED indicator** — Replace `WebStatusIndicator` with `GpioLedIndicator` driving an RGB LED strip using the state color mapping
3. **Microphone input** — Replace `AudioFileInputAdapter` with `MicrophoneAudioInput` capturing from a USB or I2S microphone
4. **Speaker output** — Replace `ConsoleTextToSpeech` with `SpeakerOutput` playing audio through a connected speaker
5. **Power management** — Add battery monitoring and low-power modes

No core application code needs rewriting — only the hardware provider implementations need to be created within the existing interface contracts.

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11+, FastAPI |
| Database | SQLite + FTS5 |
| Validation | Pydantic v2 |
| HTTP Client | httpx |
| Local LLM | llama.cpp (optional) |
| Local STT | whisper.cpp (optional) |
| Local TTS | Piper (optional) |
| Frontend | HTML, CSS, JavaScript |
| Weather API | wttr.in (free, no key required) |
| News API | Wikinews (free, no key required) |
