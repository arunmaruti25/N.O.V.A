import os
import sys
import asyncio
import io
import time
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List, Tuple
import httpx
import numpy as np
import sounddevice as sd
import speech_recognition as sr
import pygame

from .config import settings

AUDIO_CACHE_DIR = settings.DATA_DIR / "audio"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# 1. TEXT-TO-SPEECH PROVIDERS (FISH SPEECH S2 / S2 PRO PRIMARY)
# ─────────────────────────────────────────────────────────────

class BaseTTSProvider(ABC):
    """Abstract base provider interface for all NOVA TTS engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def synthesize(self, text: str, output_path: Path) -> Dict[str, Any]:
        """Synthesize text to audio file. Returns dict with status and metadata."""
        pass


class FishSpeechTTSProvider(BaseTTSProvider):
    """
    Primary TTS Provider: Fish Speech S2 / S2 Pro.
    Supports local self-hosted Fish Speech API server or Fish Audio cloud API.
    """

    @property
    def name(self) -> str:
        return "Fish Speech S2"

    async def synthesize(self, text: str, output_path: Path) -> Dict[str, Any]:
        clean_text = text.strip()
        if not clean_text:
            return {"success": False, "error": "Empty text provided.", "engine": self.name}

        api_url = settings.FISH_SPEECH_API_URL.strip() or "https://api.fish.audio/v1/tts"
        api_key = settings.FISH_SPEECH_API_KEY.strip()
        model = settings.FISH_SPEECH_MODEL.strip() or "s2-pro"

        # Check for authentication requirements
        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        elif "api.fish.audio" in api_url:
            return {
                "success": False,
                "error": "Fish Speech S2 Pro cloud API requires FISH_SPEECH_API_KEY in backend/.env. Alternatively, host a local server at FISH_SPEECH_API_URL (e.g. http://127.0.0.1:8080/v1/tts).",
                "engine": self.name,
                "missing_config": "FISH_SPEECH_API_KEY",
            }

        payload = {
            "text": clean_text,
            "model": model,
            "format": "mp3",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(api_url, json=payload, headers=headers)
                if response.status_code == 200:
                    output_path.write_bytes(response.content)
                    return {
                        "success": True,
                        "engine": self.name,
                        "model": model,
                        "file_path": str(output_path),
                        "bytes": len(response.content),
                    }
                elif response.status_code == 401:
                    return {
                        "success": False,
                        "error": "Fish Speech API authentication failed (HTTP 401 Unauthorized). Please check your FISH_SPEECH_API_KEY.",
                        "engine": self.name,
                        "status_code": 401,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Fish Speech API returned HTTP {response.status_code}: {response.text[:150]}",
                        "engine": self.name,
                        "status_code": response.status_code,
                    }
        except httpx.ConnectError:
            return {
                "success": False,
                "error": f"Unable to connect to Fish Speech server at {api_url}. Verify the server is running or configure FISH_SPEECH_API_KEY for cloud access.",
                "engine": self.name,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Fish Speech synthesis error: {str(e)}",
                "engine": self.name,
            }


class EdgeTTSProvider(BaseTTSProvider):
    """Secondary fallback TTS provider using edge-tts."""

    @property
    def name(self) -> str:
        return "Edge-TTS (Fallback)"

    async def synthesize(self, text: str, output_path: Path) -> Dict[str, Any]:
        clean_text = text.strip()
        if not clean_text:
            return {"success": False, "error": "Empty text provided.", "engine": self.name}
        try:
            import edge_tts
            communicate = edge_tts.Communicate(clean_text, "en-US-JennyNeural")
            await communicate.save(str(output_path))
            return {
                "success": True,
                "engine": self.name,
                "file_path": str(output_path),
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Edge-TTS synthesis error: {str(e)}",
                "engine": self.name,
            }


class TTSManager:
    """
    Central TTS manager.
    Enforces Fish Speech S2 / S2 Pro as primary voice, with graceful fallback.
    Manages local audio playback and real-time interruption.
    """

    def __init__(self):
        self.primary_engine: BaseTTSProvider = FishSpeechTTSProvider()
        self.fallback_engine: BaseTTSProvider = EdgeTTSProvider()
        self._mixer_initialized: bool = False
        self._active_play_task: Optional[asyncio.Task] = None
        self._init_mixer()

    def _init_mixer(self):
        """Initialize pygame audio mixer safely."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            self._mixer_initialized = True
        except Exception as e:
            self._mixer_initialized = False

    async def synthesize(
        self,
        text: str,
        output_filename: str = "response.mp3",
    ) -> Dict[str, Any]:
        """
        Synthesize response using primary Fish Speech S2 engine.
        Falls back to secondary engine if primary is unconfigured or offline.
        """
        target_path = AUDIO_CACHE_DIR / output_filename

        # 1. Attempt Primary: Fish Speech S2 / S2 Pro
        res = await self.primary_engine.synthesize(text, target_path)
        if res.get("success"):
            return res

        # Primary failed or unconfigured; record reason and use fallback
        primary_err = res.get("error", "Unknown error")
        fallback_res = await self.fallback_engine.synthesize(text, target_path)
        fallback_res["fallback_used"] = True
        fallback_res["primary_engine"] = self.primary_engine.name
        fallback_res["primary_error"] = primary_err
        return fallback_res

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        try:
            if self._mixer_initialized and pygame.mixer.get_init():
                return bool(pygame.mixer.music.get_busy())
        except Exception:
            pass
        return False

    def stop_playback(self):
        """Immediately interrupts and halts any active audio playback."""
        try:
            if self._mixer_initialized and pygame.mixer.get_init():
                pygame.mixer.music.stop()
                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass
        except Exception:
            pass

        if self._active_play_task and not self._active_play_task.done():
            self._active_play_task.cancel()

    async def play_audio_async(
        self,
        file_path: Path,
        cancel_event: Optional[asyncio.Event] = None,
    ) -> bool:
        """
        Plays audio file locally on speakers asynchronously.
        Supports instant cancellation via cancel_event.
        """
        if not file_path.exists():
            return False

        self.stop_playback()

        try:
            self._init_mixer()
            if not self._mixer_initialized:
                return False

            pygame.mixer.music.load(str(file_path))
            pygame.mixer.music.play()

            # Poll until playback finishes or cancellation requested
            while pygame.mixer.music.get_busy():
                if cancel_event and cancel_event.is_set():
                    self.stop_playback()
                    return False
                await asyncio.sleep(0.05)

            if cancel_event and cancel_event.is_set():
                self.stop_playback()
                return False

            return True
        except asyncio.CancelledError:
            self.stop_playback()
            raise
        except Exception:
            self.stop_playback()
            return False


# ─────────────────────────────────────────────────────────────
# 2. MICROPHONE & SPEECH-TO-TEXT ENGINE
# ─────────────────────────────────────────────────────────────

class VoiceInputManager:
    """
    Asynchronous microphone capture and Speech-to-Text conversion.
    Uses sounddevice to access Windows audio hardware natively without PyAudio.
    """

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

    def _record_raw_pcm(
        self,
        max_duration: Optional[float] = None,
        samplerate: int = 16000,
        cancel_event: Optional[asyncio.Event] = None,
        silence_threshold: Optional[float] = None,
        energy_threshold: Optional[int] = None,
        state_callback: Optional[Callable[[str, str], None]] = None,
    ) -> Optional[bytes]:
        """
        Captures PCM audio chunks via sounddevice.
        Implements natural voice turn-taking:
        - Configurable silence threshold (1-2s window)
        - Waits for continuation if user briefly pauses
        - Seamlessly continues the same command if speech resumes
        """
        max_dur = max_duration if max_duration is not None else settings.VOICE_MAX_DURATION_SECONDS
        silence_thresh = silence_threshold if silence_threshold is not None else settings.VOICE_SILENCE_THRESHOLD_SECONDS
        energy_thresh = energy_threshold if energy_threshold is not None else settings.VOICE_ENERGY_THRESHOLD

        chunk_duration = 0.1
        chunk_samples = int(samplerate * chunk_duration)
        recorded_chunks = []

        speech_started = False
        silence_start_time = None
        start_time = time.time()

        try:
            with sd.InputStream(
                samplerate=samplerate,
                channels=1,
                dtype="int16",
                blocksize=chunk_samples,
            ) as stream:
                while time.time() - start_time < max_dur:
                    if cancel_event and cancel_event.is_set():
                        return None

                    data, overflowed = stream.read(chunk_samples)
                    recorded_chunks.append(data.copy())

                    # Calculate RMS energy for voice activity
                    rms = np.sqrt(np.mean(data.astype(np.float32) ** 2))
                    if rms > energy_thresh:
                        if not speech_started:
                            speech_started = True
                            if state_callback:
                                state_callback("SPEECH_DETECTED", "Speech detected...")
                        elif silence_start_time is not None:
                            # Speech resumed after a brief pause! Continue the same command
                            if state_callback:
                                state_callback("SPEECH_DETECTED", "Speech resumed, continuing command...")
                        silence_start_time = None
                    elif speech_started:
                        if silence_start_time is None:
                            silence_start_time = time.time()
                            if state_callback:
                                state_callback("WAITING_FOR_CONTINUATION", "Waiting for continuation...")
                        elif time.time() - silence_start_time >= silence_thresh:
                            # Configured silence threshold reached: finalize turn
                            if state_callback:
                                state_callback("FINALIZING", "Finalizing utterance...")
                            break

            if not recorded_chunks:
                return None

            pcm_array = np.concatenate(recorded_chunks, axis=0)
            return pcm_array.tobytes()
        except Exception as e:
            return None

    def simulate_turn_taking(
        self,
        events: List[Tuple[float, float]],
        silence_threshold: float = 2.0,
        energy_threshold: int = 220,
    ) -> Dict[str, Any]:
        """
        Simulate turn-taking logic for deterministic testing.
        events: List of (duration_seconds, rms_level) tuples representing speech segments and pauses.
        """
        states_visited = []
        speech_started = False
        silence_elapsed = 0.0
        finalized = False
        speech_segments_count = 0
        current_state = "LISTENING"

        for dur, rms in events:
            if rms > energy_threshold:
                if not speech_started:
                    speech_started = True
                    speech_segments_count += 1
                    current_state = "SPEECH_DETECTED"
                    states_visited.append(current_state)
                elif silence_elapsed > 0:
                    # Resumed speech after pause!
                    speech_segments_count += 1
                    current_state = "SPEECH_DETECTED"
                    states_visited.append(current_state)
                silence_elapsed = 0.0
            elif speech_started:
                silence_elapsed += dur
                if current_state != "WAITING_FOR_CONTINUATION":
                    current_state = "WAITING_FOR_CONTINUATION"
                    states_visited.append(current_state)
                if silence_elapsed >= silence_threshold:
                    current_state = "FINALIZING"
                    states_visited.append(current_state)
                    finalized = True
                    break

        return {
            "finalized": finalized,
            "speech_started": speech_started,
            "speech_segments_count": speech_segments_count,
            "silence_elapsed": silence_elapsed,
            "states_visited": states_visited,
            "final_state": current_state,
        }

    async def listen_and_recognize(
        self,
        max_duration: Optional[float] = None,
        cancel_event: Optional[asyncio.Event] = None,
        silence_threshold: Optional[float] = None,
        energy_threshold: Optional[int] = None,
        state_callback: Optional[Callable[[str, str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Captures audio from microphone and transcribes it asynchronously.
        Non-blocking to the FastAPI event loop.
        """
        try:
            # Run recording in background thread so event loop remains responsive
            pcm_bytes = await asyncio.to_thread(
                self._record_raw_pcm,
                max_duration,
                16000,
                cancel_event,
                silence_threshold,
                energy_threshold,
                state_callback,
            )

            if cancel_event and cancel_event.is_set():
                return {"success": False, "cancelled": True, "error": "Listening cancelled"}

            if not pcm_bytes:
                return {
                    "success": False,
                    "silence": True,
                    "error": "No audio signal detected or microphone unavailable.",
                }

            # Convert PCM bytes into speech_recognition AudioData
            audio = sr.AudioData(pcm_bytes, 16000, 2)

            # Transcribe via recognizer in thread
            def do_stt():
                return self.recognizer.recognize_google(audio)

            try:
                transcript = await asyncio.to_thread(do_stt)
                return {
                    "success": True,
                    "transcript": transcript.strip(),
                }
            except sr.UnknownValueError:
                return {
                    "success": False,
                    "silence": True,
                    "error": "No speech detected (silence or unintelligible).",
                }
            except sr.RequestError as e:
                return {
                    "success": False,
                    "error": f"Speech recognition service error: {str(e)}",
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Microphone error: {str(e)}",
            }


# Global singleton instances for easy application-wide access
tts_manager = TTSManager()
voice_input_manager = VoiceInputManager()

async def synthesize(
    text: str,
    output_filename: str = "response.mp3",
) -> Dict[str, Any]:
    """Compatibility wrapper for TTS generation."""
    return await tts_manager.synthesize(text, output_filename)

def listen(timeout: int = 5, phrase_time_limit: int = 8) -> Dict[str, Any]:
    """Synchronous listen wrapper for quick CLI checks."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(voice_input_manager.listen_and_recognize(max_duration=phrase_time_limit))
    finally:
        loop.close()
