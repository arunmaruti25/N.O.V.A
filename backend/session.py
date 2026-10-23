"""One interruptible command session per WebSocket connection."""
import asyncio
import copy
import json
import threading
import time
import uuid
from contextlib import suppress
from pathlib import Path

from .config import settings
from .memory import list_memories, save_memory, delete_memory
from .orchestrator import orchestrate_task, execute_task_context, select_model_by_intent
from .privacy import private_mode
from .task_manager import TaskManager
from .tools.registry import tool_registry
from .tools.computer import get_system_info, get_system_volume
from .tools.vision import capture_screen
from .tools.web import web_search
from .tools.planner import classify_task_control_intent
from .tools.disambiguation import strip_assistant_prefix
from .voice import tts_manager, voice_input_manager


class Session:
    def __init__(self, websocket, desktop_lock):
        self.ws = websocket
        self.desktop_lock = desktop_lock
        self.send_lock = asyncio.Lock()
        self.tasks = TaskManager()
        self.worker = None
        self.cancel_event = threading.Event()
        self.pending = None
        self.conversation = []
        self.closed = False
        self.owns_desktop = False

    async def send(self, event, payload):
        if not self.closed:
            async with self.send_lock:
                await self.ws.send_json({"type": event, "payload": payload})

    async def error(self, message):
        await self.send("ERROR", {"message": message})

    async def sync(self):
        await self.send("MEMORY_SYNC", {"memories": await list_memories()})
        await self.send("SKILLS_SYNC", {"tools": tool_registry.list_tools()})
        await self.send("MODEL_CONFIG", {"models": [
            {"provider": name, "tag": getattr(settings, name.upper() + "_MODEL"),
             "configured": bool(getattr(settings, name.upper() + "_API_KEY", True))}
            for name in ("Gemini", "Groq", "NVIDIA", "Ollama")
        ]})

    def busy(self):
        return self.worker is not None and not self.worker.done()

    async def dispatch(self, event):
        if not isinstance(event, dict) or not isinstance(event.get("payload", {}), dict):
            return await self.error("Invalid event: expected an object and an object payload.")
        kind, payload = event.get("type"), event.get("payload", {})
        if not isinstance(kind, str):
            return await self.error("Event type must be a string.")
        if payload.get("task_id") is not None and not isinstance(payload["task_id"], str):
            return await self.error("Task ID must be a string.")
        if kind == "USER_INPUT" and isinstance(payload.get("text"), str):
            control = classify_task_control_intent(strip_assistant_prefix(payload["text"]))
            if control:
                kind = {"PAUSE": "TASK_PAUSE", "CANCEL": "TASK_CANCEL", "RESUME": "TASK_RESUME"}[control["action"]]
                payload = {**payload, "task_id": control.get("target")}
        if kind == "PING":
            return await self.send("PONG", {})
        if kind in {"INTERRUPT", "TASK_CANCEL"}:
            self.cancel_event.set()
            task = self.tasks.request_cancel(payload.get("task_id"))
            self.pending = None
            # Only the owner may interrupt the shared speaker.
            if self.busy() and not self.worker.cancelling():
                if self.owns_desktop:
                    tts_manager.stop_playback()
                self.worker.cancel()
            return await self.send("TASK_CANCELLED", {"task_id": task.task_id if task else None,
                "status": "CANCELLED", "description": "Cancellation requested. The current atomic action may finish."})
        if kind == "TASK_PAUSE":
            task = self.tasks.request_pause()
            if not task:
                return await self.error("No running desktop task to pause.")
            return await self.send("STATE_CHANGE", {"status": "EXECUTING", "detail": "Pausing after the current action"})
        if kind == "MEMORY_LIST":
            return await self.send("MEMORY_SYNC", {"memories": await list_memories()})
        if self.busy():
            return await self.error("A command is running. Pause or cancel it before starting another.")
        if kind == "PERMISSION_DECISION":
            grant = self.pending
            if not grant or payload.get("approval_id") != grant["approval_id"] or time.monotonic() > grant["expires"]:
                return await self.error("This approval is invalid or expired. Submit the command again.")
            self.pending = None
            if payload.get("authorized") is not True:
                self.tasks.request_cancel(grant.get("task_id"))
                return await self.send("TASK_CANCELLED", {"task_id": grant.get("task_id"), "status": "CANCELLED", "description": "Action declined."})
            payload = grant
        elif self.pending:
            return await self.error("Confirm or decline the pending action first.")
        if kind not in {"USER_INPUT", "START_LISTENING", "TASK_RESUME", "PERMISSION_DECISION",
                        "MEMORY_SAVE", "MEMORY_DELETE", "SYSTEM_STATUS", "CAPTURE_SCREEN", "WEB_SEARCH"}:
            return await self.error("Unknown event type.")
        if self.desktop_lock.locked():
            return await self.error("Another NOVA session is using the desktop. Try again when it finishes.")
        self.cancel_event = threading.Event()
        self.worker = asyncio.create_task(self.run(kind, payload))

    async def ask(self, result):
        self.pending = {**copy.deepcopy(result), "approval_id": uuid.uuid4().hex,
                        "expires": time.monotonic() + 300}
        await self.send("STATE_CHANGE", {"status": "CONFIRMATION", "detail": "Review this action"})
        await self.send("PERMISSION_REQUEST", {k: v for k, v in self.pending.items() if k != "expires"})

    async def atomic(self, awaitable):
        # A cancelled coroutine cannot stop an OS action already running in a thread.
        # Keep the desktop lock until that action has actually returned.
        operation = asyncio.ensure_future(awaitable)
        try:
            return await asyncio.shield(operation)
        except asyncio.CancelledError:
            await operation
            raise

    async def run(self, kind, payload):
        model = payload.get("model", "auto")
        if not isinstance(model, str):
            return await self.error("Model must be a string.")
        if model.lower() not in {"auto", "gemini", "groq", "nvidia", "ollama"}:
            return await self.error("Unknown model provider.")
        text = payload.get("text", "")
        if not isinstance(text, str) or len(text) > 16000:
            return await self.error("Command must be text, up to 16,000 characters.")
        local = select_model_by_intent(text, model) == "Ollama"
        token = private_mode.set(local)
        try:
            async with self.desktop_lock:
                self.owns_desktop = True
                await self.send("STATE_CHANGE", {"status": "PROCESSING", "detail": "Working on your request"})
                if kind == "SYSTEM_STATUS":
                    system, volume = await asyncio.gather(asyncio.to_thread(get_system_info), asyncio.to_thread(get_system_volume))
                    await self.send("SYSTEM_STATUS", {"system": system, "volume": volume})
                    result = {"status": "SUCCESS", "response": "System information refreshed."}
                elif kind == "MEMORY_SAVE":
                    category = payload.get("category", "User Note")
                    if not isinstance(category, str) or len(category) > 100:
                        raise ValueError("Invalid memory category.")
                    saved = await save_memory(category, text)
                    result = {"status": "SUCCESS" if saved["success"] else "ERROR", "response": "Memory saved." if saved["success"] else saved["error"]}
                elif kind == "MEMORY_DELETE":
                    memories = await list_memories()
                    item = next((m for m in memories if m["id"] == payload.get("id")), None)
                    if not item:
                        raise ValueError("Memory not found.")
                    return await self.ask({"action": "memory.delete", "id": item["id"], "title": "Delete memory?", "description": "This removes the saved note.", "detail": item["text"]})
                elif kind == "CAPTURE_SCREEN":
                    output = await self.atomic(asyncio.to_thread(capture_screen, False, True))
                    await self.send("VISION_RESULT", output)
                    result = {"status": "SUCCESS" if output["success"] else "ERROR", "response": output.get("message") or output.get("error")}
                elif kind == "WEB_SEARCH":
                    if local:
                        raise ValueError("Web search is disabled in local mode.")
                    if not text.strip():
                        raise ValueError("Enter a search query.")
                    output = await asyncio.to_thread(web_search, text.strip(), 5)
                    await self.send("WEB_RESULT", output)
                    result = {"status": "SUCCESS" if output["success"] else "ERROR", "response": output.get("summary") or output.get("error")}
                elif kind in {"TASK_RESUME", "PERMISSION_DECISION"}:
                    if kind == "PERMISSION_DECISION" and payload["action"] == "memory.delete":
                        deleted = await delete_memory(payload["id"])
                        result = {"status": "SUCCESS" if deleted else "ERROR", "response": "Memory deleted." if deleted else "Memory no longer exists."}
                    else:
                        if kind == "TASK_RESUME":
                            task, error = self.tasks.resume_task(payload.get("task_id"))
                            if error:
                                raise ValueError(error)
                        else:
                            task = self.tasks.get_task(payload.get("task_id"))
                            if (not task or task.current_step != payload.get("step_index")
                                or task.plan[task.current_step].get("tool") != payload["action"]
                                or task.plan[task.current_step].get("arguments", {}) != payload["arguments"]):
                                raise ValueError("Pending action changed. Please submit it again.")
                        private_mode.set(task.execution_context.get("private", False))
                        result = await execute_task_context(task, payload.get("action") if kind == "PERMISSION_DECISION" else None, self.send, self.tasks)
                else:
                    if kind == "START_LISTENING":
                        if local:
                            raise ValueError("Speech recognition uses an online service. Use typed commands in local mode.")
                        await self.send("STATE_CHANGE", {"status": "LISTENING", "detail": "Speak now"})
                        heard = await self.atomic(voice_input_manager.listen_and_recognize(cancel_event=self.cancel_event))
                        if not heard.get("success"):
                            raise ValueError(heard.get("error", "No speech recognized."))
                        text = heard["transcript"]
                        await self.send("TRANSCRIPT", {"text": text})
                        private_mode.set(select_model_by_intent(text, model) == "Ollama")
                    result = await orchestrate_task(text, model, on_task_event=self.send, manager=self.tasks, conversation=self.conversation)
                    self.conversation = (self.conversation + [{"role": "user", "content": text}, {"role": "assistant", "content": result.get("response", "")}])[-16:]
                await self.finish(result, payload.get("speech_enabled") is True)
        except asyncio.CancelledError:
            self.tasks.request_cancel()
            if not self.closed:
                await self.send("STATE_CHANGE", {"status": "IDLE", "detail": "Cancelled"})
        except Exception as exc:
            await self.error(str(exc))
        finally:
            self.owns_desktop = False
            private_mode.reset(token)

    async def finish(self, result, speak=False):
        status = result.get("status", "ERROR")
        if status == "CONFIRMATION_REQUIRED":
            return await self.ask(result)
        text = result.get("response", "")
        await self.send("ASSISTANT_RESPONSE", {"text": text, "model": result.get("model_used"), "tool_output": result.get("tool_output")})
        if result.get("task_id") and status in {"PAUSED", "CANCELLED", "ERROR"}:
            await self.send({"PAUSED": "TASK_PAUSED", "CANCELLED": "TASK_CANCELLED", "ERROR": "TASK_FAILED"}[status], {"task_id": result["task_id"], "description": text, "error": text})
        await self.send("MEMORY_SYNC", {"memories": await list_memories()})
        await self.send("ACTIVITY_LOG", {"action": result.get("action", "Request"), "detail": text,
                        "type": "system", "status": "error" if status == "ERROR" else status.lower()})
        if status == "ERROR":
            return await self.error(text)
        if status == "SUCCESS" and speak and not private_mode.get():
            await self.send("STATE_CHANGE", {"status": "SPEAKING", "detail": "Preparing speech"})
            try:
                audio = await asyncio.wait_for(tts_manager.synthesize(text[:4000]), timeout=30)
            except (TimeoutError, OSError):
                audio = {"success": False, "error": "Speech service timed out or could not create audio."}
            audio_path = audio.get("file_path") or audio.get("audio_path")
            path = Path(audio_path) if audio.get("success") and audio_path else None
            if path:
                try:
                    played = await tts_manager.play_audio_async(path, cancel_event=self.cancel_event)
                    if not played and not self.cancel_event.is_set():
                        await self.send("NOTIFICATION", {"type": "info", "title": "Playback unavailable", "message": "Read the text response instead."})
                finally:
                    tts_manager.stop_playback()
                    path.unlink(missing_ok=True)
            elif not audio.get("success"):
                await self.send("NOTIFICATION", {"type": "info", "title": "Speech unavailable", "message": audio.get("error", "Read the text response instead.")})
        await self.send("STATE_CHANGE", {"status": "PAUSED" if status == "PAUSED" else "IDLE", "detail": text})

    async def close(self):
        self.closed = True
        self.cancel_event.set()
        self.tasks.request_cancel()
        if self.busy():
            if self.owns_desktop:
                tts_manager.stop_playback()
            if not self.worker.cancelling():
                self.worker.cancel()
            with suppress(asyncio.CancelledError):
                await self.worker
