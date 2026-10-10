import io
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import httpx
from fastapi import FastAPI
from app.api.routes import router
from app.core.mute_controller import mute_controller
from app.core.privacy import require_local_url, require_lookup_url


class VoiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        mute_controller.unmute()
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.state.stt = Mock(is_available=Mock(return_value=True), transcribe=AsyncMock(return_value='hello'))
        self.app.state.tts = Mock(is_available=Mock(return_value=True), speak=AsyncMock(return_value=b'RIFFtest'))
        self.app.state.command_processor = Mock(process_text=AsyncMock())

    def tearDown(self):
        mute_controller.unmute()

    async def test_busy_health_probe_does_not_reject_valid_speech(self):
        from app.domain.models import CommandResponse
        self.app.state.stt.is_available.return_value = False
        self.app.state.command_processor.process_text.return_value = CommandResponse(
            success=True, action='answer', processing_mode='LOCAL', response='Hi!', state='ARMED')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://test') as client:
            result = await client.post('/api/audio', files={'file': ('test.wav', b'RIFFtest', 'audio/wav')})
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json()['success'])
        self.app.state.stt.is_available.assert_not_called()
        self.app.state.stt.transcribe.assert_awaited_once()

    async def test_muted_audio_does_not_transcribe_or_speak(self):
        mute_controller.mute()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://test') as client:
            audio = await client.post('/api/audio', files={'file': ('test.wav', b'RIFFtest', 'audio/wav')})
            speech = await client.post('/api/tts', json={'text': 'Hello'})
        self.assertFalse(audio.json()['success'])
        self.assertEqual(speech.status_code, 409)
        self.app.state.stt.transcribe.assert_not_called()
        self.app.state.tts.speak.assert_not_called()

    async def test_mute_during_transcription_discards_result_and_deletes_audio(self):
        paths = []
        async def transcribe(path):
            paths.append(path)
            self.assertTrue(path.exists())
            mute_controller.mute()
            return 'remember an unwanted fact'
        self.app.state.stt.transcribe.side_effect = transcribe
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://test') as client:
            result = await client.post('/api/audio', files={'file': ('test.wav', b'RIFFtest', 'audio/wav')})
        self.assertEqual(result.json()['state'], 'MUTED')
        self.app.state.command_processor.process_text.assert_not_called()
        self.assertTrue(paths and all(not path.exists() for path in paths))

    async def test_mute_during_synthesis_does_not_release_audio(self):
        async def speak(text):
            mute_controller.mute()
            return b'RIFFtest'
        self.app.state.tts.speak.side_effect = speak
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://test') as client:
            result = await client.post('/api/tts', json={'text': 'Hello'})
        self.assertEqual(result.status_code, 409)
        self.assertNotIn(b'RIFFtest', result.content)

    async def test_transcription_failure_deletes_temporary_audio(self):
        paths = []
        async def transcribe(path):
            paths.append(path)
            raise ValueError('invalid recording')
        self.app.state.stt.transcribe.side_effect = transcribe
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://test') as client:
            result = await client.post('/api/audio', files={'file': ('test.wav', b'RIFFtest', 'audio/wav')})
        self.assertEqual(result.status_code, 500)
        self.assertTrue(paths and all(not path.exists() for path in paths))

    def test_local_endpoints_reject_cloud_and_other_computers(self):
        for url in ('https://example.com', 'http://192.168.1.10:8081', 'http://localhost.example.com', 'http://user:pass@localhost'):
            with self.subTest(url=url), self.assertRaises(ValueError): require_local_url(url)
        for url in ('http://127.0.0.1:8081', 'http://localhost:8082', 'http://[::1]:8081'):
            self.assertEqual(require_local_url(url), url)
        with self.assertRaises(ValueError): require_lookup_url('https://example.com', 'wttr.in')
        with self.assertRaises(ValueError): require_lookup_url('http://wttr.in', 'wttr.in')
        self.assertEqual(require_lookup_url('https://wttr.in', 'wttr.in'), 'https://wttr.in')


if __name__ == '__main__': unittest.main()
