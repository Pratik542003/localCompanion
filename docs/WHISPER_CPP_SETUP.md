# whisper.cpp Setup Guide

Local speech-to-text engine for the Local Companion. Converts audio files to text entirely on your device — no cloud, no API keys.

> **Note:** whisper.cpp is optional. The dashboard also supports live microphone input via the browser's built-in SpeechRecognition API (works in Chrome/Edge without whisper.cpp). You only need whisper.cpp for audio file uploads or if browser speech recognition isn't available.

---

## Hardware Requirements

| Spec | Minimum | Recommended |
|------|---------|-------------|
| RAM | 4 GB | 8+ GB |
| Disk | 150 MB (base.en model) | 500 MB (small.en model) |
| CPU | Any 64-bit | ARM64 or modern x64 |

---

## Step 1: Download whisper.cpp

Go to the **latest release**: https://github.com/ggerganov/whisper.cpp/releases

Download the right build for your machine:

| Your Machine | Download This |
|---|---|
| Snapdragon / Windows ARM laptop | `whisper-<version>-bin-win-arm64.zip` |
| Intel / AMD Windows laptop | `whisper-<version>-bin-x64.zip` |
| Linux x64 | `whisper-<version>-bin-ubuntu-x64.zip` |

---

## Step 2: Extract

Extract the ZIP to a folder. Recommended location:

```
C:\whisper-cpp\
```

After extraction you should see `whisper-server.exe` (or `server` on older versions) inside the folder or in a `Release` subfolder.

---

## Step 3: Download Whisper Model

Download one of these models:

### Option A: base.en (Recommended — good balance)

- Size: ~150 MB
- Best for: fast English transcription
- Download: https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin

```powershell
mkdir C:\whisper-cpp\models
cd C:\whisper-cpp\models

curl -L -o ggml-base.en.bin "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin"
```

Or download directly in your browser from the link above.

### Option B: tiny.en (Fastest — lower accuracy)

- Size: ~75 MB
- Best for: very fast transcription on low-spec hardware
- Download: https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin

```powershell
curl -L -o ggml-tiny.en.bin "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin"
```

### Option C: small.en (Most accurate)

- Size: ~500 MB
- Best for: best accuracy, slower processing
- Download: https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin

```powershell
curl -L -o ggml-small.en.bin "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin"
```

---

## Step 4: Start the Server

Open PowerShell/Terminal and run:

```powershell
cd C:\whisper-cpp
.\whisper-server.exe -m models\ggml-base.en.bin --port 8081
```

If the executable is in a `Release` subfolder:
```powershell
cd C:\whisper-cpp\Release
.\whisper-server.exe -m ..\models\ggml-base.en.bin --port 8081
```

### Command Flags

| Flag | What It Does | Adjust When |
|------|-------------|-------------|
| `-m` | Path to model file | Change if you used a different model |
| `--port` | Server port | Change if 8081 is taken |
| `-t` | CPU threads | Set to your CPU core count |

Wait until you see:
```
whisper_server: server is listening on http://0.0.0.0:8081
```

---

## Step 5: Verify It Works

Open a **new** PowerShell window:

```powershell
# Health check (if supported by your version)
Invoke-RestMethod http://localhost:8081/health
```

To test with an actual audio file:
```powershell
# Record a short WAV file or use any existing one
curl -X POST http://localhost:8081/inference -F "file=@test.wav"
```

---

## Connect to Local Companion

Edit `C:\Pratik\makeathon\local-companion\.env`:

```
WHISPER_CPP_URL=http://localhost:8081
WHISPER_CPP_TIMEOUT=30
```

Then restart the Local Companion app. The "Upload Audio" button on the dashboard will now work.

---

## How Audio Input Works in Local Companion

The dashboard supports **three** ways to input audio:

| Method | Requires whisper.cpp? | How It Works |
|--------|----------------------|-------------|
| **Text input** | No | Type commands directly |
| **Record button** (browser speech) | No | Uses Chrome/Edge SpeechRecognition API — transcription happens in the browser |
| **Continuous listening** | No | Same as above but always-on |
| **Upload audio file** | Yes | Sends audio file to whisper.cpp for transcription |

---

## Supported Audio Formats

The Local Companion accepts these audio file formats for upload:
- `.wav` (recommended)
- `.mp3`
- `.ogg`
- `.flac`
- `.webm`

Maximum file size: 25 MB

---

## Performance Tips

| Tip | How |
|-----|-----|
| Faster transcription | Use `tiny.en` model |
| Better accuracy | Use `small.en` model |
| Reduce RAM usage | Use `tiny.en` model |
| Long audio files | Increase timeout in `.env`: `WHISPER_CPP_TIMEOUT=60` |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `whisper-server.exe` not found | Check if it's in a `Release` subfolder, or try `server.exe` (older versions) |
| "Port 8081 already in use" | Kill the process: `netstat -ano \| findstr :8081` then `taskkill /PID <pid> /F` |
| Upload button says "Speech-to-text is not available" | whisper.cpp server is not running or URL is wrong in `.env` |
| Transcription is empty | Audio may be too quiet, too short, or in a format whisper can't decode. Try a `.wav` file |
| Out of memory | Use the `tiny.en` model |
| Slow transcription | Use `tiny.en` model or reduce audio length |
