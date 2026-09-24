import time
from typing import Dict, Any, List, Optional
import pyautogui
from .registry import ToolDefinition, tool_registry
from ..permissions import PermissionLevel

pyautogui.FAILSAFE = False

def type_text(text: str, interval: float = 0.02) -> Dict[str, Any]:
    """Type text into currently focused input field."""
    safe_interval = max(0.001, min(0.5, float(interval)))
    try:
        pyautogui.write(text, interval=safe_interval)
        return {
            "success": True,
            "typed_length": len(text),
            "preview": text[:50] + ("..." if len(text) > 50 else ""),
            "message": f"Successfully typed {len(text)} characters.",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to type text: {str(e)}"}

def press_key(key: str) -> Dict[str, Any]:
    """Press a single keyboard key (e.g. 'enter', 'tab', 'esc', 'space', 'backspace')."""
    clean_key = key.strip().lower()
    if clean_key not in pyautogui.KEY_NAMES:
        return {
            "success": False,
            "error": f"Unknown or disallowed key '{key}'.",
            "allowed_sample": ["enter", "tab", "esc", "space", "backspace", "up", "down", "left", "right"],
        }
    try:
        pyautogui.press(clean_key)
        return {"success": True, "key": clean_key, "message": f"Pressed key '{clean_key}'."}
    except Exception as e:
        return {"success": False, "key": clean_key, "error": str(e)}

def press_hotkey(keys: List[str]) -> Dict[str, Any]:
    """Press a keyboard combination (e.g. ['ctrl', 'c'], ['ctrl', 'v'], ['alt', 'tab'], ['win', 'd'])."""
    clean_keys = [k.strip().lower() for k in keys if k.strip()]
    if not clean_keys:
        return {"success": False, "error": "Keys list cannot be empty."}

    for k in clean_keys:
        if k not in pyautogui.KEY_NAMES:
            return {"success": False, "error": f"Invalid key '{k}' in hotkey sequence."}

    try:
        pyautogui.hotkey(*clean_keys)
        return {"success": True, "keys": clean_keys, "message": f"Executed hotkey: {' + '.join(clean_keys)}"}
    except Exception as e:
        return {"success": False, "keys": clean_keys, "error": str(e)}

def clipboard_copy() -> Dict[str, Any]:
    """Simulate Ctrl+C to copy selected content to clipboard."""
    try:
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.1)
        # Attempt to read clipboard content
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        clip = root.clipboard_get()
        root.destroy()
        return {"success": True, "clipboard": clip[:200], "message": "Copied selection to clipboard."}
    except Exception:
        return {"success": True, "message": "Dispatched Ctrl+C copy signal."}

def clipboard_paste(text: Optional[str] = None) -> Dict[str, Any]:
    """Simulate Ctrl+V to paste into current focused field."""
    try:
        if text:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
            root.destroy()
        pyautogui.hotkey('ctrl', 'v')
        return {"success": True, "message": "Dispatched Ctrl+V paste signal."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def register_keyboard_tools():
    tool_registry.register(ToolDefinition(
        name="keyboard.type",
        category="keyboard",
        description="Type text string into the active focused input field.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text content to type"},
                "interval": {"type": "number", "description": "Delay in seconds between keystrokes (default: 0.02)"},
            },
            "required": ["text"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=type_text,
    ))

    tool_registry.register(ToolDefinition(
        name="keyboard.press",
        category="keyboard",
        description="Press a single key (e.g. enter, tab, esc, backspace, space, up, down).",
        parameters={
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key name to press"},
            },
            "required": ["key"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=press_key,
    ))

    tool_registry.register(ToolDefinition(
        name="keyboard.hotkey",
        category="keyboard",
        description="Press a keyboard shortcut combination (e.g. ['ctrl', 'c'], ['alt', 'tab'], ['win', 'd']).",
        parameters={
            "type": "object",
            "properties": {
                "keys": {
                    "type": "array",
                    "description": "List of key names",
                    "items": {"type": "string"},
                },
            },
            "required": ["keys"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=press_hotkey,
    ))

    tool_registry.register(ToolDefinition(
        name="keyboard.copy",
        category="keyboard",
        description="Dispatch Ctrl+C copy command to active selection.",
        parameters={"type": "object", "properties": {}},
        permission_level=PermissionLevel.SAFE,
        execute_fn=clipboard_copy,
    ))

    tool_registry.register(ToolDefinition(
        name="keyboard.paste",
        category="keyboard",
        description="Dispatch Ctrl+V paste command to active field.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Optional text to place on clipboard before pasting"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=clipboard_paste,
    ))

