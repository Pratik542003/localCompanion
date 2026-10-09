from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    companion_mode: str = "demo"
    wake_word_enabled: bool = True
    wake_phrase: str = "Hey Companion"

    llama_cpp_url: str = "http://localhost:8080"
    llama_cpp_model: str = "default"
    llama_cpp_timeout: int = 30

    whisper_cpp_url: str = "http://localhost:8081"
    whisper_cpp_timeout: int = 30

    piper_binary_path: str = ""
    piper_model_path: str = ""

    weather_provider_url: str = "https://wttr.in"
    weather_timeout: int = 10

    database_path: str = "data/companion.db"

    host: str = "0.0.0.0"
    port: int = 8000

    allowed_audio_extensions: list[str] = [".wav", ".mp3", ".ogg", ".flac", ".webm"]
    max_audio_size_mb: int = 25

    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}

    @property
    def db_path(self) -> Path:
        return Path(self.database_path)

    @property
    def is_demo_mode(self) -> bool:
        return self.companion_mode.lower() == "demo"


settings = Settings()
