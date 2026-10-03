import io
import os
import base64
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ImageDraw
import psutil

from ..config import settings
from .vision import capture_screen

OBSERVATION_CACHE_DIR = settings.DATA_DIR / "observation"
OBSERVATION_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Common browser executable names
BROWSER_EXECUTABLES = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe", "vivaldi.exe"}

# Common Windows application name mappings
APP_NAME_MAPPINGS = {
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge",
    "firefox.exe": "Mozilla Firefox",
    "brave.exe": "Brave Browser",
    "opera.exe": "Opera Browser",
    "code.exe": "Visual Studio Code",
    "notepad.exe": "Notepad",
    "calc.exe": "Calculator",
    "calculatorapp.exe": "Calculator",
    "explorer.exe": "File Explorer",
    "cmd.exe": "Command Prompt",
    "powershell.exe": "Windows PowerShell",
    "windowsterminal.exe": "Windows Terminal",
    "wt.exe": "Windows Terminal",
    "taskmgr.exe": "Task Manager",
    "mspaint.exe": "Paint",
    "whatsapp.exe": "WhatsApp",
    "whatsappdesktop.exe": "WhatsApp",
    "spotify.exe": "Spotify",
    "slack.exe": "Slack",
    "discord.exe": "Discord",
    "teams.exe": "Microsoft Teams",
}

# ─────────────────────────────────────────────────────────────
# 1. FORMAL COMPUTER STATE DATA STRUCTURES
# ─────────────────────────────────────────────────────────────

from dataclasses import dataclass, field

@dataclass
class UIElementInfo:
    """Structured representation of an actionable or informational UI element."""
    name: str
    control_type: str = ""
    automation_id: str = ""
    bounding_box: Dict[str, int] = field(default_factory=dict)  # left, top, right, bottom, width, height, center_x, center_y
    is_focused: bool = False
    is_enabled: bool = True
    value: Optional[str] = None
    class_name: Optional[str] = None
    help_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.control_type,
            "control_type": self.control_type,
            "automation_id": self.automation_id,
            "bounding_box": self.bounding_box,
            "is_focused": self.is_focused,
            "is_enabled": self.is_enabled,
            "value": self.value,
            "class_name": self.class_name,
            "help_text": self.help_text,
        }

@dataclass
class WindowInfo:
    """Structured representation of an OS window."""
    hwnd: int
    title: str
    process_name: str
    pid: int
    rect: Dict[str, int] = field(default_factory=dict)
    is_active: bool = False
    is_visible: bool = True
    is_minimized: bool = False
    is_maximized: bool = False
    is_uwp: bool = False
    app_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hwnd": self.hwnd,
            "title": self.title,
            "process_name": self.process_name,
            "pid": self.pid,
            "rect": self.rect,
            "is_active": self.is_active,
            "is_visible": self.is_visible,
            "is_minimized": self.is_minimized,
            "is_maximized": self.is_maximized,
            "is_uwp": self.is_uwp,
            "app_name": self.app_name,
        }

@dataclass
class ComputerState:
    """
    Unified, normalized representation of current Windows computer state:
    OS state + Windows UI Automation + Vision.
    """
    timestamp: float
    screen: Dict[str, int]            # width, height
    mouse_position: Tuple[int, int]   # x, y
    active_window: WindowInfo
    open_windows: List[WindowInfo]
    visible_applications: List[Dict[str, Any]]
    running_applications: List[str]
    ui_elements: List[UIElementInfo]
    focused_element: Optional[UIElementInfo]
    browser_state: Dict[str, Any]
    screenshot: Dict[str, Any]
    context_summary: str
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def visible_apps(self) -> List[str]:
        res = []
        for app in self.visible_applications:
            if isinstance(app, dict):
                res.append(app.get("name") or app.get("process_name") or "")
            else:
                res.append(str(app))
        return res

    @property
    def running_apps(self) -> List[str]:
        return self.running_applications

    def to_dict(self) -> Dict[str, Any]:
        base = {
            "timestamp": self.timestamp,
            "screen": self.screen,
            "mouse_position": {"x": self.mouse_position[0], "y": self.mouse_position[1]},
            "cursor_position": {"x": self.mouse_position[0], "y": self.mouse_position[1]},
            "active_window": self.active_window.to_dict() if self.active_window else {},
            "active_app": self.active_window.process_name if self.active_window else "",
            "open_windows": [w.to_dict() for w in self.open_windows],
            "visible_windows": [w.to_dict() for w in self.open_windows if w.is_visible and not w.is_minimized],
            "visible_applications": self.visible_applications,
            "visible_apps": self.visible_apps,
            "running_applications": self.running_applications,
            "running_apps": self.running_applications,
            "ui_elements": [e.to_dict() for e in self.ui_elements],
            "ui_elements_count": len(self.ui_elements),
            "focused_element": self.focused_element.to_dict() if self.focused_element else None,
            "browser_state": self.browser_state,
            "screenshot": self.screenshot,
            "context_summary": self.context_summary,
            "message": f"Observed computer state: Active window '{self.active_window.title if self.active_window else 'None'}' with {len(self.ui_elements)} visible UI elements.",
            "success": True,
        }
        if self.extra:
            base.update(self.extra)
        return base


# ─────────────────────────────────────────────────────────────
# 2. WINDOW & UWP HOST RESOLUTION HELPERS
# ─────────────────────────────────────────────────────────────

def resolve_app_name_from_process_or_title(process_name: str, title: str) -> str:
    """Infer human-friendly application name from executable name or window title."""
    clean_proc = (process_name or "").lower()
    if clean_proc in APP_NAME_MAPPINGS:
        return APP_NAME_MAPPINGS[clean_proc]

    # Check title heuristics
    clean_title = (title or "").lower()
    if "whatsapp" in clean_title or "whatsapp" in clean_proc:
        return "WhatsApp"
    elif "chrome" in clean_title or "chrome" in clean_proc:
        return "Google Chrome"
    elif "edge" in clean_title or "msedge" in clean_proc:
        return "Microsoft Edge"
    elif "visual studio code" in clean_title or " - code" in clean_title:
        return "Visual Studio Code"
    elif "notepad" in clean_title:
        return "Notepad"
    elif "calculator" in clean_title:
        return "Calculator"
    elif "file explorer" in clean_title:
        return "File Explorer"

    # Default to base process name without extension capitalized
    base = clean_proc.replace(".exe", "")
    return base.capitalize() if base else "Application"

def resolve_uwp_real_process(hwnd: int, title: str = "") -> Tuple[str, int, str]:
    """
    Resolve the real underlying UWP application when a window is hosted inside
    Windows ApplicationFrameHost.exe (e.g. WhatsApp, Calculator, Mail).
    Returns (real_process_name, real_pid, real_app_name).
    """
    try:
        import uiautomation as auto
        ctrl = auto.ControlFromHandle(hwnd)
        if ctrl:
            # Check direct or children controls for distinct ProcessId
            for child in ctrl.GetChildren():
                c_pid = getattr(child, "ProcessId", 0)
                if c_pid and c_pid != 0:
                    try:
                        p = psutil.Process(c_pid)
                        pname = p.name()
                        if pname.lower() != "applicationframehost.exe":
                            app_name = resolve_app_name_from_process_or_title(pname, ctrl.Name)
                            return pname, c_pid, app_name
                    except Exception:
                        pass
    except Exception:
        pass

    # Heuristic fallback based on title
    if title:
        t_lower = title.lower()
        if "whatsapp" in t_lower:
            return "WhatsApp.exe", 0, "WhatsApp"
        elif "calculator" in t_lower:
            return "CalculatorApp.exe", 0, "Calculator"
        elif "spotify" in t_lower:
            return "Spotify.exe", 0, "Spotify"
        elif "slack" in t_lower:
            return "slack.exe", 0, "Slack"
        elif "discord" in t_lower:
            return "Discord.exe", 0, "Discord"

    return "", 0, ""


# ─────────────────────────────────────────────────────────────
# 3. NATIVE OS PERCEPTION PRIMITIVES
# ─────────────────────────────────────────────────────────────

def get_cursor_position() -> Tuple[int, int]:
    """Get current mouse cursor position (X, Y)."""
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
    HWND, title, process name, PID, position, size, window states, and UWP attributes.
    """
    info = {
        "hwnd": 0,
        "title": "",
        "process_name": "",
        "pid": 0,
        "rect": {"left": 0, "top": 0, "right": 0, "bottom": 0, "width": 0, "height": 0},
        "is_active": True,
        "is_visible": True,
        "is_maximized": False,
        "is_minimized": False,
        "is_browser": False,
        "is_uwp": False,
        "app_name": "",
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
                    p_name = p.name()
                    info["process_name"] = p_name
                    if p_name.lower() in BROWSER_EXECUTABLES:
                        info["is_browser"] = True

                    # UWP Frame Host resolution
                    if p_name.lower() == "applicationframehost.exe":
                        info["is_uwp"] = True
                        real_p, real_pid, real_app = resolve_uwp_real_process(hwnd)
                        if real_p:
                            info["process_name"] = real_p
                            info["pid"] = real_pid
                            info["app_name"] = real_app
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

            if not info["app_name"]:
                info["app_name"] = resolve_app_name_from_process_or_title(info["process_name"], title)

    except Exception:
        # Fallback using pygetwindow
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
                info["app_name"] = resolve_app_name_from_process_or_title("", active_w.title)
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

def get_open_windows(include_invisible: bool = False, limit: int = 40) -> List[Dict[str, Any]]:
    """
    Enumerate all open desktop windows with comprehensive OS attributes:
    HWND, title, process name, PID, position, size, visibility, minimized/maximized state,
    and UWP modern packaged application resolution.
    """
    windows = []
    foreground_hwnd = 0

    try:
        import win32gui
        import win32process
        foreground_hwnd = win32gui.GetForegroundWindow()

        def enum_handler(hwnd, extra):
            is_vis = win32gui.IsWindowVisible(hwnd) != 0
            if not is_vis and not include_invisible:
                return

            title = win32gui.GetWindowText(hwnd).strip()
            # Filter out internal/system placeholder windows unless explicitly requested
            if not title or title in ["Program Manager", "Default IME", "MSCTFIME UI"]:
                return

            l, t, r, b = win32gui.GetWindowRect(hwnd)
            w, h = r - l, b - t
            is_min = win32gui.IsIconic(hwnd) != 0
            is_max = win32gui.IsZoomed(hwnd) != 0

            # Only include windows with reasonable dimensions or minimized state
            if (w > 30 and h > 30) or is_min:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                p_name = ""
                is_uwp = False
                app_name = ""

                if pid:
                    try:
                        p = psutil.Process(pid)
                        p_name = p.name()
                        if p_name.lower() == "applicationframehost.exe":
                            is_uwp = True
                            real_p, real_pid, real_app = resolve_uwp_real_process(hwnd)
                            if real_p:
                                p_name = real_p
                                pid = real_pid
                                app_name = real_app
                    except Exception:
                        pass

                if not app_name:
                    app_name = resolve_app_name_from_process_or_title(p_name, title)

                extra.append({
                    "hwnd": hwnd,
                    "title": title,
                    "process_name": p_name,
                    "pid": pid,
                    "app_name": app_name,
                    "is_active": hwnd == foreground_hwnd,
                    "is_visible": is_vis,
                    "is_minimized": is_min,
                    "is_maximized": is_max,
                    "is_uwp": is_uwp,
                    "rect": {"left": l, "top": t, "right": r, "bottom": b, "width": w, "height": h},
                })

        win32gui.EnumWindows(enum_handler, windows)
    except Exception:
        # Fallback to pygetwindow
        try:
            import pygetwindow as gw
            for w in gw.getAllWindows():
                t = w.title.strip()
                if t and (w.width > 30 or w.isMinimized):
                    app_n = resolve_app_name_from_process_or_title("", t)
                    windows.append({
                        "hwnd": getattr(w, "_hWnd", 0),
                        "title": t,
                        "process_name": "",
                        "pid": 0,
                        "app_name": app_n,
                        "is_active": getattr(w, "isActive", False),
                        "is_visible": getattr(w, "visible", True),
                        "is_minimized": getattr(w, "isMinimized", False),
                        "is_maximized": getattr(w, "isMaximized", False),
                        "is_uwp": False,
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
            "whatsapp.exe": "WhatsApp",
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
                        "app_name": known_gui[pname],
                        "is_active": False,
                        "is_visible": True,
                        "is_minimized": False,
                        "is_maximized": False,
                        "is_uwp": False,
                        "rect": {"left": 0, "top": 0, "right": 1920, "bottom": 1080, "width": 1920, "height": 1080},
                    })
            except Exception:
                pass

    return windows[:limit]

def list_visible_windows(limit: int = 15) -> List[Dict[str, Any]]:
    """Legacy compatibility helper listing visible, non-empty top-level windows."""
    open_wins = get_open_windows(include_invisible=False, limit=limit)
    return [w for w in open_wins if w.get("is_visible") and not w.get("is_minimized")][:limit]

def get_visible_applications(open_windows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group visible desktop windows by application name."""
    apps_dict = {}
    for w in open_windows:
        if not w.get("is_visible") or w.get("is_minimized"):
            continue
        app_name = w.get("app_name") or w.get("process_name") or "Application"
        if app_name not in apps_dict:
            apps_dict[app_name] = {
                "name": app_name,
                "process_name": w.get("process_name", ""),
                "pid": w.get("pid", 0),
                "is_active": w.get("is_active", False),
                "window_count": 0,
                "windows": [],
            }
        apps_dict[app_name]["window_count"] += 1
        apps_dict[app_name]["windows"].append({
            "title": w.get("title", ""),
            "hwnd": w.get("hwnd", 0),
            "rect": w.get("rect", {}),
            "is_active": w.get("is_active", False),
        })
        if w.get("is_active"):
            apps_dict[app_name]["is_active"] = True

    return list(apps_dict.values())

def get_running_applications(limit: int = 60) -> List[str]:
    """Retrieve distinct names of active running desktop applications/processes."""
    app_names = set()
    for proc in psutil.process_iter(['name']):
        try:
            name = (proc.info['name'] or '').strip()
            if not name:
                continue
            lower_name = name.lower()
            if lower_name.endswith(".sys") or lower_name.startswith("svchost") or lower_name.startswith("system"):
                continue
            app_names.add(name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return sorted(list(app_names))[:limit]


# ─────────────────────────────────────────────────────────────
# 4. WINDOWS UI AUTOMATION LAYER (ELEMENTS & FOCUS)
# ─────────────────────────────────────────────────────────────

def get_focused_element() -> Optional[Dict[str, Any]]:
    """
    Capture the specific UI element that currently holds keyboard focus
    via Windows UI Automation (search inputs, text areas, focused buttons, etc.).
    """
    try:
        import uiautomation as auto
        focused = auto.GetFocusedControl()
        if not focused:
            return None

        rect = focused.BoundingRectangle
        w = rect.width() if rect else 0
        h = rect.height() if rect else 0
        cx = rect.left + w // 2 if rect else 0
        cy = rect.top + h // 2 if rect else 0
        c_type = (focused.ControlTypeName or "Control").replace("Control", "")

        val = None
        try:
            val_pat = focused.GetValuePattern()
            if val_pat:
                val = val_pat.Value
        except Exception:
            pass

        return {
            "name": (focused.Name or "").strip(),
            "type": c_type,
            "control_type": c_type,
            "automation_id": getattr(focused, "AutomationId", ""),
            "bounding_box": {
                "left": int(rect.left) if rect else 0,
                "top": int(rect.top) if rect else 0,
                "right": int(rect.right) if rect else 0,
                "bottom": int(rect.bottom) if rect else 0,
                "width": int(w),
                "height": int(h),
                "center_x": int(cx),
                "center_y": int(cy),
            },
            "is_focused": True,
            "is_enabled": getattr(focused, "IsEnabled", True),
            "value": val,
            "class_name": getattr(focused, "ClassName", ""),
            "help_text": getattr(focused, "HelpText", ""),
        }
    except Exception:
        return None

def extract_active_ui_elements(max_elements: int = 40) -> List[Dict[str, Any]]:
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

        seen = set()

        def walk(control, depth=0):
            if len(elements) >= max_elements or depth > 6:
                return

            try:
                name = (control.Name or "").strip()
                c_type = control.ControlTypeName or ""
                rect = control.BoundingRectangle
                is_enabled = getattr(control, "IsEnabled", True)

                # Filter for actionable / meaningful UI elements
                actionable_types = {
                    "ButtonControl", "EditControl", "HyperlinkControl", "MenuItemControl",
                    "TabItemControl", "CheckBoxControl", "RadioButtonControl", "ComboBoxControl",
                    "ListItemControl", "TreeItemControl", "ToolBarControl", "DocumentControl",
                    "TextControl", "SplitButtonControl", "CustomControl"
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

                            val = None
                            try:
                                val_pat = control.GetValuePattern()
                                if val_pat:
                                    val = val_pat.Value
                            except Exception:
                                pass

                            elements.append({
                                "name": name,
                                "type": clean_type,
                                "control_type": clean_type,
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
                                "is_enabled": is_enabled,
                                "value": val,
                                "automation_id": getattr(control, "AutomationId", ""),
                                "class_name": getattr(control, "ClassName", ""),
                                "help_text": getattr(control, "HelpText", ""),
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
    mouse = observation.get("mouse_position") or observation.get("cursor_position") or {}
    mx = mouse.get("x", 0) if isinstance(mouse, dict) else (mouse[0] if isinstance(mouse, (list, tuple)) else 0)
    my = mouse.get("y", 0) if isinstance(mouse, dict) else (mouse[1] if isinstance(mouse, (list, tuple)) else 0)

    lines.append(f"Screen: {screen.get('width', 1920)}x{screen.get('height', 1080)} | Cursor: ({mx}, {my})")

    act_win = observation.get("active_window", {})
    if act_win.get("title"):
        app_lbl = act_win.get("app_name") or act_win.get("process_name") or "unknown"
        lines.append(f"Active Window: \"{act_win['title']}\" (App: {app_lbl}, PID: {act_win.get('pid', 0)})")
    else:
        lines.append("Active Window: Desktop / No foreground window")

    focused_el = observation.get("focused_element")
    if focused_el:
        lines.append(f"Keyboard Focus: [{focused_el.get('type', 'Control')} \"{focused_el.get('name', 'unnamed')}\"]")

    browser_state = observation.get("browser_state", {})
    if browser_state.get("is_browser"):
        tab_info = browser_state.get("tab_title") or "Active Tab"
        url_info = f" ({browser_state['url']})" if browser_state.get("url") else ""
        lines.append(f"Browser State: \"{tab_info}\"{url_info} [App: {browser_state.get('browser_name')}]")

    vis_apps = observation.get("visible_applications", [])
    if vis_apps:
        app_names = [a["name"] for a in vis_apps if a.get("name")]
        lines.append(f"Visible Applications: {', '.join(app_names[:8])}")

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


# ─────────────────────────────────────────────────────────────
# 5. UNIFIED COMPUTER STATE GENERATOR (PHASE A CORE)
# ─────────────────────────────────────────────────────────────

def get_computer_state(
    include_screenshot: bool = False,
    include_ui_elements: bool = True,
    save_screenshot_to_disk: bool = False,
) -> ComputerState:
    """
    Construct the normalized, typed ComputerState representation combining:
    OS State (win32gui, psutil) + Windows UI Automation (uiautomation) + Vision (mss).
    """
    screen_size = get_screen_metrics()
    cur_x, cur_y = get_cursor_position()
    raw_active_win = get_active_window_info()

    active_win = WindowInfo(
        hwnd=raw_active_win.get("hwnd", 0),
        title=raw_active_win.get("title", ""),
        process_name=raw_active_win.get("process_name", ""),
        pid=raw_active_win.get("pid", 0),
        rect=raw_active_win.get("rect", {}),
        is_active=True,
        is_visible=raw_active_win.get("is_visible", True),
        is_minimized=raw_active_win.get("is_minimized", False),
        is_maximized=raw_active_win.get("is_maximized", False),
        is_uwp=raw_active_win.get("is_uwp", False),
        app_name=raw_active_win.get("app_name", ""),
    )

    browser_st = extract_browser_state(raw_active_win)
    raw_open_windows = get_open_windows(include_invisible=False, limit=30)
    open_windows = [
        WindowInfo(
            hwnd=w.get("hwnd", 0),
            title=w.get("title", ""),
            process_name=w.get("process_name", ""),
            pid=w.get("pid", 0),
            rect=w.get("rect", {}),
            is_active=w.get("is_active", False),
            is_visible=w.get("is_visible", True),
            is_minimized=w.get("is_minimized", False),
            is_maximized=w.get("is_maximized", False),
            is_uwp=w.get("is_uwp", False),
            app_name=w.get("app_name", ""),
        )
        for w in raw_open_windows
    ]

    visible_apps = get_visible_applications(raw_open_windows)
    running_apps = get_running_applications(limit=50)

    raw_ui_elems = extract_active_ui_elements(max_elements=35) if include_ui_elements else []
    ui_elements = [
        UIElementInfo(
            name=e.get("name", ""),
            control_type=e.get("type", "Control"),
            automation_id=e.get("automation_id", ""),
            bounding_box=e.get("bounding_box", {}),
            is_focused=e.get("is_focused", False),
            is_enabled=e.get("is_enabled", True),
            value=e.get("value"),
            class_name=e.get("class_name"),
            help_text=e.get("help_text"),
        )
        for e in raw_ui_elems
    ]

    raw_focused = get_focused_element()
    focused_element = UIElementInfo(
        name=raw_focused.get("name", ""),
        control_type=raw_focused.get("type", "Control"),
        automation_id=raw_focused.get("automation_id", ""),
        bounding_box=raw_focused.get("bounding_box", {}),
        is_focused=True,
        is_enabled=raw_focused.get("is_enabled", True),
        value=raw_focused.get("value"),
        class_name=raw_focused.get("class_name"),
        help_text=raw_focused.get("help_text"),
    ) if raw_focused else None

    screenshot_info = {}
    if include_screenshot:
        screenshot_info = capture_screen(save_to_disk=save_screenshot_to_disk, return_base64=True)

    # Build context summary dictionary for text synthesis
    summary_dict = {
        "screen": screen_size,
        "mouse_position": {"x": cur_x, "y": cur_y},
        "active_window": raw_active_win,
        "browser_state": browser_st,
        "visible_applications": visible_apps,
        "ui_elements": raw_ui_elems,
        "focused_element": raw_focused,
    }
    context_summary = format_ui_context_summary(summary_dict)

    return ComputerState(
        timestamp=time.time(),
        screen=screen_size,
        mouse_position=(cur_x, cur_y),
        active_window=active_win,
        open_windows=open_windows,
        visible_applications=visible_apps,
        running_applications=running_apps,
        ui_elements=ui_elements,
        focused_element=focused_element,
        browser_state=browser_st,
        screenshot=screenshot_info,
        context_summary=context_summary,
    )

def get_unified_observation(
    include_screenshot: bool = False,
    include_ui_elements: bool = True,
    save_screenshot_to_disk: bool = False,
) -> Dict[str, Any]:
    """
    Unified Computer Observation Interface (Backward compatible with all existing callers & tests).
    Returns complete ComputerState as dictionary with all existing and enriched perception keys.
    """
    state = get_computer_state(
        include_screenshot=include_screenshot,
        include_ui_elements=include_ui_elements,
        save_screenshot_to_disk=save_screenshot_to_disk,
    )
    return state.to_dict()
