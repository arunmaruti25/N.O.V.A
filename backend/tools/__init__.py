"""
NOVA Modular Tool Engine and Central Registry.
"""
from .registry import tool_registry, ToolDefinition, ToolResult
from .app_control import register_app_tools
from .browser_control import register_browser_tools
from .keyboard_control import register_keyboard_tools
from .mouse_control import register_mouse_tools
from .window_control import register_window_tools
from .file_control import register_file_tools
from .system_control import register_system_tools
from .media_control import register_media_tools
from .screen_control import register_screen_tools
from .computer_use import register_computer_use_tools

# Auto-register all tool modules into tool_registry singleton
register_app_tools()
register_browser_tools()
register_keyboard_tools()
register_mouse_tools()
register_window_tools()
register_file_tools()
register_system_tools()
register_media_tools()
register_screen_tools()
register_computer_use_tools()

__all__ = [
    "tool_registry",
    "ToolDefinition",
    "ToolResult",
]
