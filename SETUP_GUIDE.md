# Local Companion — Setup Guide

## Prerequisites
- Python 3.11 or newer
- Windows ARM64 or x64 machine
- ~3 GB free disk space for the AI model

---

## Part 1: Project Setup

```powershell
# 1. Clone or copy the project
cd C:\Pratik\makeathon\local-companion

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
.venv\Scripts\Activate.ps1

# 4. Install dependencies
python -m pip install -e .

# 5. Create config file
copy .env.example .env
```

---

## Part 2: Run in Demo Mode (no AI model needed)

```powershell
# Start the app
cd C:\Pratik\makeathon\local-companion
.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

Open **http://localhost:8000** in your browser.

Try these commands in the dashboard:
```
Hey Companion, remember that the client meeting is Friday at 3 PM
Hey Companion, when is the client meeting?
Hey Companion, add testing the credential flow to my task list
Hey Companion, show my pending tasks
Hey Companion, mark testing the credential flow as completed
Hey Companion, what is the weather in Bangalore?
```

---

## Part 3: llama.cpp Setup (Local AI Mode)

### Download llama.cpp

1. Go to: https://github.com/ggerganov/llama.cpp/releases
2. Download the correct build for your machine:
   - Snapdragon/ARM laptop → `win-arm64` (CPU)
   - Intel/AMD laptop → `win-cpu-x64`
3. Extract to `C:\llama-cpp\`

### Download the AI model

```powershell
mkdir C:\llama-cpp\models

# Phi-3.5-mini (~2.3 GB) — recommended
Invoke-WebRequest -Uri "https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf" -OutFile "C:\llama-cpp\models\phi-3.5-mini-Q4.gguf"
```

Alternative smaller model (~0.8 GB, faster but less accurate):
```powershell
Invoke-WebRequest -Uri "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf" -OutFile "C:\llama-cpp\models\llama-1b-Q4.gguf"
```

### Start llama.cpp server

```powershell
cd C:\llama-cpp
.\llama-server.exe -m models\phi-3.5-mini-Q4.gguf --port 8080 -c 2048 -t 8
```

Wait until you see "listening on port 8080".

### Verify llama.cpp is running

Open a new PowerShell:
```powershell
Invoke-RestMethod http://localhost:8080/health
```

### Switch Local Companion to Local AI mode

Edit `C:\Pratik\makeathon\local-companion\.env`:
```
COMPANION_MODE=local_ai
LLAMA_CPP_URL=http://localhost:8080
LLAMA_CPP_TIMEOUT=60
```

### Start Local Companion

Open a second PowerShell:
```powershell
cd C:\Pratik\makeathon\local-companion
.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

Open **http://localhost:8000**

---

## Running — Two Terminals Needed

```
Terminal 1 (AI model):   cd C:\llama-cpp && .\llama-server.exe -m models\phi-3.5-mini-Q4.gguf --port 8080 -c 2048 -t 8
Terminal 2 (App):        cd C:\Pratik\makeathon\local-companion && .venv\Scripts\Activate.ps1 && python -m uvicorn app.main:app --reload
Browser:                 http://localhost:8000
```

---

## Quick Reference

| What | Command |
|------|---------|
| Activate venv | `.venv\Scripts\Activate.ps1` |
| Start app (demo) | `python -m uvicorn app.main:app --reload` |
| Start llama.cpp | `.\llama-server.exe -m models\phi-3.5-mini-Q4.gguf --port 8080 -c 2048 -t 8` |
| Check app health | `Invoke-RestMethod http://localhost:8000/health` |
| Check llama health | `Invoke-RestMethod http://localhost:8080/health` |
| Dashboard | http://localhost:8000 |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `python` not found | Install Python 3.11+ from https://www.python.org/downloads/ and check "Add to PATH" |
| Port 8000 in use | `netstat -ano \| findstr :8000` then `taskkill /PID <pid> /F` |
| Port 8080 in use | Same as above with `:8080` |
| llama.cpp crashes | Try the smaller model (Llama-3.2-1B) or reduce context: `-c 1024` |
| Slow responses | Reduce threads: `-t 4` or use the 1B model |
| Weather not working | Check internet connection — weather is the only online feature |
