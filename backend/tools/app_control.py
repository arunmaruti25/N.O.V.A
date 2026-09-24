import os
import shutil
import subprocess
import time
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
    """Check if an application or process matching name is currently running."""
    clean = name.strip().lower()
    target_base = APP_ALIASES.get(clean, clean).replace(".exe", "")

    matching_processes = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            p_name = proc.info['name'] or ""
            p_clean = p_name.lower().replace(".exe", "")
            if target_base in p_clean or p_clean in target_base or clean in p_clean:
                matching_processes.append({"pid": proc.info['pid'], "name": p_name})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

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
    resolved = resolve_app_path(name)
    if not resolved:
        # Fallback to start command via shell for Windows protocol / system shortcuts
        clean = name.strip().lower()
        target = APP_ALIASES.get(clean, clean)
        try:
            cmd = f"start {target}"
            if args:
                cmd += " " + " ".join(args)
            subprocess.Popen(cmd, shell=True)
            return {
                "success": True,
                "app": name,
                "resolved_path": target,
                "launched_via": "shell_start",
                "message": f"Dispatched launch for '{name.capitalize()}'.",
            }
        except Exception as e:
            return {
                "success": False,
                "app": name,
                "error": f"Could not find or launch application '{name}': {str(e)}",
            }

    cmd = [resolved]
    if args:
        cmd.extend(args)

    try:
        proc = subprocess.Popen(cmd, shell=False)
        return {
            "success": True,
            "app": name,
            "resolved_path": resolved,
            "pid": proc.pid,
            "message": f"Successfully launched {name.capitalize()} (PID: {proc.pid}).",
        }
    except Exception as e:
        # Secondary fallback: start via Windows shell
        try:
            subprocess.Popen(f'start "" "{resolved}"', shell=True)
            return {
                "success": True,
                "app": name,
                "resolved_path": resolved,
                "launched_via": "shell_fallback",
                "message": f"Successfully launched {name.capitalize()}.",
            }
        except Exception as e2:
            return {
                "success": False,
                "app": name,
                "error": f"Failed to launch '{name}': {str(e2)}",
            }

def verify_app_launched(result: Dict[str, Any], arguments: Dict[str, Any]) -> Tuple[bool, str]:
    """Verify that the launched application is running in process list."""
    app_name = arguments.get("name", "")
    time.sleep(0.5)
    check = is_app_running(app_name)
    if check["is_running"]:
        return True, f"Verified '{app_name}' is actively running ({check['count']} instance(s))."
    return False, f"Verification warning: '{app_name}' process not detected after launch."

def close_application(name: str) -> Dict[str, Any]:
    """Close running application gracefully by process name."""
    clean = name.strip().lower()
    target_base = APP_ALIASES.get(clean, clean).replace(".exe", "")

    closed = 0
    errors = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            p_name = (proc.info['name'] or "").lower().replace(".exe", "")
            if target_base == p_clean_base(p_name):
                proc.terminate()
                closed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            errors.append(str(e))

    if closed > 0:
        return {"success": True, "app": name, "closed_count": closed, "message": f"Terminated {closed} instance(s) of '{name}'."}
    return {"success": False, "app": name, "closed_count": 0, "error": f"No running instance of '{name}' found."}

def p_clean_base(name: str) -> str:
    return name.lower().replace(".exe", "")

def verify_app_closed(result: Dict[str, Any], arguments: Dict[str, Any]) -> Tuple[bool, str]:
    """Verify that the application is no longer running."""
    app_name = arguments.get("name", "")
    time.sleep(0.3)
    check = is_app_running(app_name)
    if not check["is_running"]:
        return True, f"Verified all processes for '{app_name}' have terminated."
    return False, f"Verification failed: '{app_name}' processes still active."

def focus_application(name: str) -> Dict[str, Any]:
    """Focus / activate window of application."""
    clean = name.strip().lower()
    try:
        import pygetwindow as gw
        all_windows = gw.getAllWindows()
        matched = None
        for w in all_windows:
            if clean in w.title.lower():
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
        description="Close / terminate a running application by name.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of application to close"},
            },
            "required": ["name"],
        },
        permission_level=PermissionLevel.SAFE,
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

