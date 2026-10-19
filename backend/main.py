"""Local HTTP and WebSocket entry point for NOVA."""
import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .memory import init_db
from .session import Session


@asynccontextmanager
async def lifespan(app):
    await init_db()
    app.state.desktop_lock = asyncio.Lock()
    app.state.connections = set()
    yield
    for session in tuple(app.state.connections):
        await session.close()


app = FastAPI(title="NOVA Personal Assistant", version="3.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS,
                   allow_methods=["GET"], allow_headers=["Content-Type"])


@app.get("/health")
async def health():
    return {"status": "online", "version": "3.0.0", "clients_connected": len(app.state.connections)}


@app.websocket("/ws/nova")
async def websocket_endpoint(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    if origin and origin not in settings.ALLOWED_ORIGINS:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    session = Session(websocket, app.state.desktop_lock)
    app.state.connections.add(session)
    try:
        await session.send("STATE_CHANGE", {"status": "IDLE", "detail": "Backend connected"})
        await session.sync()
        while True:
            raw = await websocket.receive_text()
            if len(raw) > 64000:
                await session.error("Request too large.")
                continue
            try:
                event = json.loads(raw)
            except (ValueError, TypeError):
                await session.error("Invalid JSON.")
                continue
            await session.dispatch(event)
    except WebSocketDisconnect:
        pass
    finally:
        await session.close()
        app.state.connections.discard(session)


frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
