"""Transport and command lifecycle tests; no real audio, network AI or desktop actions."""
import asyncio
import threading
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.main import app
from backend import session as sessions
from backend.session import Session
from backend.tools.registry import ToolResult, ToolDefinition, ToolRegistry
from backend.permissions import PermissionLevel


class Socket:
    def __init__(self):
        self.events = []

    async def send_json(self, event):
        self.events.append(event)


@pytest.mark.asyncio
async def test_background_status_does_not_interrupt_running_task(monkeypatch):
    monkeypatch.setattr(sessions, 'get_system_info', lambda: {'cpu_percent': 12, 'disk_percent': 24})
    monkeypatch.setattr(sessions, 'get_system_volume', lambda: {'volume_percent': 30})
    session = Session(Socket(), asyncio.Lock())
    session.worker = asyncio.create_task(asyncio.sleep(60))
    try:
        await session.dispatch({'type': 'GET_SYSTEM_STATUS'})
        assert session.ws.events[-1]['type'] == 'SYSTEM_STATUS'
        assert session.ws.events[-1]['payload']['system']['disk_percent'] == 24
        assert not session.worker.done()
    finally:
        session.worker.cancel()
        await asyncio.gather(session.worker, return_exceptions=True)


@pytest.mark.asyncio
async def test_status_capability_and_unknown_event_diagnostics(monkeypatch):
    monkeypatch.setattr(sessions, 'list_memories', AsyncMock(return_value=[]))
    monkeypatch.setattr(sessions, 'get_system_info', lambda: {'cpu_percent': 12})
    monkeypatch.setattr(sessions, 'get_system_volume', lambda: {'volume_percent': 30})
    session = Session(Socket(), asyncio.Lock())
    await session.sync()
    config = next(e['payload'] for e in session.ws.events if e['type'] == 'MODEL_CONFIG')
    assert 'GET_SYSTEM_STATUS' in config['supported_events']
    session.ws.events.clear()
    await session.dispatch({'type': 'GET_SYSTEM_STATUS'})
    assert [e['type'] for e in session.ws.events] == ['SYSTEM_STATUS']
    await session.dispatch({'type': 'UNSUPPORTED_REQUEST'})
    error = session.ws.events[-1]['payload']
    assert error['code'] == 'UNKNOWN_EVENT'
    assert error['event_type'] == 'UNSUPPORTED_REQUEST'
    assert 'restart the backend' in error['message']


def until(ws, kind):
    for _ in range(50):
        event = ws.receive_json()
        if event["type"] == kind:
            return event["payload"]
    raise AssertionError(f"Did not receive {kind}")


def test_memory_survives_reconnection_and_delete_requires_approval():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        with client.websocket_connect("/ws/nova") as ws:
            until(ws, "MODEL_CONFIG")
            ws.send_json({"type": "MEMORY_SAVE", "payload": {"text": "Keep this note"}})
            saved = until(ws, "MEMORY_SYNC")["memories"]
            assert len(saved) == 1
            until(ws, "STATE_CHANGE")
        with client.websocket_connect("/ws/nova") as ws:
            assert until(ws, "MEMORY_SYNC")["memories"][0]["text"] == "Keep this note"
            until(ws, "MODEL_CONFIG")
            ws.send_json({"type": "MEMORY_DELETE", "payload": {"id": saved[0]["id"]}})
            approval = until(ws, "PERMISSION_REQUEST")
            ws.send_json({"type": "PERMISSION_DECISION", "payload": {"approval_id": approval["approval_id"], "authorized": False}})
            until(ws, "TASK_CANCELLED")
            ws.send_json({"type": "MEMORY_LIST"})
            assert len(until(ws, "MEMORY_SYNC")["memories"]) == 1


def test_rejects_untrusted_origin_and_recovers_from_malformed_messages():
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/nova", headers={"origin": "https://untrusted.example"}):
                pass
        with client.websocket_connect("/ws/nova") as ws:
            until(ws, "MODEL_CONFIG")
            for bad in ("not json", "[]", '{"type":"USER_INPUT","payload":42}'):
                ws.send_text(bad)
                assert until(ws, "ERROR")["message"]
            ws.send_json({"type": "PING"})
            assert until(ws, "PONG") == {}


@pytest.mark.asyncio
async def test_cancel_is_processed_during_inference(monkeypatch):
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def slow(*args, **kwargs):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    monkeypatch.setattr(sessions, "orchestrate_task", slow)
    socket = Socket()
    session = Session(socket, asyncio.Lock())
    await session.dispatch({"type": "USER_INPUT", "payload": {"text": "explain a concept"}})
    await asyncio.wait_for(started.wait(), 1)
    await session.dispatch({"type": "PING"})
    assert socket.events[-1]["type"] == "PONG"
    await session.dispatch({"type": "USER_INPUT", "payload": {"text": "cancel"}})
    await asyncio.wait_for(session.worker, 1)
    assert cancelled.is_set()
    assert not session.desktop_lock.locked()


@pytest.mark.asyncio
async def test_approval_keeps_original_arguments_and_cannot_replay(monkeypatch):
    socket = Socket()
    session = Session(socket, asyncio.Lock())
    original = {"path": "C:/test/original.txt"}
    task = session.tasks.create_task("delete original", [{"tool": "file.delete", "arguments": original, "thought": "delete requested file"}])
    await session.ask({"action": "file.delete", "task_id": task.task_id, "step_index": 0, "arguments": original})
    approval_id = session.pending["approval_id"]
    execute = AsyncMock(return_value=ToolResult(success=True, tool="file.delete", verified=True))
    monkeypatch.setattr(sessions.tool_registry, "execute", execute)
    payload = {"approval_id": approval_id, "authorized": True, "action": "system.power", "arguments": {"action": "shutdown"}}
    await session.dispatch({"type": "PERMISSION_DECISION", "payload": payload})
    await session.worker
    execute.assert_awaited_once_with("file.delete", original, pre_authorized=True)
    await session.dispatch({"type": "PERMISSION_DECISION", "payload": payload})
    assert socket.events[-1]["type"] == "ERROR"
    assert execute.await_count == 1


@pytest.mark.asyncio
async def test_direct_confirmation_bypass_is_ignored(monkeypatch):
    execute = AsyncMock(return_value=ToolResult(success=True))
    monkeypatch.setattr(sessions.tool_registry, "execute", execute)
    session = Session(Socket(), asyncio.Lock())
    await session.dispatch({"type": "USER_INPUT", "payload": {"text": "shutdown computer", "confirmed_action": "system.power"}})
    await session.worker
    execute.assert_not_awaited()
    assert session.pending["action"] == "system.power"


@pytest.mark.asyncio
async def test_local_mode_disables_network_voice_and_search(monkeypatch):
    listen = AsyncMock()
    search = lambda *args: pytest.fail("Local mode contacted web search")
    monkeypatch.setattr(sessions.voice_input_manager, "listen_and_recognize", listen)
    monkeypatch.setattr(sessions, "web_search", search)
    session = Session(Socket(), asyncio.Lock())
    for kind in ("START_LISTENING", "WEB_SEARCH"):
        await session.dispatch({"type": kind, "payload": {"model": "Ollama", "text": "my query"}})
        await session.worker
        assert session.ws.events[-1]["type"] == "ERROR"
    listen.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancel_waits_for_atomic_os_action_before_unlocking():
    registry = ToolRegistry()
    started, release = threading.Event(), threading.Event()

    def action():
        started.set()
        release.wait(3)
        return {"success": True}

    registry.register(ToolDefinition("test.action", "test", "test", {}, PermissionLevel.SAFE, action))
    operation = asyncio.create_task(registry.execute("test.action", {}))
    assert await asyncio.to_thread(started.wait, 1)
    operation.cancel()
    await asyncio.sleep(0.01)
    assert not operation.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await operation


@pytest.mark.asyncio
async def test_sessions_do_not_share_task_state():
    lock = asyncio.Lock()
    a, b = Session(Socket(), lock), Session(Socket(), lock)
    task = a.tasks.create_task("example", [])
    await b.dispatch({"type": "TASK_CANCEL", "payload": {"task_id": task.task_id}})
    assert task.status == "RUNNING"


@pytest.mark.asyncio
async def test_pause_resumes_from_next_step(monkeypatch):
    from backend.orchestrator import execute_task_context
    session = Session(Socket(), asyncio.Lock())
    task = session.tasks.create_task("two actions", [
        {"tool": "keyboard.type", "arguments": {"text": "first"}},
        {"tool": "keyboard.type", "arguments": {"text": "second"}},
    ])
    calls = []

    async def execute(name, arguments, **kwargs):
        calls.append(arguments["text"])
        if len(calls) == 1:
            session.tasks.request_pause()
        return ToolResult(success=True, verified=True, tool=name)

    monkeypatch.setattr(sessions.tool_registry, "execute", execute)
    assert (await execute_task_context(task, manager=session.tasks))["status"] == "PAUSED"
    assert calls == ["first"]
    session.tasks.resume_task(task.task_id)
    assert (await execute_task_context(task, manager=session.tasks))["status"] == "SUCCESS"
    assert calls == ["first", "second"]
