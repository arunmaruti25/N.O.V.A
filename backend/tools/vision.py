import io
import base64
from pathlib import Path
from typing import Dict, Any
from PIL import Image, ImageDraw
from ..config import settings

VISION_CACHE_DIR = settings.DATA_DIR / "vision"
VISION_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def capture_screen(save_to_disk: bool = True, return_base64: bool = False) -> Dict[str, Any]:
    """
    Capture current primary monitor using mss with graceful fallback if the process
    is executed in a non-interactive Windows service or headless environment.
    """
    img = None
    width = 1920
    height = 1080

    try:
        import mss
        with mss.MSS() as sct:
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            width = monitor["width"]
            height = monitor["height"]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    except Exception as exc:
        return {"success": False, "error": f"Screen capture unavailable: {exc}", "has_base64": False, "base64_preview": "", "file_path": ""}

    file_path = ""
    if save_to_disk and img:
        target_path = VISION_CACHE_DIR / "latest_screen.png"
        img.save(target_path, format="PNG")
        file_path = str(target_path)

    b64_data = ""
    if return_base64 and img:
        buffer = io.BytesIO()
        thumb = img.copy()
        thumb.thumbnail((1280, 720))
        thumb.save(buffer, format="JPEG", quality=85)
        b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return {
        "success": True,
        "width": width,
        "height": height,
        "file_path": file_path,
        "has_base64": bool(b64_data),
        "base64_preview": b64_data,
        "message": f"Captured display ({width}x{height}).",
    }
