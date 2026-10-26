"""Speech input regressions without live microphones or network services."""
import asyncio
import threading
from unittest.mock import AsyncMock

import numpy as np
import pytest

from backend import session as sessions
from backend import voice
from backend.session import Session


@pytest.mark.asyncio
async def test_stop_listening_transcribes_instead_of_discarding(monkeypatch):
    started = asyncio.Event()

    async def recognize(*, cancel_event, stop_event, state_callback):
        await asyncio.to_thread(state_callback, "SPEECH_DETECTED", "Speech detected...")
        started.set()
        await asyncio.to_thread(stop_event.wait, 1)
        assert stop_event.is_set()
        assert not cancel_event.is_set()
        return {"success": True, "transcript": "hello nova"}

    ws = type("Socket", (), {"send_json": AsyncMock()})()
    session = Session(ws, asyncio.Lock())
    monkeypatch.setattr(sessions.voice_input_manager, "listen_and_recognize", recognize)
    orchestrate = AsyncMock(return_value={"status": "SUCCESS", "response": "Hello"})
    monkeypatch.setattr(sessions, "orchestrate_task", orchestrate)
    monkeypatch.setattr(session, "finish", AsyncMock())
    await session.dispatch({"type": "START_LISTENING"})
    await asyncio.wait_for(started.wait(), 1)
    await session.dispatch({"type": "STOP_LISTENING"})
    await asyncio.wait_for(session.worker, 2)
    orchestrate.assert_awaited_once()
    assert orchestrate.call_args.args[0] == "hello nova"
    assert any(c.args[0]["type"] == "TRANSCRIPT" for c in ws.send_json.call_args_list)
    assert any(c.args[0].get("payload", {}).get("status") == "SPEECH_DETECTED"
               for c in ws.send_json.call_args_list)
    assert not session.desktop_lock.locked()


def test_recorder_keeps_audio_when_stopped(monkeypatch):
    stop = threading.Event()
    chunk = np.full((1600, 1), 400, dtype=np.int16)

    class Stream:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, count):
            stop.set()
            return chunk, False

    monkeypatch.setattr(voice.sd, "InputStream", lambda **kwargs: Stream())
    pcm = voice.VoiceInputManager()._record_raw_pcm(stop_event=stop)
    assert pcm == chunk.tobytes()


@pytest.mark.asyncio
async def test_device_error_is_not_reported_as_silence(monkeypatch):
    def broken_stream(**kwargs):
        raise voice.sd.PortAudioError("device unavailable")

    monkeypatch.setattr(voice.sd, "InputStream", broken_stream)
    result = await voice.VoiceInputManager().listen_and_recognize()
    assert not result["success"]
    assert not result.get("silence")
    assert "device unavailable" in result["error"]


@pytest.mark.asyncio
async def test_cancel_still_discards_recording(monkeypatch):
    started = asyncio.Event()

    async def recognize(*, cancel_event, **kwargs):
        started.set()
        await asyncio.to_thread(cancel_event.wait, 1)
        return {"success": False, "cancelled": True}

    ws = type("Socket", (), {"send_json": AsyncMock()})()
    session = Session(ws, asyncio.Lock())
    monkeypatch.setattr(sessions.voice_input_manager, "listen_and_recognize", recognize)
    orchestrate = AsyncMock()
    monkeypatch.setattr(sessions, "orchestrate_task", orchestrate)
    await session.dispatch({"type": "START_LISTENING"})
    await asyncio.wait_for(started.wait(), 1)
    await session.dispatch({"type": "INTERRUPT"})
    await asyncio.wait_for(session.worker, 2)
    orchestrate.assert_not_awaited()
    assert not any(c.args[0]["type"] == "TRANSCRIPT" for c in ws.send_json.call_args_list)
    assert not session.desktop_lock.locked()
