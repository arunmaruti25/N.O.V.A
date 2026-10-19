"""Request-local privacy policy, propagated to asyncio worker threads."""
from contextvars import ContextVar

private_mode = ContextVar("nova_private_mode", default=False)
