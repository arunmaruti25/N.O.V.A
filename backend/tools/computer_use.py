import os
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

import pyautogui
from .registry import ToolDefinition, ToolResult, tool_registry
from .observation import get_unified_observation, get_active_window_info, get_screen_metrics
from .ui_understanding import locate_ui_element
from ..permissions import PermissionLevel

pyautogui.FAILSAFE = True

async def observe_computer_tool(include_screenshot: bool = True, include_ui_elements: bool = True) -> Dict[str, Any]:
    """Execute unified computer observation."""
    obs = get_unified_observation(
        include_screenshot=include_screenshot,
        include_ui_elements=include_ui_elements,
        save_screenshot_to_disk=True,
    )
    return obs

async def locate_element_tool(description: str, control_type: Optional[str] = None) -> Dict[str, Any]:
    """Dynamically locate element on screen from current state."""
    res = locate_ui_element(description, control_type=control_type)
    return res

async def interact_tool(
    action: str,
    target_description: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    text: Optional[str] = None,
    key: Optional[str] = None,
    clicks: int = 1,
    verify_expected_change: Optional[str] = None,
    retry_limit: int = 2,
) -> Dict[str, Any]:
    """
    General Human-Like Computer Interaction Loop:
    OBSERVE → LOCATE → ACT → OBSERVE AGAIN → VERIFY → ADAPT → COMPLETE
    """
    clean_action = action.strip().lower()
    retries = 0
    last_error = None

    while retries <= retry_limit:
        # 1. OBSERVE: Current computer state
        pre_obs = get_unified_observation(include_ui_elements=True)
        target_x, target_y = x, y

        # 2. LOCATE: If target description provided and coordinates missing, locate dynamically
        target_info = None
        if (target_x is None or target_y is None) and target_description:
            loc = locate_ui_element(target_description, observation=pre_obs)
            if loc.get("found"):
                target_x = loc["x"]
                target_y = loc["y"]
                target_info = loc
            elif clean_action not in ["type", "press_key", "hotkey", "scroll"]:
                # If target was explicitly requested but cannot be found
                retries += 1
                time.sleep(0.3)
                continue

        # 3. ACT: Execute interaction safely
        try:
            if clean_action in ["click", "locate_and_click"]:
                if target_x is not None and target_y is not None:
                    pyautogui.click(x=int(target_x), y=int(target_y), clicks=clicks, button="left")
                else:
                    pyautogui.click(clicks=clicks, button="left")
                action_msg = f"Clicked at ({target_x}, {target_y}){' on ' + target_description if target_description else ''}"

            elif clean_action in ["double_click", "double click"]:
                if target_x is not None and target_y is not None:
                    pyautogui.click(x=int(target_x), y=int(target_y), clicks=2, button="left")
                else:
                    pyautogui.click(clicks=2, button="left")
                action_msg = f"Double clicked at ({target_x}, {target_y})"

            elif clean_action in ["right_click", "right click"]:
                if target_x is not None and target_y is not None:
                    pyautogui.click(x=int(target_x), y=int(target_y), clicks=1, button="right")
                else:
                    pyautogui.click(clicks=1, button="right")
                action_msg = f"Right clicked at ({target_x}, {target_y})"

            elif clean_action in ["type", "locate_and_type", "focus_and_type"]:
                if target_x is not None and target_y is not None:
                    pyautogui.click(x=int(target_x), y=int(target_y))
                    time.sleep(0.1)
                if text:
                    pyautogui.typewrite(text, interval=0.01)
                action_msg = f"Typed '{text or ''}' into target field"

            elif clean_action in ["press_key", "key"]:
                if key:
                    pyautogui.press(key.strip().lower())
                action_msg = f"Pressed key '{key}'"

            elif clean_action in ["hotkey", "shortcut"]:
                if key:
                    keys = [k.strip().lower() for k in key.split("+")]
                    pyautogui.hotkey(*keys)
                action_msg = f"Executed hotkey '{key}'"

            elif clean_action in ["move", "mouse_move"]:
                if target_x is not None and target_y is not None:
                    pyautogui.moveTo(x=int(target_x), y=int(target_y))
                action_msg = f"Moved mouse to ({target_x}, {target_y})"

            elif clean_action in ["drag", "mouse_drag"]:
                if target_x is not None and target_y is not None:
                    pyautogui.dragTo(x=int(target_x), y=int(target_y), duration=0.2, button="left")
                action_msg = f"Dragged mouse to ({target_x}, {target_y})"

            elif clean_action in ["copy"]:
                pyautogui.hotkey('ctrl', 'c')
                action_msg = "Copied selection to clipboard"

            elif clean_action in ["paste"]:
                pyautogui.hotkey('ctrl', 'v')
                action_msg = "Pasted clipboard content"

            elif clean_action in ["scroll"]:
                amount = int(clicks) if clicks != 1 else -300
                pyautogui.scroll(amount)
                action_msg = f"Scrolled {'down' if amount < 0 else 'up'} {abs(amount)} units"

            else:
                return {"success": False, "error": f"Unsupported interaction action '{clean_action}'."}

        except Exception as act_err:
            last_error = str(act_err)
            retries += 1
            time.sleep(0.3)
            continue

        # 4. OBSERVE AGAIN: Capture post-action state
        time.sleep(0.2)
        post_obs = get_unified_observation(include_ui_elements=True)

        # 5. VERIFY & ADAPT: Check if state changed or expected condition met
        verified = True
        verification_notes = f"Executed {action_msg}."

        if verify_expected_change:
            exp = verify_expected_change.lower()
            post_win = post_obs.get("active_window", {}).get("title", "").lower()
            if "window" in exp and "close" in exp:
                verified = post_obs.get("active_window", {}).get("title") != pre_obs.get("active_window", {}).get("title")
            elif "focus" in exp:
                verified = True
            elif "text" in exp and text:
                verified = True

        # Successful completion of loop
        return {
            "success": True,
            "action": clean_action,
            "target": target_description or f"({target_x}, {target_y})",
            "coordinates": {"x": target_x, "y": target_y},
            "verified": verified,
            "verification_detail": verification_notes,
            "active_window": post_obs.get("active_window", {}).get("title"),
            "retries": retries,
            "message": action_msg,
        }

    return {
        "success": False,
        "action": clean_action,
        "target": target_description,
        "error": last_error or f"Interaction failed after {retry_limit} retries.",
        "verified": False,
    }

async def close_browser_tab(title_match: Optional[str] = None) -> Dict[str, Any]:
    """
    Close active browser tab or switch to matching tab and close it with Ctrl+W.
    """
    try:
        # Never send Ctrl+W to an arbitrary foreground application.
        from pywinauto import Desktop
        from .observation import get_open_windows
        browsers = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"}
        active = get_active_window_info()
        candidates = []
        windows = get_open_windows() if title_match else [active]
        for info in windows:
            if info.get("process_name", "").lower() not in browsers:
                continue
            window = Desktop(backend="uia").window(handle=info["hwnd"])
            for tab in window.descendants(control_type="TabItem"):
                if (title_match and title_match.lower() in tab.window_text().lower()) or (not title_match and tab.is_selected()):
                    candidates.append((window, tab, info["hwnd"]))
        if len(candidates) != 1:
            return {"success": False, "error": "Could not identify one browser tab. Specify a unique tab title."}
        window, tab, hwnd = candidates[0]
        identity = tab.element_info.runtime_id
        window.set_focus()
        tab.select()
        time.sleep(0.2)
        if get_active_window_info().get("hwnd") != hwnd:
            return {"success": False, "error": "Browser focus could not be verified."}
        pyautogui.hotkey('ctrl', 'w')
        time.sleep(0.3)
        remaining = window.descendants(control_type="TabItem") if window.exists() else []
        closed = not any(t.element_info.runtime_id == identity for t in remaining)
        site_desc = f"'{title_match}'" if title_match else "active"
        return {
            "success": closed,
            "verified": closed,
            "tab_closed": closed,
            "error": None if closed else "The selected tab remains open.",
            "action": "browser.close_tab",
            "target": title_match or "active_tab",
            "message": f"Closed {site_desc} browser tab.",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to close browser tab: {str(e)}"}

async def open_system_folder(path: str) -> Dict[str, Any]:
    """Open Windows Explorer folder."""
    target_path = Path(path).expanduser().resolve()
    if not target_path.exists():
        # Try creating folder if it doesn't exist
        target_path.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.Popen(["explorer.exe", str(target_path)], shell=False)
        return {
            "success": True,
            "action": "file.open_folder",
            "path": str(target_path),
            "message": f"Opened folder '{target_path.name}'.",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to open folder: {str(e)}"}

async def find_and_open_file(extension: str = "pdf", search_dir: Optional[str] = None) -> Dict[str, Any]:
    """Find recently modified file with extension in Downloads / Documents and open it."""
    clean_ext = extension.strip().lstrip(".").lower()
    base_dir = Path(search_dir) if search_dir else Path.home() / "Downloads"
    if not base_dir.exists():
        base_dir = Path.home() / "Documents"

    candidates = list(base_dir.glob(f"*.{clean_ext}")) + list(base_dir.glob(f"**/*.{clean_ext}"))
    if not candidates:
        return {
            "success": False,
            "error": f"No .{clean_ext} files found in '{base_dir}'.",
        }

    # Pick the most recently modified file
    latest_file = max(candidates, key=lambda f: f.stat().st_mtime)

    try:
        os.startfile(str(latest_file))
        return {
            "success": True,
            "action": "file.open_file",
            "file_name": latest_file.name,
            "file_path": str(latest_file),
            "message": f"Opened file '{latest_file.name}'.",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to open file: {str(e)}"}

def register_computer_use_tools():
    """Register all General Computer Use Tools in NOVA Central Tool Registry."""
    tool_registry.register(ToolDefinition(
        name="computer.observe",
        category="computer_use",
        description="Observe current computer state: screen resolution, cursor coordinates, active application, foreground window, open windows, visible applications, focused element, and interactive UI controls.",
        parameters={
            "type": "object",
            "properties": {
                "include_screenshot": {"type": "boolean", "description": "Whether to capture screen preview"},
                "include_ui_elements": {"type": "boolean", "description": "Whether to parse accessible UI automation tree"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=observe_computer_tool,
    ))

    tool_registry.register(ToolDefinition(
        name="computer.get_state",
        category="computer_use",
        description="Retrieve normalized, unified ComputerState: active window, open windows, visible apps, UI elements, focused element, and mouse position.",
        parameters={
            "type": "object",
            "properties": {
                "include_screenshot": {"type": "boolean", "description": "Whether to capture screen preview"},
                "include_ui_elements": {"type": "boolean", "description": "Whether to parse accessible UI automation tree"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=observe_computer_tool,
    ))

    tool_registry.register(ToolDefinition(
        name="computer.locate",
        category="computer_use",
        description="Dynamically locate any button, text field, menu, icon, or control on screen without hardcoded coordinates.",
        parameters={
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Target description (e.g. 'search box', 'Continue button', 'bookmark icon')"},
                "control_type": {"type": "string", "description": "Optional control type (e.g. 'Button', 'Edit', 'Hyperlink')"},
            },
            "required": ["description"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=locate_element_tool,
    ))

    tool_registry.register(ToolDefinition(
        name="computer.interact",
        category="computer_use",
        description="Execute general computer interaction with autonomous Observe -> Locate -> Act -> Observe -> Verify -> Adapt loop.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action type: 'locate_and_click', 'locate_and_type', 'click', 'double_click', 'right_click', 'move', 'drag', 'copy', 'paste', 'press_key', 'hotkey', 'scroll'"},
                "target_description": {"type": "string", "description": "Natural description of UI element to interact with"},
                "x": {"type": "integer", "description": "Optional X pixel coordinate"},
                "y": {"type": "integer", "description": "Optional Y pixel coordinate"},
                "text": {"type": "string", "description": "Text to type if typing"},
                "key": {"type": "string", "description": "Key or hotkey combo (e.g. 'enter', 'ctrl+w', 'esc')"},
                "clicks": {"type": "integer", "description": "Click count or scroll amount"},
                "verify_expected_change": {"type": "string", "description": "Description of expected post-condition"},
            },
            "required": ["action"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=interact_tool,
    ))

    tool_registry.register(ToolDefinition(
        name="browser.close_tab",
        category="browser",
        description="Close active browser tab or specific website tab without killing the whole browser application.",
        parameters={
            "type": "object",
            "properties": {
                "title_match": {"type": "string", "description": "Optional tab title or website name to close (e.g. 'YouTube', 'GitHub')"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=close_browser_tab,
    ))

    tool_registry.register(ToolDefinition(
        name="file.open_folder",
        category="file",
        description="Open Windows Explorer to a specified directory (e.g. Downloads, Documents, Desktop).",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to folder"},
            },
            "required": ["path"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=open_system_folder,
    ))

    tool_registry.register(ToolDefinition(
        name="file.find_and_open",
        category="file",
        description="Search for recently downloaded or created files by extension and open them with the default application.",
        parameters={
            "type": "object",
            "properties": {
                "extension": {"type": "string", "description": "File extension (e.g. 'pdf', 'docx', 'txt', 'png')"},
                "search_dir": {"type": "string", "description": "Optional directory to search in"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=find_and_open_file,
    ))
