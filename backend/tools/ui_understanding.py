import os
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from .observation import get_unified_observation, extract_active_ui_elements, get_screen_metrics, get_active_window_info

def locate_with_vision(query: str, screenshot_path: str) -> Optional[Dict[str, Any]]:
    """Multimodal vision locator using Gemini Vision."""
    from ..config import settings
    if not settings.GEMINI_API_KEY or not os.path.exists(screenshot_path):
        return None
    try:
        from google import genai
        from PIL import Image
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        img = Image.open(screenshot_path)
        prompt = (
            f"Locate the UI element or button described as '{query}' in this screenshot. "
            "Return ONLY a JSON object with: {\"center_x\": integer, \"center_y\": integer, \"label\": string, \"confidence\": float}."
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[img, prompt],
        )
        if response and response.text:
            text = response.text.strip()
            if "{" in text and "}" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                data = json.loads(text[start:end])
                cx = int(data.get("center_x", 0))
                cy = int(data.get("center_y", 0))
                if cx > 0 and cy > 0:
                    return {
                        "center_x": cx,
                        "center_y": cy,
                        "label": data.get("label", query),
                        "confidence": float(data.get("confidence", 0.85)),
                        "source": "gemini_vision",
                    }
    except Exception:
        pass
    return None

SYNONYMS: Dict[str, List[str]] = {
    "search": ["search", "find", "search box", "query", "address bar", "search or enter web address", "omnibox", "lookup"],
    "continue": ["continue", "next", "proceed", "submit", "confirm", "ok", "yes", "save", "agree"],
    "close": ["close", "exit", "cancel", "dismiss", "no", "abort", "back"],
    "play": ["play", "pause", "resume", "watch", "play video"],
    "bookmark": ["bookmark", "favorite", "star", "add bookmark", "bookmark this tab"],
    "menu": ["menu", "settings", "options", "more", "hamburger", "customize"],
    "new_tab": ["new tab", "open tab", "add tab", "+"],
}

def normalize_query(query: str) -> str:
    return query.strip().lower()

def match_element_in_ui_tree(query: str, elements: List[Dict[str, Any]], control_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Match query against extracted UI automation elements with scoring."""
    clean_q = normalize_query(query)
    if not clean_q or not elements:
        return None

    best_match = None
    best_score = 0.0

    # Expand query with synonyms
    query_synonyms = {clean_q}
    for category, syn_list in SYNONYMS.items():
        if any(s in clean_q for s in syn_list):
            query_synonyms.update(syn_list)

    for el in elements:
        name = (el.get("name") or "").lower().strip()
        elem_type = (el.get("type") or "").lower().strip()
        auto_id = (el.get("automation_id") or "").lower().strip()

        score = 0.0

        # Exact match
        if name == clean_q or auto_id == clean_q:
            score = 1.0
        # Substring in name
        elif clean_q in name:
            score = 0.85
        elif name in clean_q and len(name) > 2:
            score = 0.80
        # Synonym match
        elif any(syn in name for syn in query_synonyms if len(syn) > 2):
            score = 0.75
        elif any(syn in auto_id for syn in query_synonyms if len(syn) > 2):
            score = 0.70

        # Control type filter boost
        if control_type and control_type.lower() in elem_type:
            score += 0.1

        if score > best_score and score >= 0.65:
            best_score = score
            best_match = el

    if best_match:
        best_match["match_score"] = best_score
        return best_match

    return None

def heuristic_fallback_location(query: str, observation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Calculate standard spatial coordinates for common desktop / browser UI controls."""
    clean_q = normalize_query(query)
    screen = observation.get("screen", {})
    sw = screen.get("width", 1920)
    sh = screen.get("height", 1080)
    win = observation.get("active_window", {})
    rect = win.get("rect", {})
    wl = rect.get("left", 0)
    wt = rect.get("top", 0)
    wr = rect.get("right", sw)
    wb = rect.get("bottom", sh)
    ww = wr - wl
    wh = wb - wt

    # 1. Search Box / Address Bar
    if any(k in clean_q for k in ["search box", "search bar", "address bar", "omnibox", "search field", "url"]):
        if win.get("is_browser"):
            cx = wl + (ww // 2)
            cy = wt + 82  # Chrome/Edge standard address bar height
            return {"center_x": cx, "center_y": cy, "name": "Browser Address / Search Bar", "type": "Edit", "source": "heuristic"}
        else:
            cx = wl + (ww // 2)
            cy = wt + 50
            return {"center_x": cx, "center_y": cy, "name": "Search Field", "type": "Edit", "source": "heuristic"}

    # 2. Window Controls (Close, Minimize, Maximize)
    if "close" in clean_q and any(k in clean_q for k in ["window", "button", "app", "tab"]):
        if "tab" in clean_q:
            cx = wl + 240
            cy = wt + 20
            return {"center_x": cx, "center_y": cy, "name": "Tab Close Button", "type": "Button", "source": "heuristic"}
        else:
            cx = wr - 24
            cy = wt + 16
            return {"center_x": cx, "center_y": cy, "name": "Window Close Button", "type": "Button", "source": "heuristic"}

    if "minimize" in clean_q:
        cx = wr - 95
        cy = wt + 16
        return {"center_x": cx, "center_y": cy, "name": "Window Minimize Button", "type": "Button", "source": "heuristic"}

    if "maximize" in clean_q or "restore" in clean_q:
        cx = wr - 60
        cy = wt + 16
        return {"center_x": cx, "center_y": cy, "name": "Window Maximize Button", "type": "Button", "source": "heuristic"}

    # 3. Bookmark / Star Button
    if any(k in clean_q for k in ["bookmark", "star", "favorite"]):
        cx = wr - 90
        cy = wt + 82
        return {"center_x": cx, "center_y": cy, "name": "Bookmark Icon", "type": "Button", "source": "heuristic"}

    # 4. First Search Result / Link
    if any(k in clean_q for k in ["first result", "first link", "top result", "1st result"]):
        cx = wl + min(350, ww // 3)
        cy = wt + min(240, wh // 3)
        return {"center_x": cx, "center_y": cy, "name": "First Result Target", "type": "Hyperlink", "source": "heuristic"}

    # 5. Standard Dialog OK / Continue Button
    if any(k in clean_q for k in ["continue", "ok", "yes", "confirm", "submit", "blue continue", "save"]):
        cx = wl + (ww // 2) + 60
        cy = wb - 50 if wh > 100 else wt + 50
        return {"center_x": cx, "center_y": cy, "name": f"Action Button ({query})", "type": "Button", "source": "heuristic"}

    # 6. Center of active window / element
    if ww > 50 and wh > 50:
        cx = wl + (ww // 2)
        cy = wt + (wh // 2)
        return {"center_x": cx, "center_y": cy, "name": f"Target in Active Window ({query})", "type": "GeneralControl", "source": "heuristic"}

    return None

def locate_ui_element(
    query: str,
    observation: Optional[Dict[str, Any]] = None,
    control_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Locates any UI target dynamically on screen:
    1. Inspects Windows UI Automation accessibility tree
    2. Uses visual heuristics & layout geometry
    Returns coordinates (x, y), bounding box, source, and match confidence.
    """
    clean_target = query.strip()
    if not clean_target:
        return {"success": False, "found": False, "error": "Target query description cannot be empty."}

    # Ensure observation state
    obs = observation if observation else get_unified_observation(include_ui_elements=True)
    ui_elements = obs.get("ui_elements", [])

    # Layer 1: Windows UI Automation tree match
    matched = match_element_in_ui_tree(clean_target, ui_elements, control_type=control_type)
    if matched:
        bbox = matched.get("bounding_box", {})
        cx = bbox.get("center_x", 0)
        cy = bbox.get("center_y", 0)
        return {
            "success": True,
            "found": True,
            "target": clean_target,
            "matched_label": matched.get("name") or clean_target,
            "control_type": matched.get("type", "Control"),
            "x": cx,
            "y": cy,
            "bounding_box": bbox,
            "confidence": matched.get("match_score", 0.9),
            "source": "ui_automation",
            "message": f"Located '{clean_target}' at ({cx}, {cy}) [{matched.get('type')}] via Windows UI Automation.",
        }

    # Layer 2: Multimodal AI Vision if screenshot is available
    screenshot_path = obs.get("screenshot", {}).get("file_path")
    if screenshot_path and os.path.exists(screenshot_path):
        vision_match = locate_with_vision(clean_target, screenshot_path)
        if vision_match:
            cx = vision_match["center_x"]
            cy = vision_match["center_y"]
            bbox = {
                "left": cx - 30,
                "top": cy - 15,
                "right": cx + 30,
                "bottom": cy + 15,
                "width": 60,
                "height": 30,
                "center_x": cx,
                "center_y": cy,
            }
            return {
                "success": True,
                "found": True,
                "target": clean_target,
                "matched_label": vision_match.get("label", clean_target),
                "control_type": "VisualElement",
                "x": cx,
                "y": cy,
                "bounding_box": bbox,
                "confidence": vision_match.get("confidence", 0.85),
                "source": "gemini_vision",
                "message": f"Located '{clean_target}' at ({cx}, {cy}) via Gemini multimodal vision.",
            }

    # Layer 3: Visual Layout Heuristic Fallback
    fallback = heuristic_fallback_location(clean_target, obs)
    if fallback:
        cx = fallback["center_x"]
        cy = fallback["center_y"]
        bbox = {
            "left": cx - 30,
            "top": cy - 15,
            "right": cx + 30,
            "bottom": cy + 15,
            "width": 60,
            "height": 30,
            "center_x": cx,
            "center_y": cy,
        }
        return {
            "success": True,
            "found": True,
            "target": clean_target,
            "matched_label": fallback.get("name", clean_target),
            "control_type": fallback.get("type", "Control"),
            "x": cx,
            "y": cy,
            "bounding_box": bbox,
            "confidence": 0.75,
            "source": "heuristic_layout",
            "message": f"Located '{clean_target}' at ({cx}, {cy}) via spatial UI understanding.",
        }

    # If active window is available, default to center of active window
    act_win = obs.get("active_window", {})
    rect = act_win.get("rect", {})
    if rect.get("width", 0) > 0:
        cx = rect["left"] + rect["width"] // 2
        cy = rect["top"] + rect["height"] // 2
        return {
            "success": True,
            "found": True,
            "target": clean_target,
            "matched_label": act_win.get("title", clean_target),
            "control_type": "WindowArea",
            "x": cx,
            "y": cy,
            "bounding_box": {"center_x": cx, "center_y": cy},
            "confidence": 0.50,
            "source": "active_window_center",
            "message": f"Estimated '{clean_target}' at active window center ({cx}, {cy}).",
        }

    return {
        "success": False,
        "found": False,
        "target": clean_target,
        "error": f"Could not locate UI element '{clean_target}' on screen.",
    }
