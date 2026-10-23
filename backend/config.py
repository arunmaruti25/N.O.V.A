import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from backend directory if present
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_BASE_URL: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    MODEL_MAX_TOKENS: int = int(os.getenv("NOVA_MODEL_MAX_TOKENS", "2048"))
    MODEL_FALLBACK_ENABLED: bool = os.getenv("NOVA_MODEL_FALLBACK", "true").lower() == "true"
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    FISH_SPEECH_API_URL: str = os.getenv("FISH_SPEECH_API_URL", "https://api.fish.audio/v1/tts")
    FISH_SPEECH_API_KEY: str = os.getenv("FISH_SPEECH_API_KEY", "")
    FISH_SPEECH_MODEL: str = os.getenv("FISH_SPEECH_MODEL", "s2-pro")
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "127.0.0.1")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DATA_DIR: Path = Path(os.getenv("NOVA_DATA_DIR", str(BASE_DIR / "data")))
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    NVIDIA_MODEL: str = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    MODEL_TIMEOUT_SECONDS: float = float(os.getenv("MODEL_TIMEOUT_SECONDS", "20"))
    ALLOWED_ORIGINS: list[str] = os.getenv("NOVA_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000").split(",")

    # Voice Turn-Taking & Continuation Configuration
    VOICE_SILENCE_THRESHOLD_SECONDS: float = float(os.getenv("VOICE_SILENCE_THRESHOLD_SECONDS", "2.0"))
    VOICE_CONTINUATION_WINDOW_SECONDS: float = float(os.getenv("VOICE_CONTINUATION_WINDOW_SECONDS", "1.5"))
    VOICE_MAX_DURATION_SECONDS: float = float(os.getenv("VOICE_MAX_DURATION_SECONDS", "12.0"))
    VOICE_ENERGY_THRESHOLD: int = int(os.getenv("VOICE_ENERGY_THRESHOLD", "220"))

    # Multi-Step Orchestration Configuration
    MAX_ORCHESTRATION_STEPS: int = int(os.getenv("MAX_ORCHESTRATION_STEPS", "10"))

settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)


