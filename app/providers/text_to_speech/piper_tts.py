from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import subprocess
import wave
from pathlib import Path

from app.domain.interfaces import TextToSpeech

logger = logging.getLogger(__name__)


class PiperTextToSpeech(TextToSpeech):
    """Generate local WAV speech without depending on the server's event loop type."""

    def __init__(self, binary_path: str, model_path: str) -> None:
        self._binary_path = binary_path
        self._model_path = model_path
        self._lock = asyncio.Lock()

    async def speak(self, text: str) -> bytes | None:
        async with self._lock:
            return await asyncio.to_thread(self._synthesize, text)

    def _synthesize(self, text: str) -> bytes | None:
        try:
            process = subprocess.run(
                [self._binary_path, '--model', self._model_path, '--output-raw'],
                input=(text + '\n').encode('utf-8'), capture_output=True,
                timeout=45, check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            if not process.stdout:
                return None
            config = json.loads(Path(self._model_path + '.json').read_text(encoding='utf-8'))
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(config['audio']['sample_rate'])
                wav.writeframes(process.stdout)
            return buffer.getvalue()
        except (OSError, subprocess.SubprocessError, ValueError, KeyError):
            logger.warning('Local speech generation failed')
            return None

    def is_available(self) -> bool:
        return (Path(self._binary_path).is_file() and Path(self._model_path).is_file()
                and Path(self._model_path + '.json').is_file())
