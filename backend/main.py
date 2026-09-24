import asyncio
import json
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pathlib import Path
from .config import settings
from .orchestrator import orchestrate_task
from .memory import init_db, list_memories, save_memory, delete_memory
from .tools.computer import get_system_info, get_system_volume, set_system_volume
from .tools.vision import capture_screen
from .voice import tts_manager, voice_input_manager
from .task_manager import task_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup
    await init_db()
    yield

app = FastAPI(
    title="NOVA Personal AI Assistant Backend",
    version="2.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, event_type: str, payload: dict):
        message = json.dumps({"type": event_type, "payload": payload})
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.active_connections.discard(connection)

    async def send_to(self, websocket: WebSocket, event_type: str, payload: dict):
        message = json.dumps({"type": event_type, "payload": payload})
        await websocket.send_text(message)

manager = ConnectionManager()

@app.get("/health")
async def health():
    """Healthcheck endpoint reporting server and system status."""
    return {
        "status": "online",
        "service": "NOVA Neural Backend",
        "version": "2.4.0",
        "environment": settings.ENVIRONMENT,
        "system": get_system_info(),
        "clients_connected": len(manager.active_connections),
    }

@app.websocket("/ws/nova")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    voice_cancel_event = asyncio.Event()

    # Send initial welcome and state sync
    await manager.send_to(
        websocket,
        "STATE_CHANGE",
        {"status": "IDLE", "detail": "Neural backend connected"},
    )
    # Sync initial memory list
    mems = await list_memories()
    await manager.send_to(websocket, "MEMORY_SYNC", {"memories": mems})

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                event = json.loads(raw_text)
            except Exception:
                continue

            event_type = event.get("type")
            payload = event.get("payload", {})

            if event_type == "USER_INPUT":
                # Cancel any previous voice/audio task
                tts_manager.stop_playback()
                voice_cancel_event.set()
                voice_cancel_event = asyncio.Event()

                user_text = payload.get("text", "")
                model = payload.get("model", "Gemini")
                confirmed_action = payload.get("confirmed_action", None)

                # Emit PROCESSING state
                await manager.send_to(
                    websocket,
                    "STATE_CHANGE",
                    {"status": "PROCESSING", "detail": "Parsing semantic intent..."},
                )

                # Emit THINKING state
                await manager.send_to(
                    websocket,
                    "STATE_CHANGE",
                    {"status": "THINKING", "detail": "Formulating reasoning plan..."},
                )

                async def send_task_event(ev_name: str, ev_data: dict):
                    await manager.send_to(websocket, ev_name, ev_data)

                # Run async orchestrator pipeline
                result = await orchestrate_task(
                    user_input=user_text,
                    preferred_model=model,
                    confirmed_action=confirmed_action,
                    on_task_event=send_task_event,
                )

                if result["status"] == "CONFIRMATION_REQUIRED":
                    # Emit CONFIRMATION state & modal trigger
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "CONFIRMATION", "detail": "AUTHORIZATION REQUIRED"},
                    )
                    await manager.send_to(
                        websocket,
                        "PERMISSION_REQUEST",
                        {
                            "title": result.get("title", "Confirm Action"),
                            "description": result.get("description", ""),
                            "detail": result.get("detail", ""),
                            "action": result.get("action", ""),
                        },
                    )
                elif result["status"] == "PAUSED":
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "PAUSED", "detail": result.get("response", "Task paused.")},
                    )
                    await manager.send_to(
                        websocket,
                        "TASK_PAUSED",
                        {
                            "task_id": result.get("task_id"),
                            "status": "PAUSED",
                            "current_step": result.get("current_step"),
                            "total_steps": result.get("total_steps"),
                            "description": result.get("response", "Paused"),
                        },
                    )
                    await manager.send_to(
                        websocket,
                        "ASSISTANT_RESPONSE",
                        {
                            "text": result.get("response", "Paused. You can give me another task."),
                            "model": "Local Engine",
                        },
                    )
                elif result["status"] == "CANCELLED":
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "IDLE", "detail": result.get("response", "Task cancelled.")},
                    )
                    await manager.send_to(
                        websocket,
                        "TASK_CANCELLED",
                        {
                            "task_id": result.get("task_id"),
                            "status": "CANCELLED",
                            "description": result.get("response", "Cancelled"),
                        },
                    )
                    await manager.send_to(
                        websocket,
                        "ASSISTANT_RESPONSE",
                        {
                            "text": result.get("response", "Task cancelled."),
                            "model": "Local Engine",
                        },
                    )
                elif result["status"] == "ERROR":
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "ERROR", "detail": result.get("response", "Error occurred")},
                    )
                    await manager.send_to(
                        websocket,
                        "ERROR",
                        {"message": result.get("response", "Execution error")},
                    )
                else:
                    # Executing & Speaking states
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "EXECUTING", "detail": f"Completed: {result.get('action', 'task')}"},
                    )
                    await manager.send_to(
                        websocket,
                        "ACTIVITY_LOG",
                        {
                            "action": result.get("action", "Command Execution"),
                            "detail": user_text,
                            "type": "computer" if "screen" not in user_text else "vision",
                            "status": "success",
                        },
                    )

                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "SPEAKING", "detail": "Responding..."},
                    )
                    await manager.send_to(
                        websocket,
                        "MODEL_INFO",
                        {
                            "provider": result.get("model_used", model),
                            "model": result.get("model_used", model),
                        },
                    )
                    await manager.send_to(
                        websocket,
                        "ASSISTANT_RESPONSE",
                        {
                            "text": result.get("response", ""),
                            "model": result.get("model_used", model),
                            "tool_output": result.get("tool_output"),
                        },
                    )

                    # Play synthesized audio locally on speakers
                    audio_path = result.get("audio_path")
                    if audio_path and Path(audio_path).exists():
                        await tts_manager.play_audio_async(Path(audio_path), cancel_event=voice_cancel_event)

                    await manager.send_to(
                        websocket,
                        "SPEECH_FINISHED",
                        {"status": "completed"},
                    )

                    # Return to IDLE after a short pause if not interrupted
                    if not voice_cancel_event.is_set():
                        await manager.send_to(
                            websocket,
                            "STATE_CHANGE",
                            {"status": "SUCCESS", "detail": "DONE"},
                        )
                        await asyncio.sleep(1.0)
                        await manager.send_to(
                            websocket,
                            "STATE_CHANGE",
                            {"status": "IDLE", "detail": ""},
                        )

            elif event_type in ["START_LISTENING", "VOICE_START"]:
                # 1. Stop any currently playing audio and reset cancel token
                tts_manager.stop_playback()
                voice_cancel_event.set()
                voice_cancel_event = asyncio.Event()

                # 2. Transition UI to LISTENING
                await manager.send_to(
                    websocket,
                    "STATE_CHANGE",
                    {"status": "LISTENING", "detail": "Listening... speak now"},
                )

                # Thread-safe callback for natural voice turn-taking states
                loop = asyncio.get_running_loop()
                def voice_state_cb(st: str, detail: str):
                    try:
                        loop.call_soon_threadsafe(
                            asyncio.create_task,
                            manager.send_to(websocket, "STATE_CHANGE", {"status": st, "detail": detail})
                        )
                    except Exception:
                        pass

                # 3. Capture microphone speech asynchronously with turn-taking continuation
                model = payload.get("model", "Gemini")
                stt_result = await voice_input_manager.listen_and_recognize(
                    cancel_event=voice_cancel_event,
                    state_callback=voice_state_cb,
                )

                if voice_cancel_event.is_set():
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "IDLE", "detail": "Voice input cancelled"},
                    )
                    continue

                if not stt_result.get("success"):
                    err_msg = stt_result.get("error", "No speech detected")
                    await manager.send_to(
                        websocket,
                        "NOTIFICATION",
                        {"type": "info", "title": "Voice Input", "message": err_msg},
                    )
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "IDLE", "detail": ""},
                    )
                    continue

                recognized_text = stt_result.get("transcript", "").strip()

                # 4. Emit live recognized transcript to frontend
                await manager.send_to(
                    websocket,
                    "TRANSCRIPT",
                    {"text": recognized_text, "source": "user"},
                )

                # 5. Transition to PROCESSING
                await manager.send_to(
                    websocket,
                    "STATE_CHANGE",
                    {"status": "PROCESSING", "detail": "Parsing semantic intent..."},
                )

                # 6. Transition to THINKING
                await manager.send_to(
                    websocket,
                    "STATE_CHANGE",
                    {"status": "THINKING", "detail": "Formulating reasoning plan..."},
                )

                async def send_voice_task_event(ev_name: str, ev_data: dict):
                    await manager.send_to(websocket, ev_name, ev_data)

                # 7. Route through NOVA orchestrator
                result = await orchestrate_task(
                    user_input=recognized_text,
                    preferred_model=model,
                    on_task_event=send_voice_task_event,
                )

                if voice_cancel_event.is_set():
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "IDLE", "detail": "Voice operation cancelled"},
                    )
                    continue

                if result["status"] == "CONFIRMATION_REQUIRED":
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "CONFIRMATION", "detail": "AUTHORIZATION REQUIRED"},
                    )
                    await manager.send_to(
                        websocket,
                        "PERMISSION_REQUEST",
                        {
                            "title": result.get("title", "Confirm Action"),
                            "description": result.get("description", ""),
                            "detail": result.get("detail", ""),
                            "action": result.get("action", ""),
                        },
                    )
                elif result["status"] == "PAUSED":
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "PAUSED", "detail": result.get("response", "Task paused.")},
                    )
                    await manager.send_to(
                        websocket,
                        "TASK_PAUSED",
                        {
                            "task_id": result.get("task_id"),
                            "status": "PAUSED",
                            "current_step": result.get("current_step"),
                            "total_steps": result.get("total_steps"),
                            "description": result.get("response", "Paused"),
                        },
                    )
                    await manager.send_to(
                        websocket,
                        "ASSISTANT_RESPONSE",
                        {
                            "text": result.get("response", "Paused. You can give me another task."),
                            "model": "Local Engine",
                        },
                    )
                    audio_path = result.get("audio_path")
                    if audio_path and Path(audio_path).exists():
                        await tts_manager.play_audio_async(Path(audio_path), cancel_event=voice_cancel_event)
                elif result["status"] == "CANCELLED":
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "IDLE", "detail": result.get("response", "Task cancelled.")},
                    )
                    await manager.send_to(
                        websocket,
                        "TASK_CANCELLED",
                        {
                            "task_id": result.get("task_id"),
                            "status": "CANCELLED",
                            "description": result.get("response", "Cancelled"),
                        },
                    )
                    await manager.send_to(
                        websocket,
                        "ASSISTANT_RESPONSE",
                        {
                            "text": result.get("response", "Task cancelled."),
                            "model": "Local Engine",
                        },
                    )
                    audio_path = result.get("audio_path")
                    if audio_path and Path(audio_path).exists():
                        await tts_manager.play_audio_async(Path(audio_path), cancel_event=voice_cancel_event)
                elif result["status"] == "ERROR":
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "ERROR", "detail": result.get("response", "Error occurred")},
                    )
                    await manager.send_to(
                        websocket,
                        "ERROR",
                        {"message": result.get("response", "Execution error")},
                    )
                else:
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "EXECUTING", "detail": f"Completed: {result.get('action', 'task')}"},
                    )
                    await manager.send_to(
                        websocket,
                        "ACTIVITY_LOG",
                        {
                            "action": result.get("action", "Voice Command"),
                            "detail": recognized_text,
                            "type": "computer" if "screen" not in recognized_text else "vision",
                            "status": "success",
                        },
                    )

                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "SPEAKING", "detail": "Responding..."},
                    )
                    await manager.send_to(
                        websocket,
                        "MODEL_INFO",
                        {
                            "provider": result.get("model_used", model),
                            "model": result.get("model_used", model),
                        },
                    )
                    await manager.send_to(
                        websocket,
                        "ASSISTANT_RESPONSE",
                        {
                            "text": result.get("response", ""),
                            "model": result.get("model_used", model),
                            "tool_output": result.get("tool_output"),
                        },
                    )

                    # Play synthesized audio locally on speakers
                    audio_path = result.get("audio_path")
                    if audio_path and Path(audio_path).exists():
                        await tts_manager.play_audio_async(Path(audio_path), cancel_event=voice_cancel_event)

                    await manager.send_to(
                        websocket,
                        "SPEECH_FINISHED",
                        {"status": "completed"},
                    )

                    if not voice_cancel_event.is_set():
                        await manager.send_to(
                            websocket,
                            "STATE_CHANGE",
                            {"status": "SUCCESS", "detail": "DONE"},
                        )
                        await asyncio.sleep(1.0)
                        await manager.send_to(
                            websocket,
                            "STATE_CHANGE",
                            {"status": "IDLE", "detail": ""},
                        )

            elif event_type in ["STOP_LISTENING", "STOP_RECORDING"]:
                voice_cancel_event.set()
                await manager.send_to(
                    websocket,
                    "STATE_CHANGE",
                    {"status": "IDLE", "detail": "Microphone stopped"},
                )

            elif event_type in ["INTERRUPT", "CANCEL"]:
                voice_cancel_event.set()
                tts_manager.stop_playback()
                await manager.send_to(
                    websocket,
                    "INTERRUPTED",
                    {"detail": "Voice operation interrupted"},
                )
                await manager.send_to(
                    websocket,
                    "STATE_CHANGE",
                    {"status": "IDLE", "detail": "Interrupted"},
                )

            elif event_type == "PERMISSION_DECISION":
                action = payload.get("action")
                authorized = payload.get("authorized", False)
                if authorized:
                    # Re-run task with confirmed action pre-authorized
                    res = await orchestrate_task(
                        user_input=action,
                        confirmed_action=action,
                    )
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "SUCCESS", "detail": f"Authorized action '{action}' executed."},
                    )
                    await asyncio.sleep(1.5)
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "IDLE", "detail": ""},
                    )
                else:
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "IDLE", "detail": "Action declined by user."},
                    )

            elif event_type == "SCREEN_CAPTURE":
                await manager.send_to(
                    websocket,
                    "STATE_CHANGE",
                    {"status": "THINKING", "detail": "Capturing display buffer..."},
                )
                cap = capture_screen(save_to_disk=True, return_base64=True)
                await manager.send_to(
                    websocket,
                    "VISION_RESULT",
                    cap,
                )
                await manager.send_to(
                    websocket,
                    "STATE_CHANGE",
                    {"status": "IDLE", "detail": ""},
                )

            elif event_type == "VOLUME_SET":
                level = payload.get("level", 50)
                vol_res = set_system_volume(level)
                await manager.send_to(websocket, "VOLUME_STATUS", vol_res)

            elif event_type == "MEMORY_SAVE":
                cat = payload.get("category", "Preferences")
                txt = payload.get("text", "")
                await save_memory(cat, txt)
                mems = await list_memories()
                await manager.send_to(websocket, "MEMORY_SYNC", {"memories": mems})

            elif event_type == "MEMORY_DELETE":
                mid = payload.get("id")
                if mid:
                    await delete_memory(int(mid))
                mems = await list_memories()
                await manager.send_to(websocket, "MEMORY_SYNC", {"memories": mems})

            elif event_type == "MEMORY_LIST":
                mems = await list_memories()
                await manager.send_to(websocket, "MEMORY_SYNC", {"memories": mems})

            elif event_type == "TASK_PAUSE":
                active_task = task_manager.get_active_task()
                if active_task:
                    task_manager.request_pause()
                    task_manager.mark_task_paused(active_task.task_id)
                    await manager.send_to(
                        websocket,
                        "TASK_PAUSED",
                        {
                            "task_id": active_task.task_id,
                            "status": "PAUSED",
                            "current_step": active_task.current_step,
                            "total_steps": len(active_task.plan),
                            "description": f"Task '{active_task.original_request}' paused.",
                        },
                    )
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "PAUSED", "detail": f"Task {active_task.task_id} paused"},
                    )
                else:
                    await manager.send_to(
                        websocket,
                        "NOTIFICATION",
                        {"type": "info", "title": "Task Manager", "message": "No active task running to pause."},
                    )

            elif event_type == "TASK_RESUME":
                task_id = payload.get("task_id")
                async def send_ws_task_event(ev_name: str, ev_data: dict):
                    await manager.send_to(websocket, ev_name, ev_data)

                res = await orchestrate_task(
                    user_input=f"resume {task_id}" if task_id else "resume",
                    on_task_event=send_ws_task_event,
                )
                await manager.send_to(
                    websocket,
                    "ASSISTANT_RESPONSE",
                    {"text": res.get("response", ""), "model": res.get("model_used", "Local Engine")},
                )

            elif event_type == "TASK_CANCEL":
                task_id = payload.get("task_id")
                cancelled = task_manager.request_cancel(task_id)
                if not cancelled:
                    paused = task_manager.get_paused_tasks()
                    if paused:
                        cancelled = task_manager.request_cancel(paused[-1].task_id)

                if cancelled:
                    await manager.send_to(
                        websocket,
                        "TASK_CANCELLED",
                        {
                            "task_id": cancelled.task_id,
                            "status": "CANCELLED",
                            "description": f"Task '{cancelled.original_request}' cancelled.",
                        },
                    )
                    await manager.send_to(
                        websocket,
                        "STATE_CHANGE",
                        {"status": "IDLE", "detail": "Task cancelled"},
                    )
                else:
                    await manager.send_to(
                        websocket,
                        "NOTIFICATION",
                        {"type": "info", "title": "Task Manager", "message": "No task found to cancel."},
                    )

            elif event_type in ["TASK_STATUS_REQUEST", "TASK_LIST"]:
                active = task_manager.get_active_task()
                tasks_data = [t.to_dict() for t in task_manager.tasks.values()]
                await manager.send_to(
                    websocket,
                    "TASK_LIST_UPDATE",
                    {
                        "tasks": tasks_data,
                        "active_task_id": task_manager.active_task_id,
                        "active_task": active.to_dict() if active else None,
                        "paused_tasks": [t.to_dict() for t in task_manager.get_paused_tasks()],
                    },
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=False,
    )

