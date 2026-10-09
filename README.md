# Local Companion

A private, offline-first personal AI companion that runs entirely on your device. All reasoning happens locally — the only permitted online calls are for real-time factual lookups (weather), never for reasoning or decision-making.

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

**Online lookups** (weather):
```
User Input -> Wake Word Check -> Reasoning (local) -> wttr.in API -> Response [ONLINE_LOOKUP]
```

Only the location parameter is sent online. No memories, tasks, conversation history, or personal information leaves the device.

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
| `OnlineLookupProvider` | `WeatherLookupProvider` | Same |

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
- `WAKE_WORD_ENABLED` — `true` (default) or `false`
- `LLAMA_CPP_URL` — URL of your llama.cpp server (for local_ai mode)
- `WEATHER_PROVIDER_URL` — Weather API URL (default: `https://wttr.in`)

## Starting the Application

```bash
python -m uvicorn app.main:app --reload
```

Then open http://localhost:8000 in your browser.

## Demo Mode

Demo mode works without any external AI models. It uses deterministic keyword matching to classify commands:

| Command Type | Example Keywords |
|-------------|-----------------|
| Save Memory | "remember", "save", "store", "note that" |
| Search Memory | "when is", "what is", "recall", "find" |
| Add Task | "add", "create task", "new task" |
| List Tasks | "show tasks", "list tasks", "pending tasks" |
| Complete Task | "mark", "complete", "finish", "done with" |
| Weather | "weather", "temperature", "forecast" |

### Example Commands

```
Hey Companion, remember that the client meeting is Friday at 3 PM
Hey Companion, when is the client meeting?
Hey Companion, add testing the credential flow to my task list
Hey Companion, show my pending tasks
Hey Companion, mark testing the credential flow as completed
Hey Companion, what is the weather in Bangalore?
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

The companion will send commands to llama.cpp for classification. If llama.cpp is unavailable, switch to Demo mode in the UI.

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
│   │   │   └── weather_provider.py # wttr.in weather lookup
│   │   └── hardware/
│   │       └── placeholders.py    # Future GPIO/hardware stubs
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/app.js
│   ├── templates/
│   │   └── dashboard.html
│   └── main.py                    # FastAPI app + lifespan
├── data/                          # SQLite database (auto-created)
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

## Current Limitations

- Demo mode uses keyword matching, not semantic understanding
- Audio input requires a running whisper.cpp server
- Text-to-speech requires Piper binary installed separately
- No continuous listening (push-to-talk via text/audio upload)
- Single-user design (no authentication)

## Future Raspberry Pi Integration Plan

The architecture is designed for a smooth transition to Raspberry Pi hardware:

1. **Physical mute switch** — Replace `SoftwareMuteController` with `GpioMuteController` reading a GPIO pin
2. **LED indicator** — Replace `WebStatusIndicator` with `GpioLedIndicator` driving an RGB LED strip using the state color mapping
3. **Microphone input** — Replace `AudioFileInputAdapter` with `MicrophoneAudioInput` capturing from a USB or I2S microphone
4. **Speaker output** — Replace `ConsoleTextToSpeech` with `SpeakerOutput` playing audio through a connected speaker
5. **Continuous listening** — Add a background audio capture loop with wake word detection
6. **Power management** — Add battery monitoring and low-power modes

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
