# llama.cpp Setup Guide

Local AI reasoning engine for the Local Companion. Runs the LLM entirely on your device — no cloud, no API keys.

## Qwen3 setup for this Windows ARM computer

The installed model is [Qwen3-4B Q4_K_M](https://huggingface.co/Qwen/Qwen3-4B-GGUF),
stored at `data/models/Qwen3-4B-Q4_K_M.gguf`. The existing ARM64 llama.cpp runtime
is at `C:\llama-cpp\models\llama-server.exe`.

Double-click `scripts/start-qwen.bat` to start Qwen, Whisper, and the companion together. Piper provides local spoken responses when TTS is enabled.
The launcher reuses an already running Qwen server. It binds to `127.0.0.1:8082`,
uses eight CPU threads and an 8192-token context, and disables thinking mode for
ordinary conversation. It does not replace a different service on that port.

The companion opens at **http://localhost:8000**. Its `/health` endpoint should
report `"model": "qwen3-4b"`. No wake phrase is required. Qwen server logs and its
process ID are under `data/runtime/`. Saved memories stay in the existing database.

For a model-only start:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-qwen.ps1
```

The downloaded file's SHA256 is
`7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`,
as published on the [official file page](https://huggingface.co/Qwen/Qwen3-4B-GGUF/blob/main/Qwen3-4B-Q4_K_M.gguf).

---

## Hardware Requirements

| Spec | Minimum | Recommended |
|------|---------|-------------|
| RAM | 8 GB | 16+ GB |
| Disk | 1 GB (small model) | 3 GB (Phi-3.5-mini) |
| CPU | Any 64-bit | ARM64 or modern x64 |

---

## Step 1: Download llama.cpp

Go to the **latest release**: https://github.com/ggerganov/llama.cpp/releases

Download the right build for your machine:

| Your Machine | Download This |
|---|---|
| Snapdragon / Windows ARM laptop | `llama-<version>-bin-win-arm64.zip` |
| Intel / AMD Windows laptop | `llama-<version>-bin-win-cpu-x64.zip` |
| Intel / AMD with NVIDIA GPU | `llama-<version>-bin-win-cuda-cu12.2.0-x64.zip` |
| Linux x64 | `llama-<version>-bin-ubuntu-x64.zip` |

---

## Step 2: Extract

Extract the ZIP to a folder. Recommended location:

```
C:\llama-cpp\
```

After extraction you should see `llama-server.exe` (or `llama-server` on Linux) inside the folder.

---

## Step 3: Download AI Model

Create a `models` folder and download one of these GGUF models:

### Option A: Phi-3.5-mini (Recommended — best accuracy)

- Size: ~2.3 GB
- Best for: accurate command classification
- Download: https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf

```powershell
mkdir C:\llama-cpp\models
cd C:\llama-cpp\models

# Using curl (recommended for large files)
curl -L -o Phi-3.5-mini-instruct-Q4_K_M.gguf "https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf"
```

Or download directly in your browser from the link above and save to `C:\llama-cpp\models\`.

### Option B: Llama-3.2-1B (Faster — less accurate)

- Size: ~0.8 GB
- Best for: faster responses on low-spec hardware
- Download: https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf

```powershell
curl -L -o Llama-3.2-1B-Instruct-Q4_K_M.gguf "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
```

---

## Step 4: Start the Server

Open PowerShell/Terminal and run:

```powershell
cd C:\llama-cpp
.\llama-server.exe -m models\Phi-3.5-mini-instruct-Q4_K_M.gguf --port 8080 -c 2048 -t 8
```

### Command Flags

| Flag | What It Does | Adjust When |
|------|-------------|-------------|
| `-m` | Path to model file | Change if you used a different model |
| `--port` | Server port | Change if 8080 is taken |
| `-c` | Context size (tokens) | Lower to 1024 if RAM is tight |
| `-t` | CPU threads | Set to your CPU core count (4, 6, 8, etc.) |

Wait until you see:
```
main: server is listening on http://0.0.0.0:8080
```

---

## Step 5: Verify It Works

Open a **new** PowerShell window:

```powershell
# Health check
Invoke-RestMethod http://localhost:8080/health

# Test a completion
curl -X POST http://localhost:8080/v1/chat/completions -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"hello"}],"temperature":0.1}'
```

You should get a JSON response back.

---

## Connect to Local Companion

Edit `C:\Pratik\makeathon\local-companion\.env`:

```
COMPANION_MODE=local_ai
LLAMA_CPP_URL=http://localhost:8080
LLAMA_CPP_TIMEOUT=120
```

Then restart the Local Companion app.

---

## Performance Tips

| Tip | How |
|-----|-----|
| Faster responses | Use the smaller 1B model |
| Reduce RAM usage | Lower context: `-c 1024` |
| Use fewer cores | Lower threads: `-t 4` |
| Snapdragon laptops | The ARM64 build runs well on CPU — no GPU needed |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `llama-server.exe` not found | Make sure you extracted the ZIP and are in the right folder |
| "Port 8080 already in use" | Kill the process: `netstat -ano \| findstr :8080` then `taskkill /PID <pid> /F` |
| Out of memory / crash | Use the smaller 1B model or reduce `-c` to 1024 |
| Very slow responses (30s+) | Reduce `-t` threads, use smaller model, or reduce `-c` |
| "Model file not found" | Check the `-m` path — make sure the `.gguf` file is in the models folder |
| Download fails midway | Use `curl -L -C - -o file.gguf <url>` to resume, or download in browser |
