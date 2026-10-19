import os
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from .registry import ToolDefinition, tool_registry
from ..permissions import PermissionLevel
from ..config import settings

# Disallowed root directories for safety
PROTECTED_PATHS = [
    Path(os.environ.get("WINDIR", "C:\\Windows")).resolve(),
    Path(os.environ.get("ProgramFiles", "C:\\Program Files")).resolve(),
    Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")).resolve(),
    Path("C:\\Windows").resolve(),
]

def sanitize_and_validate_path(path_str: str, allow_create: bool = False) -> Tuple[bool, Optional[Path], Optional[str]]:
    """
    Validate that target path is valid and does not target protected operating system directories.
    """
    try:
        p = Path(path_str).expanduser().resolve()
        for protected in PROTECTED_PATHS:
            if p == protected or protected in p.parents:
                return False, None, f"Access Denied: Path '{path_str}' is within a protected system directory."
        return True, p, None
    except Exception as e:
        return False, None, f"Invalid path syntax: {str(e)}"

def search_files(pattern: str, directory: Optional[str] = None, max_results: int = 15) -> Dict[str, Any]:
    """Search for files matching a glob pattern."""
    target_dir = Path(directory).expanduser().resolve() if directory else settings.DATA_DIR
    valid, base_path, err = sanitize_and_validate_path(str(target_dir))
    if not valid:
        return {"success": False, "error": err}

    if not base_path.exists() or not base_path.is_dir():
        return {"success": False, "error": f"Directory '{directory}' does not exist or is not a directory."}

    matched = []
    try:
        for p in base_path.rglob(pattern):
            if any(protected in p.parents for protected in PROTECTED_PATHS):
                continue
            matched.append({
                "name": p.name,
                "path": str(p),
                "is_dir": p.is_dir(),
                "size_bytes": p.stat().st_size if p.is_file() else 0,
            })
            if len(matched) >= max_results:
                break

        return {
            "success": True,
            "pattern": pattern,
            "directory": str(base_path),
            "count": len(matched),
            "results": matched,
            "message": f"Found {len(matched)} match(es) for '{pattern}' in {base_path}.",
        }
    except Exception as e:
        return {"success": False, "error": f"Search failed: {str(e)}"}

def list_directory(directory: Optional[str] = None) -> Dict[str, Any]:
    """List directory contents with item metadata."""
    target_dir = Path(directory).expanduser().resolve() if directory else settings.DATA_DIR
    valid, base_path, err = sanitize_and_validate_path(str(target_dir))
    if not valid:
        return {"success": False, "error": err}

    if not base_path.exists() or not base_path.is_dir():
        return {"success": False, "error": f"Directory '{directory}' does not exist."}

    items = []
    try:
        for entry in os.scandir(base_path):
            st = entry.stat()
            items.append({
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size_bytes": st.st_size if entry.is_file() else 0,
                "modified": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
            })
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {
            "success": True,
            "directory": str(base_path),
            "count": len(items),
            "items": items[:50],
            "message": f"Listed {len(items)} items in {base_path}.",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to list directory: {str(e)}"}

def inspect_metadata(path: str) -> Dict[str, Any]:
    """Inspect file or directory metadata."""
    valid, p, err = sanitize_and_validate_path(path)
    if not valid:
        return {"success": False, "error": err}
    if not p.exists():
        return {"success": False, "error": f"Path '{path}' does not exist."}

    try:
        st = p.stat()
        return {
            "success": True,
            "path": str(p),
            "name": p.name,
            "is_dir": p.is_dir(),
            "size_bytes": st.st_size if p.is_file() else 0,
            "extension": p.suffix if p.is_file() else "",
            "modified": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
            "created": datetime.fromtimestamp(st.st_ctime, timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def read_text_file(path: str, max_chars: int = 10000) -> Dict[str, Any]:
    """Safely read text file content up to character limit."""
    valid, p, err = sanitize_and_validate_path(path)
    if not valid:
        return {"success": False, "error": err}
    if not p.exists() or not p.is_file():
        return {"success": False, "error": f"File '{path}' does not exist."}

    # Reject reading massive binary or large files
    if p.stat().st_size > 5 * 1024 * 1024:
        return {"success": False, "error": f"File exceeds safe read threshold (size: {p.stat().st_size} bytes)."}

    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_chars)
        return {
            "success": True,
            "path": str(p),
            "content": content,
            "characters_read": len(content),
            "truncated": len(content) >= max_chars,
        }
    except Exception as e:
        return {"success": False, "error": f"Could not read file: {str(e)}"}

def create_file(path: str, content: str = "") -> Dict[str, Any]:
    """Create a new file with specified content."""
    valid, p, err = sanitize_and_validate_path(path, allow_create=True)
    if not valid:
        return {"success": False, "error": err}

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "x", encoding="utf-8") as f:
            f.write(content)
        return {
            "success": True,
            "path": str(p),
            "bytes_written": len(content.encode("utf-8")),
            "message": f"Successfully created file '{p.name}'.",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to create file: {str(e)}"}

def verify_file_created(result: Dict[str, Any], arguments: Dict[str, Any]) -> Tuple[bool, str]:
    """Verify that the created file exists on disk."""
    p_str = arguments.get("path", "")
    p = Path(p_str).expanduser().resolve()
    if p.exists() and p.is_file():
        return True, f"Verified file exists on disk ({p.stat().st_size} bytes)."
    return False, f"Verification failed: file '{p_str}' not found on disk."

def copy_file(source: str, destination: str) -> Dict[str, Any]:
    """Copy a file safely."""
    v1, src, e1 = sanitize_and_validate_path(source)
    if not v1: return {"success": False, "error": e1}
    v2, dst, e2 = sanitize_and_validate_path(destination, allow_create=True)
    if not v2: return {"success": False, "error": e2}

    if not src.exists():
        return {"success": False, "error": f"Source '{source}' does not exist."}

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return {"success": True, "source": str(src), "destination": str(dst), "message": f"Copied to {dst}."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def move_file(source: str, destination: str) -> Dict[str, Any]:
    """Move a file safely."""
    v1, src, e1 = sanitize_and_validate_path(source)
    if not v1: return {"success": False, "error": e1}
    v2, dst, e2 = sanitize_and_validate_path(destination, allow_create=True)
    if not v2: return {"success": False, "error": e2}

    if not src.exists():
        return {"success": False, "error": f"Source '{source}' does not exist."}

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, dst)
        return {"success": True, "source": str(src), "destination": str(dst), "message": f"Moved to {dst}."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_file(path: str) -> Dict[str, Any]:
    """
    Delete a file permanently.
    NOTE: Requires explicit user confirmation via frontend modal.
    """
    valid, p, err = sanitize_and_validate_path(path)
    if not valid:
        return {"success": False, "error": err}
    if not p.exists():
        return {"success": False, "error": f"File '{path}' does not exist."}

    try:
        if p.is_file():
            p.unlink()
            return {"success": True, "path": str(p), "message": f"Deleted file '{p.name}'."}
        elif p.is_dir():
            shutil.rmtree(p)
            return {"success": True, "path": str(p), "message": f"Deleted directory '{p.name}'."}
        return {"success": False, "error": "Unknown path type."}
    except Exception as e:
        return {"success": False, "error": f"Deletion failed: {str(e)}"}

def verify_file_deleted(result: Dict[str, Any], arguments: Dict[str, Any]) -> Tuple[bool, str]:
    """Verify that the target file was removed from the filesystem."""
    p_str = arguments.get("path", "")
    p = Path(p_str).expanduser().resolve()
    if not p.exists():
        return True, f"Verified file '{p.name}' is no longer present on disk."
    return False, f"Verification failed: file '{p.name}' still exists."

def register_file_tools():
    tool_registry.register(ToolDefinition(
        name="file.search",
        category="file",
        description="Search for files matching a glob pattern (e.g. *.txt, report*.pdf).",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob search pattern"},
                "directory": {"type": "string", "description": "Optional search root directory"},
                "max_results": {"type": "integer", "description": "Maximum matches to return (default: 15)"},
            },
            "required": ["pattern"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=search_files,
    ))

    tool_registry.register(ToolDefinition(
        name="file.list_directory",
        category="file",
        description="List files and folders in a directory with sizes and timestamps.",
        parameters={
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory path to list"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=list_directory,
    ))

    tool_registry.register(ToolDefinition(
        name="file.inspect_metadata",
        category="file",
        description="Inspect metadata (size, created, modified) of a file or folder.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Target file or folder path"},
            },
            "required": ["path"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=inspect_metadata,
    ))

    tool_registry.register(ToolDefinition(
        name="file.read_text",
        category="file",
        description="Read the text content of a file up to safe character limit.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to text file"},
                "max_chars": {"type": "integer", "description": "Maximum characters to read (default: 10000)"},
            },
            "required": ["path"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=read_text_file,
    ))

    tool_registry.register(ToolDefinition(
        name="file.create_file",
        category="file",
        description="Create a new file with specified text content.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Destination file path"},
                "content": {"type": "string", "description": "Text content to write into file"},
            },
            "required": ["path"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=create_file,
        verify_fn=verify_file_created,
    ))

    tool_registry.register(ToolDefinition(
        name="file.copy",
        category="file",
        description="Copy a file to a new destination.",
        parameters={
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source file path"},
                "destination": {"type": "string", "description": "Destination file path"},
            },
            "required": ["source", "destination"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=copy_file,
    ))

    tool_registry.register(ToolDefinition(
        name="file.move",
        category="file",
        description="Move or rename a file to a new destination.",
        parameters={
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source file path"},
                "destination": {"type": "string", "description": "Destination file path"},
            },
            "required": ["source", "destination"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=move_file,
    ))

    # DELETE REQUIRES CONFIRMATION
    tool_registry.register(ToolDefinition(
        name="file.delete",
        category="file",
        description="Permanently delete a file or directory. REQUIRES EXPLICIT USER CONFIRMATION.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Target file or directory path to delete"},
            },
            "required": ["path"],
        },
        permission_level=PermissionLevel.CONFIRMATION_REQUIRED,
        execute_fn=delete_file,
        verify_fn=verify_file_deleted,
    ))

