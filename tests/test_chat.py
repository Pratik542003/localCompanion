import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings
from app.core.mute_controller import mute_controller
from app.core.wake_word import WakeWordProcessor
from app.domain.models import ActionType
from app.providers.reasoning.demo_provider import DemoReasoningProvider
from app.providers.reasoning.llama_provider import LlamaCppReasoningProvider
from app.repositories.database import init_db
from app.repositories.interaction_repo import SQLiteInteractionRepository
from app.repositories.memory_repo import SQLiteMemoryRepository
from app.repositories.network_event_repo import SQLiteNetworkEventRepository
from app.repositories.task_repo import SQLiteTaskRepository
from app.services.command_processor import CommandProcessor


class ChatTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_path = settings.database_path
        self.old_wake = settings.wake_word_enabled
        self.old_mode = settings.companion_mode
        settings.database_path = str(Path(self.temp.name) / "test.db")
        settings.wake_word_enabled = False
        mute_controller.unmute()
        await init_db()
        self.memories = SQLiteMemoryRepository()
        self.processor = CommandProcessor(
            DemoReasoningProvider(), self.memories, SQLiteTaskRepository(),
            SQLiteInteractionRepository(), SQLiteNetworkEventRepository(),
        )

    async def asyncTearDown(self):
        settings.database_path = self.old_path
        settings.wake_word_enabled = self.old_wake
        settings.companion_mode = self.old_mode
        self.temp.cleanup()

    async def test_reported_conversation_uses_latest_fact(self):
        await self.processor.process_text("meeting is Friday at 3 PM")
        await self.processor.process_text("meeting is at 3:00 PM")
        greeting = await self.processor.process_text("Hey")
        self.assertEqual(greeting.action, "answer")
        self.assertIn("Hi!", greeting.response)
        await self.processor.process_text("my meeting is in Monday at 3 PM")
        reply = await self.processor.process_text("when i have a meeeting?")
        self.assertIn("Monday at 3 PM", reply.response)
        self.assertNotIn("Friday", reply.response)
        self.assertEqual(reply.response, "Your meeting is on Monday at 3 PM.")
        reply = await self.processor.process_text("when is my meeting?")
        self.assertEqual(reply.response, "Your meeting is on Monday at 3 PM.")
        self.assertEqual(len(await self.memories.get_all()), 3)
        math_reply = await self.processor.process_text("what is 4 + 6")
        self.assertEqual(math_reply.response, "10")
        self.assertEqual(math_reply.processing_mode, "LOCAL")

    async def test_saving_preserves_subject_and_case(self):
        await self.processor.process_text("remember that Alice's birthday is May 8")
        await self.processor.process_text("my meeting is Monday at 3 PM")
        content = {m.content for m in await self.memories.get_all()}
        self.assertIn("Alice's birthday is May 8", content)
        self.assertIn("my meeting is Monday at 3 PM", content)

    async def test_recall_remains_specific_and_excludes_deleted_records(self):
        await self.processor.process_text("remember Alice client meeting is Friday")
        await self.processor.process_text("remember Bob client meeting is Monday")
        reply = await self.processor.process_text("when is Alice client meeting?")
        self.assertIn("Friday", reply.response)
        self.assertNotIn("Monday", reply.response)
        matches = await self.memories.search("Alice client meeting")
        await self.memories.soft_delete(matches[0].id)
        self.assertEqual(await self.memories.search("Alice client meeting"), [])
        self.assertEqual(await self.memories.search("when is it?"), [])

    async def test_math_is_bounded_and_does_not_execute_code(self):
        for text, expected in [
            ("what is 4 plus 6?", "10"),
            ("calculate (4 + 6) * 2", "20"),
            ("what is 1000001 + 0.5", "1000001.5"),
            ("calculate -4 + 6", "2"),
            ("calculate 8 / 2", "4"),
        ]:
            with self.subTest(text=text):
                self.assertEqual((await self.processor.process_text(text)).response, expected)
        reply = await self.processor.process_text("what is 1 / 0")
        self.assertIn("zero", reply.response)
        result = await DemoReasoningProvider().reason("__import__('os').system('echo bad')")
        self.assertEqual(result.action, ActionType.UNSUPPORTED)

    async def test_keywords_do_not_match_inside_words(self):
        result = await DemoReasoningProvider().reason("hello there")
        self.assertNotEqual(result.action, ActionType.LIST_TASKS)
        result = await DemoReasoningProvider().reason("my address is Mumbai")
        self.assertEqual(result.action, ActionType.SAVE_MEMORY)

    async def test_local_ai_shortcuts_and_offline_fallback(self):
        provider = LlamaCppReasoningProvider("http://localhost:8080", "default", 5)
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
            self.assertEqual((await provider.reason("Hey")).action, ActionType.ANSWER)
            self.assertEqual((await provider.reason("what is 4 + 6")).response, "10")
            post.assert_not_called()
            post.side_effect = httpx.ConnectError("offline")
            result = await provider.reason("my meeting is Monday at 3 PM")
            self.assertEqual(result.parameters["content"], "my meeting is Monday at 3 PM")

    async def test_local_ai_conversation_response_is_delivered(self):
        provider = LlamaCppReasoningProvider("http://localhost:8080", "default", 5)
        self.processor._reasoning = provider
        response = httpx.Response(200, request=httpx.Request("POST", "http://localhost"),
            json={"choices": [{"message": {"content":
                '{"action":"answer","parameters":{},"confidence":0.9,"response":"I can help you plan your day."}'}}]})
        await self.processor.process_text("Hey")
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=response) as post:
            reply = await self.processor.process_text("How can you help me?")
            messages = post.call_args.kwargs["json"]["messages"]
            self.assertEqual(messages[-3]["content"], "Hey")
            self.assertIn("Hi!", messages[-2]["content"])
            self.assertEqual(messages[-1]["content"], "How can you help me?")
        self.assertEqual(reply.response, "I can help you plan your day.")

    async def test_mode_switch_changes_active_provider_and_clear_resets_history(self):
        app = FastAPI()
        app.include_router(router)
        app.state.command_processor = self.processor
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://test") as client:
            reply = await client.post("/api/mode", json={"mode": "local_ai"})
            self.assertEqual(reply.status_code, 200)
            self.assertIsInstance(self.processor._reasoning, LlamaCppReasoningProvider)
            await client.post("/api/command", json={"text": "Hey"})
            self.assertTrue(self.processor._conversation)
            reply = await client.post("/api/conversation/clear", json={})
            self.assertTrue(reply.json()["success"])
            self.assertEqual(self.processor._conversation, [])
            await client.post("/api/mode", json={"mode": "demo"})
            self.assertIsInstance(self.processor._reasoning, DemoReasoningProvider)

    async def test_bad_model_output_has_useful_fallback(self):
        provider = LlamaCppReasoningProvider("http://localhost:8080", "default", 5)
        for content in ('[]', '{"action":"answer","confidence":"bad"}',
                        '{"action":"answer","confidence":0.9,"response":""}'):
            response = httpx.Response(200, request=httpx.Request("POST", "http://localhost"),
                json={"choices": [{"message": {"content": content}}]})
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=response):
                result = await provider.reason("Explain photosynthesis")
            self.assertEqual(result.action, ActionType.UNSUPPORTED)
            self.assertIn("reliable answer", result.response)

    async def test_wake_phrase_is_optional_and_can_still_be_used(self):
        wake = WakeWordProcessor("Hey Companion", enabled=False)
        self.assertEqual(wake.process("what is 4 + 6"), (True, "what is 4 + 6"))
        self.assertEqual(wake.process("Hey Companion, what is 4 + 6"),
                         (True, "what is 4 + 6"))
        reply = await self.processor.process_text("Hey Companion, what is 4 + 6")
        self.assertEqual(reply.response, "10")
        wake = WakeWordProcessor("Hey Companion", enabled=True)
        self.assertEqual(wake.process("what is 4 + 6"), (False, ""))

    async def test_plain_model_follow_up_is_delivered_but_actions_still_execute(self):
        provider = LlamaCppReasoningProvider("http://localhost:8080", "default", 5)
        response = httpx.Response(200, request=httpx.Request("POST", "http://localhost"),
            json={"choices": [{"message": {"content": "Plants make food using sunlight."}}]})
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=response):
            result = await provider.reason("Make that simpler.")
            self.assertEqual(result.action, ActionType.ANSWER)
            self.assertEqual(result.response, "Plants make food using sunlight.")
            result = await provider.reason("remember my meeting is Monday at 3 PM")
            self.assertEqual(result.action, ActionType.SAVE_MEMORY)
            self.assertEqual(result.parameters["content"], "my meeting is Monday at 3 PM")

    async def test_names_are_saved_and_assistant_identity_is_separate(self):
        # Even a model that routes everything to chat cannot skip these operations.
        self.processor._reasoning = LlamaCppReasoningProvider("http://localhost:8080", "default", 5)
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
            reply = await self.processor.process_text("my name is rishav")
            self.assertEqual(reply.action, "save_memory")
            self.assertIn("Nice to meet you, Rishav", reply.response)
            reply = await self.processor.process_text("what is your name")
            self.assertEqual(reply.response, "I'm Local Companion, your local personal assistant.")
            reply = await self.processor.process_text("what is my name?")
            self.assertEqual(reply.response, "Your name is Rishav.")
            self.processor.clear_conversation()
            reply = await self.processor.process_text("do you remember my name?")
            self.assertEqual(reply.response, "Your name is Rishav.")
            post.assert_not_called()
        self.assertEqual((await self.memories.get_all())[0].content, "my name is rishav")

    async def test_name_recall_ignores_other_people_and_uses_latest_user_name(self):
        await self.processor.process_text("remember Alice's name is Alice")
        reply = await self.processor.process_text("what is my name?")
        self.assertIn("don't know your name yet", reply.response)
        await self.processor.process_text("my name is Rishav")
        await self.processor.process_text("remember Bob's name is Bob")
        self.assertEqual((await self.processor.process_text("what's my name?")).response,
                         "Your name is Rishav.")
        await self.processor.process_text("my name is Rishav Kumar")
        self.assertEqual((await self.processor.process_text("what is my name?")).response,
                         "Your name is Rishav Kumar.")

    async def test_general_questions_are_not_treated_as_personal_memory_searches(self):
        provider = LlamaCppReasoningProvider("http://localhost:8082", "qwen3-4b", 5)
        response = httpx.Response(200, request=httpx.Request("POST", "http://localhost"),
            json={"choices": [{"message": {"content": "Gravity is the attraction between masses."}}]})
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=response):
            result = await provider.reason("what is gravity?")
        self.assertEqual(result.action, ActionType.ANSWER)
        self.assertIn("attraction", result.response)
        await self.processor.process_text("remember my email is rishav@example.com")
        result = await self.processor.process_text("what is my email?")
        self.assertIn("rishav@example.com", result.response)

    async def test_preferences_are_saved_and_recalled_without_model(self):
        self.processor._reasoning = LlamaCppReasoningProvider("http://localhost:8082", "qwen3-4b", 5)
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
            saved = await self.processor.process_text("my favorite color is blue")
            self.assertTrue(saved.success)
            self.assertEqual(saved.action, "save_memory")
            reply = await self.processor.process_text("what is my favorite color?")
            self.assertEqual(reply.response, "Your favorite color is blue.")
            post.assert_not_called()
        self.assertEqual(len(await self.memories.get_all()), 1)

    async def test_model_cannot_execute_or_claim_an_unperformed_write(self):
        provider = LlamaCppReasoningProvider("http://localhost:8082", "qwen3-4b", 5)
        for content in ("I've saved your favorite color.",
                        '{"action":"save_memory","parameters":{"content":"invented"},"response":"Saved"}'):
            response = httpx.Response(200, request=httpx.Request("POST", "http://localhost"),
                json={"choices": [{"message": {"content": content}}]})
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=response):
                result = await provider.reason("Thanks for helping")
            self.assertNotEqual(result.action, ActionType.SAVE_MEMORY)
            self.assertNotIn("I've saved", result.response)
        self.assertEqual(await self.memories.get_all(), [])

    async def test_failed_database_write_does_not_acknowledge_success(self):
        with patch.object(self.memories, "save", new_callable=AsyncMock, side_effect=OSError("disk full")):
            result = await self.processor.process_text("remember my favorite color is blue")
        self.assertFalse(result.success)
        self.assertNotIn("saved", result.response)

    async def test_mute_during_reasoning_blocks_pending_action(self):
        from app.domain.models import ReasoningResult
        async def reason(text):
            mute_controller.mute()
            return ReasoningResult(action=ActionType.SAVE_MEMORY, parameters={"content": "invented"}, confidence=1, response="saved")
        with patch.object(self.processor._reasoning, "reason", new=reason):
            result = await self.processor.process_text("Please help me think")
        self.assertEqual(result.state, "MUTED")
        self.assertFalse(result.success)
        self.assertEqual(await self.memories.get_all(), [])
        mute_controller.unmute()

    async def test_explanations_containing_command_words_do_not_change_tasks(self):
        provider = DemoReasoningProvider()
        for text in ("Explain how to add numbers", "How do I complete a project?", "Explain why a meeting is useful"):
            self.assertEqual((await provider.reason(text)).action, ActionType.UNSUPPORTED)


if __name__ == "__main__":
    unittest.main()
