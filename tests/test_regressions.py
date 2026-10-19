"""Offline regression tests. No real desktop actions or provider calls."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend import router
from backend.task_understanding import SuccessCondition
from backend.tools.file_control import create_file
from backend.tools.planner import plan_task_from_natural_language


@pytest.mark.asyncio
async def test_local_inference_never_contacts_cloud(monkeypatch):
    cloud = AsyncMock(return_value="cloud response")
    monkeypatch.setattr(router, "generate_ollama", AsyncMock(return_value=None))
    for name in ("generate_gemini", "generate_groq", "generate_nvidia"):
        monkeypatch.setattr(router, name, cloud)
    result = await router.route_inference("private note", preferred_provider="Ollama")
    cloud.assert_not_awaited()
    assert result["provider"] == "Local"


def test_create_file_preserves_existing_contents(tmp_path):
    target = tmp_path / "notes.txt"
    target.write_text("keep this", encoding="utf-8")
    result = create_file(str(target), "replacement")
    assert result["success"] is False
    assert target.read_text(encoding="utf-8") == "keep this"


@pytest.mark.parametrize("command", ["unmute volume", "unmute"])
def test_unmute_is_not_mute_or_toggle(command):
    assert plan_task_from_natural_language(command) == [
        {"tool": "system.mute", "arguments": {"mute": False}}
    ]


def test_opening_messenger_does_not_verify_a_sent_message():
    condition = SuccessCondition("message_sent", "Send hello", "WhatsApp")
    result = condition.verify(SimpleNamespace(), {
        "tool": "app.launch", "success": True, "verified": True,
        "result": {"message": "Opened WhatsApp"},
    })
    assert result.satisfied is False


@pytest.mark.asyncio
async def test_manual_model_selection_is_respected():
    from backend.orchestrator import select_model_by_intent
    assert select_model_by_intent("Explain this Python code", "Groq") == "Groq"


@pytest.mark.asyncio
async def test_all_steps_execute_for_generic_goal(monkeypatch):
    from backend import orchestrator
    from backend.task_manager import task_manager
    from backend.tools.registry import ToolResult
    task_manager.clear_flags()
    task = task_manager.create_task("two actions", [
        {"tool": "keyboard.type", "arguments": {"text": "hello"}},
        {"tool": "keyboard.press", "arguments": {"key": "enter"}},
    ], success_condition=SuccessCondition("tool_success", "two actions", "test"))
    execute = AsyncMock(return_value=ToolResult(success=True, tool="keyboard.type", verified=True))
    monkeypatch.setattr(orchestrator.tool_registry, "execute", execute)
    monkeypatch.setattr(orchestrator, "get_computer_state", lambda **kw: SimpleNamespace())
    monkeypatch.setattr(orchestrator, "synthesize", AsyncMock(return_value={"success": False}))
    result = await orchestrator.execute_task_context(task)
    assert result["status"] == "SUCCESS"
    assert execute.await_count == 2
