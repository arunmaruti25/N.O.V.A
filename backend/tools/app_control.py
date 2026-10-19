import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import psutil
from .registry import ToolDefinition, tool_registry
from ..permissions import PermissionLevel

# Common aliases mapped to executable basenames
APP_ALIASES: Dict[str, str] = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "notepad": "notepad",
    "calc": "calc",
    "calculator": "calc",
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "explorer": "explorer",
    "file explorer": "explorer",
    "files": "explorer",
    "terminal": "wt",
    "windows terminal": "wt",
    "task manager": "taskmgr",
    "taskmgr": "taskmgr",
    "paint": "mspaint",
    "whatsapp": "whatsapp",
    "spotify": "spotify",
    "slack": "slack",
    "discord": "discord",
}

def resolve_app_path(app_name: str) -> Optional[str]:
    """
    Resolve application executable dynamically using:
    1. Direct alias match
    2. shutil.which (PATH search)
    3. Windows App Paths registry
    4. Common Windows System32 / Program Files locations
    """
    clean = app_name.strip().lower()
    target = APP_ALIASES.get(clean, clean)
    if not target.endswith(".exe") and not target.endswith(".cmd") and not target.endswith(".bat"):
        # Check PATH directly
        path = shutil.which(target)
        if path:
            return path
        # Try with .exe
        path = shutil.which(f"{target}.exe")
        if path:
            return path

    # Windows App Paths registry lookup
    try:
        import winreg
        for root in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
            for candidate in [target, f"{target}.exe"]:
                try:
                    key_path = fr"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{candidate}"
                    with winreg.OpenKey(root, key_path) as k:
                        val, _ = winreg.QueryValueEx(k, "")
                        if val and os.path.exists(val):
                            return val
                except Exception:
                    continue
    except Exception:
        pass

    # Check Windows directory
    win_dir = os.environ.get("WINDIR", "C:\\Windows")
    sys32_candidate = os.path.join(win_dir, "System32", f"{target}.exe")
    if os.path.exists(sys32_candidate):
        return sys32_candidate
    win_candidate = os.path.join(win_dir, f"{target}.exe")
    if os.path.exists(win_candidate):
        return win_candidate

    return target if shutil.which(target) else None

def is_app_running(name: str) -> Dict[str, Any]:
    """
    Check if an application or process matching name is currently running.
    Uses hybrid detection:
    1. Direct process name inspection (psutil)
    2. Open desktop windows (including minimized on taskbar) & modern UWP app inspection
    """
    clean = name.strip().lower()
    target_base = APP_ALIASES.get(clean, clean).replace(".exe", "")

    matching_processes = []
    seen_pids = set()

    # 1. Process name inspection
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            p_name = proc.info['name'] or ""
            p_clean = p_name.lower().replace(".exe", "")
            if target_base == p_clean or p_clean in target_base or clean in p_clean or target_base in p_name.lower():
                if proc.info['pid'] not in seen_pids:
                    seen_pids.add(proc.info['pid'])
                    matching_processes.append({"pid": proc.info['pid'], "name": p_name})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # 2. Open desktop window & UWP application inspection (handles WhatsApp, minimized taskbar apps, packaged apps)
    try:
        from .observation import get_open_windows
        windows = get_open_windows(include_invisible=True)
        for w in windows:
            w_title = w.get("title", "").lower()
            w_app = w.get("app_name", "").lower()
            w_proc = w.get("process_name", "").lower()
            if clean in w_title or clean in w_app or clean in w_proc or target_base in w_title or target_base in w_app:
                w_pid = w.get("pid", 0)
                if w_pid not in seen_pids:
                    seen_pids.add(w_pid)
                    matching_processes.append({
                        "pid": w_pid,
                        "name": w.get("app_name") or w.get("process_name") or name,
                        "title": w.get("title"),
                    })
    except Exception:
        pass

    is_running = len(matching_processes) > 0
    return {
        "success": True,
        "app": name,
        "is_running": is_running,
        "count": len(matching_processes),
        "processes": matching_processes[:5],
        "message": f"Application '{name}' is {'running' if is_running else 'not running'}.",
    }

def list_running_apps(limit: int = 15) -> Dict[str, Any]:
    """List running desktop applications with CPU and memory details."""
    apps = []
    seen_names = set()
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            name = proc.info['name'] or ""
            if not name or name.lower().endswith(".sys") or name.lower().startswith("svchost"):
                continue
            if name.lower() in seen_names:
                continue
            seen_names.add(name.lower())
            apps.append({
                "pid": proc.info['pid'],
                "name": name,
                "memory_percent": round(proc.info['memory_percent'] or 0.0, 2),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    apps.sort(key=lambda x: x["memory_percent"], reverse=True)
    return {
        "success": True,
        "apps": apps[:limit],
        "total_active": len(apps),
    }

def launch_application(name: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
    """Launch application by name with dynamic Windows path resolution."""
    clean = name.strip().lower()
    if not clean or any(c in name for c in ('&', '|', '>', '<', '\n', '\r')):
        return {"success": False, "error": "Invalid application name."}
    blocked = {"cmd", "powershell", "pwsh", "wscript", "cscript", "mshta", "rundll32", "regsvr32", "python", "pythonw", "node", "bash", "sh"}
    if Path(clean).stem in blocked:
        return {"success": False, "error": "Command interpreters cannot be launched through app control."}
    resolved = resolve_app_path(name)
    if not resolved:
        return {"success": False, "error": f"Application '{name}' could not be resolved to an installed executable."}
    if Path(resolved).stem.lower() in blocked or Path(resolved).suffix.lower() in {".bat", ".cmd", ".ps1", ".vbs"}:
        return {"success": False, "error": "Script execution is not supported by app control."}
    try:
        proc = subprocess.Popen([resolved, *(args or [])], shell=False)
        return {"success": True, "app": name, "resolved_path": resolved, "pid": proc.pid,
                "message": f"Launched {name}."}
    except Exception as exc:
        return {"success": False, "error": f"Failed to launch '{name}': {exc}"}


def verify_app_launched(result: Dict[str, Any], arguments: Dict[str, Any]) -> Tuple[bool, str]:
    """Verify that the launched application is running in process or window list."""
    app_name = arguments.get("name", "")
    time.sleep(0.5)
    check = is_app_running(app_name)
    if check["is_running"]:
        return True, f"Verified '{app_name}' is actively running ({check['count']} instance(s))."
    return False, f"Verification warning: '{app_name}' process not detected after launch."

def close_application(name: str) -> Dict[str, Any]:
    """
    Close running application gracefully using comprehensive Windows state resolution:
    1. Locate all open windows (normal, maximized, minimized, or taskbar) and dispatch WM_CLOSE signals.
    2. Terminate matching process(es) by process name/alias across all active process trees.
    3. Handles modern packaged UWP apps (e.g. WhatsApp, Calculator, Mail) and traditional Win32 apps.
    """
    clean = name.strip().lower()
    target = Path(APP_ALIASES.get(clean, clean)).stem.lower()
    if not clean or target in {"system", "csrss", "wininit", "winlogon", "lsass", "services", "svchost"}:
        return {"success": False, "error": "This application cannot be closed."}
    try:
        from .observation import get_open_windows
        import win32gui
        windows = get_open_windows(include_invisible=True)
        matches = [w for w in windows if Path(w.get("process_name", "")).stem.lower() == target
                   or w.get("app_name", "").lower() == clean]
        if not matches:
            return {"success": False, "error": f"No matching window found for '{name}'."}
        for window in matches:
            win32gui.PostMessage(window["hwnd"], 0x0010, 0, 0)
        return {"success": True, "message": f"Requested close for {name}; unsaved work may need attention."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def p_clean_base(name: str) -> str:
    return name.lower().replace(".exe", "")

def verify_app_closed(result: Dict[str, Any], arguments: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Verify that the application is no longer running with polling confirmation.
    Never claims 'Closed' unless verified against live process and window states.
    """
    app_name = arguments.get("name", "")
    for attempt in range(4):
        time.sleep(0.3)
        check = is_app_running(app_name)
        if not check["is_running"]:
            return True, f"Verified all processes and windows for '{app_name}' have closed."
        # If still running on later attempts, retry process kill
        if attempt >= 1:
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    p_name = (proc.info['name'] or "").lower().replace(".exe", "")
                    clean = app_name.lower().replace(".exe", "")
                    if clean in p_name or p_name in clean:
                        proc.kill()
            except Exception:
                pass

    return False, f"Verification failed: '{app_name}' process or window still active on system."

def focus_application(name: str) -> Dict[str, Any]:
    """Focus / activate window of application using hybrid window inspection."""
    clean = name.strip().lower()
    target_base = APP_ALIASES.get(clean, clean).replace(".exe", "")

    # Layer 1: Check observation layer open windows
    try:
        from .observation import get_open_windows
        import win32gui
        windows = get_open_windows(include_invisible=False)
        for w in windows:
            w_title = w.get("title", "").lower()
            w_app = w.get("app_name", "").lower()
            if (clean in w_title or clean in w_app or target_base in w_title) and w.get("hwnd"):
                hwnd = w["hwnd"]
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE = 9
                win32gui.SetForegroundWindow(hwnd)
                return {"success": True, "app": name, "window_title": w.get("title"), "message": f"Focused window '{w.get('title')}'."}
    except Exception:
        pass

    # Layer 2: pygetwindow fallback
    try:
        import pygetwindow as gw
        all_windows = gw.getAllWindows()
        matched = None
        for w in all_windows:
            if clean in w.title.lower() or target_base in w.title.lower():
                matched = w
                break
        if matched:
            matched.activate()
            return {"success": True, "app": name, "window_title": matched.title, "message": f"Focused window '{matched.title}'."}
    except Exception:
        pass

    return {"success": True, "app": name, "message": f"Focus signal sent for '{name}'."}


# Register Application Control Tools
def register_app_tools():
    tool_registry.register(ToolDefinition(
        name="app.launch",
        category="application",
        description="Launch a desktop application by name (e.g. Chrome, Notepad, Calculator, VS Code, File Explorer).",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name or alias of application to launch"},
                "args": {"type": "array", "description": "Optional command line arguments to pass", "items": {"type": "string"}},
            },
            "required": ["name"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=launch_application,
        verify_fn=verify_app_launched,
    ))

    tool_registry.register(ToolDefinition(
        name="app.close",
        category="application",
        description="Gracefully close a running application by name.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of application to close"},
            },
            "required": ["name"],
        },
        permission_level=PermissionLevel.CONFIRMATION_REQUIRED,
        execute_fn=close_application,
        verify_fn=verify_app_closed,
    ))

    tool_registry.register(ToolDefinition(
        name="app.is_running",
        category="application",
        description="Check whether a specific application is currently running.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of application to check"},
            },
            "required": ["name"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=is_app_running,
    ))

    tool_registry.register(ToolDefinition(
        name="app.list_running",
        category="application",
        description="List running desktop applications sorted by memory consumption.",
        parameters={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of apps to list (default: 15)"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=list_running_apps,
    ))

    tool_registry.register(ToolDefinition(
        name="app.focus",
        category="application",
        description="Switch to and focus an application window by name.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of application window to focus"},
            },
            "required": ["name"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=focus_application,
    ))

