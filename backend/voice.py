import os
import sys
import asyncio
import io
import time
import threading
import uuid
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
    Includes smart failover cooldown to prevent request hangs when API credit is depleted.
    """

    def __init__(self):
        self._disabled_until: float = 0.0
        self._last_error: str = ""

    @property
    def name(self) -> str:
        return "Fish Speech S2"

    async def synthesize(self, text: str, output_path: Path) -> Dict[str, Any]:
        clean_text = text.strip()
        if not clean_text:
            return {"success": False, "error": "Empty text provided.", "engine": self.name}

        # Check if temporarily bypassed due to depleted credits or prior failures
        if time.time() < self._disabled_until:
            return {
                "success": False,
                "error": f"Fish Speech cloud API temporarily bypassed (credit/network cooldown): {self._last_error}",
                "engine": self.name,
                "bypassed": True,
            }

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
            async with httpx.AsyncClient(timeout=3.5) as client:
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
                elif response.status_code in [401, 402]:
                    err_msg = "Fish Speech API authentication failed (HTTP 401 Unauthorized)." if response.status_code == 401 else "Fish Speech API insufficient credits (HTTP 402)."
                    self._disabled_until = time.time() + 300.0  # 5 min cooldown
                    self._last_error = err_msg
                    return {
                        "success": False,
                        "error": err_msg,
                        "engine": self.name,
                        "status_code": response.status_code,
                    }
                else:
                    err_msg = f"Fish Speech API returned HTTP {response.status_code}: {response.text[:150]}"
                    self._disabled_until = time.time() + 60.0
                    self._last_error = err_msg
                    return {
                        "success": False,
                        "error": err_msg,
                        "engine": self.name,
                        "status_code": response.status_code,
                    }
        except httpx.ConnectError:
            err_msg = f"Unable to connect to Fish Speech server at {api_url}."
            self._disabled_until = time.time() + 60.0
            self._last_error = err_msg
            return {
                "success": False,
                "error": err_msg,
                "engine": self.name,
            }
        except Exception as e:
            err_msg = f"Fish Speech synthesis error: {str(e)}"
            self._disabled_until = time.time() + 60.0
            self._last_error = err_msg
            return {
                "success": False,
                "error": err_msg,
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
        from .privacy import private_mode
        if private_mode.get():
            return {"success": False, "disabled": True, "error": "Cloud speech is disabled in local mode."}
        target_path = AUDIO_CACHE_DIR / f"{uuid.uuid4().hex}-{Path(output_filename).name}"

        completed = False
        try:
            res = await self.primary_engine.synthesize(text, target_path)
            if not res.get("success"):
                primary_error = res.get("error", "Unknown error")
                res = await self.fallback_engine.synthesize(text, target_path)
                res.update(fallback_used=True, primary_engine=self.primary_engine.name, primary_error=primary_error)
            completed = bool(res.get("success"))
            return res
        finally:
            if not completed:
                target_path.unlink(missing_ok=True)

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
        self.recognizer.operation_timeout = 15
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

    def _record_raw_pcm(
        self,
        max_duration: Optional[float] = None,
        samplerate: int = 16000,
        cancel_event: Optional[threading.Event] = None,
        silence_threshold: Optional[float] = None,
        energy_threshold: Optional[int] = None,
        state_callback: Optional[Callable[[str, str], None]] = None,
        stop_event: Optional[threading.Event] = None,
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

        try:
            with sd.InputStream(
                samplerate=samplerate,
                channels=1,
                dtype="int16",
                blocksize=chunk_samples,
            ) as stream:
                start_time = time.monotonic()
                while time.monotonic() - start_time < max_dur:
                    if cancel_event and cancel_event.is_set():
                        return None
                    if stop_event and stop_event.is_set():
                        break

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
                            silence_start_time = time.monotonic()
                            if state_callback:
                                state_callback("WAITING_FOR_CONTINUATION", "Waiting for continuation...")
                        elif time.monotonic() - silence_start_time >= silence_thresh:
                            # Configured silence threshold reached: finalize turn
                            if state_callback:
                                state_callback("FINALIZING", "Finalizing utterance...")
                            break

            if not recorded_chunks:
                return None

            pcm_array = np.concatenate(recorded_chunks, axis=0)
            return pcm_array.tobytes()
        except Exception as e:
            raise RuntimeError(f"Unable to record microphone audio: {e}") from e

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
        cancel_event: Optional[threading.Event] = None,
        silence_threshold: Optional[float] = None,
        energy_threshold: Optional[int] = None,
        state_callback: Optional[Callable[[str, str], None]] = None,
        stop_event: Optional[threading.Event] = None,
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
                stop_event,
            )

            if cancel_event and cancel_event.is_set():
                return {"success": False, "cancelled": True, "error": "Listening cancelled"}

            if not pcm_bytes:
                return {
                    "success": False,
                    "silence": True,
                    "error": "No audio signal detected or microphone unavailable.",
                }

            if state_callback:
                state_callback("PROCESSING", "Transcribing your speech...")

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


# ─────────────────────────────────────────────────────────────
# 3. SIRI-LIKE VOICE ASSISTANT LIFECYCLE
# "Hey NOVA" → listen → execute → speak → follow-up conversation → standby
# ─────────────────────────────────────────────────────────────

from enum import Enum

class VoiceAssistantState(str, Enum):
    STANDBY = "STANDBY"                     # Passive wake-word listening
    WAKE_DETECTED = "WAKE_DETECTED"         # "Hey NOVA" recognized
    LISTENING = "LISTENING"                 # Actively capturing user speech
    PROCESSING = "PROCESSING"               # Parsing semantic intent
    THINKING = "THINKING"                   # Formulating execution plan
    EXECUTING = "EXECUTING"                 # Executing computer actions
    SPEAKING = "SPEAKING"                   # Speaking response via TTS
    FOLLOW_UP = "FOLLOW_UP"                 # Follow-up conversational window (4-5s)
    IDLE = "IDLE"                           # Idle state
    INTERRUPTED = "INTERRUPTED"             # User interrupted playback or listening

WAKE_WORDS = ["hey nova", "okay nova", "ok nova", "hi nova", "nova", "hey computer"]

def strip_assistant_prefix(text: str) -> str:
    """
    Strips assistant wake words or invocation prefixes:
    'Hey NOVA, play Bohemian Rhapsody' -> 'play Bohemian Rhapsody'
    'NOVA, shut down my laptop' -> 'shut down my laptop'
    'Hey NOVA' -> ''
    """
    if not text:
        return ""
    clean = text.strip()
    pattern = r'^(?:hey\s+nova|okay\s+nova|ok\s+nova|hi\s+nova|nova)[\s,:]*'
    stripped = re.sub(pattern, '', clean, flags=re.IGNORECASE).strip()
    return stripped

def detect_wake_word(text: str) -> Tuple[bool, str]:
    """
    Detects if spoken or typed text contains a wake word.
    Returns (has_wake_word, remaining_command).
    """
    if not text:
        return False, ""
    clean = text.strip()
    lower = clean.lower()

    for w in WAKE_WORDS:
        if lower.startswith(w):
            remainder = clean[len(w):].strip().lstrip(",:;").strip()
            return True, remainder
        elif f" {w} " in f" {lower} ":
            idx = lower.find(w)
            remainder = clean[idx + len(w):].strip().lstrip(",:;").strip()
            return True, remainder

    return False, clean

class VoiceAssistantSession:
    """
    Coordinates the Siri-like voice lifecycle for NOVA:
    STANDBY (passive wake-word listening)
      ↳ "Hey NOVA" detected
      ↳ LISTENING (active speech capture)
      ↳ PROCESSING / THINKING
      ↳ EXECUTING (8-stage computer use loop)
      ↳ SPEAKING (TTS synthesis & speaker playback)
      ↳ FOLLOW_UP (4-5s continuation window for natural back-and-forth)
          ↳ user speaks -> LISTENING (no wake-word needed)
          ↳ timeout -> STANDBY
    Push-to-talk is always available to override or initiate commands instantly.
    """

    def __init__(self, follow_up_timeout: float = 4.5):
        self.state: VoiceAssistantState = VoiceAssistantState.STANDBY
        self.follow_up_timeout: float = follow_up_timeout
        self.last_interaction_time: float = 0.0
        self.is_push_to_talk: bool = False
        self.history: List[Dict[str, Any]] = []

    def set_state(self, new_state: VoiceAssistantState, detail: str = "") -> Dict[str, Any]:
        """Transition assistant state and record event."""
        prev = self.state
        self.state = new_state
        self.last_interaction_time = time.time()
        entry = {
            "from_state": prev.value if isinstance(prev, VoiceAssistantState) else str(prev),
            "to_state": new_state.value if isinstance(new_state, VoiceAssistantState) else str(new_state),
            "detail": detail,
            "timestamp": time.time(),
        }
        self.history.append(entry)
        return entry

    def handle_voice_utterance(
        self,
        transcript: str,
        is_ptt: bool = False,
    ) -> Dict[str, Any]:
        """
        Process an utterance according to current assistant lifecycle:
        - If in STANDBY: requires wake-word unless push-to-talk.
        - If in FOLLOW_UP: accepts natural command directly without wake-word.
        - If in LISTENING: processes command directly.
        """
        raw = (transcript or "").strip()
        has_wake, remainder = detect_wake_word(raw)

        if is_ptt:
            # Push-to-talk bypasses wake-word requirements unconditionally
            clean_cmd = strip_assistant_prefix(raw)
            self.set_state(VoiceAssistantState.LISTENING, "Push-to-talk input accepted")
            return {
                "accepted": True,
                "command": clean_cmd,
                "is_wake_word_only": not bool(clean_cmd),
                "is_follow_up": False,
                "is_ptt": True,
                "state": VoiceAssistantState.LISTENING.value,
            }

        if self.state == VoiceAssistantState.FOLLOW_UP:
            # In follow-up conversation window: accepts direct continuation
            clean_cmd = strip_assistant_prefix(raw)
            self.set_state(VoiceAssistantState.LISTENING, "Follow-up speech received")
            return {
                "accepted": True,
                "command": clean_cmd,
                "is_wake_word_only": False,
                "is_follow_up": True,
                "is_ptt": False,
                "state": VoiceAssistantState.LISTENING.value,
            }

        # Otherwise must be in STANDBY or IDLE: check for wake-word
        if has_wake:
            self.set_state(VoiceAssistantState.WAKE_DETECTED, "Wake word detected")
            if remainder:
                self.set_state(VoiceAssistantState.PROCESSING, f"Command: {remainder}")
                return {
                    "accepted": True,
                    "command": remainder,
                    "is_wake_word_only": False,
                    "is_follow_up": False,
                    "is_ptt": False,
                    "state": VoiceAssistantState.PROCESSING.value,
                }
            else:
                self.set_state(VoiceAssistantState.LISTENING, "Listening for command after wake word")
                return {
                    "accepted": True,
                    "command": "",
                    "is_wake_word_only": True,
                    "is_follow_up": False,
                    "is_ptt": False,
                    "state": VoiceAssistantState.LISTENING.value,
                }

        # No wake word and not in follow up -> ignore or stay in standby
        return {
            "accepted": False,
            "command": "",
            "is_wake_word_only": False,
            "is_follow_up": False,
            "is_ptt": False,
            "state": self.state.value,
        }

    def simulate_lifecycle_flow(
        self,
        interactions: List[Tuple[str, float]],
    ) -> List[str]:
        """
        Simulate a sequence of (utterance, elapsed_time_since_last) interactions
        to verify state transitions:
        STANDBY → WAKE → LISTENING → SPEAKING → FOLLOW_UP → [Continuation or Timeout]
        """
        states_sequence = [self.state.value]

        for utterance, time_delta in interactions:
            # Check if follow-up expired
            if self.state == VoiceAssistantState.FOLLOW_UP and time_delta > self.follow_up_timeout:
                self.set_state(VoiceAssistantState.STANDBY, "Follow-up window expired, returning to standby")
                states_sequence.append(self.state.value)

            res = self.handle_voice_utterance(utterance)
            if res["accepted"]:
                states_sequence.append(self.state.value)
                # Simulate execution & speaking
                self.set_state(VoiceAssistantState.SPEAKING, "Synthesizing and playing response")
                states_sequence.append(self.state.value)
                # Enter follow-up window
                self.set_state(VoiceAssistantState.FOLLOW_UP, "Entering follow-up conversation window")
                states_sequence.append(self.state.value)

        return states_sequence

voice_assistant = VoiceAssistantSession()

