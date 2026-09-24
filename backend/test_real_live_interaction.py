import asyncio
import unittest
from backend.task_manager import task_manager, TaskStatus
from backend.orchestrator import orchestrate_task
from backend.voice import voice_input_manager

class RealLiveWindowsInteractionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        task_manager.tasks.clear()
        task_manager.task_history.clear()
        task_manager.active_task_id = None
        task_manager.clear_flags()

    async def test_full_live_user_flow(self):
        events_logged = []

        async def capture_event(name, data):
            events_logged.append((name, data))

        # 1. User says: "open notepad and get system info" (multi-step plan)
        res1 = await orchestrate_task(
            user_input="open notepad",
            on_task_event=capture_event,
        )
        self.assertEqual(res1["status"], "SUCCESS")
        task_a_id = list(task_manager.tasks.keys())[0]

        # 2. User starts a 2-step task: "Search files for log and get processes"
        res_plan = await orchestrate_task(
            user_input="search files for log",
            on_task_event=capture_event,
        )
        task_b_id = list(task_manager.tasks.keys())[-1]

        # 3. Simulate user says "Pause" when idle vs active
        res_pause = await orchestrate_task(
            user_input="Pause",
            on_task_event=capture_event,
        )
        self.assertIn("pause", res_pause["response"].lower())

        # Manually create a paused multi-step task to test interleaved execution
        multi_plan = [
            {"tool": "system.info", "arguments": {}},
            {"tool": "system.set_volume", "arguments": {"level": 55}},
            {"tool": "system.processes", "arguments": {"limit": 5}},
        ]
        task_paused = task_manager.create_task("Multi-step diagnostics", multi_plan)
        # Complete step 0
        task_manager.mark_step_completed(task_paused.task_id, 0, multi_plan[0], {"success": True})
        task_manager.mark_task_paused(task_paused.task_id)
        self.assertEqual(task_paused.status, TaskStatus.PAUSED)
        self.assertEqual(task_paused.current_step, 1)

        # 4. User says: "Open Notepad" while Task is paused -> Executes as new Task C
        res_c = await orchestrate_task(
            user_input="open notepad",
            on_task_event=capture_event,
        )
        self.assertEqual(res_c["status"], "SUCCESS")
        # Original task MUST still be paused at step 1
        self.assertEqual(task_paused.status, TaskStatus.PAUSED)
        self.assertEqual(task_paused.current_step, 1)

        # 5. User says: "Resume" or "Continue the previous task"
        res_resume = await orchestrate_task(
            user_input=f"resume {task_paused.task_id}",
            on_task_event=capture_event,
        )
        self.assertEqual(res_resume["status"], "SUCCESS")
        # Task should now be completed
        self.assertEqual(task_paused.status, TaskStatus.COMPLETED)
        self.assertEqual(task_paused.current_step, 3)

        # 6. User says: "Cancel that"
        res_cancel = await orchestrate_task(
            user_input="cancel that",
            on_task_event=capture_event,
        )
        self.assertIn(res_cancel["status"], ["CANCELLED", "SUCCESS"])

if __name__ == "__main__":
    unittest.main()
