"""
Tests for Phases B, C, D, E, F:
- Phase B: Goal Understanding & Semantic Success Conditions
- Phase C: State-Aware Task Planner
- Phase D: Observe-Act-Verify Execution Loop
- Phase E: Dynamic Replanning & Error Recovery
- Phase F: Model Router Intent Optimization
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.task_understanding import (
    understand_user_goal,
    IntentType,
    UserGoal,
    SuccessCondition,
    VerificationResult,
)
from backend.tools.observation import ComputerState, WindowInfo, UIElementInfo
from backend.tools.planner import plan_task_from_goal, generate_recovery_plan
from backend.task_manager import TaskManager, TaskContext, TaskStatus
from backend.orchestrator import select_model_by_intent, execute_task_context
from backend.router import ModelProvider
from backend.tools.registry import ToolResult


# ─────────────────────────────────────────────────────────────
# 1. PHASE B TESTS: GOAL UNDERSTANDING & SUCCESS CONDITIONS
# ─────────────────────────────────────────────────────────────

def test_intent_categorization_informational():
    """Verify informational queries are categorized as INFORMATIONAL without computer actions."""
    goal = understand_user_goal("What is the speed of light?")
    assert goal.intent_type == IntentType.INFORMATIONAL
    assert goal.goal_category == "information"
    assert goal.success_condition is not None
    assert goal.success_condition.type == "answered"


def test_intent_categorization_ambiguous():
    """Verify underspecified commands trigger AMBIGUOUS intent with clarification prompt."""
    goal = understand_user_goal("Play a video on YouTube")
    assert goal.intent_type == IntentType.AMBIGUOUS
    assert goal.clarification_prompt is not None
    assert "Which" in goal.clarification_prompt or "video" in goal.clarification_prompt


def test_intent_categorization_action_media():
    """Verify specific playback request creates ACTION_TASK with playback_active condition."""
    goal = understand_user_goal("Play Soong on YouTube")
    assert goal.intent_type == IntentType.ACTION_TASK
    assert goal.goal_category == "media_playback"
    assert goal.entities.get("query") == "Soong"
    assert goal.success_condition is not None
    assert goal.success_condition.type == "playback_active"


def test_intent_categorization_action_close_app():
    """Verify close application creates ACTION_TASK with app_closed condition."""
    goal = understand_user_goal("Close WhatsApp")
    assert goal.intent_type == IntentType.ACTION_TASK
    assert goal.goal_category == "app_lifecycle"
    assert goal.target.lower() == "whatsapp"
    assert goal.success_condition is not None
    assert goal.success_condition.type == "app_closed"


def test_intent_categorization_action_messaging():
    """Verify messaging request extracts recipient, message, and WhatsApp target."""
    goal = understand_user_goal("Open WhatsApp and send hello to Rahul")
    assert goal.intent_type == IntentType.ACTION_TASK
    assert goal.goal_category == "messaging"
    assert goal.entities.get("recipient") == "Rahul"
    assert "hello" in goal.entities.get("message").lower()
    assert goal.success_condition.type == "message_sent"


def test_success_condition_app_closed_verification():
    """Verify SuccessCondition.verify accurately inspects ComputerState open windows."""
    cond = SuccessCondition(type="app_closed", description="WhatsApp closed", target="WhatsApp")

    # State with WhatsApp still open
    w_open = WindowInfo(hwnd=10, title="WhatsApp", process_name="ApplicationFrameHost.exe", pid=100)
    state_open = ComputerState(
        timestamp=0.0, screen={}, mouse_position=(0, 0), active_window=w_open,
        open_windows=[w_open], visible_applications=[{"name": "WhatsApp"}],
        running_applications=["WhatsApp.exe"], ui_elements=[], focused_element=None,
        browser_state={}, screenshot={}, context_summary=""
    )
    res_open = cond.verify(state_open)
    assert res_open.satisfied is False
    assert res_open.suggested_next_action == "force_close"

    # State where WhatsApp is closed
    state_closed = ComputerState(
        timestamp=0.0, screen={}, mouse_position=(0, 0), active_window=None,
        open_windows=[], visible_applications=[], running_applications=[],
        ui_elements=[], focused_element=None, browser_state={}, screenshot={}, context_summary=""
    )
    res_closed = cond.verify(state_closed)
    assert res_closed.satisfied is True


# ─────────────────────────────────────────────────────────────
# 2. PHASE C TESTS: STATE-AWARE TASK PLANNER
# ─────────────────────────────────────────────────────────────

def test_planner_skips_launch_if_app_already_open():
    """Verify planner avoids redundant app.launch if target app is already open."""
    goal = understand_user_goal("Open WhatsApp and send meeting notes to Rahul")
    w = WindowInfo(hwnd=1, title="WhatsApp", process_name="ApplicationFrameHost.exe", pid=2)
    state = ComputerState(
        timestamp=0.0, screen={}, mouse_position=(0, 0), active_window=w,
        open_windows=[w], visible_applications=[{"name": "WhatsApp"}],
        running_applications=[], ui_elements=[], focused_element=None,
        browser_state={}, screenshot={}, context_summary=""
    )

    plan = plan_task_from_goal(goal, current_state=state)
    tools = [step["tool"] for step in plan]
    # Should NOT launch app again since it's already open
    assert "app.launch" not in tools
    assert "app.focus" in tools or "computer.interact" in tools
    assert "keyboard.type" in tools


def test_planner_launches_if_app_closed():
    """Verify planner includes app.launch if target app is not running."""
    goal = understand_user_goal("Open WhatsApp and send hello to Rahul")
    state = ComputerState(
        timestamp=0.0, screen={}, mouse_position=(0, 0), active_window=None,
        open_windows=[], visible_applications=[], running_applications=[],
        ui_elements=[], focused_element=None, browser_state={}, screenshot={}, context_summary=""
    )
    plan = plan_task_from_goal(goal, current_state=state)
    tools = [step["tool"] for step in plan]
    assert tools[0] == "app.launch"


# ─────────────────────────────────────────────────────────────
# 3. PHASE D & E TESTS: OBSERVE-ACT-VERIFY AND RECOVERY LOOP
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_observe_act_verify_completes_early_on_success_condition():
    """Verify task execution completes early as soon as SuccessCondition is satisfied."""
    from backend.task_manager import task_manager
    goal = understand_user_goal("Close WhatsApp")
    plan = [
        {"tool": "app.close", "arguments": {"name": "whatsapp"}},
        {"tool": "window.close", "arguments": {"title": "WhatsApp"}},  # Redundant fallback step
    ]
    task = task_manager.create_task("Close WhatsApp", plan, goal=goal, success_condition=goal.success_condition)

    # Mock tool registry execution to report success
    tool_mock_res = ToolResult(
        tool_name="app.close",
        success=True,
        result={"message": "Process terminated."},
        verified=True,
    )

    # Mock get_computer_state so that post-execution state shows WhatsApp closed
    closed_state = ComputerState(
        timestamp=0.0, screen={}, mouse_position=(0, 0), active_window=None,
        open_windows=[], visible_applications=[], running_applications=[],
        ui_elements=[], focused_element=None, browser_state={}, screenshot={}, context_summary=""
    )

    with patch("backend.orchestrator.tool_registry.execute", AsyncMock(return_value=tool_mock_res)), \
         patch("backend.orchestrator.get_computer_state", return_value=closed_state), \
         patch("backend.orchestrator.synthesize", AsyncMock(return_value={"success": True, "file_path": "mock.mp3"})):
        res = await execute_task_context(task)
        assert res["status"] == "SUCCESS"
        assert res["verified"] is True
        # Only 1 step should have been executed because condition was verified!
        assert len(task.completed_steps) == 1
        assert task.status == TaskStatus.COMPLETED


def test_dynamic_recovery_plan_generation():
    """Verify generate_recovery_plan generates corrective actions when a step fails."""
    from backend.task_manager import task_manager
    goal = understand_user_goal("Close WhatsApp")
    task = task_manager.create_task("Close WhatsApp", [], goal=goal, success_condition=goal.success_condition)

    # Simulated state: WhatsApp is still open as a window
    w = WindowInfo(hwnd=555, title="WhatsApp", process_name="ApplicationFrameHost.exe", pid=999)
    state = ComputerState(
        timestamp=0.0, screen={}, mouse_position=(0, 0), active_window=w,
        open_windows=[w], visible_applications=[], running_applications=[],
        ui_elements=[], focused_element=None, browser_state={}, screenshot={}, context_summary=""
    )

    rec = generate_recovery_plan(task, state, {"success": False, "error": "Access denied terminating process."})
    assert rec is not None
    assert len(rec) >= 1
    # Recovery should attempt window-level close for the open window
    assert rec[0]["tool"] == "window.close"
    assert rec[0]["arguments"]["title"] == "WhatsApp"


# ─────────────────────────────────────────────────────────────
# 4. PHASE F TESTS: MODEL ROUTER INTENT OPTIMIZATION
# ─────────────────────────────────────────────────────────────

def test_router_multimodal_to_gemini():
    """Verify vision, screen, and UI observation intents route to Gemini."""
    assert select_model_by_intent("Inspect my screen and find the submit button") == ModelProvider.GEMINI
    assert select_model_by_intent("Take a screenshot and explain what's on the screen") == ModelProvider.GEMINI


def test_router_complex_reasoning_to_gemini():
    """Verify complex reasoning routes to Gemini."""
    assert select_model_by_intent("Analyze the architectural tradeoffs between microservices and monoliths step by step") == ModelProvider.GEMINI


def test_router_coding_to_nvidia():
    """Verify coding and script requests route to NVIDIA NIM."""
    assert select_model_by_intent("Write a Python script to parse JSON and sort items") == ModelProvider.NVIDIA


def test_router_simple_to_groq():
    """Verify quick conversational commands route to Groq for ultra-low latency."""
    assert select_model_by_intent("Hello Nova, what time is it?") == ModelProvider.GROQ
    assert select_model_by_intent("Open Notepad") == ModelProvider.GROQ
