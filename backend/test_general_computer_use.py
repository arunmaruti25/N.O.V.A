import os
import asyncio
import unittest
from pathlib import Path

from backend.tools.registry import tool_registry, ToolDefinition, ToolResult
from backend.tools.planner import plan_task_from_natural_language, parse_llm_tool_calls
from backend.tools.observation import get_unified_observation, get_active_window_info, get_screen_metrics
from backend.tools.ui_understanding import locate_ui_element, match_element_in_ui_tree
from backend.tools.disambiguation import resolve_target_entity
from backend.orchestrator import orchestrate_task
from backend.permissions import PermissionLevel, evaluate_tool_permission
from backend.config import settings

class NovaGeneralComputerUseEngineTests(unittest.IsolatedAsyncioTestCase):
    """
    Comprehensive verification suite for NOVA General Human-Like Computer Use Engine:
    SEE → UNDERSTAND → PLAN → ACT → OBSERVE → VERIFY → ADAPT → COMPLETE
    """

    # 1. General Screen & Computer Observation
    async def test_01_general_screen_observation(self):
        """1. General screen observation: captures screen dimensions, active window, visible windows, and UI automation tree."""
        res = await tool_registry.execute("computer.observe", {"include_screenshot": False, "include_ui_elements": True})
        self.assertTrue(res.success)
        obs = res.result
        self.assertIn("screen", obs)
        self.assertGreater(obs["screen"]["width"], 0)
        self.assertGreater(obs["screen"]["height"], 0)
        self.assertIn("active_window", obs)
        self.assertIn("visible_windows", obs)
        self.assertIn("ui_elements", obs)
        self.assertIn("context_summary", obs)

    # 2. Vision / UI Target Detection Without Hardcoded Coordinates
    async def test_02_ui_target_detection(self):
        """2. UI target detection: resolves coordinates dynamically using UI tree and spatial understanding."""
        # Simulated UI tree elements
        simulated_elements = [
            {
                "name": "Search or enter web address",
                "type": "Edit",
                "automation_id": "address-bar",
                "bounding_box": {"left": 200, "top": 50, "right": 800, "bottom": 85, "width": 600, "height": 35, "center_x": 500, "center_y": 67},
            },
            {
                "name": "Continue",
                "type": "Button",
                "automation_id": "btn-continue",
                "bounding_box": {"left": 400, "top": 300, "right": 520, "bottom": 340, "width": 120, "height": 40, "center_x": 460, "center_y": 320},
            },
        ]
        # Match search box
        matched_search = match_element_in_ui_tree("search box", simulated_elements)
        self.assertIsNotNone(matched_search)
        self.assertEqual(matched_search["bounding_box"]["center_x"], 500)
        self.assertEqual(matched_search["bounding_box"]["center_y"], 67)

        # Match continue button
        matched_btn = match_element_in_ui_tree("blue Continue button", simulated_elements)
        self.assertIsNotNone(matched_btn)
        self.assertEqual(matched_btn["bounding_box"]["center_x"], 460)

    # 3. Dynamic Click with Target Localization
    async def test_03_dynamic_click_interaction(self):
        """3. Dynamic click: executes mouse click with coordinate bounds check."""
        res = await tool_registry.execute("computer.interact", {
            "action": "click",
            "x": 450,
            "y": 350,
            "target_description": "Continue Button",
        })
        self.assertTrue(res.success)
        self.assertTrue(res.verified)
        self.assertEqual(res.result["coordinates"]["x"], 450)
        self.assertEqual(res.result["coordinates"]["y"], 350)

    # 4. Dynamic Typing and Focus-and-Type
    async def test_04_dynamic_typing_interaction(self):
        """4. Dynamic typing: focuses input and types text string safely."""
        res = await tool_registry.execute("computer.interact", {
            "action": "locate_and_type",
            "x": 300,
            "y": 200,
            "text": "NOVA General Computer Use Verification",
            "target_description": "Search input field",
        })
        self.assertTrue(res.success)
        self.assertTrue(res.verified)
        self.assertIn("Typed", res.result["message"])

    # 5. Observe → Act → Observe Loop
    async def test_05_observe_act_observe_loop(self):
        """5. Observe -> Act -> Observe loop: verifies pre and post state capture during interaction."""
        res = await tool_registry.execute("computer.interact", {
            "action": "press_key",
            "key": "escape",
            "verify_expected_change": "dismiss modal or clear focus",
        })
        self.assertTrue(res.success)
        self.assertTrue(res.verified)
        self.assertIn("active_window", res.result)

    # 6. Application vs Process vs Window Distinction
    async def test_06_application_vs_window_distinction(self):
        """6. Application vs window distinction: resolves 'Close this window' as window.close vs 'Close Chrome' as app.close."""
        # "Close this window" -> window.close
        plan_win = plan_task_from_natural_language("Close this window")
        self.assertIsNotNone(plan_win)
        self.assertEqual(plan_win[0]["tool"], "window.close")

        # "Close Chrome" -> app.close
        plan_app = plan_task_from_natural_language("Close Chrome")
        self.assertIsNotNone(plan_app)
        self.assertEqual(plan_app[0]["tool"], "app.close")
        self.assertEqual(plan_app[0]["arguments"]["name"], "chrome")

    # 7. Website / Browser Tab vs Application Distinction
    async def test_07_website_tab_vs_application_distinction(self):
        """7. Website / tab vs application distinction: resolves 'Close YouTube' as browser.close_tab rather than killing Chrome."""
        plan_tab = plan_task_from_natural_language("Close YouTube")
        self.assertIsNotNone(plan_tab)
        self.assertEqual(plan_tab[0]["tool"], "browser.close_tab")
        self.assertEqual(plan_tab[0]["arguments"]["title_match"], "YouTube")

        # Disambiguation classifier check
        resolved = resolve_target_entity("Close YouTube")
        self.assertEqual(resolved["entity_type"], "BROWSER_TAB")
        self.assertEqual(resolved["action"], "browser.close_tab")

    # 8. Browser General Interaction
    async def test_08_browser_general_interaction(self):
        """8. Browser interaction: tab close and scroll controls."""
        # Tab close tool execution
        tab_res = await tool_registry.execute("browser.close_tab", {"title_match": "YouTube"})
        self.assertTrue(tab_res.success)
        self.assertIn("browser.close_tab", tab_res.tool)

        # Tab scroll execution
        scroll_res = await tool_registry.execute("browser.scroll", {"clicks": -200})
        self.assertTrue(scroll_res.success)

    # 9. Unknown / Unfamiliar UI Interaction
    async def test_09_unfamiliar_ui_interaction(self):
        """9. Unfamiliar UI interaction: AI locates and interacts with dynamically described UI elements."""
        plan = plan_task_from_natural_language("Click the blue Continue button")
        self.assertIsNotNone(plan)
        self.assertEqual(plan[0]["tool"], "computer.interact")
        self.assertEqual(plan[0]["arguments"]["action"], "locate_and_click")
        self.assertIn("Continue", plan[0]["arguments"]["target_description"])

        # Execute dynamic interaction
        res = await tool_registry.execute("computer.interact", plan[0]["arguments"])
        self.assertTrue(res.success)

    # 10. Multi-Step Dynamic Task
    async def test_10_multi_step_dynamic_task(self):
        """10. Multi-step dynamic task: launches app, observes, types message, and verifies."""
        res = await orchestrate_task("Open Notepad and type General AI Control Test")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res.get("verified"))

    # 11. Verification Failure Handling
    async def test_11_verification_failure(self):
        """11. Verification failure: correctly flags failure when non-existent target or operation fails."""
        res = await tool_registry.execute("app.close", {"name": "phantom_application_xyz_9999"})
        self.assertFalse(res.success)
        self.assertIn("No running instance", res.error)

    # 12. Recovery and Retry
    async def test_12_recovery_and_retry(self):
        """12. Recovery and retry: verifies retry loop on transient interaction."""
        res = await tool_registry.execute("computer.interact", {
            "action": "press_key",
            "key": "tab",
            "retry_limit": 1,
        })
        self.assertTrue(res.success)
        self.assertEqual(res.result["retries"], 0)

    # 13. Permission-Required Action Gateway
    async def test_13_permission_gateway(self):
        """13. Permission gateway: requires confirmation for consequential actions like deletion or power."""
        res = await orchestrate_task("delete file secret_data.txt")
        self.assertEqual(res["status"], "CONFIRMATION_REQUIRED")
        self.assertTrue(res.get("requires_user_approval"))

    # 14. Blocked Malicious / Prohibited Actions
    async def test_14_blocked_actions(self):
        """14. Blocked actions: permanently rejects dangerous command injections, eval, and format commands."""
        res = await orchestrate_task("format disk c:")
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("Security Alert", res["response"])

    # 15. Offline / Local Fallback Execution
    async def test_15_offline_local_fallback(self):
        """15. Offline / local fallback: executes general computer tasks locally without cloud dependencies."""
        res = await orchestrate_task("Open Downloads", preferred_model="offline")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["action"], "file.open_folder")

    # 16. Recent File Search & Open
    async def test_16_recent_file_search_and_open(self):
        """16. File disambiguation & open: resolves 'Open the PDF I downloaded' to file.find_and_open."""
        plan = plan_task_from_natural_language("Open the PDF I downloaded")
        self.assertIsNotNone(plan)
        self.assertEqual(plan[0]["tool"], "file.find_and_open")
        self.assertEqual(plan[0]["arguments"]["extension"], "pdf")

if __name__ == "__main__":
    unittest.main()
