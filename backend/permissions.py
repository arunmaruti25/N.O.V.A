from enum import Enum
from dataclasses import dataclass
from typing import Dict, Set

class PermissionLevel(str, Enum):
    SAFE = "SAFE"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    BLOCKED = "BLOCKED"

@dataclass
class PermissionCheckResult:
    level: PermissionLevel
    action: str
    target: str
    reason: str
    is_authorized: bool

# Explicit allowlist of inherently safe operations
SAFE_ACTIONS: Set[str] = {
    "chat",
    "system_info",
    "volume",
    "get_volume",
    "set_volume",
    "list_processes",
    "launch_allowed_app",
    "capture_screen",
    "web_search",
    "save_memory",
    "list_memories",
    "retrieve_memories",
    "status_check",
    "voice_synthesize",
}

# Actions strictly requiring explicit user confirmation via frontend modal
CONFIRMATION_ACTIONS: Dict[str, str] = {
    "shutdown": "Action initiates shutdown of the host Windows operating system.",
    "restart": "Action initiates a system reboot of the host Windows computer.",
    "delete_file": "Action permanently removes files or folders from storage.",
    "delete_memory": "Action erases personal stored context from memory database.",
    "send_external_message": "Action transmits data or messages outside the local machine.",
    "terminate_process": "Action forcefully terminates an active running process.",
}

# Operations permanently disallowed and blocked
BLOCKED_ACTIONS: Set[str] = {
    "arbitrary_shell",
    "eval_code",
    "exec_code",
    "format_disk",
    "modify_registry_root",
    "kill_critical_system_process",
}

def evaluate_permission(action: str, target: str = "") -> PermissionCheckResult:
    """Centralized safety gate evaluating permission level for any requested action."""
    action_key = action.strip().lower()
    
    # 1. Block prohibited destructive or arbitrary execution
    if action_key in BLOCKED_ACTIONS:
        return PermissionCheckResult(
            level=PermissionLevel.BLOCKED,
            action=action_key,
            target=target,
            reason=f"Action '{action_key}' is blocked by security policy.",
            is_authorized=False,
        )

    # 2. Check for actions requiring explicit user authorization
    if action_key in CONFIRMATION_ACTIONS:
        return PermissionCheckResult(
            level=PermissionLevel.CONFIRMATION_REQUIRED,
            action=action_key,
            target=target,
            reason=CONFIRMATION_ACTIONS[action_key],
            is_authorized=False,
        )

    # 3. Check for safe actions
    if action_key in SAFE_ACTIONS:
        return PermissionCheckResult(
            level=PermissionLevel.SAFE,
            action=action_key,
            target=target,
            reason="Action is allowlisted and verified safe.",
            is_authorized=True,
        )

    # Unknown actions default to confirmation required for safety
    return PermissionCheckResult(
        level=PermissionLevel.CONFIRMATION_REQUIRED,
        action=action_key,
        target=target,
        reason=f"Unrecognized action '{action_key}' requires explicit authorization.",
        is_authorized=False,
    )

def evaluate_tool_permission(tool_name: str, arguments: Dict[str, Any] = None) -> PermissionCheckResult:
    """Centralized safety gate evaluating permission level for structured tool calls."""
    name = (tool_name or "").strip().lower()
    args = arguments or {}
    args_str = str(args)

    # 1. Block prohibited patterns across all tool arguments
    blocked_patterns = [
        "eval(", "exec(", "powershell -enc", "format c:", "rm -rf /",
        "cmd.exe /c format", "drop database", "format disk"
    ]
    for pattern in blocked_patterns:
        if pattern in args_str.lower() or pattern in name:
            return PermissionCheckResult(
                level=PermissionLevel.BLOCKED,
                action=tool_name,
                target=args_str,
                reason=f"Action '{tool_name}' blocked: Contains prohibited pattern '{pattern}'.",
                is_authorized=False,
            )

    # 2. Check confirmation required tools
    if name in ["file.delete", "system.power"]:
        reason = "System shutdown / reboot requires user confirmation." if "power" in name else "File deletion permanently removes data."
        return PermissionCheckResult(
            level=PermissionLevel.CONFIRMATION_REQUIRED,
            action=tool_name,
            target=args_str,
            reason=reason,
            is_authorized=False,
        )

    # 3. Check registered tools
    try:
        from .tools.registry import tool_registry
        tool = tool_registry.get(tool_name)
        if tool:
            return PermissionCheckResult(
                level=tool.permission_level,
                action=tool_name,
                target=args_str,
                reason=f"Tool '{tool_name}' permission level: {tool.permission_level.value}",
                is_authorized=(tool.permission_level == PermissionLevel.SAFE),
            )
    except Exception:
        pass

    # 4. Fallback to existing evaluate_permission
    return evaluate_permission(name, args_str)

