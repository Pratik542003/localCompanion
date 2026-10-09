# Local Companion — Live Demo Script

Use this exact sequence during the hackathon demo. Total time: ~5 minutes.

---

## Pre-Demo Checklist

Before you go on stage, make sure all three are running:

```powershell
# Terminal 1 — AI Model
cd C:\llama-cpp
.\llama-server.exe -m models\Phi-3.5-mini-instruct-Q4_K_M.gguf --port 8080 -c 2048 -t 8

# Terminal 2 — Speech-to-Text (optional)
cd C:\whisper-cpp
.\whisper-server.exe -m models\ggml-base.en.bin --port 8081

# Terminal 3 — Local Companion
cd C:\Pratik\makeathon\local-companion
.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

Open **http://localhost:8000** in Chrome/Edge. Clear any old data:
- Delete all test memories (click Delete on each)
- Clear conversation history (click "Clear History")

---

## Demo Flow

### Act 1: Introduction (30 seconds)

> "This is Local Companion — a private, offline-first AI companion. Everything you see runs entirely on this device. No cloud AI, no subscriptions, no data leaving the machine."

**Show:** Point to the dashboard — state badge (Blue = ARMED), mode selector (Local AI), mute button.

---

### Act 2: Memory & Recall (60 seconds)

**Save memories — type or speak these:**

```
remember that Shreyash birthday is on 25th January
```
> "Notice the badge says LOCAL — this was processed entirely on-device by our local LLM."

```
the wifi password is Guest2026
```

```
the client meeting is Friday at 3 PM
```

**Search memories:**

```
when is Shreyash birthday?
```
> "It finds exactly the right memory — not everything, just what matches."

```
what is the wifi password?
```

**Point out:** Memories panel on the right shows all saved facts.

---

### Act 3: Productivity / Task Management (45 seconds)

```
add review pull requests to my task list
```

```
add buy groceries to my task list
```

**Show tasks panel** — both tasks appear as "pending."

```
mark buy groceries as completed
```

**Show:** Task status changes to "completed" with green badge.

```
show my pending tasks
```

> "One task remaining — review pull requests."

---

### Act 4: Online Lookup — The Boundary (60 seconds)

> "Now watch what happens when I ask something that requires real-time data."

```
what is the weather in Mumbai?
```

> **Point out THREE things:**
> 1. State badge turned **Amber** (ONLINE_LOOKUP) — visually different from purple (local)
> 2. Response badge says **ONLINE LOOKUP** instead of LOCAL
> 3. **Network Events panel** at the bottom logged exactly what was sent: only the location "Mumbai" went to wttr.in — no personal data

```
what's the latest news?
```

> "Same thing — badge shows ONLINE LOOKUP, and the network log shows only the request to Wikinews. Our memories, tasks, and conversation never leave the device."

---

### Act 5: Graceful Degradation (30 seconds)

```
write me a poem about the sunset
```

> "Instead of hallucinating or failing silently, the companion honestly says: 'I cannot answer this reliably using my current local capabilities.' This is by design — we'd rather be honest than wrong."

---

### Act 6: Continuous Listening (45 seconds)

> "The problem statement requires continuous local sensing. Watch this."

1. Click **"Continuous: Off"** — it turns green, says "Continuous: On"
2. State badge turns **Green** (LISTENING)
3. **Speak naturally:** "remember that the team standup is at 10 AM every day"
4. Wait 2 seconds — it auto-detects the pause and processes
5. Response appears in chat history
6. Microphone automatically resumes listening

> "No button clicks needed. It listens continuously, detects when you stop speaking, processes locally, and goes back to listening."

Click **"Continuous: Off"** to stop.

---

### Act 7: Privacy & Mute (30 seconds)

1. Click **Mute** button — badge turns Grey (MUTED)
2. Try a command: "remember something" → "The companion is currently muted."
3. Click **Unmute** — badge turns Blue (ARMED)

> "The mute switch is a hard stop. When muted, nothing is processed. In a hardware version, this would be a physical switch."

---

### Act 8: Architecture Highlight (30 seconds)

> "Everything is built with clean interfaces. We have abstract base classes for every component — AudioInput, ReasoningProvider, MuteController, StatusIndicator. Right now these are software implementations. To move to a Raspberry Pi with a physical button and LED, we just swap the implementations — zero application code changes."

---

## Backup: If Something Goes Wrong

| Problem | Quick Fix |
|---------|-----------|
| AI not responding | Switch to Demo mode (dropdown) — keyword-based, instant |
| Continuous listening not working | Use Record button or type commands |
| Weather fails | Skip to next demo point — "internet connectivity issue" |
| Slow response | Say "the local model is processing on CPU" — it's expected |

---

## Key Phrases to Hit During Demo

Use these exact phrases to score well on each criteria:

- **Privacy:** "Raw audio never leaves the device. Temp files are deleted immediately after processing."
- **Local reasoning:** "All classification and decision-making happens on-device via llama.cpp. Zero cloud AI calls."
- **Online boundary:** "Only the location parameter goes online. No memories, no tasks, no conversation history."
- **Extensibility:** "Abstract interfaces make this hardware-agnostic. Raspberry Pi integration requires zero core code changes."
- **Graceful degradation:** "We'd rather be honest than hallucinate. Unsupported queries get an explicit fallback."
- **Open source:** "Entire stack is open source — Python, FastAPI, llama.cpp, whisper.cpp, SQLite."
