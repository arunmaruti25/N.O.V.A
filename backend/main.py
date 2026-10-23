"""Local HTTP and WebSocket entry point for NOVA."""
import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .memory import init_db
from .session import Session
from .router import discover_models


@asynccontextmanager
async def lifespan(app):
    await init_db()
    app.state.desktop_lock = asyncio.Lock()
    app.state.connections = set()
    try:
        yield
    finally:
        await asyncio.gather(*(session.close() for session in tuple(app.state.connections)), return_exceptions=True)
        app.state.connections.clear()


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
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            raw = message.get("text")
            if not isinstance(raw, str):
                await session.error("Expected a JSON text message.")
                continue
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


@app.get("/models/{provider}")
async def models(provider: str):
    try:
        return await discover_models(provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
