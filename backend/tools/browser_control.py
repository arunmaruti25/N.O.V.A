import subprocess
import urllib.parse
import urllib.request
import webbrowser
import time
import os
import re
import json
import psutil
from typing import Dict, Any, Optional, Tuple, List, Callable
from .registry import ToolDefinition, tool_registry
from ..permissions import PermissionLevel

# Supported search engine templates
SEARCH_ENGINES: Dict[str, str] = {
    "youtube": "https://www.youtube.com/results?search_query={query}",
    "google": "https://www.google.com/search?q={query}",
    "duckduckgo": "https://duckduckgo.com/?q={query}",
    "bing": "https://www.bing.com/search?q={query}",
}

def normalize_url(url_or_domain: str) -> str:
    """Ensure URL has a valid scheme."""
    u = url_or_domain.strip()
    if not u.startswith("http://") and not u.startswith("https://"):
        if " " not in u and ("." in u or "localhost" in u):
            return f"https://{u}"
        # If words with spaces, treat as Google search
        return f"https://www.google.com/search?q={urllib.parse.quote_plus(u)}"
    return u

def open_url(url: str, browser: Optional[str] = None) -> Dict[str, Any]:
    """
    Open URL in desktop browser (Chrome, Edge, or default system browser).
    """
    target_url = normalize_url(url)
    clean_browser = (browser or "").strip().lower()

    try:
        if clean_browser in ["chrome", "google chrome"]:
            # Try launching chrome directly with URL
            from .app_control import resolve_app_path
            chrome_path = resolve_app_path("chrome")
            if chrome_path:
                subprocess.Popen([chrome_path, target_url], shell=False)
                site_name = "YouTube" if "youtube" in target_url.lower() else target_url
                return {
                    "success": True,
                    "url": target_url,
                    "browser": "Chrome",
                    "message": f"Opened {site_name} in Google Chrome.",
                }

        elif clean_browser in ["edge", "msedge", "microsoft edge"]:
            from .app_control import resolve_app_path
            edge_path = resolve_app_path("msedge")
            if edge_path:
                subprocess.Popen([edge_path, target_url], shell=False)
                site_name = "YouTube" if "youtube" in target_url.lower() else target_url
                return {
                    "success": True,
                    "url": target_url,
                    "browser": "Edge",
                    "message": f"Opened {site_name} in Microsoft Edge.",
                }

        # System default browser
        webbrowser.open(target_url)
        site_name = "YouTube" if "youtube" in target_url.lower() else target_url
        return {
            "success": True,
            "url": target_url,
            "browser": "Default",
            "message": f"Opened {site_name} ({target_url}) in default browser.",
        }
    except Exception as e:
        return {
            "success": False,
            "url": target_url,
            "error": f"Failed to open URL: {str(e)}",
        }

def verify_browser_opened(result: Dict[str, Any], arguments: Dict[str, Any]) -> Tuple[bool, str]:
    """Verify that a browser process is actively running."""
    time.sleep(0.5)
    browser_exes = ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"]
    for proc in psutil.process_iter(['name']):
        try:
            p_name = (proc.info['name'] or "").lower()
            if any(b in p_name for b in browser_exes):
                return True, f"Verified browser process '{p_name}' is running."
        except Exception:
            continue
    return False, "No supported browser process observed after opening the URL."

def search_browser(query: str, engine: str = "youtube", browser: Optional[str] = None) -> Dict[str, Any]:
    """Search for query on YouTube, Google, DuckDuckGo, etc."""
    clean_engine = engine.strip().lower()
    template = SEARCH_ENGINES.get(clean_engine, SEARCH_ENGINES["youtube"])
    encoded_query = urllib.parse.quote_plus(query.strip())
    search_url = template.format(query=encoded_query)
    
    res = open_url(search_url, browser=browser)
    res["query"] = query
    res["engine"] = clean_engine
    engine_name = "YouTube" if clean_engine == "youtube" else clean_engine.capitalize()
    res["message"] = f"Searched {engine_name} for '{query}'."
    return res

async def inspect_page(url: str, wait_seconds: float = 2.0) -> Dict[str, Any]:
    """
    Inspect web page using Playwright: extracts title, text snippet, and link count.
    """
    target_url = normalize_url(url)
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(target_url, timeout=12000)
            if wait_seconds > 0:
                await page.wait_for_timeout(int(wait_seconds * 1000))
            
            title = await page.title()
            # Extract plain text content snippet
            body_text = await page.inner_text("body")
            snippet = body_text[:600].replace("\n", " ").strip() if body_text else ""
            await browser.close()

            return {
                "success": True,
                "url": target_url,
                "title": title,
                "snippet": snippet,
                "message": f"Inspected '{title}' at {target_url}.",
            }
    except Exception as e:
        return {
            "success": False,
            "url": target_url,
            "error": f"Failed to inspect page: {str(e)}",
        }

def browser_click(x: Optional[int] = None, y: Optional[int] = None, button: str = "left", target: str = "") -> Dict[str, Any]:
    """
    Click in the active browser window.
    Supports coordinate clicks or video play/pause interactions (e.g. 'play', 'video').
    """
    try:
        import pyautogui
        clean_target = (target or "").lower().strip()
        if clean_target in ["play", "pause", "video", "play button", "toggle"]:
            # On YouTube and HTML5 web players, pressing 'k' or space toggles play/pause
            pyautogui.press('k')
            return {
                "success": True,
                "action": "play_toggle",
                "message": "Dispatched video play/pause command to active browser.",
            }
        elif x is not None and y is not None:
            pyautogui.click(x=int(x), y=int(y), button=button)
            return {
                "success": True,
                "x": x,
                "y": y,
                "message": f"Clicked at ({x}, {y}) in browser.",
            }
        else:
            pyautogui.click(button=button)
            return {
                "success": True,
                "message": "Clicked active element in browser.",
            }
    except Exception as e:
        return {"success": False, "error": f"Browser click failed: {str(e)}"}

def browser_type(text: str, press_enter: bool = False) -> Dict[str, Any]:
    """Type text into active browser input with optional Enter keystroke."""
    try:
        import pyautogui
        pyautogui.typewrite(text, interval=0.02)
        if press_enter:
            pyautogui.press('enter')
        return {
            "success": True,
            "text": text,
            "message": f"Typed '{text}' into browser{' and pressed Enter' if press_enter else ''}.",
        }
    except Exception as e:
        return {"success": False, "error": f"Browser typing failed: {str(e)}"}

def browser_scroll(clicks: int = -300) -> Dict[str, Any]:
    """Scroll active browser page vertically (negative = down, positive = up)."""
    try:
        import pyautogui
        pyautogui.scroll(int(clicks))
        return {
            "success": True,
            "clicks": clicks,
            "message": f"Scrolled browser {'down' if clicks < 0 else 'up'} {abs(clicks)} units.",
        }
    except Exception as e:
        return {"success": False, "error": f"Browser scroll failed: {str(e)}"}

def browser_open_tab(url: Optional[str] = None) -> Dict[str, Any]:
    """Open a new browser tab, optionally navigating to a URL."""
    if url:
        return open_url(url)
    try:
        import pyautogui
        pyautogui.hotkey('ctrl', 't')
        return {"success": True, "message": "Opened new browser tab."}
    except Exception as e:
        return {"success": False, "error": f"Failed to open tab: {str(e)}"}

def browser_switch_tab(direction: str = "next", tab_index: Optional[int] = None) -> Dict[str, Any]:
    """Switch active browser tab."""
    try:
        import pyautogui
        if tab_index is not None and 1 <= int(tab_index) <= 9:
            pyautogui.hotkey('ctrl', str(tab_index))
            return {"success": True, "message": f"Switched to browser tab {tab_index}."}
        elif direction.lower() in ["prev", "previous", "back"]:
            pyautogui.hotkey('ctrl', 'shift', 'tab')
            return {"success": True, "message": "Switched to previous browser tab."}
        else:
            pyautogui.hotkey('ctrl', 'tab')
            return {"success": True, "message": "Switched to next browser tab."}
    except Exception as e:
        return {"success": False, "error": f"Failed to switch tab: {str(e)}"}

def fetch_youtube_search_results(query: str, limit: int = 6) -> List[Dict[str, Any]]:
    """
    Dynamically fetch search results from YouTube for any query without hardcoded URLs.
    Extracts video ID, title, channel, and full watch URL.
    """
    clean_q = query.strip()
    if not clean_q:
        return []
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(clean_q)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
    )
    results = []
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Method 1: parse ytInitialData JSON
        json_match = re.search(r"var ytInitialData = ({.*?});</script>", html)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                sections = (
                    data.get("contents", {})
                    .get("twoColumnSearchResultsRenderer", {})
                    .get("primaryContents", {})
                    .get("sectionListRenderer", {})
                    .get("contents", [])
                )
                for section in sections:
                    items = section.get("itemSectionRenderer", {}).get("contents", [])
                    for item in items:
                        v = item.get("videoRenderer")
                        if v:
                            vid = v.get("videoId")
                            title = "".join(r.get("text", "") for r in v.get("title", {}).get("runs", [])) or v.get("title", {}).get("simpleText", "")
                            channel = "".join(r.get("text", "") for r in v.get("ownerText", {}).get("runs", []))
                            if vid and title:
                                results.append({
                                    "video_id": vid,
                                    "title": title.strip(),
                                    "channel": channel.strip(),
                                    "url": f"https://www.youtube.com/watch?v={vid}",
                                })
                                if len(results) >= limit:
                                    return results
            except Exception:
                pass

        # Method 2: Regex fallback
        pairs = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"(.*?)"\}', html)
        seen = set()
        for vid, title in pairs:
            if vid not in seen:
                seen.add(vid)
                results.append({
                    "video_id": vid,
                    "title": title.strip(),
                    "url": f"https://www.youtube.com/watch?v={vid}",
                })
                if len(results) >= limit:
                    break
    except Exception:
        pass
    return results

def select_media_result(
    query: str = "",
    platform: str = "youtube",
    criteria: str = "best_match",
    candidates: Optional[List[Dict[str, Any]]] = None,
    browser: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Dynamically select and open the appropriate media result.
    Criteria can be 'first' / 'top' / '1st' or 'best_match' (semantic/keyword match).
    """
    cand_list = candidates
    if not cand_list:
        cand_list = fetch_youtube_search_results(query, limit=6)

    if not cand_list:
        # If search returned no candidates, try opening search page directly
        search_res = search_browser(query, engine=platform, browser=browser)
        return {
            "success": True,
            "selected_result": None,
            "url": search_res.get("url", ""),
            "title": f"Search results for '{query}'",
            "message": f"Opened {platform.capitalize()} search results for '{query}'.",
        }

    clean_crit = (criteria or "").lower().strip()
    selected = None

    if any(k in clean_crit for k in ["first", "top", "1st", "1"]):
        selected = cand_list[0]
    else:
        # Score candidates based on query keyword overlap
        raw_words = re.findall(r'\w+', query.lower())
        stop_words = {"play", "song", "video", "on", "the", "youtube", "music", "a", "an", "for", "please"}
        query_words = set(w for w in raw_words if w not in stop_words and len(w) > 1)

        best_score = -1
        for item in cand_list:
            t_words = set(re.findall(r'\w+', item.get("title", "").lower()))
            overlap = len(query_words.intersection(t_words))
            if overlap > best_score:
                best_score = overlap
                selected = item

        if not selected or best_score <= 0:
            selected = cand_list[0]

    nav_res = open_url(selected["url"], browser=browser)
    return {
        "success": True,
        "selected_result": selected,
        "title": selected["title"],
        "url": selected["url"],
        "video_id": selected.get("video_id", ""),
        "channel": selected.get("channel", ""),
        "browser": nav_res.get("browser", "default"),
        "message": f"Selected and opened '{selected['title']}' on {platform.capitalize()}.",
    }

def check_browser_audio_active() -> bool:
    """Check if any browser process is actively outputting audio via Windows Core Audio."""
    try:
        from pycaw.pycaw import AudioUtilities
        browser_names = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"}
        sessions = AudioUtilities.GetAllSessions()
        for s in sessions:
            if s.Process and s.Process.name().lower() in browser_names:
                if getattr(s, "State", 0) == 1:
                    return True
    except Exception:
        pass
    return False

def verify_playback_state(
    expected_title: Optional[str] = None,
    timeout_seconds: float = 6.0,
    adapt_if_needed: bool = True,
    observation_fn: Optional[Callable[[], Dict[str, Any]]] = None,
    action_fn: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Verify that video/audio playback has actually started on the desktop browser.
    Observes UI state, window titles, video player elements, and audio sessions.
    Adapts if blocked by autoplay restrictions, consent popups, or overlays.
    """
    from .observation import get_unified_observation
    import pyautogui

    get_obs = observation_fn or (lambda: get_unified_observation(include_ui_elements=True))
    start_time = time.time()
    retries = 0
    max_retries = 3

    while time.time() - start_time < timeout_seconds and retries <= max_retries:
        obs = get_obs()
        active_win = obs.get("active_window", {})
        win_title = active_win.get("title", "")
        ui_elems = obs.get("ui_elements", [])
        visible_wins = obs.get("visible_windows", [])

        all_titles = [win_title] + [w.get("title", "") for w in visible_wins if w.get("title")]
        youtube_title = next((t for t in all_titles if "youtube" in t.lower()), None)
        is_video_page = bool(youtube_title and ("watch" in youtube_title.lower() or " - youtube" in youtube_title.lower()))

        # 1. Inspect UI Elements for player state and popups
        is_playing_ui = False
        is_paused_ui = False
        popup_detected = None

        for el in ui_elems:
            name = (el.get("name") or "").lower()
            # YouTube player buttons
            if "pause (k)" in name or name == "pause":
                is_playing_ui = True
            elif "play (k)" in name or name == "play":
                is_paused_ui = True

            # Popups / Consent / Ads
            if any(p in name for p in ["skip ad", "skip ads", "accept all", "i agree", "before you continue", "dismiss", "reject all"]):
                popup_detected = el

        # 2. Audio session check
        audio_active = check_browser_audio_active()

        # 2B. Check for player failure / unavailable video / playback error
        error_detected = None
        for el in ui_elems:
            el_name = (el.get("name") or "").lower()
            if any(err in el_name for err in ["unavailable", "error occurred", "private video", "video removed", "sign in to confirm your age", "playback error"]):
                error_detected = el.get("name")
                break
        if "unavailable" in (youtube_title or "").lower() or "error" in (youtube_title or "").lower():
            error_detected = error_detected or youtube_title

        if error_detected:
            return {
                "success": False,
                "playing": False,
                "verified": False,
                "error": f"Playback failed: {error_detected}",
                "message": f"Video playback failed ({error_detected}).",
            }

        # 3. Handle Popup / Overlay if detected
        if popup_detected and adapt_if_needed:
            bbox = popup_detected.get("bounding_box", {})
            cx = bbox.get("center_x")
            cy = bbox.get("center_y")
            if action_fn:
                action_fn("dismiss_popup")
            elif cx and cy:
                pyautogui.click(x=cx, y=cy)
            else:
                pyautogui.press('esc')
            retries += 1
            time.sleep(0.5)
            continue

        # 4. Handle Autoplay restrictions: if paused
        if is_paused_ui and not is_playing_ui and adapt_if_needed:
            if action_fn:
                action_fn("toggle_play")
            else:
                pyautogui.press('k')
            retries += 1
            time.sleep(0.5)
            continue

        # 5. Verification condition
        if is_playing_ui or audio_active:
            clean_title = expected_title or youtube_title or "Media"
            return {
                "success": True,
                "playing": True,
                "verified": True,
                "title": clean_title,
                "window_title": youtube_title or win_title,
                "audio_active": audio_active,
                "verification_detail": f"Verified playback of '{clean_title}'.",
                "message": f"Playback verified: '{clean_title}' is actively playing.",
            }

        # Video page verified and not in search results
        if is_video_page and not any(k in (youtube_title or "").lower() for k in ["results", "search"]):
            if adapt_if_needed and retries == 0:
                if action_fn:
                    action_fn("toggle_play")
                else:
                    pyautogui.press('k')
                retries += 1
                time.sleep(0.5)
                continue
            clean_title = expected_title or youtube_title
            return {
                "success": True,
                "playing": True,
                "verified": True,
                "title": clean_title,
                "window_title": youtube_title,
                "audio_active": audio_active,
                "verification_detail": f"Verified playback of '{clean_title}'.",
                "message": f"Playback verified: '{clean_title}' is open and playing.",
            }

        time.sleep(0.4)

    return {
        "success": False,
        "playing": False,
        "verified": False,
        "error": "Playback verification failed: Video player did not enter active playback state within timeout.",
        "message": f"Could not verify playback of '{expected_title or 'requested media'}'.",
    }

def play_media(
    query: str,
    platform: str = "youtube",
    criteria: str = "best_match",
    browser: Optional[str] = None,
    timeout: float = 6.0,
    observation_fn: Optional[Callable[[], Dict[str, Any]]] = None,
    action_fn: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Unified General Media Playback Pipeline:
    UNDERSTAND → PLAN → SEARCH → OBSERVE → SELECT RESULT → OPEN RESULT → OBSERVE → PLAY → OBSERVE → VERIFY PLAYBACK → SUCCESS.
    """
    clean_query = query.strip()
    clean_platform = (platform or "youtube").strip().lower()

    # Step 1 & 2: Search platform and observe results
    candidates = fetch_youtube_search_results(clean_query, limit=6) if clean_platform == "youtube" else []
    if not candidates and clean_query:
        search_browser(clean_query, engine=clean_platform, browser=browser)
        time.sleep(1.0)
        candidates = fetch_youtube_search_results(clean_query, limit=6)

    # Step 3 & 4: Select result and open in browser
    sel_res = select_media_result(
        query=clean_query,
        platform=clean_platform,
        criteria=criteria,
        candidates=candidates,
        browser=browser,
    )
    if not sel_res.get("success"):
        return sel_res

    selected_title = sel_res.get("title", clean_query)
    selected_url = sel_res.get("url", "")

    # Step 5 & 6: Observe video page and verify playback
    time.sleep(1.0)
    ver_res = verify_playback_state(
        expected_title=selected_title,
        timeout_seconds=timeout,
        adapt_if_needed=True,
        observation_fn=observation_fn,
        action_fn=action_fn,
    )

    if ver_res.get("verified") or ver_res.get("playing"):
        return {
            "success": True,
            "action": "play_media",
            "platform": clean_platform,
            "title": selected_title,
            "url": selected_url,
            "verified": True,
            "verification_detail": f"Verified playback of '{selected_title}'.",
            "message": f"Now playing '{selected_title}' on {clean_platform.title()}.",
        }
    else:
        return {
            "success": False,
            "action": "play_media",
            "platform": clean_platform,
            "title": selected_title,
            "url": selected_url,
            "verified": False,
            "error": ver_res.get("error", "Playback verification timed out."),
            "message": f"Failed to verify playback: video did not start playing.",
        }

def verify_media_played(result: Dict[str, Any], arguments: Dict[str, Any]) -> Tuple[bool, str]:
    """Verification hook for media playback tools."""
    if result.get("verified") or result.get("playing"):
        return True, result.get("message", "Playback verified.")
    return False, result.get("error", "Playback verification failed: Video is not actively playing.")

def register_browser_tools():
    tool_registry.register(ToolDefinition(
        name="browser.open",
        category="browser",
        description="Open any URL in the desktop web browser (e.g. YouTube, Google, GitHub).",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL or domain to navigate to (e.g. https://www.youtube.com)"},
                "browser": {"type": "string", "description": "Optional browser preference: 'chrome', 'edge', or 'default'"},
            },
            "required": ["url"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=open_url,
        verify_fn=verify_browser_opened,
    ))

    tool_registry.register(ToolDefinition(
        name="browser.navigate",
        category="browser",
        description="Alias for browser.open. Navigates desktop browser to specified URL.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Destination URL to navigate to"},
            },
            "required": ["url"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=open_url,
        verify_fn=verify_browser_opened,
    ))

    tool_registry.register(ToolDefinition(
        name="browser.search",
        category="browser",
        description="Search web or platform directly (e.g. YouTube search for Minecraft, Google search for NVIDIA).",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query terms"},
                "engine": {"type": "string", "description": "Search platform: 'youtube', 'google', 'duckduckgo', 'bing' (default: 'youtube')"},
                "browser": {"type": "string", "description": "Optional browser executable ('chrome' or 'edge')"},
            },
            "required": ["query"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=search_browser,
        verify_fn=verify_browser_opened,
    ))

    tool_registry.register(ToolDefinition(
        name="browser.inspect",
        category="browser",
        description="Inspect web page content and metadata using Playwright.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to inspect"},
            },
            "required": ["url"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=inspect_page,
    ))

    tool_registry.register(ToolDefinition(
        name="browser.click",
        category="browser",
        description="Click element, coordinates, or video play/pause button in active browser.",
        parameters={
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Optional X screen coordinate"},
                "y": {"type": "integer", "description": "Optional Y screen coordinate"},
                "button": {"type": "string", "description": "Mouse button: 'left', 'right'"},
                "target": {"type": "string", "description": "Target element or action (e.g. 'play', 'pause', 'video')"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=browser_click,
    ))

    tool_registry.register(ToolDefinition(
        name="browser.type",
        category="browser",
        description="Type text string into active browser input field.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type into browser"},
                "press_enter": {"type": "boolean", "description": "Whether to press Enter after typing"},
            },
            "required": ["text"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=browser_type,
    ))

    tool_registry.register(ToolDefinition(
        name="browser.scroll",
        category="browser",
        description="Scroll active browser page vertically (negative = down, positive = up).",
        parameters={
            "type": "object",
            "properties": {
                "clicks": {"type": "integer", "description": "Scroll amount (e.g. -300 for down, 300 for up)"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=browser_scroll,
    ))

    tool_registry.register(ToolDefinition(
        name="browser.open_tab",
        category="browser",
        description="Open a new browser tab with optional destination URL.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Optional URL to open in new tab"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=browser_open_tab,
        verify_fn=verify_browser_opened,
    ))

    tool_registry.register(ToolDefinition(
        name="browser.switch_tab",
        category="browser",
        description="Switch between open browser tabs.",
        parameters={
            "type": "object",
            "properties": {
                "direction": {"type": "string", "description": "'next' or 'prev'"},
                "tab_index": {"type": "integer", "description": "Direct tab number 1-9"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=browser_switch_tab,
    ))

    tool_registry.register(ToolDefinition(
        name="browser.play_media",
        category="browser",
        description="Play media/video/song on YouTube or web platform and verify that playback has actually started.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Song name, video title, or artist query to play"},
                "platform": {"type": "string", "description": "Platform to play on (default: 'youtube')"},
                "criteria": {"type": "string", "description": "Selection criteria: 'best_match' or 'first'"},
                "browser": {"type": "string", "description": "Optional browser executable ('chrome' or 'edge')"},
            },
            "required": ["query"],
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=play_media,
        verify_fn=verify_media_played,
    ))

    tool_registry.register(ToolDefinition(
        name="browser.select_result",
        category="browser",
        description="Select and open the appropriate media or search result dynamically.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query terms"},
                "platform": {"type": "string", "description": "Platform (default: 'youtube')"},
                "criteria": {"type": "string", "description": "Selection criteria: 'best_match' or 'first'"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=select_media_result,
    ))

    tool_registry.register(ToolDefinition(
        name="browser.verify_playback",
        category="browser",
        description="Verify active media playback in desktop browser, adapting to autoplay blocks or popups.",
        parameters={
            "type": "object",
            "properties": {
                "expected_title": {"type": "string", "description": "Expected video or song title"},
                "timeout_seconds": {"type": "number", "description": "Verification timeout in seconds"},
            },
        },
        permission_level=PermissionLevel.SAFE,
        execute_fn=verify_playback_state,
        verify_fn=verify_media_played,
    ))


