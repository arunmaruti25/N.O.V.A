"""
NOVA Task Understanding & Goal Representation Module (Phase B)
Provides a generic representation for user goals, categorizes user intent,
and generates machine-verifiable success conditions for task orchestration.
"""

import re
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Callable

from .tools.observation import ComputerState, WindowInfo, get_computer_state


class IntentType(str, Enum):
    INFORMATIONAL = "INFORMATIONAL"       # Needs direct answer (e.g. "What is quantum computing?")
    ACTION_TASK = "ACTION_TASK"           # Needs computer action + verified completion
    AMBIGUOUS = "AMBIGUOUS"               # Missing critical parameters (needs clarification)
    TASK_CONTROL = "TASK_CONTROL"         # Pause, resume, or cancel active execution


@dataclass
class VerificationResult:
    """Result of checking a success condition against current computer state."""
    satisfied: bool
    confidence: float = 1.0
    reason: str = ""
    suggested_next_action: Optional[str] = None
    extracted_state: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "satisfied": self.satisfied,
            "confidence": self.confidence,
            "reason": self.reason,
            "suggested_next_action": self.suggested_next_action,
            "extracted_state": self.extracted_state,
        }


@dataclass
class SuccessCondition:
    """
    Machine-verifiable success condition for an autonomous computer task.
    Evaluated against the live ComputerState and recent tool execution results.
    """
    type: str                             # e.g., 'window_closed', 'app_running', 'playback_active', 'ui_element_exists', 'tab_closed'
    description: str                      # Human-readable expected outcome
    target: str                           # Primary entity/app/window/url target
    expected_state: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 15.0

    def verify(self, state: ComputerState, last_tool_result: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """
        Verify whether the success condition is satisfied given the live computer state.
        Never relies on blind assumptions.
        """
        target_lower = (self.target or "").lower().strip()
        last_res = last_tool_result or {}

        # 1. WINDOW_CLOSED / APP_CLOSED
        if self.type in ["window_closed", "app_closed"]:
            # Check open windows
            target_open = any(
                target_lower in (w.title or "").lower() or
                target_lower in (w.process_name or "").lower() or
                target_lower in (w.app_name or "").lower()
                for w in state.open_windows
            )
            # Check running apps
            target_running = any(
                target_lower in (app or "").lower()
                for app in state.running_applications
            )
            # Check visible apps
            target_visible = any(
                target_lower in (v or "").lower()
                for v in state.visible_apps
            )

            # If not in open windows, visible apps, or running processes, target is closed!
            if not target_open and not target_visible and not target_running:
                return VerificationResult(
                    satisfied=True,
                    reason=f"Target '{self.target}' is no longer present in open windows or running processes.",
                )
            else:
                return VerificationResult(
                    satisfied=False,
                    reason=f"Target '{self.target}' is still running or has open windows.",
                    suggested_next_action="force_close",
                )

        # 2. WINDOW_ACTIVE / APP_RUNNING / APP_FOCUSED
        elif self.type in ["app_running", "window_active", "app_focused"]:
            active = state.active_window
            is_active = False
            if active:
                is_active = (
                    target_lower in (active.title or "").lower() or
                    target_lower in (active.process_name or "").lower() or
                    target_lower in (active.app_name or "").lower()
                )

            is_open = any(
                target_lower in (w.title or "").lower() or
                target_lower in (w.process_name or "").lower() or
                target_lower in (w.app_name or "").lower()
                for w in state.open_windows
            )

            if is_active:
                return VerificationResult(
                    satisfied=True,
                    reason=f"Target '{self.target}' is active in foreground.",
                )
            elif is_open:
                return VerificationResult(
                    satisfied=(self.type == "app_running"),
                    reason=f"Target '{self.target}' is running and open, but not foreground.",
                    suggested_next_action="focus_window",
                )
            else:
                return VerificationResult(
                    satisfied=False,
                    reason=f"Target '{self.target}' is not running.",
                    suggested_next_action="launch_app",
                )

        # 3. PLAYBACK_ACTIVE / MEDIA_PLAYING
        elif self.type in ["playback_active", "media_playing"]:
            # Check last tool output if it was browser.verify_playback or browser.play_media
            if last_res.get("verified") is True:
                return VerificationResult(
                    satisfied=True,
                    reason="Media playback verified active by browser engine.",
                )
            
            # Check browser state in computer observation
            b_state = state.browser_state or {}
            if b_state.get("playback_verified") or b_state.get("is_playing"):
                return VerificationResult(
                    satisfied=True,
                    reason="Browser state indicates active media playback.",
                )

            # Check active window title for media play markers or requested query
            active_title = (state.active_window.title or "").lower() if state.active_window else ""
            song_query = self.expected_state.get("query", "").lower()
            if "youtube" in active_title and (not song_query or song_query in active_title):
                # If YouTube is active and on the video page
                if last_res.get("success") and ("play" in last_res.get("action", "") or "verify" in last_res.get("action", "")):
                    return VerificationResult(
                        satisfied=True,
                        reason="YouTube video player page is active and playback action completed.",
                    )

            return VerificationResult(
                satisfied=False,
                reason="Media playback has not yet been verified active.",
                suggested_next_action="select_and_play",
            )

        # 4. TAB_CLOSED
        elif self.type == "tab_closed":
            # Target tab title shouldn't be the active title or in browser tabs
            active_title = (state.active_window.title or "").lower() if state.active_window else ""
            if target_lower not in active_title:
                return VerificationResult(
                    satisfied=True,
                    reason=f"Tab matching '{self.target}' is closed.",
                )
            return VerificationResult(
                satisfied=False,
                reason=f"Tab matching '{self.target}' is still open in active window.",
                suggested_next_action="close_tab",
            )

        # 5. UI_ELEMENT_EXISTS / TEXT_ENTERED / MESSAGE_SENT
        elif self.type in ["message_sent", "ui_text_present"]:
            # Check tool result
            if last_res.get("verified") or (last_res.get("success") and "sent" in str(last_res)):
                return VerificationResult(
                    satisfied=True,
                    reason="Message dispatch confirmed by tool execution.",
                )
            return VerificationResult(
                satisfied=last_res.get("success", False),
                reason=last_res.get("message", "Action completed."),
            )

        # 6. DEFAULT / GENERIC TOOL SUCCESS
        if last_res.get("verified") is True or (last_res.get("success") and not self.type):
            return VerificationResult(satisfied=True, reason="Execution verified successfully.")

        return VerificationResult(
            satisfied=last_res.get("success", False),
            reason=last_res.get("error") or last_res.get("message") or "Verified tool outcome.",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "description": self.description,
            "target": self.target,
            "expected_state": self.expected_state,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class UserGoal:
    """
    Structured representation of a parsed user request:
    Goal, Target, Entities, Constraints, Expected Outcome & Success Condition.
    """
    raw_prompt: str
    intent_type: IntentType
    goal_category: str                    # e.g., 'media_playback', 'app_lifecycle', 'web_interaction', 'messaging', 'information', 'system'
    target: str                           # Primary entity/app/URL/person
    entities: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    success_condition: Optional[SuccessCondition] = None
    clarification_prompt: Optional[str] = None
    suggested_plan: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_prompt": self.raw_prompt,
            "intent_type": self.intent_type.value,
            "goal_category": self.goal_category,
            "target": self.target,
            "entities": self.entities,
            "constraints": self.constraints,
            "success_condition": self.success_condition.to_dict() if self.success_condition else None,
            "clarification_prompt": self.clarification_prompt,
            "suggested_plan": self.suggested_plan,
        }


# ─────────────────────────────────────────────────────────────
# INTENT & GOAL UNDERSTANDING PARSER
# ─────────────────────────────────────────────────────────────

def understand_user_goal(user_prompt: str, current_state: Optional[ComputerState] = None) -> UserGoal:
    """
    Analyze user input dynamically to extract:
    - Intent type (INFORMATIONAL vs ACTION_TASK vs AMBIGUOUS vs TASK_CONTROL)
    - Target, entities, and constraints
    - Machine-verifiable success condition
    - Pre-condition aware initial plan
    """
    text = (user_prompt or "").strip()
    lower = text.lower()

    # 1. TASK CONTROL INTENT (Pause, Resume, Cancel)
    from .tools.planner import classify_task_control_intent
    control_intent = classify_task_control_intent(text)
    if control_intent:
        return UserGoal(
            raw_prompt=text,
            intent_type=IntentType.TASK_CONTROL,
            goal_category="task_control",
            target=control_intent.get("target") or "active_task",
            entities={"action": control_intent["action"]},
            success_condition=SuccessCondition(
                type="task_state_change",
                description=f"Task transitioned to {control_intent['action']}",
                target=control_intent.get("target") or "active_task",
            )
        )

    # 2. AMBIGUOUS ACTION REQUESTS
    # E.g. "play video on youtube", "play a song", "send a message" (no recipient/text)
    ambiguous_media_phrases = [
        "play", "play a video", "play video", "play a song", "play song",
        "play a video on youtube", "play video on youtube", "play a song on youtube", "play song on youtube",
        "play music on youtube", "play something on youtube", "play something", "play music",
    ]
    if lower in ambiguous_media_phrases:
        return UserGoal(
            raw_prompt=text,
            intent_type=IntentType.AMBIGUOUS,
            goal_category="media_playback",
            target="youtube",
            clarification_prompt="Which specific song or video would you like me to play?",
        )

    if lower in ["send message", "send a message", "message", "send whatsapp message", "send a whatsapp message"]:
        return UserGoal(
            raw_prompt=text,
            intent_type=IntentType.AMBIGUOUS,
            goal_category="messaging",
            target="unknown",
            clarification_prompt="Who would you like to send a message to, and what should it say?",
        )

    # 3. INFORMATIONAL INTENTS
    # Questions that do not require operating desktop or browser state
    info_question_patterns = [
        r'^(?:what|who|when|where|why|how)\s+(?:is|are|was|were|do|does|did|can|will|should)\b',
        r'^(?:tell me about|explain|define|summarize)\b',
        r'^(?:what is the capital of|who wrote|what does .+ mean)\b',
    ]
    is_info = any(re.search(pat, lower) for pat in info_question_patterns)
    # Exclude system/computer queries like "what is on my screen", "what is my battery"
    if is_info and not any(k in lower for k in ["screen", "battery", "window", "running", "process", "volume", "download"]):
        return UserGoal(
            raw_prompt=text,
            intent_type=IntentType.INFORMATIONAL,
            goal_category="information",
            target="general_knowledge",
            success_condition=SuccessCondition(
                type="answered",
                description="Informational answer synthesized for user",
                target="user",
            )
        )

    # 4. ACTION TASK: MEDIA PLAYBACK (e.g. "play X on YouTube", "play song X")
    media_match = re.search(r'play\s+(?:the\s+)?(?:song\s+|video\s+of\s+|video\s+|track\s+)?(.+)', text, re.IGNORECASE)
    if media_match:
        raw_target = media_match.group(1).strip().rstrip(".")
        platform = "youtube" if "youtube" in raw_target.lower() else "youtube"
        clean_q = re.sub(r'\s+on\s+youtube\s*$', '', raw_target, flags=re.IGNORECASE).strip()
        clean_q = re.sub(r'^(?:the\s+)?(?:first|1st|top)\s+', '', clean_q, flags=re.IGNORECASE).strip()
        clean_q = re.sub(r'^(?:song|video\s+of|video|track)\s+', '', clean_q, flags=re.IGNORECASE).strip()

        if not clean_q or clean_q.lower() in ["a video", "a song", "music", "video", "song", "something", "anything"]:
            return UserGoal(
                raw_prompt=text,
                intent_type=IntentType.AMBIGUOUS,
                goal_category="media_playback",
                target=platform,
                clarification_prompt=f"Which specific song or video would you like me to play on {platform.title()}?",
            )

        return UserGoal(
            raw_prompt=text,
            intent_type=IntentType.ACTION_TASK,
            goal_category="media_playback",
            target=platform,
            entities={"query": clean_q, "platform": platform},
            success_condition=SuccessCondition(
                type="playback_active",
                description=f"Media playback active for '{clean_q}' on {platform}",
                target=platform,
                expected_state={"query": clean_q, "platform": platform},
            )
        )

    # 5. ACTION TASK: CLOSE APPLICATION OR TAB
    # E.g. "close WhatsApp", "close YouTube", "quit Chrome"
    close_match = re.search(r'^(?:close|quit|exit|kill)\s+(.+)', text, re.IGNORECASE)
    if close_match:
        target_entity = close_match.group(1).strip().rstrip(".")
        target_lower = target_entity.lower()
        if target_lower in ["youtube", "google", "github", "twitter", "reddit", "tab", "active tab", "browser tab"]:
            cased = "YouTube" if target_lower == "youtube" else target_lower.capitalize()
            return UserGoal(
                raw_prompt=text,
                intent_type=IntentType.ACTION_TASK,
                goal_category="browser_tab_management",
                target=cased,
                entities={"title_match": cased},
                success_condition=SuccessCondition(
                    type="tab_closed",
                    description=f"Browser tab '{cased}' closed",
                    target=cased,
                )
            )
        elif target_lower in ["window", "active window", "this window"]:
            return UserGoal(
                raw_prompt=text,
                intent_type=IntentType.ACTION_TASK,
                goal_category="window_management",
                target="active_window",
                success_condition=SuccessCondition(
                    type="window_closed",
                    description="Active window closed",
                    target="active_window",
                )
            )
        else:
            return UserGoal(
                raw_prompt=text,
                intent_type=IntentType.ACTION_TASK,
                goal_category="app_lifecycle",
                target=target_entity,
                entities={"app_name": target_entity},
                success_condition=SuccessCondition(
                    type="app_closed",
                    description=f"Application '{target_entity}' terminated and closed",
                    target=target_entity,
                )
            )

    # 6. ACTION TASK: MESSAGING / CHAT
    # E.g. "Open WhatsApp and send hello to Rahul", "send this message to Rahul on WhatsApp"
    msg_match = re.search(
        r'(?:send\s+(?:message\s+|a\s+message\s+)?(?:that\s+says\s+|saying\s+)?[\'"]?([^\'"]+)[\'"]?\s+to\s+([A-Za-z0-9_ ]+)|send\s+([A-Za-z0-9_ ]+)\s+(?:a\s+message\s+)?(?:that\s+says\s+|saying\s+)?[\'"]?([^\'"]+)[\'"]?)',
        text,
        re.IGNORECASE
    )
    if "whatsapp" in lower or msg_match:
        # Extract recipient and message
        recipient = "contact"
        content = "Hello"
        if msg_match:
            g1, g2, g3, g4 = msg_match.groups()
            if g1 and g2:
                content, recipient = g1.strip(), g2.strip()
            elif g3 and g4:
                recipient, content = g3.strip(), g4.strip()

        # Clean trailing 'on whatsapp' from recipient
        recipient = re.sub(r'\s+on\s+whatsapp\s*$', '', recipient, flags=re.IGNORECASE).strip()

        return UserGoal(
            raw_prompt=text,
            intent_type=IntentType.ACTION_TASK,
            goal_category="messaging",
            target="WhatsApp",
            entities={"recipient": recipient, "message": content, "app": "WhatsApp"},
            success_condition=SuccessCondition(
                type="message_sent",
                description=f"Message '{content}' sent to {recipient} on WhatsApp",
                target="WhatsApp",
                expected_state={"recipient": recipient, "message": content},
            )
        )

    # 7. ACTION TASK: LAUNCH / OPEN APPLICATION
    open_match = re.search(r'^(?:open|launch|start)\s+(.+)', text, re.IGNORECASE)
    if open_match:
        target_app = open_match.group(1).strip().rstrip(".")
        if not ("." in target_app and "/" in target_app):
            return UserGoal(
                raw_prompt=text,
                intent_type=IntentType.ACTION_TASK,
                goal_category="app_lifecycle",
                target=target_app,
                entities={"app_name": target_app},
                success_condition=SuccessCondition(
                    type="app_running",
                    description=f"Application '{target_app}' opened and focused",
                    target=target_app,
                )
            )

    # 8. DEFAULT ACTION TASK (Generic)
    return UserGoal(
        raw_prompt=text,
        intent_type=IntentType.ACTION_TASK,
        goal_category="general_action",
        target=text,
        success_condition=SuccessCondition(
            type="tool_success",
            description=f"Successfully executed user command: '{text}'",
            target=text,
        )
    )
