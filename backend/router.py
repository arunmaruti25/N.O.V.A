import os
import asyncio
import httpx
from typing import Dict, Any, Optional
from .config import settings

class ModelProvider:
    GEMINI = "Gemini"
    GROQ = "Groq"
    NVIDIA = "NVIDIA"
    OLLAMA = "Ollama"
    LOCAL = "Local"

async def generate_gemini(prompt: str, system_instruction: str = "") -> Optional[str]:
    """Generate response via Google Gemini API."""
    if not settings.GEMINI_API_KEY:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        full_prompt = f"{system_instruction}\n\nUser: {prompt}" if system_instruction else prompt
        
        # Try active Gemini models in order
        candidate_models = [settings.GEMINI_MODEL]
        for model_name in candidate_models:
            try:
                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                )
                if response and response.text:
                    return response.text.strip()
            except Exception:
                continue
    except Exception:
        pass
    return None

async def generate_groq(prompt: str, system_instruction: str = "") -> Optional[str]:
    """Generate response via Groq Cloud API."""
    if not settings.GROQ_API_KEY:
        return None
    client = None
    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        candidate_models = [settings.GROQ_MODEL]
        for model_name in candidate_models:
            try:
                chat_completion = await asyncio.wait_for(
                    client.chat.completions.create(
                        messages=messages,
                        model=model_name,
                        temperature=0.3,
                        max_tokens=600,
                    ),
                    timeout=10.0,
                )
                content = chat_completion.choices[0].message.content
                if content:
                    return content.strip()
            except Exception:
                continue
    except Exception:
        pass
    finally:
        if client:
            try:
                await client.close()
            except Exception:
                pass
    return None

async def generate_nvidia(prompt: str, system_instruction: str = "") -> Optional[str]:
    """Generate response via NVIDIA NIM API."""
    if not settings.NVIDIA_API_KEY:
        return None
    client = None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.NVIDIA_API_KEY,
        )
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        candidate_models = [settings.NVIDIA_MODEL]
        for model_name in candidate_models:
            try:
                chat_completion = await asyncio.wait_for(
                    client.chat.completions.create(
                        messages=messages,
                        model=model_name,
                        temperature=0.3,
                        max_tokens=600,
                    ),
                    timeout=12.0,
                )
                content = chat_completion.choices[0].message.content
                if content:
                    return content.strip()
            except Exception:
                continue
    except Exception:
        pass
    finally:
        if client:
            try:
                await client.close()
            except Exception:
                pass
    return None

async def generate_ollama(prompt: str, system_instruction: str = "") -> Optional[str]:
    """Generate response via local Ollama instance."""
    candidate_models = [settings.OLLAMA_MODEL]
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
    full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt

    for model_name in candidate_models:
        try:
            payload = {
                "model": model_name,
                "prompt": full_prompt,
                "stream": False,
            }
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    ans = data.get("response", "").strip()
                    if ans:
                        return ans
        except Exception:
            continue
    return None

def generate_local_fallback(prompt: str) -> str:
    return "No inference provider is available. Configure an API key or start Ollama with the configured model. Local desktop and memory commands are still available."

async def route_inference(
    prompt: str,
    preferred_provider: str = ModelProvider.GEMINI,
    system_instruction: str = "You are NOVA, a calm, precise personal AI assistant for Windows.",
) -> Dict[str, Any]:
    """
    Route prompt to requested provider with automatic fallback:
    Gemini <-> Groq <-> NVIDIA <-> Ollama -> Local Fallback
    """
    clean_provider = preferred_provider.strip().lower()

    if clean_provider == "gemini":
        providers_order = [ModelProvider.GEMINI, ModelProvider.GROQ, ModelProvider.NVIDIA, ModelProvider.OLLAMA]
    elif clean_provider == "groq":
        providers_order = [ModelProvider.GROQ, ModelProvider.GEMINI, ModelProvider.NVIDIA, ModelProvider.OLLAMA]
    elif clean_provider == "nvidia":
        providers_order = [ModelProvider.NVIDIA, ModelProvider.GEMINI, ModelProvider.GROQ, ModelProvider.OLLAMA]
    elif clean_provider == "ollama":
        # Selecting local inference is a privacy boundary, not a preference.
        providers_order = [ModelProvider.OLLAMA]
    else:
        providers_order = [ModelProvider.GEMINI, ModelProvider.GROQ, ModelProvider.NVIDIA, ModelProvider.OLLAMA]

    generators = {
        ModelProvider.GEMINI: generate_gemini, ModelProvider.GROQ: generate_groq,
        ModelProvider.NVIDIA: generate_nvidia, ModelProvider.OLLAMA: generate_ollama,
    }
    for prov in providers_order:
        try:
            answer = await asyncio.wait_for(generators[prov](prompt, system_instruction),
                                            timeout=settings.MODEL_TIMEOUT_SECONDS)
        except (TimeoutError, Exception):
            answer = None
        if answer:
            return {"provider": prov, "text": answer, "fallback_used": prov.lower() != clean_provider}
    return {"provider": ModelProvider.LOCAL, "text": generate_local_fallback(prompt),
            "mode": "Unavailable", "fallback_used": True, "unavailable": True}
