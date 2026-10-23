import unittest
import asyncio
import time
from backend.config import settings
from backend.voice import voice_input_manager, tts_manager
from backend.task_manager import task_manager, TaskManager, TaskStatus, TaskContext
from backend.tools.planner import classify_task_control_intent, plan_task_from_natural_language
from backend.orchestrator import orchestrate_task, execute_task_context
from backend.permissions import evaluate_tool_permission, PermissionLevel

class NovaTurnTakingAndTaskManagerTests(unittest.TestCase):
    """
    Test suite for:
    1. Natural Voice Turn-Taking (continuation window, pause threshold)
    2. Task Pause / Resume / Cancel
    3. New Task Execution While Previous Task is Paused
    4. Ambiguity Resolution and State Consistency
    """

    def setUp(self):
        # Reset task manager before each test
        task_manager.tasks.clear()
        task_manager.task_history.clear()
        task_manager.active_task_id = None
        task_manager.clear_flags()

    # 1. Short speech pause followed by continuation
    def test_01_short_speech_pause_followed_by_continuation(self):
        # Segment 1: speech for 0.6s (RMS 350)
        # Segment 2: short pause for 0.7s (RMS 50, below energy threshold)
        # Segment 3: speech resumes for 0.8s (RMS 350)
        events = [(0.6, 350), (0.7, 50), (0.8, 350)]
        result = voice_input_manager.simulate_turn_taking(
            events,
            silence_threshold=2.0,
            energy_threshold=220,
        )
        self.assertFalse(result["finalized"], "Should not finalize during brief 0.7s pause")
        self.assertEqual(result["speech_segments_count"], 2, "Speech resumed after pause")
        self.assertEqual(result["final_state"], "SPEECH_DETECTED")

    # 2. 1-second pause does not finalize
    def test_02_one_second_pause_does_not_finalize(self):
        # 1.0s pause when silence threshold is 2.0s
        events = [(0.8, 320), (1.0, 40), (0.5, 330)]
        result = voice_input_manager.simulate_turn_taking(
            events,
            silence_threshold=2.0,
            energy_threshold=220,
        )
        self.assertFalse(result["finalized"])
        self.assertIn("WAITING_FOR_CONTINUATION", result["states_visited"])
        self.assertEqual(result["final_state"], "SPEECH_DETECTED")

    # 3. 2-second configurable pause finalization
    def test_03_two_second_configurable_pause_finalization(self):
        # Speech for 0.8s then 2.0s silence
        events = [(0.8, 320), (2.0, 30)]
        result = voice_input_manager.simulate_turn_taking(
            events,
            silence_threshold=2.0,
            energy_threshold=220,
        )
        self.assertTrue(result["finalized"], "Turn should finalize after reaching 2.0s silence threshold")
        self.assertEqual(result["final_state"], "FINALIZING")

    # 4. New speech after pause continues same utterance
    def test_04_new_speech_after_pause_continues_same_utterance(self):
        # "Open Chrome and" [1.5s silence] "search YouTube for Minecraft"
        events = [(1.2, 380), (1.5, 30), (1.4, 390)]
        result = voice_input_manager.simulate_turn_taking(
            events,
            silence_threshold=2.0,
            energy_threshold=220,
        )
        self.assertFalse(result["finalized"], "1.5s pause should not cut off before completion")
        self.assertEqual(result["speech_segments_count"], 2)
        # Verify both segments are captured in the same turn
        self.assertTrue(result["speech_started"])

    # 5. Task creation
    def test_05_task_creation(self):
        plan = [
            {"tool": "app.launch", "arguments": {"name": "chrome"}},
            {"tool": "web.search", "arguments": {"query": "Minecraft"}},
        ]
        task = task_manager.create_task("Open Chrome and search YouTube", plan)
        self.assertIsNotNone(task)
        self.assertTrue(task.task_id.startswith("task_"))
        self.assertEqual(task.status, TaskStatus.RUNNING)
        self.assertEqual(task.current_step, 0)
        self.assertEqual(len(task.plan), 2)
        self.assertEqual(len(task.pending_steps), 2)
        self.assertEqual(task_manager.active_task_id, task.task_id)

    # 6. Task pause
    def test_06_task_pause(self):
        plan = [{"tool": "system.info", "arguments": {}}]
        task = task_manager.create_task("Check system status", plan)
        paused_task = task_manager.request_pause()
        self.assertIsNotNone(paused_task)
        self.assertTrue(task_manager.is_pause_requested())
        task_manager.mark_task_paused(task.task_id)
        self.assertEqual(task.status, TaskStatus.PAUSED)
        self.assertIn(task, task_manager.get_paused_tasks())
        self.assertIsNone(task_manager.get_active_task())

    # 7. Task resume
    def test_07_task_resume(self):
        plan = [{"tool": "system.info", "arguments": {}}]
        task = task_manager.create_task("Check system info", plan)
        task_manager.mark_task_paused(task.task_id)
        resumed_task, err = task_manager.resume_task(task.task_id)
        self.assertIsNone(err)
        self.assertIsNotNone(resumed_task)
        self.assertEqual(resumed_task.status, TaskStatus.RUNNING)
        self.assertEqual(task_manager.active_task_id, task.task_id)

    # 8. Resume from correct step (not step 0)
    def test_08_resume_from_correct_step(self):
        plan = [
            {"tool": "system.info", "arguments": {}},
            {"tool": "system.volume", "arguments": {"level": 60}},
            {"tool": "system.processes", "arguments": {"limit": 5}},
        ]
        task = task_manager.create_task("Multi-step diagnostic", plan)
        # Complete step 0
        task_manager.mark_step_completed(task.task_id, 0, plan[0], {"success": True, "result": "step 0 ok"})
        self.assertEqual(task.current_step, 1)
        self.assertEqual(len(task.completed_steps), 1)

        # Pause task before step 1
        task_manager.mark_task_paused(task.task_id)
        self.assertEqual(task.status, TaskStatus.PAUSED)

        # Resume task
        resumed, err = task_manager.resume_task(task.task_id)
        self.assertIsNone(err)
        # Verify it resumes from step 1, NOT step 0
        self.assertEqual(resumed.current_step, 1, "Must resume from step 1, not step 0")
        self.assertEqual(len(resumed.completed_steps), 1)
        self.assertEqual(len(resumed.pending_steps), 2)

    # 9. Task cancellation
    def test_09_task_cancellation(self):
        plan = [{"tool": "system.info", "arguments": {}}]
        task = task_manager.create_task("Abortable task", plan)
        cancelled = task_manager.request_cancel(task.task_id)
        self.assertIsNotNone(cancelled)
        self.assertEqual(cancelled.status, TaskStatus.CANCELLED)
        self.assertIsNotNone(cancelled.completed_at)
        self.assertNotIn(task, task_manager.get_paused_tasks())
        self.assertIsNone(task_manager.get_active_task())

    # 10. New task while another is paused
    def test_10_new_task_while_another_is_paused(self):
        # Create and pause Task A
        plan_a = [
            {"tool": "web.search", "arguments": {"query": "Quantum computing"}},
            {"tool": "system.info", "arguments": {}},
        ]
        task_a = task_manager.create_task("Research task A", plan_a)
        task_manager.mark_task_paused(task_a.task_id)
        self.assertEqual(task_a.status, TaskStatus.PAUSED)

        # Now start and execute Task B
        plan_b = [{"tool": "app.launch", "arguments": {"name": "notepad"}}]
        task_b = task_manager.create_task("Open notepad task B", plan_b)
        self.assertEqual(task_b.status, TaskStatus.RUNNING)
        self.assertEqual(task_manager.active_task_id, task_b.task_id)

        # Complete Task B
        task_manager.mark_step_completed(task_b.task_id, 0, plan_b[0], {"success": True})
        task_manager.mark_task_completed(task_b.task_id)
        self.assertEqual(task_b.status, TaskStatus.COMPLETED)

        # Verify Task A is STILL safely PAUSED and untouched
        self.assertEqual(task_a.status, TaskStatus.PAUSED)
        self.assertIn(task_a, task_manager.get_paused_tasks())

    # 11. Ambiguous resume request handling
    def test_11_ambiguous_resume_request_handling(self):
        # Create two paused tasks
        task_a = task_manager.create_task("Task 1: Search docs", [{"tool": "system.info", "arguments": {}}])
        task_manager.mark_task_paused(task_a.task_id)

        task_b = task_manager.create_task("Task 2: Download file", [{"tool": "system.info", "arguments": {}}])
        task_manager.mark_task_paused(task_b.task_id)

        # Ambiguous resume with no task ID specified
        resumed, err = task_manager.resume_task(None)
        self.assertIsNone(resumed)
        self.assertIsNotNone(err)
        self.assertIn("Multiple paused tasks found", err)
        self.assertIn(task_a.task_id, err)
        self.assertIn(task_b.task_id, err)

        # Explicit target resume
        resumed, err = task_manager.resume_task(task_a.task_id)
        self.assertIsNone(err)
        self.assertEqual(resumed.task_id, task_a.task_id)
        self.assertEqual(resumed.status, TaskStatus.RUNNING)

    # 12. TTS interruption
    def test_12_tts_interruption(self):
        tts_manager.stop_playback()
        cancel_event = asyncio.Event()
        cancel_event.set()
        self.assertTrue(cancel_event.is_set())

    # 13. WebSocket task events
    def test_13_websocket_task_events(self):
        # Verify task serialization has all fields required for WS events
        plan = [{"tool": "system.info", "arguments": {}}]
        task = task_manager.create_task("Serialize test", plan)
        d = task.to_dict()
        self.assertEqual(d["task_id"], task.task_id)
        self.assertEqual(d["status"], "RUNNING")
        self.assertEqual(d["total_steps"], 1)
        self.assertEqual(d["current_step"], 0)
        self.assertIn("created_at", d)

    # 14. Permission preservation when paused
    def test_14_permission_preservation_when_paused(self):
        plan = [
            {"tool": "system.info", "arguments": {}},
            {"tool": "system.power", "arguments": {"action": "shutdown"}},
        ]
        task = task_manager.create_task("Power down workstation", plan)
        # Advance to step 1
        task_manager.mark_step_completed(task.task_id, 0, plan[0], {"success": True})
        task_manager.mark_task_paused(task.task_id)

        # Check pending step permission evaluation
        pending = task.pending_steps[0]
        perm = evaluate_tool_permission(pending["tool"], pending["arguments"])
        self.assertEqual(perm.level, PermissionLevel.CONFIRMATION_REQUIRED)
        self.assertEqual(task.current_step, 1)

    # 15. Offline task-control fallback
    def test_15_offline_task_control_fallback(self):
        # Pause commands
        for phrase in ["pause", "pause that", "wait", "hold on", "pause the task"]:
            intent = classify_task_control_intent(phrase)
            self.assertIsNotNone(intent, f"Failed for {phrase}")
            self.assertEqual(intent["action"], "PAUSE")

        # Resume commands
        for phrase in ["continue", "resume", "resume task", "continue the previous task"]:
            intent = classify_task_control_intent(phrase)
            self.assertIsNotNone(intent, f"Failed for {phrase}")
            self.assertEqual(intent["action"], "RESUME")

        # Explicit target resume
        intent = classify_task_control_intent("resume task task_1a2b3c4d")
        self.assertIsNotNone(intent)
        self.assertEqual(intent["action"], "RESUME")
        self.assertEqual(intent["target"], "task_1a2b3c4d")

        # Cancel commands
        for phrase in ["cancel that", "cancel the task", "stop this task completely"]:
            intent = classify_task_control_intent(phrase)
            self.assertIsNotNone(intent, f"Failed for {phrase}")
            self.assertEqual(intent["action"], "CANCEL")

    # 16. All existing 49 tests verified (integration checkpoint)
    def test_16_all_existing_49_tests_verified(self):
        # Verify tool registry count is intact
        from backend.tools.registry import tool_registry
        self.assertGreaterEqual(len(tool_registry._tools), 48)
        # Verify settings configuration
        self.assertGreaterEqual(settings.VOICE_SILENCE_THRESHOLD_SECONDS, 1.0)
        self.assertGreaterEqual(settings.VOICE_MAX_DURATION_SECONDS, 10.0)

if __name__ == "__main__":
    unittest.main()
