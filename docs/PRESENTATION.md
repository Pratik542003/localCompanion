# Local Companion — Presentation Content

Use this content for your slides. Suggested: 10-12 slides, 5-7 minutes.

---

## Slide 1: Title

**Local Companion**
*A Private, Offline-First Personal AI Companion*

- Team: [Your Team Name]
- Infosys Makeathon 2026

---

## Slide 2: The Problem

**Cloud AI assistants have a trust problem.**

- Humane AI Pin shut down when backend services changed
- Rabbit R1 underdelivered when cloud dependencies failed
- Always-listening pendants (Limitless, Omi) face ongoing privacy debates
- Every voice assistant today sends your data to someone else's server

**The gap:** No personal AI companion that keeps reasoning truly local — immune to shutdowns, subscriptions, and privacy breaches.

---

## Slide 3: Our Solution

**Local Companion** — an AI assistant where:

- All reasoning runs on YOUR device (llama.cpp)
- Raw audio never leaves the machine
- Only approved factual lookups (weather, news) go online
- Works offline, no subscription, no cloud dependency
- Honest about what it can and can't do

---

## Slide 4: What It Does

| Domain | Capability | Processing |
|--------|-----------|------------|
| Memory & Recall | Save facts, search memories | 100% Local |
| Productivity | Add/list/complete tasks | 100% Local |
| Weather | Real-time weather lookup | Online (location only) |
| News | Latest headlines | Online (topic only) |
| Unsupported | Honest fallback | 100% Local |

Two human-potential domains: **Memory/Recall** + **Productivity/Tasks**

---

## Slide 5: Privacy by Design

```
                    What stays LOCAL              What goes ONLINE
                    ─────────────────            ─────────────────
                    ✓ All AI reasoning            ✓ Weather location
                    ✓ All memories                ✓ News topic
                    ✓ All tasks                   
                    ✓ All audio                   ✗ No memories
                    ✓ All conversations           ✗ No tasks
                                                  ✗ No audio
                                                  ✗ No personal data
```

- Raw audio deleted immediately after processing
- Every online request logged in Network Events audit trail
- Responses clearly labeled LOCAL or ONLINE LOOKUP
- Physical mute switch stops all processing

---

## Slide 6: Architecture

```
    ┌──────────────────────────────────────────┐
    │              Web Dashboard               │
    │   Voice Input │ Text Input │ State Badge  │
    └──────────────────┬───────────────────────┘
                       │
    ┌──────────────────┴───────────────────────┐
    │           FastAPI Backend                 │
    │  Command Processor → Action Router       │
    └────┬─────────┬──────────┬────────────────┘
         │         │          │
    ┌────┴───┐ ┌───┴────┐ ┌──┴──────────┐
    │ Local  │ │ SQLite │ │   Online    │
    │ LLM    │ │ + FTS5 │ │   Lookups   │
    │(llama) │ │        │ │(weather,    │
    └────────┘ └────────┘ │ news)       │
                          └─────────────┘
         100% LOCAL          APPROVED ONLY
```

---

## Slide 7: Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | Python 3.11, FastAPI | Fast async API, production-grade |
| AI Reasoning | llama.cpp (Phi-3.5-mini) | On-device LLM, no cloud |
| Speech-to-Text | whisper.cpp + Browser API | Dual input, both local |
| Text-to-Speech | Browser SpeechSynthesis | No external service needed |
| Database | SQLite + FTS5 | Full-text search, zero setup |
| Weather | wttr.in | Free, no API key, privacy-friendly |
| News | Wikinews API | Free, no API key, no tracking |

**100% open-source stack. No paid APIs. No vendor lock-in.**

---

## Slide 8: Modularity & Extensibility

Every component is behind an **abstract interface**:

```python
class ReasoningProvider(ABC):        # → DemoProvider / LlamaCppProvider
class MuteController(ABC):           # → SoftwareMute / GpioMute
class StatusIndicator(ABC):          # → WebIndicator / GpioLedIndicator
class AudioInput(ABC):               # → BrowserMic / UsbMicrophone
class OnlineLookupProvider(ABC):     # → Weather / News / (add more)
```

**To move from laptop → Raspberry Pi:**
- Swap `SoftwareMuteController` → `GpioMuteController`
- Swap `WebStatusIndicator` → `GpioLedIndicator`
- Zero application code changes

**To add a new online lookup (e.g., search):**
- Create one new provider file
- Add one enum value
- Wire it in — done

---

## Slide 9: Key Features

| Feature | Details |
|---------|---------|
| Continuous Listening | Browser SpeechRecognition, auto-detects pause |
| Wake Word | Configurable phrase ("Hey Companion") |
| Mute Switch | Hard stop — nothing processed when muted |
| State Indicator | 8 color-coded states (listening, reasoning, online, etc.) |
| Conversation History | Chat-style UI with LOCAL/ONLINE badges |
| Text-to-Speech | Browser-based TTS toggle |
| Demo Mode | Works without any AI model (keyword matching) |
| Network Audit | Every online request logged and visible |

---

## Slide 10: Graceful Degradation

| Scenario | Behavior |
|----------|----------|
| Query beyond AI capability | "I cannot answer this reliably..." (honest fallback) |
| llama.cpp not running | Switch to Demo mode (keyword matching) |
| Internet down | Local features work perfectly, online lookups fail gracefully |
| whisper.cpp not running | Browser speech recognition still works |
| Unsupported browser | Text input always available |

**We'd rather be honest than hallucinate.**

---

## Slide 11: Live Demo

[Run through the demo script — see DEMO_SCRIPT.md]

Show in order:
1. Save memories (LOCAL badge)
2. Recall memories (precise search)
3. Add and complete tasks
4. Weather lookup (ONLINE LOOKUP badge + Network Events)
5. News lookup (ONLINE LOOKUP)
6. Unsupported query (graceful fallback)
7. Continuous listening mode
8. Mute switch

---

## Slide 12: What's Next — Raspberry Pi Roadmap

| Component | Current (Laptop) | Future (Raspberry Pi) |
|-----------|------------------|----------------------|
| Mute | Software button | Physical GPIO switch |
| Indicator | Web badge | RGB LED strip |
| Microphone | Browser API | USB/I2S microphone |
| Speaker | Browser TTS | Connected speaker + Piper |
| Form Factor | Web dashboard | Desk companion device |

Hardware abstraction layer is already in place — migration is implementation, not redesign.

---

## Slide 13: Summary

**Local Companion delivers:**

- Privacy by design — not as an afterthought
- On-device reasoning — immune to shutdowns and connectivity loss
- Clear online/offline boundary — auditable and transparent
- Modular architecture — hardware-agnostic, extensible
- Honest AI — graceful degradation over silent failure
- 100% open-source — no vendor lock-in

**Built for humans who want an AI that works FOR them, not ON them.**

---

## Q&A Preparation

**"Why not use Ollama?"**
> llama.cpp gives us direct control over the inference server with minimal overhead. Ollama is built on llama.cpp anyway — we chose the leaner option for edge deployment.

**"Why a laptop instead of Raspberry Pi?"**
> Our architecture is hardware-agnostic by design. Every component is behind an abstract interface with documented hardware placeholders. The laptop lets us demonstrate full capability; the Pi migration is an implementation swap, not a rewrite.

**"What if the model gives wrong answers?"**
> We use a classification approach, not open-ended generation. The model classifies into 8 action types — save memory, search, add task, etc. If confidence is low or the query doesn't fit, we return an honest "I can't handle this" instead of guessing.

**"How do you handle sensitive data like passwords?"**
> Everything stays in a local SQLite database on the device. No cloud sync, no telemetry, no analytics. The only data that goes online is a weather location or news topic — visible in the Network Events audit trail.

**"Can this scale to more features?"**
> Yes — add a new provider file, add an enum value, wire it in. We added news lookup in under 50 lines of code following the same pattern as weather.
