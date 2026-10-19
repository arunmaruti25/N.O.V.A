import re
import json
from typing import List, Dict, Any, Optional
from .registry import tool_registry

def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Extract first valid JSON object from text."""
    # Check code block first
    code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except Exception:
            pass

    # Direct curly brace match
    brace_match = re.search(r'(\{[\s\S]*\})', text)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except Exception:
            pass
    return None

def normalize_tool_name(name: str) -> Optional[str]:
    """Normalize tool names across different LLM output conventions."""
    if not name or not isinstance(name, str):
        return None
    clean = name.strip().lower()
    if clean.startswith("functions."):
        clean = clean[10:]

    # Direct match
    if tool_registry.get(clean):
        return clean

    # Convert underscore to dot: e.g. browser_open -> browser.open, app_launch -> app.launch
    if "_" in clean:
        dotted = clean.replace("_", ".", 1)
        if tool_registry.get(dotted):
            return dotted

    # Common model aliases
    aliases = {
        "open_url": "browser.open",
        "navigate": "browser.navigate",
        "search": "browser.search",
        "launch": "app.launch",
        "open_app": "app.launch",
        "close_app": "app.close",
        "click": "mouse.click",
        "type": "keyboard.type",
        "screenshot": "screen.capture",
        "volume": "system.set_volume",
        "set_volume": "system.set_volume",
        "observe": "computer.observe",
        "observe_screen": "computer.observe",
        "get_computer_state": "computer.get_state",
        "get_state": "computer.get_state",
        "locate": "computer.locate",
        "locate_element": "computer.locate",
        "interact": "computer.interact",
        "close_tab": "browser.close_tab",
        "open_folder": "file.open_folder",
        "find_file": "file.find_and_open",
    }
    if clean in aliases and tool_registry.get(aliases[clean]):
        return aliases[clean]

    return None

def parse_llm_tool_calls(text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Parse model response for structured tool requests:
    Single: {"tool": "...", "arguments": {...}}
    Multi-step: {"steps": [{"tool": "...", "arguments": {...}}, ...]}
    Also handles OpenAI / standard function format: {"name": "...", "parameters": {...}}
    """
    data = extract_json_object(text)
    if not data or not isinstance(data, dict):
        return None

    steps = []
    # 1. Multi-step list
    if "steps" in data and isinstance(data["steps"], list):
        for s in data["steps"]:
            if isinstance(s, dict):
                raw_name = s.get("tool") or s.get("name") or s.get("function") or s.get("action")
                matched_tool = normalize_tool_name(raw_name)
                args = s.get("arguments") or s.get("parameters") or s.get("args") or {}
                if matched_tool:
                    steps.append({
                        "tool": matched_tool,
                        "arguments": args if isinstance(args, dict) else {},
                        "thought": data.get("thought", ""),
                    })
        if steps:
            return steps

    # 2. Single tool invocation
    raw_name = data.get("tool") or data.get("name") or data.get("function") or data.get("action")
    matched_tool = normalize_tool_name(raw_name)
    if matched_tool:
        args = data.get("arguments") or data.get("parameters") or data.get("args") or {}
        return [{
            "tool": matched_tool,
            "arguments": args if isinstance(args, dict) else {},
            "thought": data.get("thought", ""),
        }]

    return None

def build_tool_system_prompt() -> str:
    """
    Dynamically generates the complete tool system instruction for AI models.
    Lists all registered tool schemas and defines actionable vs conversational behavior.
    """
    tools = tool_registry.list_tools()
    tool_lines = []
    for t in tools:
        params = t.get("parameters", {}).get("properties", {})
        param_items = [f"{k}: {v.get('type', 'any')}" for k, v in params.items()]
        param_sig = ", ".join(param_items)
        tool_lines.append(f"- {t['name']}({param_sig}): {t['description']}")

    tool_manifest = "\n".join(tool_lines)

    return (
        "You are NOVA, an advanced personal AI desktop assistant for Windows with direct, general-purpose computer use capabilities.\n\n"
        "=== CAPABILITIES & TOOLS ===\n"
        "You have direct access to execute computer, desktop, browser, UI automation, and OS actions on the host Windows workstation. "
        "Here are your active registered tools:\n"
        f"{tool_manifest}\n\n"
        "=== GENERAL COMPUTER USE DECISION RULES ===\n"
        "1. SEE → UNDERSTAND → PLAN → ACT → OBSERVE → VERIFY → ADAPT:\n"
        "   When interacting with unfamiliar user interfaces, websites, dialogs, or applications:\n"
        "   - Use 'computer.observe' to inspect the screen and accessible UI controls.\n"
        "   - Use 'computer.locate' or 'computer.interact' to target buttons, input fields, menus, or icons dynamically by description without hardcoded coordinates.\n"
        "   - Prefer specialized tools ('app.launch', 'browser.open', 'system.set_volume', 'file.read_text') when available as they provide direct OS verification.\n\n"
        "2. ENTITY DISAMBIGUATION:\n"
        "   - Distinguish between application, browser tab, window, file, folder, and UI element.\n"
        "   - 'Close YouTube' -> browser tab control ('browser.close_tab') rather than terminating Chrome.\n"
        "   - 'Close Chrome' -> application control ('app.close').\n"
        "   - 'Close this window' -> active window control ('window.close').\n"
        "   - 'Open Downloads' -> folder control ('file.open_folder').\n"
        "   - 'Open the PDF I downloaded' -> file search ('file.find_and_open').\n\n"
        "3. CONVERSATIONAL REQUESTS:\n"
        "   If the user asks an informational, conceptual, or conversational question (e.g. 'What is YouTube?', 'Who was Ada Lovelace?', 'Explain quantum physics', 'How are you?'), "
        "   respond with a natural, concise spoken answer. DO NOT emit any tool calls for conversational questions.\n\n"
        "4. ACTION REQUESTS:\n"
        "   If the user asks you to perform an action, open an app, control the browser, search a website, click, type, manage files, shut down, restart, or inspect the screen, "
        "   YOU MUST SELECT AND RETURN A STRUCTURED TOOL CALL in JSON format:\n"
        "   ```json\n"
        "   {\n"
        "     \"tool\": \"<registered_tool_name>\",\n"
        "     \"arguments\": { <arguments> }\n"
        "   }\n"
        "   ```\n"
        "   Or for multi-step tasks:\n"
        "   ```json\n"
        "   {\n"
        "     \"steps\": [\n"
        "       { \"tool\": \"<tool_1>\", \"arguments\": { ... } },\n"
        "       { \"tool\": \"<tool_2>\", \"arguments\": { ... } }\n"
        "     ]\n"
        "   }\n"
        "   ```\n\n"
        "   CRITICAL SECURITY & PERMISSION RULE:\n"
        "   For sensitive actions like shutting down ('system.power'), restarting, or deleting files ('file.delete'), DO NOT ask for confirmation in text. "
        "   NOVA has a built-in security and permission gateway that automatically intercepts these actions and asks the user for confirmation. "
        "   ALWAYS emit the JSON tool call directly so NOVA's permission gateway can handle confirmation safely.\n\n"
        "5. AMBIGUOUS ACTION REQUESTS:\n"
        "   If the user asks you to perform an action but omitted critical details (e.g. 'Play a video on YouTube' without specifying which video), "
        "   ask a brief, direct clarification (e.g. 'Which video would you like me to play on YouTube?'). "
        "   NEVER state that you cannot control the browser or computer! You HAVE direct browser and computer control tools.\n\n"
        "6. POST-EXECUTION REASONING:\n"
        "   When tool results are provided, evaluate if further tools are required. If the request has been fully satisfied, "
        "   provide a concise confirmation message for TTS speech.\n\n"
        "7. SEARCH vs PLAY COMPLETION REQUIREMENTS:\n"
        "   - 'search for X' or 'find X' (e.g. 'Search YouTube for Arijit Singh', 'Find a Minecraft video'):\n"
        "     Goal is SEARCH. The completion requirement is that search results are displayed. Return 'browser.search'.\n"
        "   - 'play X' (e.g. 'Play Soong Yeshanagula Anirudh on YouTube', 'Play the first result', 'Play the song X on YouTube'):\n"
        "     Goal is PLAY + VERIFY_PLAYBACK. The completion requirement is that the requested media is opened and active playback is actually verified. Return 'browser.play_media'.\n"
        "   - 'pause X': Goal is PAUSE. Return 'browser.click' with target 'pause' or 'media.play_pause'.\n"
        "   - 'resume X': Goal is RESUME. Return 'browser.click' with target 'play' or 'media.play_pause'.\n"
        "   - 'stop X': Goal is STOP. Return 'browser.close_tab' or 'media.stop'.\n"
        "   - CRITICAL: Never report 'Done' or 'Playing' unless the post-condition has actually been verified.\n"
    )


def plan_task_from_natural_language(user_input: str) -> Optional[List[Dict[str, Any]]]:
    """
    Deterministic semantic planner for computer control tasks.
    Enables instant, resilient local desktop control even when offline.
    """
    text = user_input.strip()
    lower = text.lower()

    # 1. Check if user input is already a raw JSON tool call
    if text.startswith("{") and text.endswith("}"):
        parsed = extract_json_object(text)
        if parsed:
            calls = parse_llm_tool_calls(text)
            if calls:
                return calls

    # 2. Battery query
    if any(k in lower for k in ["battery", "battery percentage", "battery level", "power status"]):
        return [{"tool": "system.battery", "arguments": {}}]

    # 3. System Status / Metrics
    if any(k in lower for k in ["system status", "system info", "cpu usage", "ram usage", "specs"]):
        return [{"tool": "system.status", "arguments": {}}]

    # 4. Computer / Screen observation
    if any(k in lower for k in ["observe screen", "what's on my screen", "what is on my screen", "inspect ui", "inspect desktop", "get computer state", "observe computer"]):
        return [{"tool": "computer.observe", "arguments": {"include_screenshot": True, "include_ui_elements": True}}]

    # Screenshot / Screen vision
    if any(k in lower for k in ["take a screenshot", "screenshot", "screen capture", "capture display", "viewfinder"]):
        return [{"tool": "screen.capture", "arguments": {"save_to_disk": True, "return_base64": True}}]

    if any(k in lower for k in ["inspect screen", "screen info", "display resolution"]):
        return [{"tool": "screen.inspect", "arguments": {}}]

    # 5. Volume controls
    if "volume" in lower:
        vol_match = re.search(r'(\d{1,3})', lower)
        if "set" in lower or "change" in lower or (vol_match and "to" in lower):
            level = int(vol_match.group(1)) if vol_match else 50
            return [{"tool": "system.set_volume", "arguments": {"level": max(0, min(100, level))}}]
        elif "unmute" in lower:
            return [{"tool": "system.mute", "arguments": {"mute": False}}]
        elif "mute" in lower:
            return [{"tool": "system.mute", "arguments": {"mute": True}}]
        else:
            return [{"tool": "system.get_volume", "arguments": {}}]

    if "mute" in lower and "volume" not in lower:
        return [{"tool": "system.mute", "arguments": {"mute": "unmute" not in lower}}]

    # 6. Compound Multi-Step: "Open Chrome and search YouTube for <query>"
    multi_browser_search = re.search(
        r'open\s+(chrome|edge|browser)\s+and\s+search\s+(youtube|google|duckduckgo)\s+for\s+(.+)',
        text,
        re.IGNORECASE
    )
    if multi_browser_search:
        b_name = multi_browser_search.group(1).strip().lower()
        e_name = multi_browser_search.group(2).strip().lower()
        query = multi_browser_search.group(3).strip().rstrip(".")
        return [
            {
                "tool": "browser.search",
                "arguments": {"query": query, "engine": e_name, "browser": b_name},
                "thought": f"Search {e_name} in {b_name} for '{query}'",
            }
        ]

    # 7. Search platform: "search youtube for <query>" or "search google for <query>"
    search_match = re.search(r'search\s+(youtube|google|duckduckgo|bing)\s+for\s+(.+)', text, re.IGNORECASE)
    if search_match:
        engine = search_match.group(1).strip().lower()
        query = search_match.group(2).strip().rstrip(".")
        return [
            {
                "tool": "browser.search",
                "arguments": {"query": query, "engine": engine},
                "thought": f"Search {engine} for '{query}'",
            }
        ]

    # 7B. Media Search vs Playback Goal Semantics
    # "play the first result" / "play the first video" / "play the first [query] video"
    first_result_match = re.search(r'play\s+(?:the\s+)?(?:first|1st|top)\s+(?:result|video)?\s*(?:of|for)?\s*(.*)', text, re.IGNORECASE)
    if first_result_match and any(k in lower for k in ["first", "1st", "top"]):
        q_raw = first_result_match.group(1).strip().rstrip(".")
        clean_q = re.sub(r'\s+on\s+youtube\s*$', '', q_raw, flags=re.IGNORECASE).strip()
        clean_q = re.sub(r'^(?:video|song)\s*(?:of|for)?\s*', '', clean_q, flags=re.IGNORECASE).strip()
        return [
            {
                "tool": "browser.play_media",
                "arguments": {"query": clean_q, "platform": "youtube", "criteria": "first"},
                "thought": f"Play first result for '{clean_q or 'current view'}' on YouTube with verified playback",
            }
        ]

    # "play the song <song> on youtube", "play <query> on youtube", "play <query> video"
    play_media_match = re.search(r'play\s+(?:the\s+)?(?:song\s+|video\s+of\s+|video\s+|track\s+)?(.+)', text, re.IGNORECASE)
    if play_media_match and not any(k == lower for k in ["play", "play music"]):
        raw_target = play_media_match.group(1).strip().rstrip(".")
        if "on youtube" in raw_target.lower():
            clean_q = re.sub(r'\s+on\s+youtube\s*$', '', raw_target, flags=re.IGNORECASE).strip()
            platform = "youtube"
        elif "on google" in raw_target.lower():
            clean_q = re.sub(r'\s+on\s+google\s*$', '', raw_target, flags=re.IGNORECASE).strip()
            platform = "google"
        else:
            clean_q = raw_target
            platform = "youtube"

        criteria = "first" if any(k in clean_q.lower() for k in ["first", "1st", "top"]) else "best_match"
        if criteria == "first":
            clean_q = re.sub(r'^(?:the\s+)?(?:first|1st|top)\s+', '', clean_q, flags=re.IGNORECASE).strip()

        clean_q = re.sub(r'^(?:the\s+)?(?:song|video\s+of|video|track)\s+', '', clean_q, flags=re.IGNORECASE).strip()

        # If user did not specify a title (e.g. "Play a video on YouTube"), return None so AI asks clarification
        if clean_q.lower() in ["a video", "a youtube video", "video", "a song", "song", "a track", "track", "something", ""] or len(clean_q.strip()) <= 1:
            return None

        return [
            {
                "tool": "browser.play_media",
                "arguments": {"query": clean_q, "platform": platform, "criteria": criteria},
                "thought": f"Search, select, and verify playback for '{clean_q}' on {platform}",
            }
        ]

    # "find a <query> video" or "find <query> video" (Search only)
    find_video_match = re.search(r'(?:find|lookup)\s+(?:a\s+)?(.+?\s+video|.+?\s+song)', text, re.IGNORECASE)
    if find_video_match and not lower.startswith("play"):
        q_raw = find_video_match.group(1).strip().rstrip(".")
        return [
            {
                "tool": "browser.search",
                "arguments": {"query": q_raw, "engine": "youtube"},
                "thought": f"Search YouTube for '{q_raw}'",
            }
        ]

    # 8. Open YouTube / Open Google / Open Website
    if "youtube" in lower and ("open" in lower or "launch" in lower or lower == "youtube"):
        return [{"tool": "browser.open", "arguments": {"url": "https://www.youtube.com"}}]
    if "google" in lower and ("open" in lower or "launch" in lower):
        return [{"tool": "browser.open", "arguments": {"url": "https://www.google.com"}}]

    # 9. Compound Multi-Step: "Open Notepad and type <text>"
    multi_type_match = re.search(r'open\s+(\w+)\s+and\s+type\s+(.+)', lower, re.IGNORECASE)
    if multi_type_match:
        app_name = multi_type_match.group(1).strip()
        # Extract original casing for typing
        raw_match = re.search(r'type\s+(.+)', text, re.IGNORECASE)
        type_content = raw_match.group(1).strip() if raw_match else "Hello NOVA"
        return [
            {"tool": "app.launch", "arguments": {"name": app_name}, "thought": f"Launch {app_name}"},
            {"tool": "keyboard.type", "arguments": {"text": type_content}, "thought": f"Type '{type_content}'"},
        ]

    # 10. Folder Operations: "Open Downloads", "Open Documents", "Open Desktop"
    for folder_key in ["downloads", "documents", "desktop", "pictures", "music", "videos"]:
        if f"open {folder_key}" in lower or f"open my {folder_key}" in lower:
            folder_path = str(Path.home() / folder_key.capitalize())
            return [{"tool": "file.open_folder", "arguments": {"path": folder_path}}]

    # 11. Recent File search & open: "Open the PDF I downloaded"
    if any(k in lower for k in ["pdf i downloaded", "downloaded pdf", "open the pdf", "recent pdf"]):
        return [{"tool": "file.find_and_open", "arguments": {"extension": "pdf"}}]

    # 12. Dynamic UI Element Interactions (e.g. "Click the search box", "Click Continue", "Click the blue button")
    if lower.startswith("double click ") or lower.startswith("double-click "):
        target_ctrl = re.sub(r'^(?:double click|double-click)\s+(?:the\s+|on\s+)?', '', text, flags=re.IGNORECASE).strip().rstrip(".")
        return [{"tool": "computer.interact", "arguments": {"action": "double_click", "target_description": target_ctrl}}]

    if lower.startswith("right click ") or lower.startswith("right-click "):
        target_ctrl = re.sub(r'^(?:right click|right-click)\s+(?:the\s+|on\s+)?', '', text, flags=re.IGNORECASE).strip().rstrip(".")
        return [{"tool": "computer.interact", "arguments": {"action": "right_click", "target_description": target_ctrl}}]

    if lower.startswith("click ") or lower.startswith("tap "):
        # Check coordinate click: "click at 400 300"
        coord_match = re.search(r'click\s+(?:at\s+)?(\d{1,4})\s*[,x\s]\s*(\d{1,4})', lower)
        if coord_match:
            return [{"tool": "mouse.click", "arguments": {"x": int(coord_match.group(1)), "y": int(coord_match.group(2))}}]

        if any(k in lower for k in ["play", "video", "play button", "pause"]):
            return [{"tool": "browser.click", "arguments": {"target": "play"}}]
        if lower in ["click", "click mouse", "mouse click"]:
            return [{"tool": "mouse.click", "arguments": {}}]

        target_ctrl = re.sub(r'^(?:click|tap)\s+(?:the\s+|on\s+)?', '', text, flags=re.IGNORECASE).strip().rstrip(".")
        return [{"tool": "computer.interact", "arguments": {"action": "locate_and_click", "target_description": target_ctrl}}]

    # 13. Dynamic UI Localization: "Locate <target>", "Find button <target>"
    if lower.startswith("locate ") or lower.startswith("find button "):
        target_ctrl = re.sub(r'^(?:locate|find button)\s+(?:the\s+)?', '', text, flags=re.IGNORECASE).strip().rstrip(".")
        return [{"tool": "computer.locate", "arguments": {"description": target_ctrl}}]

    # 14. Type text: "type <text>"
    if lower.startswith("type "):
        raw_text = text[5:].strip()
        return [{"tool": "keyboard.type", "arguments": {"text": raw_text}}]

    # 15. Press key: "press enter", "press esc"
    key_match = re.search(r'press\s+key\s+(\w+)|press\s+(enter|tab|esc|backspace|space|up|down)', lower)
    if key_match:
        k = key_match.group(1) or key_match.group(2)
        return [{"tool": "keyboard.press", "arguments": {"key": k}}]

    # 16. Browser tab & scroll controls
    if "scroll down" in lower or "page down" in lower:
        return [{"tool": "browser.scroll", "arguments": {"clicks": -300}}]
    if "scroll up" in lower or "page up" in lower:
        return [{"tool": "browser.scroll", "arguments": {"clicks": 300}}]
    if "new tab" in lower or "open tab" in lower:
        return [{"tool": "browser.open_tab", "arguments": {}}]
    if "switch tab" in lower or "next tab" in lower:
        return [{"tool": "browser.switch_tab", "arguments": {"direction": "next"}}]
    if "close tab" in lower or "close active tab" in lower:
        return [{"tool": "browser.close_tab", "arguments": {}}]

    # 17. Close entity disambiguation: "Close YouTube" vs "Close Chrome" vs "Close window"
    if lower.startswith("close ") or lower.startswith("quit ") or lower.startswith("exit "):
        target_name = re.sub(r'^(?:close|quit|exit)\s+', '', lower).strip().rstrip(".")
        if target_name in ["youtube", "google", "github", "reddit", "twitter", "tab", "browser tab"]:
            cased = "YouTube" if target_name == "youtube" else ("GitHub" if target_name == "github" else target_name.capitalize())
            return [{"tool": "browser.close_tab", "arguments": {"title_match": cased}}]
        if target_name in ["window", "active window", "this window", "current window"]:
            return [{"tool": "window.close", "arguments": {"title": ""}}]
        return [{"tool": "app.close", "arguments": {"name": target_name}}]

    # 18. Application Launch / Open
    if lower.startswith("open ") or lower.startswith("launch "):
        target_app = text.split(maxsplit=1)[1].strip().rstrip(".")
        # Exclude web URLs or domains
        if "." in target_app and "/" in target_app:
            return [{"tool": "browser.open", "arguments": {"url": target_app}}]
        return [{"tool": "app.launch", "arguments": {"name": target_app}}]

    # 19. Application Focus / Switch
    if lower.startswith("focus ") or lower.startswith("switch to "):
        target_app = text.replace("switch to ", "").replace("focus ", "").strip()
        return [{"tool": "app.focus", "arguments": {"name": target_app}}]

    # 20. Window management
    if "minimize" in lower:
        m_match = re.search(r'minimize\s+(?:window\s+)?(.+)', lower)
        t = m_match.group(1).strip() if m_match else ""
        return [{"tool": "window.minimize", "arguments": {"title": t}}]
    if "maximize" in lower:
        m_match = re.search(r'maximize\s+(?:window\s+)?(.+)', lower)
        t = m_match.group(1).strip() if m_match else ""
        return [{"tool": "window.maximize", "arguments": {"title": t}}]
    if "restore window" in lower:
        return [{"tool": "window.restore", "arguments": {"title": ""}}]
    if "list windows" in lower:
        return [{"tool": "window.list", "arguments": {}}]

    # 21. Media controls
    if any(k == lower for k in ["play", "play music", "pause music", "resume music"]):
        return [{"tool": "media.play_pause", "arguments": {}}]
    if any(k in lower for k in ["next song", "next track", "skip song"]):
        return [{"tool": "media.next", "arguments": {}}]
    if any(k in lower for k in ["previous song", "prev track"]):
        return [{"tool": "media.prev", "arguments": {}}]

    # 22. File Operations
    if "search files" in lower or "find files" in lower:
        pat_match = re.search(r'(?:search files for|find files matching|search files)\s+(.+)', lower)
        pattern = pat_match.group(1).strip() if pat_match else "*.*"
        return [{"tool": "file.search", "arguments": {"pattern": pattern}}]

    if "read file" in lower:
        f_match = re.search(r'read file\s+(.+)', lower)
        fpath = f_match.group(1).strip() if f_match else ""
        return [{"tool": "file.read_text", "arguments": {"path": fpath}}]

    if "delete file" in lower or "remove file" in lower:
        f_match = re.search(r'(?:delete file|remove file)\s+(.+)', lower)
        fpath = f_match.group(1).strip() if f_match else ""
        return [{"tool": "file.delete", "arguments": {"path": fpath}}]

    # 23. Power controls (Confirmation required)
    if "shut down" in lower or "shutdown" in lower:
        return [{"tool": "system.power", "arguments": {"action": "shutdown"}}]
    if "restart" in lower or "reboot" in lower:
        return [{"tool": "system.power", "arguments": {"action": "restart"}}]

    # 24. Process listing
    if "processes" in lower or "task manager" in lower:
        return [{"tool": "system.processes", "arguments": {"limit": 15}}]

    return None

def classify_task_control_intent(text: str) -> Optional[Dict[str, Any]]:
    """
    Classify whether a user request is an explicit task execution control command:
    - PAUSE: immediately stop active execution, preserve context
    - RESUME: restore paused task and continue from next pending step
    - CANCEL: permanently terminate target or active task
    """
    clean = text.strip().lower().rstrip(".!")

    # 1. PAUSE commands
    pause_phrases = [
        "pause", "pause that", "pause task", "pause the task", "wait",
        "hold on", "stop for a moment", "pause execution", "pause please",
        "hold on a second", "wait a minute", "pause what you are doing"
    ]
    if clean in pause_phrases or clean.startswith("pause that") or clean.startswith("pause task"):
        return {"action": "PAUSE"}

    # 2. RESUME commands
    resume_phrases = [
        "continue", "resume", "continue what you were doing", "resume the previous task",
        "continue the paused task", "resume task", "continue task", "resume the task",
        "resume paused task", "keep going", "continue execution", "continue the previous task"
    ]
    if clean in resume_phrases or clean.startswith("resume ") or clean.startswith("continue "):
        task_match = re.search(r'(?:resume|continue)\s+(?:task\s+)?(task_[a-f0-9]+)', clean)
        target = task_match.group(1) if task_match else None
        return {"action": "RESUME", "target": target}

    # 3. CANCEL commands
    cancel_phrases = [
        "cancel that", "cancel the task", "forget that task", "stop this task completely",
        "cancel task", "cancel current task", "stop task", "abort task", "cancel execution"
    ]
    if clean in cancel_phrases or clean.startswith("cancel task") or clean.startswith("cancel that"):
        task_match = re.search(r'(?:cancel|forget|stop)\s+(?:task\s+)?(task_[a-f0-9]+)', clean)
        target = task_match.group(1) if task_match else None
        return {"action": "CANCEL", "target": target}

    return None


def plan_task_from_goal(goal: Any, current_state: Optional[Any] = None) -> List[Dict[str, Any]]:
    """
    State-aware task planning: inspects current ComputerState before selecting actions.
    Emits atomic actions targeted at fulfilling the goal's SuccessCondition.
    """
    category = getattr(goal, "goal_category", "")
    target = getattr(goal, "target", "")
    entities = getattr(goal, "entities", {})

    # 1. Media Playback (YouTube, etc.)
    if category == "media_playback":
        query = entities.get("query", target)
        platform = entities.get("platform", "youtube")
        return [
            {
                "tool": "browser.play_media",
                "arguments": {"query": query, "platform": platform, "criteria": "first"},
                "thought": f"Search, select, and verify active playback for '{query}' on {platform}",
            }
        ]

    # 2. Messaging (WhatsApp, etc.)
    if category == "messaging":
        app_name = entities.get("app", "whatsapp")
        recipient = entities.get("recipient", "contact")
        message = entities.get("message", "Hello")

        steps = []
        is_already_open = False
        if current_state:
            open_wins = getattr(current_state, "open_windows", [])
            for w in open_wins:
                title = (getattr(w, "title", "") or "").lower()
                pname = (getattr(w, "process_name", "") or "").lower()
                app_n = (getattr(w, "app_name", "") or "").lower()
                if "whatsapp" in title or "whatsapp" in pname or "whatsapp" in app_n:
                    is_already_open = True
                    break

        if not is_already_open:
            steps.append({
                "tool": "app.launch",
                "arguments": {"name": app_name},
                "thought": f"Launch {app_name}",
            })
        else:
            steps.append({
                "tool": "app.focus",
                "arguments": {"name": app_name},
                "thought": f"Switch focus to {app_name}",
            })

        steps.extend([
            {
                "tool": "computer.interact",
                "arguments": {
                    "action": "locate_and_click",
                    "target_description": "Search or start a new chat",
                },
                "thought": f"Locate search field to find {recipient}",
            },
            {
                "tool": "keyboard.type",
                "arguments": {"text": recipient},
                "thought": f"Type recipient name '{recipient}'",
            },
            {
                "tool": "keyboard.press",
                "arguments": {"key": "enter"},
                "thought": "Open conversation with recipient",
            },
            {
                "tool": "keyboard.type",
                "arguments": {"text": message},
                "thought": f"Type message '{message}'",
            },
            {
                "tool": "keyboard.press",
                "arguments": {"key": "enter"},
                "thought": "Send message",
            },
        ])
        return steps

    # 3. Application Lifecycle (Close, Open, Focus)
    if category == "app_lifecycle":
        app_name = entities.get("app_name", target)
        condition = getattr(goal, "success_condition", None)
        c_type = getattr(condition, "type", "") if condition else ""
        if c_type == "app_closed":
            return [
                {
                    "tool": "app.close",
                    "arguments": {"name": app_name},
                    "thought": f"Close {app_name}",
                }
            ]
        elif c_type in ["app_running", "app_focused"]:
            if current_state and getattr(current_state, "active_window", None):
                act = current_state.active_window
                t_lower = app_name.lower()
                if t_lower in act.title.lower() or t_lower in act.process_name.lower() or t_lower in act.app_name.lower():
                    return []
            return [
                {
                    "tool": "app.launch",
                    "arguments": {"name": app_name},
                    "thought": f"Launch {app_name}",
                }
            ]

    # 4. Browser Tab Management (Close Tab)
    if category == "browser_tab_management":
        title_match = entities.get("title_match", target)
        return [
            {
                "tool": "browser.close_tab",
                "arguments": {"title_match": title_match},
                "thought": f"Close tab matching '{title_match}'",
            }
        ]

    # 5. Fallback to natural language planner
    raw = getattr(goal, "raw_prompt", "")
    return plan_task_from_natural_language(raw) or []


def generate_recovery_plan(task: Any, state: Any, last_res: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Phase E: Dynamic replanning and recovery when execution is interrupted or verification fails.
    Compares observed ComputerState with expected goal state and generates corrective actions.
    """
    if not task:
        return None

    rec_attempts = getattr(task, "recovery_attempts", 0)
    max_rec = getattr(task, "max_recovery_attempts", 3)
    if rec_attempts >= max_rec:
        return None

    condition = getattr(task, "success_condition", None)
    cond_type = getattr(condition, "type", "") if condition else ""
    target = getattr(condition, "target", "") if condition else ""

    # Recovery 1: Application failed to close via psutil (e.g. UWP app inside ApplicationFrameHost)
    if cond_type in ["app_closed", "window_closed"]:
        target_lower = target.lower()
        open_windows = getattr(state, "open_windows", [])
        for w in open_windows:
            w_title = getattr(w, "title", "")
            w_proc = getattr(w, "process_name", "")
            w_app = getattr(w, "app_name", "")
            if target_lower in w_title.lower() or target_lower in w_proc.lower() or target_lower in w_app.lower():
                return [
                    {
                        "tool": "window.close",
                        "arguments": {"title": w_title},
                        "thought": f"Recovery: Close window '{w_title}' directly via OS window manager",
                    }
                ]

    # Recovery 2: Media playback did not start (e.g. YouTube Ad, consent modal, or player paused)
    if cond_type in ["playback_active", "media_playing"]:
        ui_elems = getattr(state, "ui_elements", [])
        for elem in ui_elems:
            el_name = (getattr(elem, "name", "") or "").lower()
            if "skip ad" in el_name or "skip ads" in el_name:
                return [
                    {
                        "tool": "computer.interact",
                        "arguments": {"action": "locate_and_click", "target_description": "Skip Ad"},
                        "thought": "Recovery: Skip video advertisement",
                    },
                    {
                        "tool": "keyboard.press",
                        "arguments": {"key": "space"},
                        "thought": "Recovery: Resume video playback",
                    }
                ]

        return [
            {
                "tool": "keyboard.press",
                "arguments": {"key": "space"},
                "thought": "Recovery: Toggle play/pause hotkey to initiate playback",
            }
        ]

    # Recovery 3: Target UI element could not be located
    if not last_res.get("success") and "locate" in str(last_res):
        if target:
            return [
                {
                    "tool": "app.focus",
                    "arguments": {"name": target},
                    "thought": f"Recovery: Re-focus {target} before re-attempting UI interaction",
                }
            ]

    return None



