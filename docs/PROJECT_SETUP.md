# Local Companion — Complete Project Setup

A private, offline-first personal AI companion. All AI reasoning runs on your device. Only approved factual lookups (weather, news) go online.

---

## Prerequisites

- **Python 3.11+** — https://www.python.org/downloads/ (check "Add to PATH" during install)
- **Browser** — Chrome or Edge (recommended for voice features)
- **~3 GB disk space** for the AI model (optional — Demo mode needs no model)

---

## Quick Start (Demo Mode — No AI Model Needed)

```powershell
# 1. Open PowerShell and navigate to the project
cd C:\Pratik\makeathon\local-companion

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
.venv\Scripts\Activate.ps1

# 4. Install dependencies
python -m pip install -e .

# 5. Start the app
python -m uvicorn app.main:app --reload
```

Open **http://localhost:8000** in your browser. Done!

---

## Configuration

The app reads settings from the `.env` file in the project root.

### Key Settings

| Setting | Values | Default |
|---------|--------|---------|
| `COMPANION_MODE` | `demo` or `local_ai` | `demo` |
| `WAKE_WORD_ENABLED` | `true` or `false` | `false` |
| `WAKE_PHRASE` | Any phrase | `Hey Companion` |
| `LLAMA_CPP_URL` | llama.cpp server URL | `http://localhost:8080` |
| `LLAMA_CPP_TIMEOUT` | Seconds | `120` |
| `WHISPER_CPP_URL` | whisper.cpp server URL | `http://localhost:8081` |
| `WEATHER_PROVIDER_URL` | Weather API URL | `https://wttr.in` |
| `NEWS_PROVIDER_URL` | News API URL | `https://en.wikinews.org` |

---

## Full Setup (Local AI Mode)

For local AI mode, you need **3 terminals** running:

### Terminal 1: llama.cpp (AI reasoning)

See [LLAMA_CPP_SETUP.md](LLAMA_CPP_SETUP.md) for detailed instructions.

```powershell
cd C:\llama-cpp
.\llama-server.exe -m models\Phi-3.5-mini-instruct-Q4_K_M.gguf --port 8080 -c 2048 -t 8
```

### Terminal 2: whisper.cpp (Speech-to-text — optional)

See [WHISPER_CPP_SETUP.md](WHISPER_CPP_SETUP.md) for detailed instructions.

```powershell
cd C:\whisper-cpp
.\whisper-server.exe -m models\ggml-base.en.bin --port 8081
```

### Terminal 3: Local Companion (the app)

```powershell
cd C:\Pratik\makeathon\local-companion
.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

Open **http://localhost:8000** in Chrome or Edge.

---

## Features

### Voice Input (3 ways)

| Method | How | Requirements |
|--------|-----|-------------|
| **Text** | Type in the command box and press Enter | None |
| **Record** | Click Record, speak, click Stop | Chrome or Edge browser |
| **Continuous Listening** | Click "Continuous: Off" to toggle on — always-on listening | Chrome or Edge browser |
| **Upload Audio** | Choose an audio file and click Upload | whisper.cpp running |

### Commands You Can Try

```
remember that Shreyash birthday is on 25th January
when is Shreyash birthday?
the wifi password is Guest2026
what is the wifi password?

add review pull requests to my task list
show my pending tasks
mark review pull requests as completed

what is the weather in Mumbai?
what is the weather in Bangalore?

what's the latest news?

write me a poem
→ "I cannot answer this reliably using my current local capabilities."
```

### Dashboard Features

| Feature | Description |
|---------|-------------|
| **State Badge** | Color-coded indicator showing what the companion is doing |
| **Mode Selector** | Switch between Demo and Local AI mode |
| **Mute Button** | Mute/unmute the companion |
| **TTS Toggle** | Enable/disable browser text-to-speech for responses |
| **Conversation History** | Scrollable chat-style history of all interactions |
| **Memories Panel** | View and delete saved memories |
| **Tasks Panel** | View tasks, mark as completed |
| **Network Events** | Audit log of all online requests (weather, news) |

---

## Application States

The state badge changes color to show what's happening:

| State | Color | Meaning |
|-------|-------|---------|
| MUTED | Grey | Companion is muted |
| ARMED | Blue | Ready for input |
| LISTENING | Green | Microphone is active |
| TRANSCRIBING | Yellow | Converting audio to text |
| REASONING_LOCAL | Purple | AI is processing locally |
| ONLINE_LOOKUP | Amber | Making an approved online request |
| SPEAKING | Cyan | Delivering response |
| ERROR | Red | Something went wrong |

---

## Project Structure

```
local-companion/
├── app/
│   ├── api/routes.py              # API endpoints
│   ├── core/
│   │   ├── config.py              # Settings from .env
│   │   ├── state_manager.py       # State machine
│   │   ├── mute_controller.py     # Mute/unmute
│   │   └── wake_word.py           # Wake phrase detection
│   ├── domain/
│   │   ├── models.py              # Data models (Pydantic)
│   │   └── interfaces.py          # Abstract interfaces
│   ├── services/
│   │   └── command_processor.py   # Command routing
│   ├── repositories/
│   │   ├── database.py            # SQLite + FTS5
│   │   ├── memory_repo.py         # Memory storage
│   │   ├── task_repo.py           # Task storage
│   │   ├── interaction_repo.py    # Interaction logs
│   │   └── network_event_repo.py  # Network audit trail
│   ├── providers/
│   │   ├── reasoning/
│   │   │   ├── demo_provider.py   # Keyword-based (demo mode)
│   │   │   ├── llama_provider.py  # llama.cpp (local AI mode)
│   │   │   └── system_prompt.txt  # Editable AI prompt
│   │   ├── speech_to_text/
│   │   │   └── whisper_provider.py
│   │   ├── text_to_speech/
│   │   │   ├── console_tts.py
│   │   │   └── piper_tts.py
│   │   ├── online_lookup/
│   │   │   ├── weather_provider.py  # wttr.in
│   │   │   └── news_provider.py     # Wikinews
│   │   └── hardware/
│   │       └── placeholders.py      # Future GPIO stubs
│   ├── static/                      # CSS, JS
│   ├── templates/                   # HTML dashboard
│   └── main.py                      # App entry point
├── docs/                            # Setup guides
├── scripts/                         # Setup & run scripts
├── data/                            # SQLite DB (auto-created)
├── pyproject.toml
├── .env
└── README.md
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/state` | Current state, mode, mute status |
| POST | `/api/mute` | Mute companion |
| POST | `/api/unmute` | Unmute companion |
| POST | `/api/command` | Send a text command |
| POST | `/api/audio` | Upload audio file for processing |
| GET | `/api/memories` | List all memories |
| GET | `/api/memories/search?q=` | Search memories |
| DELETE | `/api/memories/{id}` | Delete a memory |
| GET | `/api/tasks` | List all tasks |
| POST | `/api/tasks` | Create a task |
| PATCH | `/api/tasks/{id}` | Update task status |
| GET | `/api/network-events` | View network audit log |
| POST | `/api/mode` | Switch demo / local_ai mode |

---

## Privacy

- All AI reasoning runs on your device (llama.cpp)
- Raw audio is never stored — temp files are deleted after processing
- Only weather location and news topic go online — no personal data
- Every online request is logged in the Network Events panel
- Responses clearly show LOCAL or ONLINE LOOKUP badges
- No cloud AI services are used — ever

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `python` not found | Install Python 3.11+ and check "Add to PATH" |
| Port 8000 in use | `netstat -ano \| findstr :8000` then `taskkill /PID <pid> /F` |
| "No module named 'app'" | Make sure you ran `pip install -e .` and activated the venv |
| Slow AI responses | Use the smaller 1B model, reduce context to `-c 1024` |
| Voice recording not working | Use Chrome or Edge — Firefox doesn't support SpeechRecognition API |
| Weather not working | Check your internet connection |
| Memories not found | Try more specific search terms (stop words are filtered) |
| Browser says "Audio not supported" | Use Chrome or Edge, ensure HTTPS or localhost |

---

## Team Quick Reference

```powershell
# One-time setup
cd C:\Pratik\makeathon\local-companion
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .

# Daily run (Demo mode — 1 terminal)
.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload

# Daily run (Local AI mode — 3 terminals)
# Terminal 1: cd C:\llama-cpp && .\llama-server.exe -m models\Phi-3.5-mini-instruct-Q4_K_M.gguf --port 8080 -c 2048 -t 8
# Terminal 2: cd C:\whisper-cpp && .\whisper-server.exe -m models\ggml-base.en.bin --port 8081
# Terminal 3: cd C:\Pratik\makeathon\local-companion && .venv\Scripts\Activate.ps1 && python -m uvicorn app.main:app --reload

# Browser: http://localhost:8000
```
