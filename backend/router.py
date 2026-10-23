"""Bounded provider adapters; failures are explicit and never include credentials."""
import asyncio
import json
from contextvars import ContextVar
from contextlib import suppress
from functools import wraps
from typing import Any, Dict, Optional
import httpx
from .config import settings


class ModelProvider:
    GEMINI = "Gemini"
    GROQ = "Groq"
    NVIDIA = "NVIDIA"
    OLLAMA = "Ollama"
    LOCAL = "Local"


# Each route owns its diagnostics, including when asyncio.wait_for creates a task.
_errors = ContextVar("provider_errors", default=None)
_history = ContextVar("provider_history", default=())


def bounded(provider):
    def decorate(function):
        @wraps(function)
        async def run(*args, **kwargs):
            try:
                return await asyncio.wait_for(function(*args, **kwargs), settings.MODEL_TIMEOUT_SECONDS)
            except TimeoutError as exc:
                _failure(provider, exc)
                return None
        return run
    return decorate


def _failure(provider, exc):
    errors = _errors.get()
    if errors is not None:
        code = (getattr(exc, "status_code", None) or getattr(exc, "code", None)
                or getattr(getattr(exc, "response", None), "status_code", None))
        reason = ("timeout" if isinstance(exc, (TimeoutError, httpx.TimeoutException))
                  else f"HTTP {code}" if isinstance(code, int) else type(exc).__name__)
        errors.append({"provider": provider, "reason": reason})


def _messages(prompt, system):
    messages = [{"role": "system", "content": system}] if system else []
    messages.extend(dict(item) for item in _history.get())
    messages.append({"role": "user", "content": prompt})
    return messages


@bounded(ModelProvider.GEMINI)
async def generate_gemini(prompt: str, system_instruction: str = "") -> Optional[str]:
    if not settings.GEMINI_API_KEY:
        return None
    client = None
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        contents = [types.Content(role="model" if m["role"] == "assistant" else "user",
                    parts=[types.Part(text=m["content"])]) for m in _messages(prompt, "")]
        response = await asyncio.wait_for(client.aio.models.generate_content_stream(
            model=settings.GEMINI_MODEL, contents=contents,
            config=types.GenerateContentConfig(system_instruction=system_instruction or None,
                temperature=0.3, max_output_tokens=settings.MODEL_MAX_TOKENS)), settings.MODEL_TIMEOUT_SECONDS)
        return "".join([chunk.text async for chunk in response if chunk.text]).strip() or None
    except Exception as exc:
        _failure(ModelProvider.GEMINI, exc)
        return None
    finally:
        if client is not None:
            with suppress(Exception):
                await asyncio.wait_for(client.aio.aclose(), 5)
            with suppress(Exception):
                client.close()


async def _compatible(provider, prompt, system):
    client = None
    try:
        if provider == ModelProvider.GROQ:
            if not settings.GROQ_API_KEY:
                return None
            from groq import AsyncGroq
            client = AsyncGroq(api_key=settings.GROQ_API_KEY, timeout=settings.MODEL_TIMEOUT_SECONDS, max_retries=1)
            model = settings.GROQ_MODEL
        else:
            if not settings.NVIDIA_API_KEY:
                return None
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.NVIDIA_API_KEY, base_url=settings.NVIDIA_BASE_URL,
                                 timeout=settings.MODEL_TIMEOUT_SECONDS, max_retries=1)
            model = settings.NVIDIA_MODEL
        response = await asyncio.wait_for(client.chat.completions.create(model=model,
            messages=_messages(prompt, system), temperature=0.3, stream=True,
            **({"max_completion_tokens": settings.MODEL_MAX_TOKENS} if provider == ModelProvider.GROQ else {"max_tokens": settings.MODEL_MAX_TOKENS})),
            settings.MODEL_TIMEOUT_SECONDS)
        async with response:
            parts = []
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    parts.append(chunk.choices[0].delta.content)
            return "".join(parts).strip() or None
    except Exception as exc:
        _failure(provider, exc)
        return None
    finally:
        if client is not None:
            with suppress(Exception):
                await asyncio.wait_for(client.close(), 5)


@bounded(ModelProvider.GROQ)
async def generate_groq(prompt: str, system_instruction: str = "") -> Optional[str]:
    return await _compatible(ModelProvider.GROQ, prompt, system_instruction)


@bounded(ModelProvider.NVIDIA)
async def generate_nvidia(prompt: str, system_instruction: str = "") -> Optional[str]:
    return await _compatible(ModelProvider.NVIDIA, prompt, system_instruction)


@bounded(ModelProvider.OLLAMA)
async def generate_ollama(prompt: str, system_instruction: str = "") -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=settings.MODEL_TIMEOUT_SECONDS) as client:
            async with client.stream("POST", f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat", json={
                "model": settings.OLLAMA_MODEL, "messages": _messages(prompt, system_instruction),
                "stream": True, "options": {"num_predict": settings.MODEL_MAX_TOKENS}}) as response:
                response.raise_for_status()
                parts, completed = [], False
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    if data.get("error"):
                        raise ValueError("Ollama returned an error")
                    parts.append(data.get("message", {}).get("content", ""))
                    if data.get("done"):
                        completed = True
                        break
                if not completed:
                    raise ValueError("Ollama stream ended without completion")
                return "".join(parts).strip() or None
    except Exception as exc:
        _failure(ModelProvider.OLLAMA, exc)
        return None


def generate_local_fallback(prompt: str) -> str:
    return "No inference provider is available. Configure an API key or start Ollama with the configured model. Local desktop and memory commands are still available."


async def route_inference(prompt: str, preferred_provider: str = ModelProvider.GEMINI,
        system_instruction: str = "You are NOVA, a calm, precise personal AI assistant for Windows.",
        conversation=None) -> Dict[str, Any]:
    if not isinstance(prompt, str) or not isinstance(preferred_provider, str):
        raise ValueError("Prompt and provider must be strings.")
    providers = [ModelProvider.GEMINI, ModelProvider.GROQ, ModelProvider.NVIDIA, ModelProvider.OLLAMA]
    selected = next((p for p in providers if p.lower() == preferred_provider.strip().lower()), None)
    if selected is None:
        raise ValueError("Unknown inference provider.")
    order = [selected] + [p for p in providers if p != selected]
    if selected == ModelProvider.OLLAMA or not settings.MODEL_FALLBACK_ENABLED:
        order = [selected]
    history = []
    for item in (conversation or [])[-16:]:
        if isinstance(item, dict) and item.get("role") in ("user", "assistant") and isinstance(item.get("content"), str):
            history.append({"role": item["role"], "content": item["content"][:16000]})
    errors = []
    error_token, history_token = _errors.set(errors), _history.set(tuple(history))
    generators = {ModelProvider.GEMINI: generate_gemini, ModelProvider.GROQ: generate_groq,
                  ModelProvider.NVIDIA: generate_nvidia, ModelProvider.OLLAMA: generate_ollama}
    try:
        for provider in order:
            try:
                answer = await asyncio.wait_for(generators[provider](prompt, system_instruction), settings.MODEL_TIMEOUT_SECONDS)
            except Exception as exc:
                _failure(provider, exc)
                answer = None
            if answer:
                return {"provider": provider, "text": answer, "fallback_used": provider != selected}
        detail = "; ".join(f"{e['provider']}: {e['reason']}" for e in errors)
        return {"provider": ModelProvider.LOCAL, "text": generate_local_fallback(prompt) + (f" ({detail})" if detail else ""),
                "mode": "Unavailable", "fallback_used": True, "unavailable": True, "errors": errors}
    finally:
        _errors.reset(error_token)
        _history.reset(history_token)

async def discover_models(provider: str):
    """Explicit, read-only discovery. Never guesses or downloads a model."""
    if provider not in (ModelProvider.GEMINI, ModelProvider.GROQ, ModelProvider.NVIDIA, ModelProvider.OLLAMA):
        raise ValueError("Unknown inference provider.")
    if provider != ModelProvider.OLLAMA and not getattr(settings, provider.upper() + '_API_KEY'):
        return {"provider": provider, "models": [], "available": False, "error": "API key is not configured."}
    headers = {}
    if provider == ModelProvider.GEMINI:
        url = 'https://generativelanguage.googleapis.com/v1beta/models'
        headers['x-goog-api-key'] = settings.GEMINI_API_KEY
    elif provider == ModelProvider.GROQ:
        url = 'https://api.groq.com/openai/v1/models'
        headers['Authorization'] = f'Bearer {settings.GROQ_API_KEY}'
    elif provider == ModelProvider.NVIDIA:
        url = settings.NVIDIA_BASE_URL.rstrip('/') + '/models'
        headers['Authorization'] = f'Bearer {settings.NVIDIA_API_KEY}'
    else:
        url = settings.OLLAMA_BASE_URL.rstrip('/') + '/api/tags'
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
        entries = data.get('models', []) if provider in ('Gemini', 'Ollama') else data.get('data', [])
        models = [item.get('id') or item.get('name') for item in entries if isinstance(item, dict)]
        return {"provider": provider, "models": [m for m in models if isinstance(m, str)], "available": True,
                "next_page_token": data.get('nextPageToken')}
    except Exception as exc:
        code = getattr(exc, 'response', None)
        reason = f'HTTP {code.status_code}' if code is not None else type(exc).__name__
        return {"provider": provider, "models": [], "available": False, "error": reason}
