import os
import re
import psutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from .observation import get_unified_observation

# Known common domains and web platforms
COMMON_WEBSITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://www.github.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://www.x.com",
    "x": "https://www.x.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "linkedin": "https://www.linkedin.com",
    "wikipedia": "https://www.wikipedia.org",
    "amazon": "https://www.amazon.com",
    "netflix": "https://www.netflix.com",
    "chatgpt": "https://chatgpt.com",
}

# Standard system user folders
STANDARD_FOLDERS = {
    "downloads": Path.home() / "Downloads",
    "documents": Path.home() / "Documents",
    "desktop": Path.home() / "Desktop",
    "pictures": Path.home() / "Pictures",
    "music": Path.home() / "Music",
    "videos": Path.home() / "Videos",
}

def resolve_target_entity(text: str, current_observation: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Classify entity type in user intent:
    - BROWSER_TAB / WEBSITE: e.g. "Close YouTube", "Open YouTube", "Close tab"
    - APPLICATION: e.g. "Close Chrome", "Open Notepad", "Launch Calculator"
    - WINDOW: e.g. "Close this window", "Minimize active window"
    - FILE: e.g. "Open the PDF I downloaded", "Find recent invoice.pdf"
    - FOLDER: e.g. "Open Downloads", "Open my desktop folder"
    - UI_CONTROL: e.g. "Click Continue", "Click the search box"
    - SYSTEM: e.g. "Volume 50%", "Battery level"
    """
    clean = text.strip()
    lower = clean.lower()
    obs = current_observation or get_unified_observation(include_ui_elements=False)

    # 1. Close Window / Active Window
    if any(k in lower for k in ["close this window", "close active window", "close current window", "close window"]):
        return {
            "entity_type": "WINDOW",
            "action": "window.close",
            "arguments": {"title": obs.get("active_window", {}).get("title", "")},
            "confidence": 0.95,
        }

    # 2. Close Browser Tab vs Close Application: "Close YouTube" vs "Close Chrome"
    if lower.startswith("close ") or lower.startswith("kill "):
        target_name = re.sub(r'^(?:close|kill|exit|terminate)\s+', '', lower).strip().rstrip(".")
        
        # Check if target is a website name
        if target_name in COMMON_WEBSITES or "youtube" in target_name or "tab" in target_name:
            # Check if active window is a browser or if there is a browser window with that title
            return {
                "entity_type": "BROWSER_TAB",
                "action": "browser.close_tab",
                "target": target_name,
                "confidence": 0.95,
                "reason": f"'{target_name}' is identified as a browser tab or website rather than a standalone OS application.",
            }

        # Check if target is a known app executable vs open window
        from .app_control import APP_ALIASES
        if target_name in APP_ALIASES:
            return {
                "entity_type": "APPLICATION",
                "action": "app.close",
                "arguments": {"name": target_name},
                "confidence": 0.90,
            }

        # Check if it matches an open window title
        for win in obs.get("visible_windows", []):
            if target_name in win.get("title", "").lower():
                return {
                    "entity_type": "WINDOW",
                    "action": "window.close",
                    "arguments": {"title": win["title"]},
                    "confidence": 0.85,
                }

    # 3. Open Folder / Explorer
    for f_name, f_path in STANDARD_FOLDERS.items():
        if f"open {f_name}" in lower or f"open my {f_name}" in lower or f"explore {f_name}" in lower:
            return {
                "entity_type": "FOLDER",
                "action": "file.open_folder",
                "arguments": {"path": str(f_path)},
                "confidence": 0.95,
            }

    # 4. Open File / Recent Downloads
    if any(k in lower for k in ["downloaded", "pdf", ".txt", ".docx", ".xlsx", ".png", ".jpg", "file i downloaded"]):
        ext_match = re.search(r'\b(pdf|txt|docx|xlsx|png|jpg|csv|zip)\b', lower)
        ext = ext_match.group(1) if ext_match else "pdf"
        return {
            "entity_type": "FILE",
            "action": "file.find_and_open",
            "arguments": {"extension": ext, "search_dir": str(STANDARD_FOLDERS["downloads"])},
            "confidence": 0.85,
        }

    # 5. UI Control Interaction
    if any(lower.startswith(k) for k in ["click ", "tap ", "press the ", "select the ", "double click ", "right click "]):
        target_control = re.sub(r'^(?:click|tap|press the|select the|double click|right click)\s+', '', clean, flags=re.IGNORECASE).strip()
        is_double = "double click" in lower
        is_right = "right click" in lower
        return {
            "entity_type": "UI_CONTROL",
            "action": "computer.interact",
            "arguments": {
                "action": "double_click" if is_double else ("right_click" if is_right else "locate_and_click"),
                "target_description": target_control,
            },
            "confidence": 0.90,
        }

    # Default fallback
    return {
        "entity_type": "GENERAL",
        "confidence": 0.50,
    }
