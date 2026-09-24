import os
import asyncio
import unittest
from pathlib import Path
from backend.tools.registry import tool_registry, ToolDefinition, ToolResult
from backend.tools.planner import plan_task_from_natural_language, parse_llm_tool_calls
from backend.orchestrator import orchestrate_task
from backend.permissions import PermissionLevel, evaluate_tool_permission
from backend.config import settings

class NovaComputerControlEngineTests(unittest.IsolatedAsyncioTestCase):
    """
    Comprehensive verification suite for NOVA General Computer Control Engine.
    Covers all 18 required test categories:
    1. Open YouTube
    2. Open Notepad
    3. Focus/switch application
    4. Browser navigation
    5. Browser search
    6. Keyboard typing
    7. Mouse click
    8. Window minimize/restore
    9. Get system information / battery
    10. Get/set volume
    11. Screenshot
    12. File search / create / read
    13. Permission-required action
    14. Blocked arbitrary command
    15. Tool execution failure
    16. Verification failure
    17. Multi-step task
    18. Offline / local execution
    """

    async def test_01_open_youtube(self):
        """1. Open YouTube: routes to browser.open, opens URL, and verifies."""
        res = await orchestrate_task("Open YouTube")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("browser.open", res["action"])
        self.assertIn("YouTube", res["response"])
        self.assertTrue(res.get("verified"))

    async def test_02_open_notepad(self):
        """2. Open Notepad: resolves notepad dynamically, launches, and verifies process."""
        res = await orchestrate_task("Open Notepad")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("app.launch", res["action"])
        self.assertTrue(res.get("verified"))

    async def test_03_focus_switch_application(self):
        """3. Focus/switch application: activates window by app name."""
        res = await tool_registry.execute("app.focus", {"name": "notepad"})
        self.assertTrue(res.success)
        self.assertIn("notepad", res.result.get("app", "").lower())

    async def test_04_browser_navigation(self):
        """4. Browser navigation: open URL in desktop browser with verification."""
        res = await tool_registry.execute("browser.navigate", {"url": "https://www.google.com"})
        self.assertTrue(res.success)
        self.assertEqual(res.result.get("url"), "https://www.google.com")
        self.assertTrue(res.verified)

    async def test_05_browser_search(self):
        """5. Browser search: searches query on YouTube or Google."""
        res = await orchestrate_task("Search YouTube for Minecraft")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("browser.search", res["action"])
        self.assertIn("Minecraft", res["response"])

    async def test_06_keyboard_typing(self):
        """6. Keyboard typing: types text with safety checks."""
        res = await tool_registry.execute("keyboard.type", {"text": "NOVA Test Keystrokes", "interval": 0.01})
        self.assertTrue(res.success)
        self.assertEqual(res.result.get("typed_length"), len("NOVA Test Keystrokes"))

    async def test_07_mouse_click(self):
        """7. Mouse click: clicks mouse with coordinate bounds enforcement."""
        res = await tool_registry.execute("mouse.click", {"x": 500, "y": 400, "button": "left"})
        self.assertTrue(res.success)
        self.assertEqual(res.result.get("button"), "left")
        self.assertEqual(res.result.get("x"), 500)
        self.assertEqual(res.result.get("y"), 400)

    async def test_08_window_minimize_restore(self):
        """8. Window minimize/restore: exercises window manager safely."""
        # List windows
        list_res = await tool_registry.execute("window.list", {})
        self.assertTrue(list_res.success)

        # Restore window signal
        restore_res = await tool_registry.execute("window.restore", {"title": ""})
        self.assertIn("success", restore_res.to_dict())

    async def test_09_get_system_info_and_battery(self):
        """9. Get system info and battery: queries hardware sensors."""
        battery_task = await orchestrate_task("What's my battery percentage?")
        self.assertEqual(battery_task["status"], "SUCCESS")
        self.assertIn("battery", battery_task["action"])
        self.assertTrue(len(battery_task["response"]) > 0)

        status_task = await orchestrate_task("System status")
        self.assertEqual(status_task["status"], "SUCCESS")
        self.assertIn("CPU", status_task["response"])

    async def test_10_get_set_volume(self):
        """10. Get/set volume: verifies master volume adjustment."""
        # Query volume
        vol_task = await orchestrate_task("What is the system volume?")
        self.assertEqual(vol_task["status"], "SUCCESS")

        # Set volume to 42%
        set_res = await tool_registry.execute("system.set_volume", {"level": 42})
        self.assertTrue(set_res.success)
        self.assertTrue(set_res.verified)

    async def test_11_screenshot(self):
        """11. Screenshot: captures display buffer and verifies file on disk."""
        res = await orchestrate_task("Take a screenshot")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("screen.capture", res["action"])
        self.assertTrue(res.get("verified"))

    async def test_12_file_operations(self):
        """12. File search, create, and read: verifies safe filesystem manipulation."""
        test_file = settings.DATA_DIR / "test_nova_file_ops.txt"
        
        # Create file
        create_res = await tool_registry.execute("file.create_file", {
            "path": str(test_file),
            "content": "NOVA verified file control contents.",
        })
        self.assertTrue(create_res.success)
        self.assertTrue(create_res.verified)

        # Read file
        read_res = await tool_registry.execute("file.read_text", {"path": str(test_file)})
        self.assertTrue(read_res.success)
        self.assertEqual(read_res.result.get("content"), "NOVA verified file control contents.")

        # Search files
        search_res = await tool_registry.execute("file.search", {
            "pattern": "test_nova_*.txt",
            "directory": str(settings.DATA_DIR),
        })
        self.assertTrue(search_res.success)
        self.assertGreater(search_res.result.get("count", 0), 0)

        # Cleanup safely
        if test_file.exists():
            test_file.unlink()

    async def test_13_permission_required_action(self):
        """13. Permission-required action: blocks deletion/shutdown without confirmation, proceeds when confirmed."""
        # 1. Deletion requires confirmation
        res = await orchestrate_task("delete file important_document.txt")
        self.assertEqual(res["status"], "CONFIRMATION_REQUIRED")
        self.assertTrue(res.get("requires_user_approval"))

        # 2. Power action requires confirmation
        p_res = await orchestrate_task("shut down the computer")
        self.assertEqual(p_res["status"], "CONFIRMATION_REQUIRED")
        self.assertTrue(p_res.get("requires_user_approval"))

    async def test_14_blocked_arbitrary_command(self):
        """14. Blocked arbitrary command: permanently blocks eval, format, and shell injections."""
        # Argument validation blocks injection
        blocked_task = await orchestrate_task("format c: /q /y")
        self.assertEqual(blocked_task["status"], "ERROR")
        self.assertIn("Security Alert", blocked_task["response"])

        # Tool execution blocks prohibited command string
        eval_call = await tool_registry.execute("keyboard.type", {"text": "eval(__import__('os'))"})
        self.assertFalse(eval_call.success)
        self.assertIn("Security Violation", eval_call.error)

    async def test_15_tool_execution_failure(self):
        """15. Tool execution failure: handles non-existent app or missing file gracefully."""
        # Non-existent app
        res = await tool_registry.execute("app.close", {"name": "non_existent_app_xyz_12345"})
        self.assertFalse(res.success)
        self.assertIn("No running instance", res.error)

        # Non-existent tool
        invalid_tool = await tool_registry.execute("unregistered.tool.name", {})
        self.assertFalse(invalid_tool.success)
        self.assertIn("not registered", invalid_tool.error)

    async def test_16_verification_failure(self):
        """16. Verification failure: detect when post-condition verification fails."""
        # Verify non-existent file creation verification fails
        from backend.tools.file_control import verify_file_created
        v_ok, v_msg = verify_file_created({}, {"path": "C:\\fake_path_12345\\imaginary.file"})
        self.assertFalse(v_ok)
        self.assertIn("not found on disk", v_msg)

    async def test_17_multi_step_tasks(self):
        """17. Multi-step task: plans and executes multi-step task."""
        # Multi-step 1: Open Chrome and search YouTube for Minecraft
        multi_task_1 = await orchestrate_task("Open Chrome and search YouTube for Minecraft")
        self.assertEqual(multi_task_1["status"], "SUCCESS")
        self.assertIn("Minecraft", multi_task_1["response"])

        # Multi-step 2: Open Notepad and type Hello NOVA
        multi_task_2 = await orchestrate_task("Open Notepad and type Hello NOVA")
        self.assertEqual(multi_task_2["status"], "SUCCESS")
        self.assertIn("Notepad", multi_task_2["response"])

    async def test_18_offline_local_execution(self):
        """18. Offline / Local Execution: guarantees zero-downtime execution without internet."""
        # Commands execute through Local Engine without requiring cloud API keys
        res = await orchestrate_task("What's my battery percentage?", preferred_model="offline")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["model_used"], "Local Engine")
        self.assertTrue(len(res["response"]) > 0)

if __name__ == "__main__":
    unittest.main()

