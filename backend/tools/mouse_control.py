from typing import Dict, Any, Optional
import pyautogui
from .registry import ToolDefinition, tool_registry
from ..permissions import PermissionLevel

pyautogui.FAILSAFE = False

def clamp_coords(x: Optional[int], y: Optional[int]):
    """Clamp coordinates to within valid primary monitor bounds."""
    w, h = pyautogui.size()
    clamped_x = max(0, min(w - 1, int(x))) if x is not None else None
    clamped_y = max(0, min(h - 1, int(y))) if y is not None else None
    return clamped_x, clamped_y

def move_mouse(x: int, y: int, duration: float = 0.1) -> Dict[str, Any]:
    """Move cursor smoothly to specified screen coordinates."""
    cx, cy = clamp_coords(x, y)
    safe_dur = max(0.0, min(2.0, float(duration)))
    try:
        pyautogui.moveTo(cx, cy, duration=safe_dur)
        return {
            "success": True,
            "x": cx,
            "y": cy,
            "message": f"Cursor positioned at ({cx}, {cy}).",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to move mouse: {str(e)}"}

def click_mouse(
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "left",
    clicks: int = 1,
) -> Dict[str, Any]:
    """Click mouse button at current cursor location or target coordinates."""
    cx, cy = clamp_coords(x, y)
    clean_btn = button.strip().lower()
    if clean_btn not in ["left", "right", "middle"]:
        clean_btn = "left"

    try:
        if cx is not None and cy is not None:
            pyautogui.click(cx, cy, clicks=clicks, button=clean_btn)
        else:
            pyautogui.click(clicks=clicks, button=clean_btn)
        curr_x, curr_y = pyautogui.position()
        target_x = cx if cx is not None else curr_x
        target_y = cy if cy is not None else curr_y
        return {
            "success": True,
            "x": target_x,
            "y": target_y,
            "button": clean_btn,
            "clicks": clicks,
            "message": f"Mouse {clean_btn} clicked ({clicks}x) at ({target_x}, {target_y}).",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to click mouse: {str(e)}"}

def double_click_mouse(x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
    """Double click mouse at current or target coordinates."""
    return click_mouse(x=x, y=y, button="left", clicks=2)

def right_click_mouse(x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
    """Right click mouse to open context menu."""
    return click_mouse(x=x, y=y, button="right", clicks=1)

def drag_mouse(x: int, y: int, duration: float = 0.3) -> Dict[str, Any]:
    """Drag from current position to target coordinates."""
    cx, cy = clamp_coords(x, y)
    safe_dur = max(0.1, min(3.0, float(duration)))
    try:
        pyautogui.dragTo(cx, cy, duration=safe_dur)
        return {"success": True, "to_x": cx, "to_y": cy, "message": f"Dragged to ({cx}, {cy})."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def scroll_mouse(clicks: int) -> Dict[str, Any]:
    """Scroll mouse wheel vertically (positive = up, negative = down)."""
    try:
        pyautogui.scroll(int(clicks))
        return {
            "success": True,
            "clicks": clicks,
            "message": f"Scrolled {'up' if clicks > 0 else 'down'} {abs(clicks)} units.",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def register_mouse_tools():
    tool_registry.register(ToolDefinition(
        name="mouse.move",
        category="mouse",
        description="Move cursor to screen coordinates (X, Y).",
        parameters={
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate in pixels"},
                "y": {"type": "integer", "description": "Y coordinate in pixels"},
                "duration": {"type": "number", "description": "Movement duration in seconds (default: 0.1)"},
            },
            "required": ["x", "y"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=move_mouse,
    ))

    tool_registry.register(ToolDefinition(
        name="mouse.click",
        category="mouse",
        description="Click mouse button at coordinates or current position.",
        parameters={
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Optional X coordinate"},
                "y": {"type": "integer", "description": "Optional Y coordinate"},
                "button": {"type": "string", "description": "Button: 'left', 'right', or 'middle' (default: 'left')"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=click_mouse,
    ))

    tool_registry.register(ToolDefinition(
        name="mouse.double_click",
        category="mouse",
        description="Double click mouse at coordinates or current position.",
        parameters={
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Optional X coordinate"},
                "y": {"type": "integer", "description": "Optional Y coordinate"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=double_click_mouse,
    ))

    tool_registry.register(ToolDefinition(
        name="mouse.right_click",
        category="mouse",
        description="Right click mouse to open context menu.",
        parameters={
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Optional X coordinate"},
                "y": {"type": "integer", "description": "Optional Y coordinate"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=right_click_mouse,
    ))

    tool_registry.register(ToolDefinition(
        name="mouse.scroll",
        category="mouse",
        description="Scroll mouse wheel vertically (positive = up, negative = down).",
        parameters={
            "type": "object",
            "properties": {
                "clicks": {"type": "integer", "description": "Amount to scroll (e.g. -300 for down, 300 for up)"},
            },
            "required": ["clicks"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=scroll_mouse,
    ))

