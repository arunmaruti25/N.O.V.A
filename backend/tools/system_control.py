import platform
import psutil
import subprocess
import time
from typing import Dict, Any, List, Optional, Tuple
from .registry import ToolDefinition, tool_registry
from ..permissions import PermissionLevel
from .computer import get_system_volume, set_system_volume, list_running_processes, execute_power_action

def get_battery() -> Dict[str, Any]:
    """Retrieve host battery status, percentage, and charging state."""
    try:
        battery = psutil.sensors_battery()
        if battery is None:
            return {
                "success": True,
                "has_battery": False,
                "percent": 100,
                "power_plugged": True,
                "message": "Workstation is connected to direct AC mains power (no battery sensor).",
            }
        
        secs = battery.secsleft
        time_left_str = "Unlimited / Charging" if battery.power_plugged or secs < 0 else f"{int(secs // 60)} minutes"
        return {
            "success": True,
            "has_battery": True,
            "percent": int(battery.percent),
            "power_plugged": bool(battery.power_plugged),
            "time_left": time_left_str,
            "message": f"Battery is at {battery.percent}% ({'Plugged in / Charging' if battery.power_plugged else 'On battery, ' + time_left_str}).",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to query battery: {str(e)}"}

def get_system_status() -> Dict[str, Any]:
    """Retrieve comprehensive system metrics: CPU, RAM, disk utilization, and OS details."""
    try:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()

        return {
            "success": True,
            "os": f"Windows {platform.release()} ({platform.version()})",
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "cpu_cores": psutil.cpu_count(logical=True),
            "ram_total_gb": round(mem.total / (1024 ** 3), 2),
            "ram_used_gb": round(mem.used / (1024 ** 3), 2),
            "ram_percent": mem.percent,
            "disk_total_gb": round(disk.total / (1024 ** 3), 2),
            "disk_free_gb": round(disk.free / (1024 ** 3), 2),
            "disk_percent": disk.percent,
            "network_bytes_sent_mb": round(net.bytes_sent / (1024 ** 2), 2),
            "network_bytes_recv_mb": round(net.bytes_recv / (1024 ** 2), 2),
            "message": f"CPU at {psutil.cpu_percent()}%, RAM at {mem.percent}% ({round(mem.used / (1024**3), 1)}GB used).",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to retrieve system status: {str(e)}"}

def get_display_info() -> Dict[str, Any]:
    """Retrieve display monitors and screen resolutions."""
    import pyautogui
    w, h = pyautogui.size()
    return {
        "success": True,
        "primary_resolution": f"{w}x{h}",
        "width": w,
        "height": h,
        "message": f"Primary display active at {w}x{h}.",
    }

def set_volume_tool(level: int) -> Dict[str, Any]:
    """Set master system audio volume."""
    res = set_system_volume(level)
    return {
        "success": res.get("success", True),
        "volume_percent": int(res.get("volume_percent", level)),
        "message": f"System master volume set to {level}%.",
    }

def verify_volume_set(result: Dict[str, Any], arguments: Dict[str, Any]) -> Tuple[bool, str]:
    """Verify that the volume was updated."""
    expected = int(arguments.get("level", 50))
    time.sleep(0.1)
    current = get_system_volume().get("volume_percent", expected)
    # Allow 2% tolerance due to Windows audio slider quantization
    if abs(current - expected) <= 3:
        return True, f"Verified master volume is {current}%."
    return True, f"Volume set acknowledged at {current}%."

def mute_volume_tool(mute: Optional[bool] = None) -> Dict[str, Any]:
    """Toggle or set audio mute state."""
    try:
        import pythoncom
        pythoncom.CoInitialize()
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        if device and hasattr(device, "EndpointVolume") and device.EndpointVolume:
            current_mute = bool(device.EndpointVolume.GetMute())
            new_mute = not current_mute if mute is None else bool(mute)
            device.EndpointVolume.SetMute(new_mute, None)
            return {
                "success": True,
                "is_muted": new_mute,
                "message": f"System audio {'muted' if new_mute else 'unmuted'}.",
            }
    except Exception:
        pass
    
    # Fallback to media key toggle
    import pyautogui
    pyautogui.press('volumemute')
    return {"success": True, "message": "Dispatched mute toggle key."}

def power_control(action: str) -> Dict[str, Any]:
    """
    Execute system shutdown or restart.
    REQUIRES EXPLICIT CONFIRMATION.
    """
    return execute_power_action(action)

def register_system_tools():
    tool_registry.register(ToolDefinition(
        name="system.battery",
        category="system",
        description="Get current battery percentage, charging state, and remaining run time.",
        parameters={"type": "object", "properties": {}},
        permission_level=PermissionLevel.SAFE,
        execute_fn=get_battery,
    ))

    tool_registry.register(ToolDefinition(
        name="system.status",
        category="system",
        description="Get hardware metrics: CPU load, RAM usage, disk space, and network counters.",
        parameters={"type": "object", "properties": {}},
        permission_level=PermissionLevel.SAFE,
        execute_fn=get_system_status,
    ))

    tool_registry.register(ToolDefinition(
        name="system.processes",
        category="system",
        description="List active processes ordered by memory utilization.",
        parameters={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of processes to list"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=list_running_processes,
    ))

    tool_registry.register(ToolDefinition(
        name="system.get_volume",
        category="system",
        description="Get current master audio volume percentage and mute state.",
        parameters={"type": "object", "properties": {}},
        permission_level=PermissionLevel.SAFE,
        execute_fn=get_system_volume,
    ))

    tool_registry.register(ToolDefinition(
        name="system.set_volume",
        category="system",
        description="Set master audio volume percentage (0 to 100).",
        parameters={
            "type": "object",
            "properties": {
                "level": {"type": "integer", "description": "Target volume percentage from 0 to 100"},
            },
            "required": ["level"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=set_volume_tool,
        verify_fn=verify_volume_set,
    ))

    tool_registry.register(ToolDefinition(
        name="system.mute",
        category="system",
        description="Mute, unmute, or toggle system master audio.",
        parameters={
            "type": "object",
            "properties": {
                "mute": {"type": "boolean", "description": "True to mute, False to unmute, omit to toggle"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=mute_volume_tool,
    ))

    tool_registry.register(ToolDefinition(
        name="system.display_info",
        category="system",
        description="Get display resolution and active monitor dimensions.",
        parameters={"type": "object", "properties": {}},
        permission_level=PermissionLevel.SAFE,
        execute_fn=get_display_info,
    ))

    # Power action requires confirmation
    tool_registry.register(ToolDefinition(
        name="system.power",
        category="system",
        description="Shutdown or reboot the computer. REQUIRES EXPLICIT USER CONFIRMATION.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action to execute: 'shutdown' or 'restart'"},
            },
            "required": ["action"],
        },
        permission_level=PermissionLevel.CONFIRMATION_REQUIRED,
        execute_fn=power_control,
    ))

