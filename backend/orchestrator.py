"""Intent routing and bounded, interruptible execution of registered tools."""
import asyncio
import json
import re
from typing import Optional

from .config import settings
from .permissions import evaluate_tool_permission, PermissionLevel
from .privacy import private_mode
from .router import route_inference, ModelProvider
from .task_manager import task_manager, TaskStatus
from .task_understanding import understand_user_goal, IntentType
from .tools.registry import tool_registry
from .tools.planner import (plan_task_from_natural_language, plan_task_from_goal,
                            generate_recovery_plan, parse_llm_tool_calls,
                            classify_task_control_intent, build_tool_system_prompt)
from .tools.observation import get_computer_state
from .tools.disambiguation import strip_assistant_prefix
from .tools.web import web_search
from .memory import save_memory, list_memories
from .voice import synthesize


def select_model_by_intent(text: str, preferred_model: Optional[str] = None) -> str:
    lower = text.lower()
    if re.search(r"\b(private|offline|locally|on-device|ollama)\b", lower):
        return ModelProvider.OLLAMA
    providers = {p.lower(): p for p in ("Gemini", "Groq", "NVIDIA", "Ollama")}
    if (preferred_model or "").lower() in providers:
        return providers[preferred_model.lower()]
    if re.search(r"\b(screen|vision|screenshot|ui|button|visual)\b", lower):
        return ModelProvider.GEMINI
    if re.search(r"\b(code|coding|python|javascript|typescript|debug|refactor|sql|algorithm)\b", lower):
        return ModelProvider.NVIDIA
    if len(text.split()) >= 16 or re.search(r"\b(analyze|compare|reason|workflow|architecture)\b", lower):
        return ModelProvider.GEMINI
    return ModelProvider.GROQ


async def _emit(callback, event, payload):
    if callback:
        await callback(event, payload)


async def _answer(text, action="chat", status="SUCCESS", **extra):
    # Speech is started by the session after the result has reached the UI.
    return {"status": status, "action": action, "response": text, **extra}


async def execute_task_context(task, confirmed_action=None, on_task_event=None, manager=None):
    manager = manager or task_manager
    await _emit(on_task_event, "TASK_STARTED", {
        "task_id": task.task_id, "status": "RUNNING", "current_step": task.current_step,
        "total_steps": len(task.plan), "description": task.original_request,
    })
    messages = []
    last_result = task.last_result or {}
    ver = None
    while task.current_step < len(task.plan):
        if task.status == TaskStatus.CANCELLED or manager.is_cancel_requested():
            manager.request_cancel(task.task_id)
            return await _answer("Task cancelled.", "task_cancel", "CANCELLED", task_id=task.task_id)
        if task.status == TaskStatus.PAUSED or manager.is_pause_requested():
            manager.mark_task_paused(task.task_id)
            return await _answer("Paused. Resume when ready.", "task_pause", "PAUSED", task_id=task.task_id)
        if len(task.completed_steps) >= settings.MAX_ORCHESTRATION_STEPS:
            task.status = TaskStatus.FAILED
            return await _answer("Task reached its step limit.", status="ERROR", task_id=task.task_id)
        index = task.current_step
        step = task.plan[index]
        tool_name, arguments = step.get("tool", ""), step.get("arguments", {})
        permission = evaluate_tool_permission(tool_name, arguments)
        # A grant applies once, to the exact pending step selected by the session.
        approved = confirmed_action == tool_name
        if permission.level == PermissionLevel.BLOCKED:
            task.status = TaskStatus.FAILED
            return await _answer(permission.reason, tool_name, "ERROR", task_id=task.task_id)
        sending = (task.goal and task.goal.goal_category == "messaging" and index == len(task.plan) - 1)
        if (permission.level == PermissionLevel.CONFIRMATION_REQUIRED or sending) and not approved:
            return {"status": "CONFIRMATION_REQUIRED", "action": tool_name, "task_id": task.task_id,
                    "step_index": index, "arguments": arguments, "title": f"Confirm {tool_name}",
                    "description": "Confirm sending this message." if sending else permission.reason,
                    "detail": json.dumps(arguments, ensure_ascii=False), "response": "Waiting for confirmation."}
        confirmed_action = None
        await _emit(on_task_event, "STATE_CHANGE", {"status": "EXECUTING", "detail": tool_name})
        await _emit(on_task_event, "TASK_STEP", {"task_id": task.task_id, "current_step": index + 1,
                    "total_steps": len(task.plan), "description": tool_name})
        result = await tool_registry.execute(tool_name, arguments, pre_authorized=approved)
        last_result = result.to_dict()
        await _emit(on_task_event, "ACTIVITY_LOG", {
            "action": tool_name, "detail": result.error or result.verification_detail,
            "type": "computer", "status": "success" if result.success else "error",
            "verified": result.verified,
        })
        # Record the attempted step, but never retry a non-idempotent action implicitly.
        manager.mark_step_completed(task.task_id, index, step, last_result)
        if task.status == TaskStatus.CANCELLED or manager.is_cancel_requested():
            return await _answer("Task cancelled after the current action finished.", "task_cancel", "CANCELLED", task_id=task.task_id)
        state = None
        if task.success_condition and task.success_condition.type != "tool_success":
            state = await asyncio.to_thread(get_computer_state, include_screenshot=False, include_ui_elements=True)
            ver = task.success_condition.verify(state, last_result)
            task.verification_history.append({"step": index, "satisfied": ver.satisfied, "reason": ver.reason})
        if not result.success:
            recovery = generate_recovery_plan(task, state, last_result) if state is not None else None
            if recovery and task.recovery_attempts < task.max_recovery_attempts:
                task.recovery_attempts += 1
                task.plan[task.current_step:task.current_step] = recovery
                task.pending_steps = task.plan[task.current_step:]
                await _emit(on_task_event, "STATE_CHANGE", {"status": "RECOVERING", "detail": "Trying a recovery action"})
                continue
            task.status = TaskStatus.FAILED
            return await _answer(result.error or "Action failed.", tool_name, "ERROR", task_id=task.task_id, tool_output=last_result)
        inner = result.result if isinstance(result.result, dict) else {}
        messages.append(inner.get("message") or f"Executed {tool_name}.")
        # Closing an app can make redundant close-window fallback steps unnecessary.
    if task.status == TaskStatus.PAUSED or manager.is_pause_requested():
        manager.mark_task_paused(task.task_id)
        return await _answer("Task paused.", "task_pause", "PAUSED", task_id=task.task_id)
    if ver and not ver.satisfied:
        task.status = TaskStatus.FAILED
        return await _answer("Actions finished, but the requested outcome could not be verified: " + ver.reason,
                             status="ERROR", task_id=task.task_id, verified=False, tool_output=last_result)
    verified = bool(ver.satisfied) if ver else all(s["result"].get("verified", False) for s in task.completed_steps)
    text = ver.reason if ver else " ".join(messages) or "Task finished."
    manager.mark_task_completed(task.task_id, {"response": text, "verified": verified})
    await _emit(on_task_event, "TASK_COMPLETED", {"task_id": task.task_id, "status": "COMPLETED",
                "current_step": task.current_step, "total_steps": len(task.plan), "description": text, "verified": verified})
    return await _answer(text, last_result.get("tool", "task"), task_id=task.task_id, verified=verified,
                         tool_output=last_result, tool_steps=[s["result"] for s in task.completed_steps])


async def execute_tool_steps(steps, confirmed_action=None):
    task = task_manager.create_task("Computer action", steps)
    return await execute_task_context(task, confirmed_action)


async def orchestrate_task(user_input, preferred_model="auto", confirmed_action=None,
                           on_task_event=None, manager=None, conversation=None):
    model = select_model_by_intent(user_input, preferred_model)
    token = private_mode.set(model == ModelProvider.OLLAMA)
    try:
        await _emit(on_task_event, "MODEL_CHANGE", {"provider": model,
            "model": getattr(settings, model.upper() + "_MODEL"), "phase": "selected"})
        result = await _orchestrate(user_input, model, confirmed_action, on_task_event,
                                   manager or task_manager, conversation or [])
        if not result.get("model_used"):
            result["model_used"] = "Local Engine"
            await _emit(on_task_event, "MODEL_CHANGE", {"provider": "Local Engine", "model": None, "phase": "active"})
        return result
    finally:
        private_mode.reset(token)


async def _orchestrate(user_input, model, confirmed_action, callback, manager, conversation):
    text = strip_assistant_prefix(user_input).strip()
    if not text:
        return await _answer("Enter a command.", status="ERROR")
    control = classify_task_control_intent(text)
    if control:
        action = control["action"]
        if action == "PAUSE":
            task = manager.request_pause()
            return await _answer("Pause requested." if task else "No running task.", "task_pause", "PAUSED" if task else "SUCCESS")
        if action == "CANCEL":
            task = manager.request_cancel(control.get("target"))
            return await _answer("Task cancelled." if task else "No running task.", "task_cancel", "CANCELLED")
        task, error = manager.resume_task(control.get("target"))
        return await _answer(error, status="ERROR") if error else await execute_task_context(task, on_task_event=callback, manager=manager)
    if re.search(r"format\s+c:|rm -rf /|del /f|eval\(|exec\(", text, re.I):
        return await _answer("This command is blocked by the execution policy.", status="ERROR")
    if text.lower().startswith("remember "):
        saved = await save_memory("User Note", text[9:].strip())
        return await _answer("Saved to memory." if saved["success"] else saved["error"], "save_memory",
                             "SUCCESS" if saved["success"] else "ERROR", tool_output=saved)
    if text.lower() in {"list memories", "show memories", "what do you remember"}:
        memories = await list_memories()
        return await _answer("\n".join(m["text"] for m in memories) or "No memories saved yet.", "list_memories", tool_output=memories)
    if re.match(r"^(search (?:web |the web |for )?|find on web )", text, re.I) and not any(k in text.lower() for k in ["youtube", "google", "file"]):
        if private_mode.get():
            return await _answer("Web search requires a network connection. Switch out of local mode to search.", status="ERROR")
        query = re.sub(r"^(search (?:web |the web |for )?|find on web )(?:for )?", "", text, flags=re.I)
        result = await asyncio.to_thread(web_search, query, 5)
        return await _answer(result.get("summary") or result.get("error"), "web_search",
                             "SUCCESS" if result["success"] else "ERROR", tool_output=result)
    goal = understand_user_goal(text)
    if goal.intent_type == IntentType.AMBIGUOUS:
        return await _answer(goal.clarification_prompt, "clarification")
    plan = None
    if goal.intent_type != IntentType.INFORMATIONAL:
        plan = plan_task_from_natural_language(text)
        if not plan and goal.goal_category in {"app_lifecycle", "messaging", "browser_tab_management", "media_playback"}:
            state = await asyncio.to_thread(get_computer_state, include_screenshot=False, include_ui_elements=False)
            plan = plan_task_from_goal(goal, state)
    provider = "Local Engine"
    if plan:
        await _emit(callback, "MODEL_CHANGE", {"provider": provider, "model": None, "phase": "active"})
    if not plan:
        system = build_tool_system_prompt()
        routed = await route_inference(text, preferred_provider=model, system_instruction=system,
                                       conversation=conversation, on_model_change=callback)
        provider = routed["provider"]
        response = routed["text"]
        plan = parse_llm_tool_calls(response) if goal.intent_type != IntentType.INFORMATIONAL else None
        if not plan:
            return await _answer(response, status="ERROR" if routed.get("unavailable") else "SUCCESS", model_used=provider)
    if len(plan) > settings.MAX_ORCHESTRATION_STEPS:
        return await _answer("This plan is too long. Please split it into smaller tasks.", status="ERROR")
    task = manager.create_task(text, plan, goal=goal, success_condition=goal.success_condition)
    task.execution_context.update({"model": model, "private": private_mode.get()})
    await _emit(callback, "TASK_CREATED", {"task_id": task.task_id, "status": "RUNNING",
                "current_step": 0, "total_steps": len(plan), "description": text})
    result = await execute_task_context(task, confirmed_action, callback, manager)
    result["model_used"] = provider
    return result
