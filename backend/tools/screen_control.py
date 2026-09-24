from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from .registry import ToolDefinition, tool_registry
from ..permissions import PermissionLevel
from .vision import capture_screen

def screen_capture_tool(save_to_disk: bool = True, return_base64: bool = True) -> Dict[str, Any]:
    """Capture screen viewport with image metadata and base64 preview."""
    res = capture_screen(save_to_disk=save_to_disk, return_base64=return_base64)
    return res

def verify_screen_capture(result: Dict[str, Any], arguments: Dict[str, Any]) -> Tuple[bool, str]:
    """Verify that a screenshot was successfully captured and saved."""
    fpath = result.get("file_path")
    if fpath and Path(fpath).exists() and Path(fpath).stat().st_size > 0:
        return True, f"Verified screen capture saved to {Path(fpath).name} ({Path(fpath).stat().st_size} bytes)."
    if result.get("has_base64"):
        return True, "Verified viewport buffer captured successfully."
    return False, "Verification warning: screenshot file not saved to disk."

def screen_inspect_tool() -> Dict[str, Any]:
    """Inspect current screen dimensions and active viewports."""
    import pyautogui
    w, h = pyautogui.size()
    return {
        "success": True,
        "width": w,
        "height": h,
        "orientation": "landscape" if w >= h else "portrait",
        "aspect_ratio": f"{round(w / h, 2)}:1",
        "message": f"Display inspected: {w}x{h} ({round(w / h, 2)}:1 aspect ratio).",
    }

def register_screen_tools():
    tool_registry.register(ToolDefinition(
        name="screen.capture",
        category="screen",
        description="Capture full screenshot of primary display with base64 preview and local caching.",
        parameters={
            "type": "object",
            "properties": {
                "save_to_disk": {"type": "boolean", "description": "Whether to save PNG to disk (default: true)"},
                "return_base64": {"type": "boolean", "description": "Whether to return thumbnail base64 string (default: true)"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=screen_capture_tool,
        verify_fn=verify_screen_capture,
    ))

    tool_registry.register(ToolDefinition(
        name="screen.inspect",
        category="screen",
        description="Inspect display metrics, dimensions, and viewport orientation.",
        parameters={"type": "object", "properties": {}},
        permission_level=PermissionLevel.SAFE,
        execute_fn=screen_inspect_tool,
    ))

