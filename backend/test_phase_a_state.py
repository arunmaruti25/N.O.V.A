"""Tests for Phase A: Unified Computer State & Perception."""
import pytest
from unittest.mock import MagicMock, patch

from backend.tools.observation import (
    ComputerState,
    WindowInfo,
    UIElementInfo,
    resolve_uwp_real_process,
    get_focused_element,
    get_open_windows,
    get_visible_applications,
    get_running_applications,
    get_computer_state,
    get_unified_observation,
)
from backend.tools.app_control import is_app_running, APP_ALIASES, close_application
from backend.tools.registry import tool_registry
from backend.tools.computer_use import register_computer_use_tools, observe_computer_tool
from backend.tools.planner import normalize_tool_name


def test_data_structures():
    """Verify dataclasses and their serialization."""
    w = WindowInfo(hwnd=1234, title="Test Window", process_name="chrome.exe", pid=5678, is_active=True)
    assert w.title == "Test Window"
    
    elem = UIElementInfo(name="Search", control_type="Edit", automation_id="search_box", value="query")
    assert elem.name == "Search"
    
    state = ComputerState(
        timestamp=123456789.0,
        screen={"width": 1920, "height": 1080},
        mouse_position=(100, 200),
        active_window=w,
        open_windows=[w],
        visible_applications=[{"name": "Google Chrome", "process_name": "chrome.exe"}],
        running_applications=["chrome.exe", "spotify.exe"],
        ui_elements=[elem],
        focused_element=elem,
        browser_state={},
        screenshot={},
        context_summary="Test Summary",
        extra={"custom_key": "val"}
    )
    d = state.to_dict()
    assert d["active_window"]["title"] == "Test Window"
    assert d["active_window"]["hwnd"] == 1234
    assert len(d["open_windows"]) == 1
    assert "Google Chrome" in d["visible_apps"]
    assert "chrome.exe" in d["running_apps"]
    assert d["focused_element"]["automation_id"] == "search_box"
    assert d["custom_key"] == "val"


def test_resolve_uwp_real_process():
    """Verify UWP process resolution logic."""
    proc, pid, name = resolve_uwp_real_process(99999, "WhatsApp")
    assert name == "WhatsApp"
    assert proc == "WhatsApp.exe"


def test_get_computer_state_live():
    """Verify live get_computer_state returns valid ComputerState on Windows."""
    state = get_computer_state(include_screenshot=False, include_ui_elements=False)
    assert isinstance(state, ComputerState)
    assert isinstance(state.open_windows, list)
    assert isinstance(state.visible_apps, list)
    assert isinstance(state.running_apps, list)
    d = state.to_dict()
    assert "active_window" in d
    assert "open_windows" in d
    assert "visible_apps" in d
    assert "running_apps" in d


def test_get_unified_observation_backward_compatibility():
    """Ensure get_unified_observation continues to return dict with all legacy and enriched keys."""
    obs = get_unified_observation(include_screenshot=False, include_ui_elements=False)
    assert isinstance(obs, dict)
    assert "active_window" in obs
    assert "open_windows" in obs
    assert "visible_apps" in obs
    assert "running_apps" in obs
    assert "focused_element" in obs
    assert obs["success"] is True


def test_app_aliases_contain_key_apps():
    """Verify common communication and media apps are registered."""
    assert "whatsapp" in APP_ALIASES
    assert "spotify" in APP_ALIASES
    assert "slack" in APP_ALIASES
    assert "discord" in APP_ALIASES


def test_is_app_running_with_mock():
    """Verify hybrid app running detection using both process names and open window titles."""
    mock_window = WindowInfo(
        hwnd=4321,
        title="WhatsApp",
        process_name="ApplicationFrameHost.exe",
        pid=1010,
        is_active=True
    )
    with patch("backend.tools.observation.get_open_windows", return_value=[mock_window]):
        res = is_app_running("whatsapp")
        assert res["is_running"] is True
        assert res["success"] is True


@pytest.mark.asyncio
async def test_computer_use_tool_registered():
    """Verify computer.get_state is available in computer tools."""
    register_computer_use_tools()
    tool = tool_registry.get("computer.get_state")
    assert tool is not None
    res = await observe_computer_tool(include_screenshot=False, include_ui_elements=False)
    assert "active_window" in res
    assert "visible_apps" in res


def test_planner_tool_normalization():
    """Verify tool normalization recognizes get_computer_state and get_state."""
    assert normalize_tool_name("get_computer_state") == "computer.get_state"
    assert normalize_tool_name("get_state") == "computer.get_state"
    assert normalize_tool_name("computer.get_state") == "computer.get_state"

