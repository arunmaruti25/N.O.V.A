import time
import asyncio
import inspect
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, List, Tuple
from ..permissions import PermissionLevel

@dataclass
class ToolResult:
    success: bool
    tool: str = ""
    result: Any = None
    verified: bool = False
    verification_detail: str = ""
    error: Optional[str] = None
    duration_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tool_name: Optional[str] = None

    def __post_init__(self):
        if not self.tool and self.tool_name:
            self.tool = self.tool_name
        elif self.tool and not self.tool_name:
            self.tool_name = self.tool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "tool": self.tool,
            "result": self.result,
            "verified": self.verified,
            "verification_detail": self.verification_detail,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }

@dataclass
class ToolDefinition:
    name: str
    category: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema specification of inputs
    permission_level: PermissionLevel
    execute_fn: Callable
    verify_fn: Optional[Callable] = None
    examples: List[Dict[str, Any]] = field(default_factory=list)

class ToolRegistry:
    """
    Centralized Tool Registry and Execution Engine for NOVA.
    Provides strict schema validation, security gate enforcement,
    structured execution, and post-execution verification.
    """
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a new tool definition."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Retrieve tool definition by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with metadata."""
        return [
            {
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "parameters": t.parameters,
                "permission_level": t.permission_level.value,
            }
            for t in self._tools.values()
        ]

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI / Gemini style tool declarations for LLM prompting."""
        schemas = []
        for t in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
            })
        return schemas

    def validate_arguments(self, tool: ToolDefinition, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Strictly validate input arguments against schema and security rules."""
        if not isinstance(arguments, dict):
            return False, f"Arguments must be a JSON object, got {type(arguments).__name__}"

        schema = tool.parameters
        required_fields = schema.get("required", [])
        for field_name in required_fields:
            if field_name not in arguments:
                return False, f"Missing required parameter '{field_name}' for tool '{tool.name}'"

        # Type checks and security checks
        properties = schema.get("properties", {})
        for key, val in arguments.items():
            if key in properties:
                prop_spec = properties[key]
                expected_type = prop_spec.get("type")
                if expected_type == "string" and not isinstance(val, str):
                    return False, f"Parameter '{key}' must be string, got {type(val).__name__}"
                elif expected_type == "integer" and not (isinstance(val, int) and not isinstance(val, bool)):
                    return False, f"Parameter '{key}' must be integer, got {type(val).__name__}"
                elif expected_type == "number" and not (isinstance(val, (int, float)) and not isinstance(val, bool)):
                    return False, f"Parameter '{key}' must be number, got {type(val).__name__}"
                elif expected_type == "boolean" and not isinstance(val, bool):
                    return False, f"Parameter '{key}' must be boolean, got {type(val).__name__}"
                elif expected_type == "array" and not isinstance(val, list):
                    return False, f"Parameter '{key}' must be array, got {type(val).__name__}"

            # Security sanitization on all string values
            if isinstance(val, str):
                lower_val = val.lower()
                blocked_patterns = [
                    "eval(", "exec(", "powershell -enc", "format c:", "rm -rf /",
                    "cmd.exe /c format", "drop database"
                ]
                for pattern in blocked_patterns:
                    if pattern in lower_val:
                        return False, f"Security Violation: Parameter '{key}' contains prohibited pattern '{pattern}'"

        return True, None

    async def execute(
        self,
        name: str,
        arguments: Dict[str, Any],
        pre_authorized: bool = False,
    ) -> ToolResult:
        """
        Execute tool through security gate:
        1. Lookup tool
        2. Validate arguments
        3. Permission check
        4. Execute
        5. Verify
        """
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                tool=name,
                error=f"Tool '{name}' is not registered in NOVA Tool Registry.",
                verified=False,
            )

        # 1. Validate Arguments
        valid, err = self.validate_arguments(tool, arguments)
        if not valid:
            return ToolResult(
                success=False,
                tool=name,
                error=f"Argument validation failed: {err}",
                verified=False,
            )

        # 2. Permission Check
        if tool.permission_level == PermissionLevel.BLOCKED:
            return ToolResult(
                success=False,
                tool=name,
                error=f"Security Alert: Tool '{name}' is permanently blocked by security policy.",
                verified=False,
            )

        if tool.permission_level == PermissionLevel.CONFIRMATION_REQUIRED and not pre_authorized:
            return ToolResult(
                success=False,
                tool=name,
                error="ACTION_REQUIRES_CONFIRMATION",
                result={
                    "confirmation_required": True,
                    "tool": name,
                    "arguments": arguments,
                    "description": tool.description,
                },
                verified=False,
            )

        # 3. Execution
        start_time = time.perf_counter()
        try:
            # Desktop libraries (including async wrappers) perform blocking OS calls.
            # Hold execution until an in-flight OS action finishes on cancellation.
            def invoke():
                if inspect.iscoroutinefunction(tool.execute_fn):
                    return asyncio.run(tool.execute_fn(**arguments))
                return tool.execute_fn(**arguments)
            operation = asyncio.create_task(asyncio.to_thread(invoke))
            try:
                exec_result = await asyncio.shield(operation)
            except asyncio.CancelledError:
                await operation
                raise

            duration_ms = int((time.perf_counter() - start_time) * 1000)

            # Check if inner execution reported failure
            if isinstance(exec_result, dict) and exec_result.get("success") is False:
                return ToolResult(
                    success=False,
                    tool=name,
                    result=exec_result,
                    error=exec_result.get("error", "Execution failed"),
                    verified=False,
                    duration_ms=duration_ms,
                )

            # 4. Verification Check
            verified = bool(isinstance(exec_result, dict) and exec_result.get("verified", False))
            verification_detail = "Action executed; outcome not independently verified."
            if tool.verify_fn:
                try:
                    if inspect.iscoroutinefunction(tool.verify_fn):
                        v_ok, v_msg = await tool.verify_fn(exec_result, arguments)
                    else:
                        v_ok, v_msg = await asyncio.to_thread(tool.verify_fn, exec_result, arguments)
                    verified = v_ok
                    verification_detail = v_msg
                except Exception as ve:
                    verified = False
                    verification_detail = f"Verification check error: {str(ve)}"

            return ToolResult(
                success=verified if tool.verify_fn else True,
                tool=name,
                result=exec_result,
                verified=verified,
                verification_detail=verification_detail,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return ToolResult(
                success=False,
                tool=name,
                error=f"Runtime error during tool execution: {str(e)}",
                verified=False,
                duration_ms=duration_ms,
            )

# Global Tool Registry Singleton
tool_registry = ToolRegistry()

