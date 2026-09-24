import asyncio
import unittest
import json
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import settings
from backend.permissions import evaluate_permission, PermissionLevel
from backend.tools.computer import (
    get_system_info,
    get_system_volume,
    set_system_volume,
    list_running_processes,
    launch_allowed_application,
)
from backend.tools.vision import capture_screen
from backend.tools.web import web_search
from backend.memory import init_db, save_memory, list_memories, retrieve_memories, delete_memory
from backend.router import (
    route_inference,
    ModelProvider,
    generate_gemini,
    generate_groq,
    generate_nvidia,
    generate_ollama,
)
from backend.orchestrator import orchestrate_task

class BackendQualityTests(unittest.IsolatedAsyncioTestCase):

    def test_01_health_endpoint(self):
        """1. Test /health REST endpoint."""
        client = TestClient(app)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "online")
        self.assertIn("service", data)
        self.assertIn("system", data)
        self.assertIn("cpu_percent", data["system"])
        self.assertIn("memory_percent", data["system"])

    def test_02_websocket_connection(self):
        """2. Test WebSocket connection and event handling."""
        client = TestClient(app)
        with client.websocket_connect("/ws/nova") as websocket:
            # 1. Expect initial STATE_CHANGE (IDLE)
            init_state = websocket.receive_json()
            self.assertEqual(init_state.get("type"), "STATE_CHANGE")
            self.assertEqual(init_state["payload"]["status"], "IDLE")

            # 2. Expect initial MEMORY_SYNC
            init_mem = websocket.receive_json()
            self.assertEqual(init_mem.get("type"), "MEMORY_SYNC")
            self.assertIsInstance(init_mem["payload"]["memories"], list)

            # 3. Send USER_INPUT event
            websocket.send_json({
                "type": "USER_INPUT",
                "payload": {"text": "what is current system volume?", "model": "Gemini"}
            })

            # Read events emitted during execution
            event_types = []
            state_statuses = []
            while True:
                msg = websocket.receive_json()
                evt_type = msg.get("type")
                event_types.append(evt_type)
                if evt_type == "STATE_CHANGE":
                    status = msg.get("payload", {}).get("status")
                    state_statuses.append(status)
                    if status == "IDLE":
                        break

            self.assertIn("ASSISTANT_RESPONSE", event_types)
            self.assertIn("ACTIVITY_LOG", event_types)
            self.assertIn("PROCESSING", state_statuses)
            self.assertIn("SPEAKING", state_statuses)

    async def test_03_gemini_connection(self):
        """3. Test Gemini live connection."""
        ans = await generate_gemini("Say NOVA Gemini active in 3 words")
        self.assertIsNotNone(ans, "Gemini failed to return response")
        self.assertTrue(len(ans) > 0)

    async def test_04_groq_connection(self):
        """4. Test Groq live connection."""
        ans = await generate_groq("Say NOVA Groq active in 3 words")
        self.assertIsNotNone(ans, "Groq failed to return response")
        self.assertTrue(len(ans) > 0)

    async def test_05_nvidia_connection(self):
        """5. Test NVIDIA NIM connection if configured."""
        if settings.NVIDIA_API_KEY:
            ans = await generate_nvidia("Say NOVA NVIDIA active in 3 words")
            self.assertIsNotNone(ans, "NVIDIA NIM failed to return response")
            self.assertTrue(len(ans) > 0)

    async def test_06_ollama_fallback(self):
        """6. Test Ollama execution / fallback."""
        ans = await generate_ollama("Say NOVA Ollama active in 3 words")
        # Ollama returns response if local daemon has model, or gracefully returns None/fallback
        if ans is not None:
            self.assertTrue(len(ans) > 0)

    async def test_07_model_routing(self):
        """7. Test dynamic model routing across all providers."""
        for provider in [ModelProvider.GEMINI, ModelProvider.GROQ, ModelProvider.NVIDIA, ModelProvider.OLLAMA]:
            res = await route_inference("Hello NOVA", preferred_provider=provider)
            self.assertIn("text", res)
            self.assertTrue(len(res["text"]) > 0)
            self.assertIn(res["provider"], [
                ModelProvider.GEMINI,
                ModelProvider.GROQ,
                ModelProvider.NVIDIA,
                ModelProvider.OLLAMA,
                ModelProvider.LOCAL,
            ])

    def test_08_permission_flow(self):
        """8. Test permission flow (SAFE, CONFIRMATION_REQUIRED, BLOCKED)."""
        safe = evaluate_permission("get_volume")
        self.assertEqual(safe.level, PermissionLevel.SAFE)
        self.assertTrue(safe.is_authorized)

        confirm = evaluate_permission("shutdown")
        self.assertEqual(confirm.level, PermissionLevel.CONFIRMATION_REQUIRED)
        self.assertFalse(confirm.is_authorized)

        blocked = evaluate_permission("arbitrary_shell")
        self.assertEqual(blocked.level, PermissionLevel.BLOCKED)
        self.assertFalse(blocked.is_authorized)

    async def test_09_memory_storage(self):
        """9. Test persistent SQLite memory operations."""
        await init_db()
        save_res = await save_memory(category="TestPreference", text="Prefers dark futuristic mode")
        self.assertTrue(save_res["success"])
        mem_id = save_res["id"]

        mems = await list_memories(category="TestPreference")
        self.assertTrue(any(m["id"] == mem_id for m in mems))

        found = await retrieve_memories("futuristic")
        self.assertGreater(len(found), 0)

        deleted = await delete_memory(mem_id)
        self.assertTrue(deleted)

    async def test_10_orchestrator_pipeline_and_confirmation(self):
        """10. Test orchestrator pipeline, tool execution, and confirmation gating."""
        # 1. Confirmation required for high-risk action
        shutdown_res = await orchestrate_task("NOVA, shut down my laptop")
        self.assertEqual(shutdown_res["status"], "CONFIRMATION_REQUIRED")
        self.assertTrue(shutdown_res["requires_user_approval"])

        # 2. Safe action: volume query/adjustment
        vol_res = await orchestrate_task("NOVA, set volume to 50%")
        self.assertEqual(vol_res["status"], "SUCCESS")
        self.assertIn("volume", vol_res["response"].lower())

if __name__ == "__main__":
    unittest.main()
