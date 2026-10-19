import os
import re
import psutil
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from .observation import get_unified_observation

# ─────────────────────────────────────────────────────────────
# 1. FORMAL ENTITY CLASSIFICATION TAXONOMY
# Distinguishes: APPLICATION vs PROCESS vs WINDOW vs BROWSER TAB vs WEBSITE vs PWA vs FILE vs FOLDER vs UI_CONTROL vs SYSTEM
# ─────────────────────────────────────────────────────────────

class EntityType(str, Enum):
    APPLICATION = "APPLICATION"       # Desktop GUI application or packaged app (e.g. Chrome, WhatsApp, VLC, Notepad)
    PROCESS = "PROCESS"               # OS Process in task list (e.g. python.exe, node.exe, background daemon)
    WINDOW = "WINDOW"                 # An OS GUI window instance (minimized, taskbar, normal, maximized)
    BROWSER_TAB = "BROWSER_TAB"       # A browser tab inside an active or background browser window
    WEBSITE = "WEBSITE"               # A web platform or URL domain (e.g. youtube.com, figma.com, news.ycombinator.com)
    PWA = "PWA"                       # Installed Progressive Web App running in standalone window
    FILE = "FILE"                     # A filesystem file (e.g. document.pdf, photo.png)
    FOLDER = "FOLDER"                 # A filesystem folder or directory (e.g. Downloads, Desktop)
    UI_CONTROL = "UI_CONTROL"         # An on-screen UI element (button, text field, link, slider)
    SYSTEM = "SYSTEM"                 # OS system hardware/settings (volume, battery, display, power)
    GENERAL = "GENERAL"               # General conversational or unclassified entity


# Known common domains and web platforms (for rapid URL resolution, not exclusivity)
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
    "figma": "https://www.figma.com",
    "spotify": "https://open.spotify.com",
    "slack": "https://app.slack.com",
    "notion": "https://www.notion.so",
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

# Known file extensions
KNOWN_EXTENSIONS = {
    "pdf", "txt", "docx", "doc", "xlsx", "xls", "pptx", "ppt",
    "png", "jpg", "jpeg", "gif", "svg", "webp", "mp4", "mp3",
    "wav", "zip", "tar", "gz", "7z", "py", "js", "html", "css",
    "json", "csv", "log", "md", "exe", "bat", "sh"
}

# Browser executable names
BROWSER_PROCS = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe", "vivaldi.exe"}


def strip_assistant_prefix(text: str) -> str:
    """Strip assistant wake words or prefixes like 'Hey NOVA,', 'NOVA,', 'Hey NOVA'."""
    pattern = r'^(?:hey\s+nova|okay\s+nova|ok\s+nova|hi\s+nova|nova)[\s,:]*'
    cleaned = re.sub(pattern, '', text.strip(), flags=re.IGNORECASE).strip()
    return cleaned if cleaned else text.strip()


def resolve_target_entity(text: str, current_observation: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Context-Aware Entity Disambiguation:
    Dynamically inspects live Windows computer state (open/minimized windows, taskbar,
    active window, running processes, filesystem paths, browser state) to distinguish
    between APPLICATION, PROCESS, WINDOW, BROWSER_TAB, WEBSITE, PWA, FILE, FOLDER, UI_CONTROL, SYSTEM.
    Never relies on hardcoded assumptions for specific apps.
    """
    clean = strip_assistant_prefix(text.strip())
    lower = clean.lower()
    obs = current_observation or get_unified_observation(include_ui_elements=False)

    active_win = obs.get("active_window", {}) or {}
    active_title = (active_win.get("title") or "").lower()
    active_proc = (active_win.get("process_name") or "").lower()
    is_active_browser = active_proc in BROWSER_PROCS or active_win.get("is_browser", False)

    open_wins = obs.get("open_windows", []) or []
    running_apps = obs.get("running_applications", []) or []

    # ─────────────────────────────────────────────────────────────
    # 1. SYSTEM CONTROLS (Volume, Battery, Power, Display)
    # ─────────────────────────────────────────────────────────────
    if any(k in lower for k in ["volume", "mute", "unmute", "sound level"]):
        return {
            "entity_type": EntityType.SYSTEM.value,
            "category": "audio",
            "action": "system.set_volume" if any(k in lower for k in ["set", "change", "to"]) else "system.get_volume",
            "confidence": 0.95,
        }

    if any(k in lower for k in ["battery", "battery percentage", "power status", "charging"]):
        return {
            "entity_type": EntityType.SYSTEM.value,
            "category": "battery",
            "action": "system.battery",
            "confidence": 0.95,
        }

    if any(k in lower for k in ["shut down", "shutdown", "restart computer", "reboot laptop"]):
        action = "restart" if any(k in lower for k in ["restart", "reboot"]) else "shutdown"
        return {
            "entity_type": EntityType.SYSTEM.value,
            "category": "power",
            "action": "system.power",
            "arguments": {"action": action},
            "confidence": 0.95,
        }

    # ─────────────────────────────────────────────────────────────
    # 2. WINDOW SPECIFIC ACTIONS ("this window", "active window", "minimize window")
    # ─────────────────────────────────────────────────────────────
    window_phrases = ["this window", "active window", "current window", "the window", "front window"]
    if any(k in lower for k in window_phrases) or (lower in ["close window", "minimize window", "maximize window"]):
        action = "window.close"
        if "minimize" in lower:
            action = "window.minimize"
        elif "maximize" in lower:
            action = "window.maximize"
        elif "restore" in lower:
            action = "window.restore"

        return {
            "entity_type": EntityType.WINDOW.value,
            "action": action,
            "arguments": {"title": active_win.get("title", "")},
            "target": active_win.get("title", ""),
            "confidence": 0.95,
            "reason": "Explicit reference to foreground or OS window.",
        }

    # ─────────────────────────────────────────────────────────────
    # 3. CLOSE / QUIT / KILL DISAMBIGUATION
    # Resolves whether the user wants to close a TAB, WINDOW, PROCESS, or APPLICATION
    # ─────────────────────────────────────────────────────────────
    close_match = re.search(r'^(?:close|quit|exit|kill|terminate|stop)\s+(.+)', lower)
    if close_match:
        target_name = close_match.group(1).strip().rstrip(".!")

        # A. Explicit tab reference (e.g. "close tab", "close this tab", "close active tab")
        if target_name in ["tab", "this tab", "active tab", "current tab", "browser tab"]:
            return {
                "entity_type": EntityType.BROWSER_TAB.value,
                "action": "browser.close_tab",
                "target": active_win.get("title", ""),
                "confidence": 0.98,
                "reason": "Explicit browser tab close requested.",
            }

        # B. Check if target matches an active or open browser tab title/domain
        # E.g. "Close YouTube" while in browser or when YouTube tab exists
        if is_active_browser and (target_name in active_title or target_name in COMMON_WEBSITES):
            return {
                "entity_type": EntityType.BROWSER_TAB.value,
                "action": "browser.close_tab",
                "target": target_name.title(),
                "arguments": {"title_match": target_name.title()},
                "confidence": 0.95,
                "reason": f"'{target_name}' is identified as a tab in the active browser window.",
            }

        # Check if any browser window has a tab matching target_name
        for w in open_wins:
            w_title = (w.get("title") or "").lower()
            w_proc = (w.get("process_name") or "").lower()
            if w_proc in BROWSER_PROCS and target_name in w_title:
                return {
                    "entity_type": EntityType.BROWSER_TAB.value,
                    "action": "browser.close_tab",
                    "target": target_name.title(),
                    "arguments": {"title_match": target_name.title()},
                    "confidence": 0.90,
                    "reason": f"Tab matching '{target_name}' found in browser window.",
                }

        # C. Check if target is a website name or URL domain
        if target_name in COMMON_WEBSITES or "." in target_name and not target_name.endswith(".exe"):
            return {
                "entity_type": EntityType.BROWSER_TAB.value,
                "action": "browser.close_tab",
                "target": target_name,
                "arguments": {"title_match": target_name},
                "confidence": 0.90,
                "reason": f"'{target_name}' is classified as a web domain/tab.",
            }

        # D. Check if target is a PWA (Progressive Web App) running standalone
        # PWAs often run via chrome_proxy.exe or msedge_proxy.exe with app name in title
        for w in open_wins:
            w_title = (w.get("title") or "").lower()
            w_proc = (w.get("process_name") or "").lower()
            if ("proxy" in w_proc or "app-id" in str(w)) and target_name in w_title:
                return {
                    "entity_type": EntityType.PWA.value,
                    "action": "window.close",
                    "arguments": {"title": w.get("title", "")},
                    "target": target_name,
                    "confidence": 0.92,
                    "reason": f"'{target_name}' is identified as an active Progressive Web App (PWA).",
                }

        # E. Check if target explicitly specifies a process (e.g. "kill python.exe" or "kill process 1234")
        if target_name.endswith(".exe") or "process" in lower:
            clean_proc = target_name.replace("process", "").strip()
            return {
                "entity_type": EntityType.PROCESS.value,
                "action": "app.close",
                "arguments": {"name": clean_proc},
                "target": clean_proc,
                "confidence": 0.95,
                "reason": f"Explicit process termination requested for '{clean_proc}'.",
            }

        # F. Check open windows (including minimized on taskbar) for specific window title
        for w in open_wins:
            w_title = (w.get("title") or "").lower()
            if target_name in w_title and len(target_name) > 3:
                # If it's a specific document or sub-window title, target window.close
                if " - " in w.get("title", "") and target_name not in ["chrome", "notepad", "code", "edge"]:
                    return {
                        "entity_type": EntityType.WINDOW.value,
                        "action": "window.close",
                        "arguments": {"title": w["title"]},
                        "target": w["title"],
                        "confidence": 0.85,
                    }

        # G. Default close target is an APPLICATION (handles minimized taskbar apps and background processes)
        return {
            "entity_type": EntityType.APPLICATION.value,
            "action": "app.close",
            "arguments": {"name": target_name},
            "target": target_name,
            "confidence": 0.90,
            "reason": f"Application lifecycle close for '{target_name}' (covering taskbar, minimized, and background instances).",
        }

    # ─────────────────────────────────────────────────────────────
    # 4. FOLDER NAVIGATION / OPEN FOLDER
    # ─────────────────────────────────────────────────────────────
    for f_name, f_path in STANDARD_FOLDERS.items():
        if f"open {f_name}" in lower or f"open my {f_name}" in lower or f"explore {f_name}" in lower or f"show {f_name}" in lower:
            return {
                "entity_type": EntityType.FOLDER.value,
                "action": "file.open_folder",
                "arguments": {"path": str(f_path)},
                "target": f_name,
                "confidence": 0.95,
                "reason": f"User folder '{f_name}' path resolved.",
            }

    # Custom folder path: e.g. "Open C:\Projects" or "Open /path/to/dir"
    folder_path_match = re.search(r'open\s+(?:folder\s+)?([A-Za-z]:\\[^\\/:*?"<>|\r\n]+)', clean)
    if folder_path_match:
        f_dir = folder_path_match.group(1).strip()
        if os.path.isdir(f_dir):
            return {
                "entity_type": EntityType.FOLDER.value,
                "action": "file.open_folder",
                "arguments": {"path": f_dir},
                "target": f_dir,
                "confidence": 0.95,
            }

    # ─────────────────────────────────────────────────────────────
    # 5. FILE SEARCH & OPEN
    # ─────────────────────────────────────────────────────────────
    if any(k in lower for k in ["downloaded", "file i downloaded", "recent file", "recent document"]):
        ext_match = re.search(r'\b(' + '|'.join(KNOWN_EXTENSIONS) + r')\b', lower)
        ext = ext_match.group(1) if ext_match else "pdf"
        return {
            "entity_type": EntityType.FILE.value,
            "action": "file.find_and_open",
            "arguments": {"extension": ext, "search_dir": str(STANDARD_FOLDERS["downloads"])},
            "target": ext,
            "confidence": 0.90,
            "reason": f"Recent downloaded {ext.upper()} file search.",
        }

    file_match = re.search(r'(?:open|read|view|show)\s+(?:the\s+)?(?:file\s+)?([^\s]+\.(' + '|'.join(KNOWN_EXTENSIONS) + r'))\b', clean, re.IGNORECASE)
    if file_match:
        fname = file_match.group(1).strip()
        fext = file_match.group(2).lower()
        return {
            "entity_type": EntityType.FILE.value,
            "action": "file.find_and_open",
            "arguments": {"extension": fext, "filename_query": fname},
            "target": fname,
            "confidence": 0.90,
            "reason": f"Filesystem document '{fname}'.",
        }

    # ─────────────────────────────────────────────────────────────
    # 6. WEBSITE NAVIGATION / OPEN WEB PLATFORM
    # ─────────────────────────────────────────────────────────────
    # Explicit URL or domain (e.g. "Open github.com", "Navigate to https://...", "Go to reddit.com")
    url_match = re.search(r'(?:open|navigate to|go to|browse to)\s+(https?://[^\s]+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)', clean, re.IGNORECASE)
    if url_match:
        raw_url = url_match.group(1).strip()
        return {
            "entity_type": EntityType.WEBSITE.value,
            "action": "browser.open",
            "arguments": {"url": raw_url},
            "target": raw_url,
            "confidence": 0.95,
            "reason": f"Web URL / domain '{raw_url}'.",
        }

    # ─────────────────────────────────────────────────────────────
    # 7. UI CONTROL INTERACTION (Click, Tap, Select, Focus)
    # ─────────────────────────────────────────────────────────────
    if any(lower.startswith(k) for k in ["click ", "tap ", "press the ", "select the ", "double click ", "right click "]):
        target_control = re.sub(r'^(?:click|tap|press the|select the|double click|right click)\s+', '', clean, flags=re.IGNORECASE).strip()
        is_double = "double click" in lower
        is_right = "right click" in lower
        return {
            "entity_type": EntityType.UI_CONTROL.value,
            "action": "computer.interact",
            "arguments": {
                "action": "double_click" if is_double else ("right_click" if is_right else "locate_and_click"),
                "target_description": target_control,
            },
            "target": target_control,
            "confidence": 0.90,
        }

    # ─────────────────────────────────────────────────────────────
    # 8. APPLICATION LAUNCH / FOCUS
    # ─────────────────────────────────────────────────────────────
    open_app_match = re.search(r'^(?:open|launch|start|focus|switch to)\s+(.+)', lower)
    if open_app_match:
        target_name = open_app_match.group(1).strip().rstrip(".!")

        # Check if it's a known website first (e.g. "Open YouTube")
        if target_name in COMMON_WEBSITES:
            return {
                "entity_type": EntityType.WEBSITE.value,
                "action": "browser.open",
                "arguments": {"url": COMMON_WEBSITES[target_name]},
                "target": target_name,
                "confidence": 0.95,
            }

        # Otherwise resolves as APPLICATION
        return {
            "entity_type": EntityType.APPLICATION.value,
            "action": "app.launch",
            "arguments": {"name": target_name},
            "target": target_name,
            "confidence": 0.90,
        }

    # Default fallback
    return {
        "entity_type": EntityType.GENERAL.value,
        "target": clean,
        "confidence": 0.50,
    }
