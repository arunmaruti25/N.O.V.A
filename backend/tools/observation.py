import io
import os
import base64
import time
import psutil
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from PIL import Image, ImageDraw

from ..config import settings
from .vision import capture_screen

OBSERVATION_CACHE_DIR = settings.DATA_DIR / "observation"
OBSERVATION_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Common browser executable names
BROWSER_EXECUTABLES = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe", "vivaldi.exe"}

def get_cursor_position() -> Tuple[int, int]:
    """Get current mouse cursor position."""
    try:
        import pyautogui
        x, y = pyautogui.position()
        return int(x), int(y)
    except Exception:
        return 0, 0

def get_screen_metrics() -> Dict[str, int]:
    """Get primary monitor screen dimensions."""
    try:
        import pyautogui
        w, h = pyautogui.size()
        return {"width": int(w), "height": int(h)}
    except Exception:
        return {"width": 1920, "height": 1080}

def get_active_window_info() -> Dict[str, Any]:
    """
    Get detailed information about the currently active foreground window:
    HWND, title, process name, PID, position, size, and window states.
    """
    info = {
        "hwnd": 0,
        "title": "",
        "process_name": "",
        "pid": 0,
        "rect": {"left": 0, "top": 0, "right": 0, "bottom": 0, "width": 0, "height": 0},
        "is_active": True,
        "is_maximized": False,
        "is_minimized": False,
        "is_browser": False,
    }

    try:
        import win32gui
        import win32process

        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            info["hwnd"] = hwnd
            title = win32gui.GetWindowText(hwnd).strip()
            info["title"] = title

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            info["pid"] = pid
            if pid:
                try:
                    p = psutil.Process(pid)
                    info["process_name"] = p.name()
                    if p.name().lower() in BROWSER_EXECUTABLES:
                        info["is_browser"] = True
                except Exception:
                    pass

            rect = win32gui.GetWindowRect(hwnd)
            l, t, r, b = rect
            info["rect"] = {
                "left": l,
                "top": t,
                "right": r,
                "bottom": b,
                "width": max(0, r - l),
                "height": max(0, b - t),
            }
            info["is_minimized"] = win32gui.IsIconic(hwnd) != 0
            info["is_maximized"] = win32gui.IsZoomed(hwnd) != 0
    except Exception:
        # Fallback using pygetwindow if win32gui had an issue
        try:
            import pygetwindow as gw
            active_w = gw.getActiveWindow()
            if active_w:
                info["title"] = active_w.title.strip()
                info["rect"] = {
                    "left": active_w.left,
                    "top": active_w.top,
                    "right": active_w.right,
                    "bottom": active_w.bottom,
                    "width": active_w.width,
                    "height": active_w.height,
                }
                info["is_maximized"] = active_w.isMaximized
                info["is_minimized"] = active_w.isMinimized
        except Exception:
            pass

    return info

def extract_browser_state(active_win: Dict[str, Any]) -> Dict[str, Any]:
    """Extract browser tab title and URL where available from window title and heuristics."""
    browser_state = {
        "is_browser": active_win.get("is_browser", False),
        "url": "",
        "tab_title": "",
        "browser_name": active_win.get("process_name", ""),
    }
    if not active_win.get("is_browser"):
        return browser_state

    full_title = active_win.get("title", "")
    tab_title = full_title
    for b_suffix in [" - Google Chrome", " - Microsoft Edge", " - Mozilla Firefox", " - Brave", " - Opera", " - Vivaldi"]:
        if b_suffix in full_title:
            tab_title = full_title.split(b_suffix)[0].strip()
            break
    browser_state["tab_title"] = tab_title

    # Known websites mapping for active tab
    common_sites = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "github": "https://www.github.com",
        "reddit": "https://www.reddit.com",
        "twitter": "https://www.x.com",
        "x": "https://www.x.com",
        "wikipedia": "https://www.wikipedia.org",
    }
    for site_key, site_url in common_sites.items():
        if site_key in tab_title.lower():
            browser_state["url"] = site_url
            break

    return browser_state

def list_visible_windows(limit: int = 15) -> List[Dict[str, Any]]:
    """List visible, non-empty top-level windows currently open."""
    windows = []
    try:
        import win32gui
        import win32process

        foreground_hwnd = win32gui.GetForegroundWindow()

        def enum_handler(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).strip()
                if title and title not in ["Program Manager", "Default IME", "MSCTFIME UI"]:
                    l, t, r, b = win32gui.GetWindowRect(hwnd)
                    w, h = r - l, b - t
                    if w > 30 and h > 30:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        p_name = ""
                        if pid:
                            try:
                                p_name = psutil.Process(pid).name()
                            except Exception:
                                pass
                        extra.append({
                            "hwnd": hwnd,
                            "title": title,
                            "process_name": p_name,
                            "pid": pid,
                            "is_focused": hwnd == foreground_hwnd,
                            "rect": {"left": l, "top": t, "right": r, "bottom": b, "width": w, "height": h},
                        })

        win32gui.EnumWindows(enum_handler, windows)
    except Exception:
        # Fallback to pygetwindow
        try:
            import pygetwindow as gw
            for w in gw.getAllWindows():
                t = w.title.strip()
                if t and w.width > 30 and w.height > 30:
                    windows.append({
                        "title": t,
                        "is_focused": w.isActive,
                        "rect": {"left": w.left, "top": w.top, "right": w.right, "bottom": w.bottom, "width": w.width, "height": w.height},
                    })
        except Exception:
            pass

    # Process inspection fallback for headless/service/subshell sessions
    if not windows:
        known_gui = {
            "chrome.exe": "Google Chrome",
            "msedge.exe": "Microsoft Edge",
            "notepad.exe": "Notepad",
            "explorer.exe": "File Explorer",
            "code.exe": "Visual Studio Code",
        }
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                pname = (proc.info['name'] or '').lower()
                if pname in known_gui:
                    windows.append({
                        "hwnd": 0,
                        "title": known_gui[pname],
                        "process_name": pname,
                        "pid": proc.info['pid'],
                        "is_focused": False,
                        "rect": {"left": 0, "top": 0, "right": 1920, "bottom": 1080, "width": 1920, "height": 1080},
                    })
            except Exception:
                pass

    return windows[:limit]

def extract_active_ui_elements(max_elements: int = 35) -> List[Dict[str, Any]]:
    """
    Extract interactive and meaningful UI elements from the foreground window
    using Windows UI Automation (buttons, input edits, links, menu items, tabs, check boxes).
    """
    elements = []
    try:
        import uiautomation as auto
        foreground = auto.GetForegroundControl()
        if not foreground:
            return elements

        # Walk controls in active window
        seen = set()

        def walk(control, depth=0):
            if len(elements) >= max_elements or depth > 6:
                return

            try:
                name = (control.Name or "").strip()
                c_type = control.ControlTypeName
                rect = control.BoundingRectangle
                is_enabled = control.IsEnabled

                # Filter for actionable / meaningful UI elements
                actionable_types = {
                    "ButtonControl", "EditControl", "HyperlinkControl", "MenuItemControl",
                    "TabItemControl", "CheckBoxControl", "RadioButtonControl", "ComboBoxControl",
                    "ListItemControl", "TreeItemControl", "ToolBarControl", "DocumentControl",
                    "TextControl"
                }

                if c_type in actionable_types and rect and is_enabled:
                    w = rect.width()
                    h = rect.height()
                    if w > 4 and h > 4:
                        cx = rect.left + w // 2
                        cy = rect.top + h // 2
                        elem_key = (name, c_type, cx, cy)
                        if elem_key not in seen:
                            seen.add(elem_key)
                            clean_type = c_type.replace("Control", "")
                            elements.append({
                                "name": name,
                                "type": clean_type,
                                "bounding_box": {
                                    "left": int(rect.left),
                                    "top": int(rect.top),
                                    "right": int(rect.right),
                                    "bottom": int(rect.bottom),
                                    "width": int(w),
                                    "height": int(h),
                                    "center_x": int(cx),
                                    "center_y": int(cy),
                                },
                                "is_focused": getattr(control, "HasKeyboardFocus", False),
                                "automation_id": getattr(control, "AutomationId", ""),
                            })

                for child in control.GetChildren():
                    walk(child, depth + 1)
            except Exception:
                pass

        walk(foreground)
    except Exception:
        pass

    return elements

def format_ui_context_summary(observation: Dict[str, Any]) -> str:
    """Format a compact, high-signal summary of the computer state for AI prompts."""
    lines = []
    screen = observation.get("screen", {})
    lines.append(f"Screen: {screen.get('width', 1920)}x{screen.get('height', 1080)} | Cursor: ({screen.get('cursor_x', 0)}, {screen.get('cursor_y', 0)})")
    
    act_win = observation.get("active_window", {})
    if act_win.get("title"):
        lines.append(f"Active Window: \"{act_win['title']}\" (Process: {act_win.get('process_name', 'unknown')}, PID: {act_win.get('pid', 0)})")
    else:
        lines.append("Active Window: Desktop / No foreground window")

    browser_state = observation.get("browser_state", {})
    if browser_state.get("is_browser"):
        tab_info = browser_state.get("tab_title") or "Active Tab"
        url_info = f" ({browser_state['url']})" if browser_state.get("url") else ""
        lines.append(f"Browser State: \"{tab_info}\"{url_info} [App: {browser_state.get('browser_name')}]")

    vis_wins = observation.get("visible_windows", [])
    if vis_wins:
        other_titles = [w['title'] for w in vis_wins if w.get('title') and w.get('title') != act_win.get('title')]
        if other_titles:
            lines.append(f"Other Visible Windows: {', '.join(f'\"{t}\"' for t in other_titles[:6])}")

    ui_elems = observation.get("ui_elements", [])
    if ui_elems:
        elem_strings = []
        for el in ui_elems[:20]:
            label = el.get("name") or el.get("automation_id") or "unnamed"
            bbox = el.get("bounding_box", {})
            cx, cy = bbox.get("center_x", 0), bbox.get("center_y", 0)
            elem_strings.append(f"[{el['type']} \"{label}\" @ ({cx},{cy})]")
        lines.append("Visible UI Controls:\n  " + "\n  ".join(elem_strings))

    return "\n".join(lines)

def get_unified_observation(
    include_screenshot: bool = False,
    include_ui_elements: bool = True,
    save_screenshot_to_disk: bool = False,
) -> Dict[str, Any]:
    """
    Unified Computer Observation Interface:
    Captures complete context: screen resolution, cursor coordinates,
    active application, active window, visible top-level windows,
    browser state if active, and accessible UI controls with bounding coordinates.
    """
    screen_size = get_screen_metrics()
    cur_x, cur_y = get_cursor_position()
    active_win = get_active_window_info()
    browser_st = extract_browser_state(active_win)
    visible_wins = list_windows_summary = list_visible_windows(limit=12)

    ui_elements = extract_active_ui_elements(max_elements=30) if include_ui_elements else []

    screenshot_info = {}
    if include_screenshot:
        screenshot_info = capture_screen(save_to_disk=save_screenshot_to_disk, return_base64=True)

    obs = {
        "success": True,
        "timestamp": time.time(),
        "screen": {
            "width": screen_size["width"],
            "height": screen_size["height"],
            "cursor_x": cur_x,
            "cursor_y": cur_y,
        },
        "active_window": active_win,
        "active_app": active_win.get("process_name", ""),
        "browser_state": browser_st,
        "visible_windows": visible_wins,
        "ui_elements": ui_elements,
        "ui_elements_count": len(ui_elements),
        "screenshot": screenshot_info,
    }

    obs["context_summary"] = format_ui_context_summary(obs)
    obs["message"] = f"Observed computer state: Active window '{active_win.get('title', 'None')}' with {len(ui_elements)} visible UI elements."
    return obs
