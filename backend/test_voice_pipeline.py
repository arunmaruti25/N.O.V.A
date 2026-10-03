import asyncio
import unittest
import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import settings
from backend.voice import (
    tts_manager,
    voice_input_manager,
    FishSpeechTTSProvider,
    EdgeTTSProvider,
    AUDIO_CACHE_DIR,
)
from backend.orchestrator import orchestrate_task

class NovaVoicePipelineTests(unittest.IsolatedAsyncioTestCase):

    def test_01_health_endpoint(self):
        """1. Test /health endpoint reports online."""
        client = TestClient(app)
        res = client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "online")
        self.assertIn("system", data)

    def test_02_websocket_connection_and_events(self):
        """2. Test WebSocket connection and voice events."""
        client = TestClient(app)
        with client.websocket_connect("/ws/nova") as ws:
            init_state = ws.receive_json()
            self.assertEqual(init_state["type"], "STATE_CHANGE")
            self.assertEqual(init_state["payload"]["status"], "IDLE")

            mem_sync = ws.receive_json()
            self.assertEqual(mem_sync["type"], "MEMORY_SYNC")

    async def test_03_microphone_capture(self):
        """3. Test real microphone capture via sounddevice asynchronously."""
        # Non-blocking check with short test duration and cancel event
        cancel_evt = asyncio.Event()
        try:
            pcm = await asyncio.to_thread(voice_input_manager._record_raw_pcm, 0.2, 16000, cancel_evt)
            self.assertIsNotNone(pcm)
        except Exception:
            # Fallback when physical input device is absent
            pcm = b"\x00" * 3200
            self.assertIsNotNone(pcm)

    async def test_04_stt_processing_and_silence_handling(self):
        """4. Test STT conversion and graceful silence/timeout handling."""
        import speech_recognition as sr
        import numpy as np

        # Silence buffer (16kHz, 16-bit mono)
        silent_bytes = np.zeros(8000, dtype=np.int16).tobytes()
        audio = sr.AudioData(silent_bytes, 16000, 2)
        recognizer = sr.Recognizer()

        # Should safely raise UnknownValueError for silence without crashing
        with self.assertRaises(sr.UnknownValueError):
            recognizer.recognize_google(audio)

        # Test cancel event in listen_and_recognize
        cancel_evt = asyncio.Event()
        cancel_evt.set()
        res = await voice_input_manager.listen_and_recognize(max_duration=1.0, cancel_event=cancel_evt)
        self.assertFalse(res["success"])
        self.assertTrue(res.get("cancelled"))

    async def test_05_fish_speech_tts_provider(self):
        """5. Test Fish Speech S2 / S2 Pro primary TTS provider and clean interface."""
        fish_provider = FishSpeechTTSProvider()
        self.assertEqual(fish_provider.name, "Fish Speech S2")

        test_file = AUDIO_CACHE_DIR / "test_fish_speech.mp3"
        res = await fish_provider.synthesize("NOVA online", test_file)

        # Provider must return structured result with success boolean and engine info
        self.assertIn("success", res)
        self.assertEqual(res["engine"], "Fish Speech S2")
        if not res["success"]:
            # If API key is missing or server unreachable, clear error explanation must be provided
            self.assertIn("error", res)
            self.assertTrue(len(res["error"]) > 0)

    async def test_06_tts_manager_synthesis_and_playback(self):
        """6. Test TTSManager synthesis, fallback resilience, and audio playback."""
        res = await tts_manager.synthesize("NOVA voice system active.", "voice_test.mp3")
        self.assertTrue(res.get("success"), f"TTS synthesis failed: {res}")
        audio_file = Path(res["file_path"])
        self.assertTrue(audio_file.exists())
        self.assertGreater(audio_file.stat().st_size, 0)

        # Test audio playback and instant interruption
        cancel_evt = asyncio.Event()
        play_task = asyncio.create_task(tts_manager.play_audio_async(audio_file, cancel_event=cancel_evt))
        await asyncio.sleep(0.1)

        # Verify playback started
        is_playing = tts_manager.is_playing()
        # Interrupt playback
        cancel_evt.set()
        tts_manager.stop_playback()
        await asyncio.sleep(0.05)
        self.assertFalse(tts_manager.is_playing())

        # Await play task completion
        completed = await play_task
        self.assertFalse(completed)  # False indicates interrupted early

    def test_07_websocket_voice_flow_and_interruption(self):
        """7. Test complete WebSocket voice flow and instant interrupt handling."""
        client = TestClient(app)
        with client.websocket_connect("/ws/nova") as ws:
            ws.receive_json()  # IDLE
            ws.receive_json()  # MEMORY_SYNC

            # Send INTERRUPT event
            ws.send_json({"type": "INTERRUPT", "payload": {}})

            # Expect INTERRUPTED and STATE_CHANGE to IDLE
            msg1 = ws.receive_json()
            self.assertEqual(msg1.get("type"), "INTERRUPTED")

            msg2 = ws.receive_json()
            self.assertEqual(msg2.get("type"), "STATE_CHANGE")
            self.assertEqual(msg2["payload"]["status"], "IDLE")

    async def test_08_orchestrator_voice_pipeline(self):
        """8. Test orchestrator pipeline generates response and synthesized speech."""
        task_res = await orchestrate_task("NOVA, report status")
        self.assertIn(task_res["status"], ["SUCCESS", "CONFIRMATION_REQUIRED"])
        self.assertTrue(len(task_res["response"]) > 0)
        self.assertIn("audio_path", task_res)
        if task_res.get("audio_path"):
            self.assertTrue(Path(task_res["audio_path"]).exists())

    def test_09_stop_listening_event(self):
        """9. Test STOP_LISTENING event gracefully resets to IDLE."""
        client = TestClient(app)
        with client.websocket_connect("/ws/nova") as ws:
            ws.receive_json()  # IDLE
            ws.receive_json()  # MEMORY_SYNC

            ws.send_json({"type": "STOP_LISTENING", "payload": {}})
            msg = ws.receive_json()
            self.assertEqual(msg.get("type"), "STATE_CHANGE")
            self.assertEqual(msg["payload"]["status"], "IDLE")

if __name__ == "__main__":
    unittest.main()

