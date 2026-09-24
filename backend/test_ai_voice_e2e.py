import asyncio
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import settings
from backend.router import ModelProvider, route_inference, generate_local_fallback
from backend.orchestrator import select_model_by_intent, orchestrate_task
from backend.voice import (
    tts_manager,
    synthesize,
    AUDIO_CACHE_DIR,
    FishSpeechTTSProvider,
)

class NovaAIVoiceE2ETests(unittest.IsolatedAsyncioTestCase):
    """
    Comprehensive End-to-End Test Suite for NOVA AI Model Routing & Voice System.
    Tests:
    1. Simple question -> Groq
    2. Complex question -> Gemini
    3. Coding request -> NVIDIA
    4. Local/private request -> Ollama
    5. Provider failure -> Fallback
    6. Voice question -> AI response -> Fish Speech audio playback
    7. WebSocket disconnect / reconnect
    8. Error handling & security guards
    """

    def test_01_simple_question_routes_to_groq(self):
        """1. Simple / conversational question routes to Groq."""
        prompt = "Hello NOVA, how are you today?"
        selected = select_model_by_intent(prompt)
        self.assertEqual(selected, ModelProvider.GROQ, f"Expected Groq for conversational prompt, got: {selected}")

    async def test_01b_groq_live_inference(self):
        """1b. Live inference execution via Groq (with automatic fallback if offline)."""
        prompt = "Reply in exactly two words: 'All systems'."
        res = await orchestrate_task(prompt, preferred_model="Groq")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn(res["model_used"], [ModelProvider.GROQ, ModelProvider.GEMINI, ModelProvider.NVIDIA, ModelProvider.OLLAMA, ModelProvider.LOCAL])
        self.assertTrue(len(res["response"]) > 0)

    def test_02_complex_question_routes_to_gemini(self):
        """2. Complex reasoning question routes to Gemini."""
        prompt = "Explain in detail the step by step philosophical implications and architecture of quantum computing."
        selected = select_model_by_intent(prompt)
        self.assertEqual(selected, ModelProvider.GEMINI, f"Expected Gemini for reasoning prompt, got: {selected}")

    async def test_02b_gemini_live_inference(self):
        """2b. Live inference execution via Gemini."""
        prompt = "In 5 words, explain why the sky appears blue."
        res = await orchestrate_task(prompt, preferred_model="Gemini")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn(res["model_used"], [ModelProvider.GEMINI, ModelProvider.GROQ, ModelProvider.NVIDIA, ModelProvider.OLLAMA, ModelProvider.LOCAL])
        self.assertTrue(len(res["response"]) > 0)

    def test_03_coding_request_routes_to_nvidia(self):
        """3. Coding request routes to NVIDIA."""
        prompt = "Write a python function to implement binary search on an array."
        selected = select_model_by_intent(prompt)
        self.assertEqual(selected, ModelProvider.NVIDIA, f"Expected NVIDIA for coding prompt, got: {selected}")

    async def test_03b_nvidia_live_inference(self):
        """3b. Live inference execution via NVIDIA."""
        prompt = "Write a one line python lambda function that squares a number."
        res = await orchestrate_task(prompt, preferred_model="NVIDIA")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn(res["model_used"], [ModelProvider.NVIDIA, ModelProvider.GEMINI, ModelProvider.GROQ, ModelProvider.OLLAMA, ModelProvider.LOCAL])
        self.assertTrue(len(res["response"]) > 0)

    def test_04_local_private_request_routes_to_ollama(self):
        """4. Local / private / offline request routes to Ollama."""
        prompt = "Process this note privately on local offline model."
        selected = select_model_by_intent(prompt)
        self.assertEqual(selected, ModelProvider.OLLAMA, f"Expected Ollama for private offline prompt, got: {selected}")

    async def test_04b_ollama_or_local_fallback(self):
        """4b. Execution of local/private task with fallback."""
        prompt = "Store context offline on device."
        res = await orchestrate_task(prompt, preferred_model="Ollama")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn(res["model_used"], [ModelProvider.OLLAMA, ModelProvider.LOCAL, ModelProvider.GROQ, ModelProvider.GEMINI])
        self.assertTrue(len(res["response"]) > 0)

    async def test_05_provider_failure_and_fallback_cascade(self):
        """5. Automatic fallback when preferred provider is unavailable."""
        # Force nonexistent provider to test full cascade to local fallback
        res = await route_inference("Provide status report", preferred_provider="invalid_provider_name")
        self.assertIn("provider", res)
        self.assertIn("text", res)
        self.assertTrue(len(res["text"]) > 0)
        # Even if all cloud APIs failed, Local Fallback guarantees an answer
        fallback_text = generate_local_fallback("System status inquiry")
        self.assertTrue(len(fallback_text) > 0)

    async def test_06_voice_question_ai_response_tts(self):
        """6. Voice Question -> AI response -> Fish Speech S2 / fallback audio synthesis & playback."""
        # Full task orchestration produces speech file
        res = await orchestrate_task("Hello NOVA, are you operational?")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(len(res["response"]) > 0)
        
        # Audio synthesis check
        audio_path = res.get("audio_path")
        self.assertTrue(audio_path, "Expected synthesized audio_path in task result")
        self.assertTrue(Path(audio_path).exists())
        self.assertGreater(Path(audio_path).stat().st_size, 0)

        # Non-blocking audio playback test with interrupt token
        cancel_evt = asyncio.Event()
        play_task = asyncio.create_task(tts_manager.play_audio_async(Path(audio_path), cancel_event=cancel_evt))
        await asyncio.sleep(0.05)
        # Verify interruption works cleanly
        cancel_evt.set()
        tts_manager.stop_playback()
        await play_task

    def test_07_websocket_disconnect_and_reconnect(self):
        """7. WebSocket connection lifecycle: connect, exchange events, disconnect, reconnect."""
        client = TestClient(app)
        
        # Connection 1
        with client.websocket_connect("/ws/nova") as ws1:
            evt1 = ws1.receive_json()
            self.assertEqual(evt1["type"], "STATE_CHANGE")
            self.assertEqual(evt1["payload"]["status"], "IDLE")
            ws1.send_json({"type": "PING", "payload": {}})
            # Wait for any potential reply or proceed to close
            
        # Reconnection 2
        with client.websocket_connect("/ws/nova") as ws2:
            evt2 = ws2.receive_json()
            self.assertEqual(evt2["type"], "STATE_CHANGE")
            self.assertEqual(evt2["payload"]["status"], "IDLE")
            mem_evt = ws2.receive_json()
            self.assertEqual(mem_evt["type"], "MEMORY_SYNC")

            ws2.send_json({
                "type": "USER_INPUT",
                "payload": {"text": "What is the system volume?"}
            })
            resp = ws2.receive_json()
            self.assertEqual(resp["type"], "STATE_CHANGE")
            self.assertEqual(resp["payload"]["status"], "PROCESSING")

    async def test_08_error_handling_and_security_guards(self):
        """8. Error handling: Malformed input, blocked commands, and security alerts."""
        # Blocked dangerous command
        dangerous_task = await orchestrate_task("format c: /q /y")
        self.assertEqual(dangerous_task["status"], "ERROR")
        self.assertIn("Security Alert", dangerous_task["response"])

        # Confirmation required for shutdown
        shutdown_task = await orchestrate_task("shut down the computer")
        self.assertEqual(shutdown_task["status"], "CONFIRMATION_REQUIRED")
        self.assertTrue(shutdown_task["requires_user_approval"])

if __name__ == "__main__":
    unittest.main()

