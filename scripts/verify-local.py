"""Live local integration check; requires the Qwen/Whisper servers, never the internet."""
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import settings
from app.core.privacy import require_local_url
from app.core.mute_controller import mute_controller
from app.main import app, lifespan

original_async_send = httpx.AsyncClient.send
original_sync_send = httpx.Client.send

async def local_async_send(client, request, **kwargs):
    require_local_url(str(request.url))
    return await original_async_send(client, request, **kwargs)

def local_sync_send(client, request, **kwargs):
    require_local_url(str(request.url))
    return original_sync_send(client, request, **kwargs)

async def verify():
    original_path = settings.database_path
    original_mode = settings.companion_mode
    try:
        settings.companion_mode = 'local_ai'
        mute_controller.unmute()
        with tempfile.TemporaryDirectory() as tmp:
            settings.database_path = str(Path(tmp) / 'verification.db')
            with patch.object(httpx.AsyncClient, 'send', local_async_send), patch.object(httpx.Client, 'send', local_sync_send):
                async with lifespan(app):
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://localhost') as client:
                        examples = [
                            ('Hey', 'Hi!'), ('my name is rishav', 'Rishav'),
                            ('what is your name', 'Local Companion'), ('what is my name?', 'Rishav'),
                            ('my meeting is Friday at 3 PM', 'saved'),
                            ('my meeting is in Monday at 3 PM', 'saved'),
                            ('when is my meeting?', 'Your meeting is on Monday at 3 PM.'),
                            ('what is 4 + 6', '10'), ('my favorite color is blue', 'saved'),
                            ('what is my favorite color?', 'blue'),
                            ('Explain photosynthesis in two sentences', 'sun'),
                            ('Make that simpler', None), ('add task buy groceries', 'added'),
                            ('show tasks', 'buy groceries'), ('complete buy groceries', 'completed'),
                            ('show tasks', 'no pending'),
                        ]
                        for text, expected in examples:
                            response = await client.post('/api/command', json={'text': text})
                            response.raise_for_status()
                            result = response.json()
                            assert result['success'] and result['action'] != 'unsupported', result
                            if expected: assert expected.lower() in result['response'].lower(), result
                            print(json.dumps({'input': text, 'response': result['response']}), flush=True)
                        speech = await client.post('/api/tts', json={'text': 'My favorite color is green.'})
                        assert speech.status_code == 200 and speech.content[:4] == b'RIFF'
                        heard = await client.post('/api/audio', files={'file': ('verification.wav', speech.content, 'audio/wav')})
                        assert heard.status_code == 200 and heard.json()['action'] == 'save_memory', heard.text
                        print('Voice transcription:', heard.json()['transcription'], flush=True)
                        recall = await client.post('/api/command', json={'text': 'what is my favorite color?'})
                        assert 'green' in recall.json()['response'].lower()
                        assert not await app.state.network_event_repo.get_all()
                        await client.post('/api/mute')
                        assert (await client.post('/api/tts', json={'text': 'Hello'})).status_code == 409
                        assert not (await client.post('/api/audio', files={'file': ('verification.wav', speech.content, 'audio/wav')})).json()['success']
                        await client.post('/api/unmute')
                        print('PASS: 16 chat turns, real Piper/Whisper round trip, memory, mute, external HTTP blocked.', flush=True)
    finally:
        mute_controller.unmute()
        settings.database_path = original_path
        settings.companion_mode = original_mode

if __name__ == '__main__':
    asyncio.run(verify())
