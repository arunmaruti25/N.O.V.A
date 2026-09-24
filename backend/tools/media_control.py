from typing import Dict, Any
import pyautogui
from .registry import ToolDefinition, tool_registry
from ..permissions import PermissionLevel

def media_action(action: str) -> Dict[str, Any]:
    """Dispatch universal Windows media hotkey."""
    clean = action.strip().lower()
    key_map = {
        "play_pause": "playpause",
        "play": "playpause",
        "pause": "playpause",
        "next": "nexttrack",
        "previous": "prevtrack",
        "prev": "prevtrack",
        "volume_up": "volumeup",
        "volume_down": "volumedown",
        "mute": "volumemute",
    }

    target_key = key_map.get(clean)
    if not target_key:
        return {"success": False, "error": f"Unknown media action '{action}'."}

    try:
        pyautogui.press(target_key)
        return {
            "success": True,
            "action": clean,
            "key": target_key,
            "message": f"Dispatched media key '{target_key}'.",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to dispatch media key: {str(e)}"}

def register_media_tools():
    tool_registry.register(ToolDefinition(
        name="media.play_pause",
        category="media",
        description="Toggle play/pause on currently active media player (Spotify, YouTube, VLC, etc.).",
        parameters={"type": "object", "properties": {}},
        permission_level=PermissionLevel.SAFE,
        execute_fn=lambda: media_action("play_pause"),
    ))

    tool_registry.register(ToolDefinition(
        name="media.next",
        category="media",
        description="Skip to next media track.",
        parameters={"type": "object", "properties": {}},
        permission_level=PermissionLevel.SAFE,
        execute_fn=lambda: media_action("next"),
    ))

    tool_registry.register(ToolDefinition(
        name="media.prev",
        category="media",
        description="Return to previous media track.",
        parameters={"type": "object", "properties": {}},
        permission_level=PermissionLevel.SAFE,
        execute_fn=lambda: media_action("prev"),
    ))

    tool_registry.register(ToolDefinition(
        name="media.volume_up",
        category="media",
        description="Increase system audio volume by one step.",
        parameters={"type": "object", "properties": {}},
        permission_level=PermissionLevel.SAFE,
        execute_fn=lambda: media_action("volume_up"),
    ))

    tool_registry.register(ToolDefinition(
        name="media.volume_down",
        category="media",
        description="Decrease system audio volume by one step.",
        parameters={"type": "object", "properties": {}},
        permission_level=PermissionLevel.SAFE,
        execute_fn=lambda: media_action("volume_down"),
    ))

