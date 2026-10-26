import platform
import psutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ALLOWED_APPS: Dict[str, str] = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "terminal": "wt",
    "windows terminal": "wt",
    "notepad": "notepad",
    "calculator": "calc",
    "task manager": "taskmgr",
    "edge": "msedge",
    "microsoft edge": "msedge",
}

def get_system_info() -> Dict[str, Any]:
    """Retrieve host system specs, memory utilization, and CPU load."""
    mem = psutil.virtual_memory()
    try:
        disk_percent = psutil.disk_usage(Path.home().anchor or '/').percent
    except OSError:
        disk_percent = None
    return {
        "os": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "architecture": platform.machine(),
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_total_gb": round(mem.total / (1024 ** 3), 2),
        "memory_used_gb": round(mem.used / (1024 ** 3), 2),
        "memory_percent": mem.percent,
        "disk_percent": disk_percent,
    }

def get_system_volume() -> Dict[str, Any]:
    """Retrieve current Windows audio volume and mute state safely."""
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        pass
    try:
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        if device and hasattr(device, "EndpointVolume") and device.EndpointVolume:
            current_scalar = device.EndpointVolume.GetMasterVolumeLevelScalar()
            is_muted = bool(device.EndpointVolume.GetMute())
            return {
                "volume_percent": int(round(current_scalar * 100)),
                "is_muted": is_muted,
                "success": True,
            }
        return {"success": False, "error": "No audio endpoint available."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def set_system_volume(level_percent: int) -> Dict[str, Any]:
    """Set Windows master audio volume safely between 0 and 100%."""
    level = max(0, min(100, int(level_percent)))
    scalar = level / 100.0
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        pass
    try:
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        if device and hasattr(device, "EndpointVolume") and device.EndpointVolume:
            device.EndpointVolume.SetMasterVolumeLevelScalar(scalar, None)
            return {"volume_percent": level, "success": True}
        return {"success": False, "error": "No audio endpoint available."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def list_running_processes(limit: int = 15) -> List[Dict[str, Any]]:
    """List top running processes sorted by memory utilization."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            info = proc.info
            if info['name']:
                processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "cpu_percent": info['cpu_percent'] or 0.0,
                    "memory_percent": round(info['memory_percent'] or 0.0, 2),
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sort descending by memory usage
    processes.sort(key=lambda p: p['memory_percent'], reverse=True)
    return processes[:limit]

def launch_allowed_application(app_name: str) -> Dict[str, Any]:
    """Launch allowlisted Windows applications only. Rejects arbitrary executables."""
    clean_name = app_name.strip().lower()
    target_cmd = ALLOWED_APPS.get(clean_name)
    
    if not target_cmd:
        # Check partial match
        for key, cmd in ALLOWED_APPS.items():
            if key in clean_name or clean_name in key:
                target_cmd = cmd
                clean_name = key
                break

    if not target_cmd:
        return {
            "success": False,
            "error": f"Application '{app_name}' is not in the allowed application list.",
            "allowed_apps": list(ALLOWED_APPS.keys()),
        }

    try:
        # Launch without arbitrary shell
        subprocess.Popen([target_cmd], shell=False)
        return {
            "success": True,
            "app": clean_name,
            "command": target_cmd,
            "message": f"Successfully launched {clean_name}.",
        }
    except Exception as e:
        # Fallback to start cmd in shell if needed for Windows PATH resolution
        try:
            subprocess.Popen(f"start {target_cmd}", shell=True)
            return {"success": True, "app": clean_name, "command": target_cmd, "message": f"Launched {clean_name}."}
        except Exception as e2:
            return {"success": False, "error": str(e2)}

def execute_power_action(action: str) -> Dict[str, Any]:
    """Execute host power actions. Note: caller MUST verify confirmation first."""
    action_key = action.strip().lower()
    if action_key == "shutdown":
        cmd = ["shutdown", "/s", "/t", "3", "/c", "NOVA initiated system shutdown"]
        subprocess.Popen(cmd, shell=False)
        return {"action": "shutdown", "success": True, "message": "System shutdown scheduled in 3 seconds."}
    elif action_key == "restart":
        cmd = ["shutdown", "/r", "/t", "3", "/c", "NOVA initiated system restart"]
        subprocess.Popen(cmd, shell=False)
        return {"action": "restart", "success": True, "message": "System reboot scheduled in 3 seconds."}
    else:
        return {"success": False, "error": f"Unknown power action '{action}'"}
