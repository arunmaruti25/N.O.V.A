from typing import Dict, Any, List, Optional
from .registry import ToolDefinition, tool_registry
from ..permissions import PermissionLevel

def list_windows() -> Dict[str, Any]:
    """List all open desktop windows with title, dimensions, and state."""
    windows_info = []
    try:
        import pygetwindow as gw
        for w in gw.getAllWindows():
            title = w.title.strip()
            if title:
                windows_info.append({
                    "title": title,
                    "is_active": w.isActive,
                    "is_minimized": w.isMinimized,
                    "is_maximized": w.isMaximized,
                    "width": w.width,
                    "height": w.height,
                })
    except Exception:
        pass

    # Fallback to win32gui if pygetwindow returned empty
    if not windows_info:
        try:
            import win32gui
            def cb(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    t = win32gui.GetWindowText(hwnd).strip()
                    if t:
                        extra.append({"title": t, "hwnd": hwnd})
            win32gui.EnumWindows(cb, windows_info)
        except Exception:
            pass

    return {
        "success": True,
        "count": len(windows_info),
        "windows": windows_info[:20],
        "message": f"Found {len(windows_info)} open window(s).",
    }

def find_window_by_title(title_query: str):
    """Find pygetwindow Window object by partial title match."""
    import pygetwindow as gw
    clean = title_query.strip().lower()
    for w in gw.getAllWindows():
        if clean in w.title.lower():
            return w
    return None

def focus_window(title: str) -> Dict[str, Any]:
    """Bring window matching title to the foreground."""
    w = find_window_by_title(title)
    if not w:
        return {"success": False, "error": f"No window matching '{title}' was found."}
    try:
        w.restore()
        w.activate()
        return {"success": True, "title": w.title, "message": f"Activated window '{w.title}'."}
    except Exception as e:
        return {"success": False, "error": f"Failed to activate window: {str(e)}"}

def minimize_window(title: str) -> Dict[str, Any]:
    """Minimize window matching title."""
    w = find_window_by_title(title)
    if not w:
        return {"success": False, "error": f"No window matching '{title}' was found."}
    try:
        w.minimize()
        return {"success": True, "title": w.title, "message": f"Minimized window '{w.title}'."}
    except Exception as e:
        return {"success": False, "error": f"Failed to minimize window: {str(e)}"}

def maximize_window(title: str) -> Dict[str, Any]:
    """Maximize window matching title."""
    w = find_window_by_title(title)
    if not w:
        return {"success": False, "error": f"No window matching '{title}' was found."}
    try:
        w.maximize()
        return {"success": True, "title": w.title, "message": f"Maximized window '{w.title}'."}
    except Exception as e:
        return {"success": False, "error": f"Failed to maximize window: {str(e)}"}

def restore_window(title: str) -> Dict[str, Any]:
    """Restore window from minimized or maximized state."""
    w = find_window_by_title(title)
    if not w:
        return {"success": False, "error": f"No window matching '{title}' was found."}
    try:
        w.restore()
        return {"success": True, "title": w.title, "message": f"Restored window '{w.title}'."}
    except Exception as e:
        return {"success": False, "error": f"Failed to restore window: {str(e)}"}

def close_window(title: str) -> Dict[str, Any]:
    """Close window matching title."""
    w = find_window_by_title(title)
    if not w:
        return {"success": False, "error": f"No window matching '{title}' was found."}
    try:
        w.close()
        return {"success": True, "title": w.title, "message": f"Closed window '{w.title}'."}
    except Exception as e:
        return {"success": False, "error": f"Failed to close window: {str(e)}"}

def move_resize_window(
    title: str,
    x: Optional[int] = None,
    y: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Dict[str, Any]:
    """Move and/or resize window matching title."""
    w = find_window_by_title(title)
    if not w:
        return {"success": False, "error": f"No window matching '{title}' was found."}
    try:
        if x is not None and y is not None:
            w.moveTo(int(x), int(y))
        if width is not None and height is not None:
            w.resizeTo(int(width), int(height))
        return {
            "success": True,
            "title": w.title,
            "x": w.left,
            "y": w.top,
            "width": w.width,
            "height": w.height,
            "message": f"Updated position/dimensions for '{w.title}'.",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to move/resize window: {str(e)}"}

def register_window_tools():
    tool_registry.register(ToolDefinition(
        name="window.list",
        category="window",
        description="List all open desktop windows and their states.",
        parameters={"type": "object", "properties": {}},
        permission_level=PermissionLevel.SAFE,
        execute_fn=list_windows,
    ))

    tool_registry.register(ToolDefinition(
        name="window.focus",
        category="window",
        description="Bring an application window matching title to the foreground.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title or partial title of window to focus"},
            },
            "required": ["title"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=focus_window,
    ))

    tool_registry.register(ToolDefinition(
        name="window.minimize",
        category="window",
        description="Minimize window matching title.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title or partial title of window to minimize"},
            },
            "required": ["title"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=minimize_window,
    ))

    tool_registry.register(ToolDefinition(
        name="window.maximize",
        category="window",
        description="Maximize window matching title.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title or partial title of window to maximize"},
            },
            "required": ["title"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=maximize_window,
    ))

    tool_registry.register(ToolDefinition(
        name="window.restore",
        category="window",
        description="Restore window matching title from minimized/maximized state.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title or partial title of window to restore"},
            },
            "required": ["title"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=restore_window,
    ))

    tool_registry.register(ToolDefinition(
        name="window.close",
        category="window",
        description="Close window matching title.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title or partial title of window to close"},
            },
            "required": ["title"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=close_window,
    ))

