"""Connect this companion to the Qwen server without changing unrelated settings."""
from pathlib import Path
import re

root = Path(__file__).resolve().parent.parent
env_path = root / ".env"
text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
original_text = text
for key, value in {
    "COMPANION_MODE": "local_ai",
    "WAKE_WORD_ENABLED": "false",
    "LLAMA_CPP_URL": "http://127.0.0.1:8082",
    "LLAMA_CPP_MODEL": "qwen3-4b",
    "LLAMA_CPP_TIMEOUT": "180",
    "WHISPER_CPP_URL": "http://127.0.0.1:8081",
    "WHISPER_CPP_TIMEOUT": "120",
    "PIPER_BINARY_PATH": (root / "data/tools/piper/piper/piper.exe").as_posix(),
    "PIPER_MODEL_PATH": (root / "data/models/piper/en_US-lessac-medium.onnx").as_posix(),
}.items():
    pattern = rf"^[ \t]*{re.escape(key)}[ \t]*=.*$"
    if re.search(pattern, text, flags=re.M):
        text = re.sub(pattern, f"{key}={value}", text, flags=re.M)
    else:
        text = text.rstrip() + f"\n{key}={value}\n"
if text != original_text:
    env_path.write_text(text, encoding="utf-8")
    # uvicorn's Python-file watcher does not normally watch .env.
    (root / "app" / "core" / "config.py").touch()
print("Companion configured for Qwen3 on port 8082; wake phrase is optional.")
