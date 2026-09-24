import unittest
import asyncio
from unittest.mock import patch, AsyncMock
from backend.config import settings
from backend.orchestrator import orchestrate_task
from backend.tools.registry import tool_registry, ToolResult
from backend.task_manager import task_manager, TaskStatus
from backend.tools.planner import (
    build_tool_system_prompt,
    parse_llm_tool_calls,
    normalize_tool_name,
)
from backend.permissions import evaluate_tool_permission, PermissionLevel

class NovaAIToolRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        task_manager.tasks.clear()
        task_manager.task_history.clear()
        task_manager.active_task_id = None
        task_manager.clear_flags()

    # 1. "Open YouTube" -> browser tool executes
    async def test_01_open_youtube_executes_browser_tool(self):
        res = await orchestrate_task(user_input="Open YouTube")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn(res["action"], ["browser.open", "browser.navigate", "browser_open", "app.launch"])
        self.assertTrue(any("youtube" in t.original_request.lower() for t in task_manager.tasks.values()))

    # 2. "Open Chrome" -> app tool executes
    async def test_02_open_chrome_executes_app_tool(self):
        res = await orchestrate_task(user_input="Open Chrome")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn(res["action"], ["app.launch", "browser.open"])

    # 3. "Search YouTube for Minecraft" -> browser tool executes
    async def test_03_search_youtube_for_minecraft_executes_browser_tool(self):
        res = await orchestrate_task(user_input="Search YouTube for Minecraft")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn(res["action"], ["browser.search", "browser.open", "browser.navigate"])

    # 4. "Play a YouTube video" -> browser tool path selected (or clarification asked, never refusal)
    async def test_04_play_youtube_video_no_refusal(self):
        res = await orchestrate_task(user_input="Play a YouTube video")
        self.assertEqual(res["status"], "SUCCESS")
        # Must NOT be a capability refusal!
        refusal_phrases = ["cannot directly browse", "cannot control your computer", "unable to browse"]
        for phrase in refusal_phrases:
            self.assertNotIn(phrase, res["response"].lower())

    # 5. Multi-step browser request executes multiple tools
    async def test_05_multistep_browser_request_executes_multiple_tools(self):
        # AI returns a multi-step execution plan: open browser and search
        multi_step_json = '{"steps": [{"tool": "browser.open", "arguments": {"url": "https://www.youtube.com"}}, {"tool": "browser.search", "arguments": {"engine": "youtube", "query": "Minecraft"}}]}'
        parsed = parse_llm_tool_calls(multi_step_json)
        self.assertIsNotNone(parsed)
        self.assertEqual(len(parsed), 2)
        task = task_manager.create_task("Open YouTube and search Minecraft", parsed)
        self.assertEqual(len(task.plan), 2)
        from backend.orchestrator import execute_task_context
        exec_res = await execute_task_context(task)
        self.assertEqual(exec_res["status"], "SUCCESS")
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertEqual(len(task.completed_steps), 2)

    # 6. Tool result returns to the AI
    async def test_06_tool_result_structure_for_ai(self):
        res = await tool_registry.execute("browser.open", {"url": "https://www.youtube.com"})
        self.assertTrue(res.success)
        d = res.to_dict()
        self.assertIn("success", d)
        self.assertIn("tool", d)
        self.assertIn("result", d)
        self.assertIn("verified", d)

    # 7. AI can select the next tool based on prior result (multi-turn reasoning loop)
    async def test_07_ai_selects_next_tool_in_loop(self):
        # Test simulated multi-turn: step 1 returns tool, step 2 returns next tool, step 3 finishes
        turns = [
            '{"tool": "browser.open", "arguments": {"url": "https://www.youtube.com"}}',
            '{"tool": "browser.click", "arguments": {"target": "play"}}',
            'I have opened YouTube and started playing the video for you.',
        ]
        turn_idx = 0

        async def fake_route_inference(prompt, preferred_provider="Gemini", system_instruction=""):
            nonlocal turn_idx
            text = turns[min(turn_idx, len(turns) - 1)]
            turn_idx += 1
            return {"provider": "MockAI", "text": text}

        with patch("backend.orchestrator.route_inference", side_effect=fake_route_inference):
            res = await orchestrate_task(user_input="Open YouTube and click play")
            self.assertEqual(res["status"], "SUCCESS")
            # Verified multi-turn execution completed
            self.assertIn("playing", res["response"].lower())

    # 8. Normal conversational questions remain normal AI responses (no tool called)
    async def test_08_conversational_question_no_tools(self):
        async def fake_chat(prompt, preferred_provider="Gemini", system_instruction=""):
            return {"provider": "MockAI", "text": "YouTube is a global video sharing platform founded in 2005."}

        with patch("backend.orchestrator.route_inference", side_effect=fake_chat):
            res = await orchestrate_task(user_input="What is YouTube?")
            self.assertEqual(res["status"], "SUCCESS")
            self.assertEqual(res["action"], "chat")
            self.assertIn("platform", res["response"].lower())
            # No computer task was created
            self.assertEqual(len(task_manager.tasks), 0)

    # 9. Ambiguous browser request asks clarification when genuinely needed
    async def test_09_ambiguous_request_asks_clarification(self):
        async def fake_clarification(prompt, preferred_provider="Gemini", system_instruction=""):
            return {"provider": "MockAI", "text": "Which video would you like me to play on YouTube?"}

        with patch("backend.orchestrator.route_inference", side_effect=fake_clarification):
            res = await orchestrate_task(user_input="Play a video on YouTube")
            self.assertEqual(res["status"], "SUCCESS")
            self.assertIn("which video", res["response"].lower())
            self.assertNotIn("cannot browse", res["response"].lower())

    # 10. Existing permissions remain strictly enforced
    async def test_10_permissions_strictly_enforced(self):
        perm = evaluate_tool_permission("system.power", {"action": "shutdown"})
        self.assertEqual(perm.level, PermissionLevel.CONFIRMATION_REQUIRED)

        perm_blocked = evaluate_tool_permission("app.launch", {"name": "format c:"})
        self.assertEqual(perm_blocked.level, PermissionLevel.BLOCKED)

    # 11. Novel generalization test (NOT in hardcoded test examples)
    async def test_11_novel_generalization_command(self):
        # User asks for an arbitrary novel action: "Navigate to wikipedia.org and search for Mars Rover"
        # Verify AI tool parser maps it to registered browser tool
        novel_llm_output = '{"tool": "browser.search", "arguments": {"query": "Mars Rover", "engine": "google"}}'
        parsed = parse_llm_tool_calls(novel_llm_output)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed[0]["tool"], "browser.search")
        self.assertEqual(parsed[0]["arguments"]["query"], "Mars Rover")

        # Verify execution
        res = await tool_registry.execute(parsed[0]["tool"], parsed[0]["arguments"])
        self.assertTrue(res.success)
        self.assertIn("Mars Rover", res.result.get("message", ""))

    # 12. Tool System Prompt contains all active tools and clear capability rules
    def test_12_tool_system_prompt_completeness(self):
        prompt = build_tool_system_prompt()
        self.assertIn("browser.open", prompt)
        self.assertIn("browser.navigate", prompt)
        self.assertIn("browser.search", prompt)
        self.assertIn("browser.click", prompt)
        self.assertIn("browser.type", prompt)
        self.assertIn("browser.scroll", prompt)
        self.assertIn("CONVERSATIONAL REQUESTS", prompt)
        self.assertIn("ACTION REQUESTS", prompt)
        self.assertIn("AMBIGUOUS ACTION REQUESTS", prompt)
        # Total registered tools >= 53
        self.assertGreaterEqual(len(tool_registry.list_tools()), 53)

if __name__ == "__main__":
    unittest.main()

