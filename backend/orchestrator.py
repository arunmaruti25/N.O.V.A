import re
from typing import Dict, Any, Optional, List, Tuple, Callable
from .config import settings
from .permissions import evaluate_permission, evaluate_tool_permission, PermissionLevel, PermissionCheckResult
from .router import route_inference, ModelProvider
from .tools.registry import tool_registry, ToolResult
from .tools.planner import (
    plan_task_from_natural_language,
    parse_llm_tool_calls,
    classify_task_control_intent,
    build_tool_system_prompt,
)
from .task_manager import task_manager, TaskContext, TaskStatus
from .tools.computer import (
    get_system_info,
    get_system_volume,
    set_system_volume,
    list_running_processes,
    launch_allowed_application,
    execute_power_action,
)
from .tools.vision import capture_screen
from .tools.web import web_search
from .memory import save_memory, list_memories, delete_memory
from .voice import synthesize

def select_model_by_intent(text: str, preferred_model: Optional[str] = None) -> str:
    """
    Intelligently route requests based on semantic intent:
    - Coding -> NVIDIA
    - Complex reasoning -> Gemini
    - Private / offline -> Ollama
    - Simple / fast conversation -> Groq
    """
    lower = text.lower()

    # 1. Private / offline requests
    if any(k in lower for k in ["offline", "local", "private", "on-device", "locally", "ollama", "disconnected"]):
        return ModelProvider.OLLAMA

    # 2. Coding requests
    coding_keywords = [
        "code", "coding", "python", "javascript", "typescript", "react", "html", "css",
        "function", "script", "algorithm", "debug", "refactor", "class", "program",
        "syntax", "compile", "bug", "sql", "api", "regex", "loop", "array", "json",
        "write a function", "write code", "implement"
    ]
    if any(k in lower for k in coding_keywords):
        return ModelProvider.NVIDIA

    # 3. Complex reasoning requests
    reasoning_keywords = [
        "why", "analyze", "analysis", "reason", "explain in detail", "compare",
        "evaluate", "break down", "philosophy", "complex", "strategy", "architecture",
        "step by step", "deep think", "ponder", "pros and cons", "implications"
    ]
    if any(k in lower for k in reasoning_keywords) or len(text.split()) >= 16:
        return ModelProvider.GEMINI

    # 4. If explicit model requested by client
    if preferred_model and preferred_model.strip().lower() in ["gemini", "nvidia", "ollama", "groq"]:
        return preferred_model.strip().title()

    # 5. Simple / fast conversation default -> Groq
    return ModelProvider.GROQ

async def execute_task_context(
    task: TaskContext,
    confirmed_action: Optional[str] = None,
    on_task_event: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Execute a task context with support for:
    - Atomic step completion
    - Safe pause before next step
    - Resumption strictly from the next pending step
    - Real-time task events over WebSocket
    """
    executed_results = list(task.completed_steps)
    messages = []
    last_action = "computer_control"

    if on_task_event:
        await on_task_event(
            "TASK_STARTED",
            {
                "task_id": task.task_id,
                "status": "RUNNING",
                "current_step": task.current_step + 1,
                "total_steps": len(task.plan),
                "description": task.original_request,
            },
        )

    while task.current_step < len(task.plan):
        i = task.current_step
        step = task.plan[i]
        tool_name = step.get("tool", "")
        arguments = step.get("arguments", {})
        last_action = tool_name

        # 1. Check if pause was requested before this step begins
        if task_manager.is_pause_requested() or task.status == TaskStatus.PAUSED:
            task_manager.mark_task_paused(task.task_id)
            if on_task_event:
                await on_task_event(
                    "TASK_PAUSED",
                    {
                        "task_id": task.task_id,
                        "status": "PAUSED",
                        "current_step": task.current_step + 1,
                        "total_steps": len(task.plan),
                        "description": f"Paused before step {task.current_step + 1}: {tool_name}",
                    },
                )
            ack_msg = "Paused. You can give me another task."
            tts_res = await synthesize(ack_msg, output_filename="response.mp3")
            return {
                "status": "PAUSED",
                "action": "task_pause",
                "task_id": task.task_id,
                "response": ack_msg,
                "current_step": task.current_step,
                "total_steps": len(task.plan),
                "audio_path": tts_res.get("file_path", "") if tts_res.get("success") else "",
            }

        # 2. Check if cancellation was requested
        if task_manager.is_cancel_requested() or task.status == TaskStatus.CANCELLED:
            task_manager.request_cancel(task.task_id)
            if on_task_event:
                await on_task_event(
                    "TASK_CANCELLED",
                    {
                        "task_id": task.task_id,
                        "status": "CANCELLED",
                        "current_step": task.current_step + 1,
                        "total_steps": len(task.plan),
                        "description": f"Cancelled: {task.original_request}",
                    },
                )
            cancel_msg = "Task cancelled."
            tts_res = await synthesize(cancel_msg, output_filename="response.mp3")
            return {
                "status": "CANCELLED",
                "action": "task_cancel",
                "task_id": task.task_id,
                "response": cancel_msg,
                "audio_path": tts_res.get("file_path", "") if tts_res.get("success") else "",
            }

        if on_task_event:
            # Emit OBSERVING state for vision/computer use tasks
            if "observe" in tool_name or "locate" in tool_name:
                await on_task_event(
                    "STATE_CHANGE",
                    {"status": "OBSERVING", "detail": f"Observing computer state for '{tool_name}'..."},
                )
            else:
                await on_task_event(
                    "STATE_CHANGE",
                    {"status": "EXECUTING", "detail": f"Executing action: {tool_name}"},
                )

            await on_task_event(
                "TASK_STEP",
                {
                    "task_id": task.task_id,
                    "status": "RUNNING",
                    "current_step": i + 1,
                    "total_steps": len(task.plan),
                    "description": f"Step {i + 1}/{len(task.plan)}: {tool_name}",
                },
            )

        # 3. Centralized Permission Evaluation
        perm_check: PermissionCheckResult = evaluate_tool_permission(tool_name, arguments)
        is_pre_authorized = False
        if confirmed_action:
            is_pre_authorized = (
                confirmed_action == tool_name
                or (arguments.get("action") and confirmed_action == arguments.get("action"))
                or (confirmed_action in ["shutdown", "restart"] and tool_name == "system.power")
                or (confirmed_action in ["delete_file", "delete"] and tool_name == "file.delete")
            )

        if perm_check.level == PermissionLevel.BLOCKED:
            task.status = TaskStatus.FAILED
            return {
                "status": "ERROR",
                "action": tool_name,
                "task_id": task.task_id,
                "error": perm_check.reason,
                "response": f"Security Alert: {perm_check.reason}",
                "action_executed": False,
            }

        if perm_check.level == PermissionLevel.CONFIRMATION_REQUIRED and not is_pre_authorized:
            return {
                "status": "CONFIRMATION_REQUIRED",
                "action": tool_name,
                "task_id": task.task_id,
                "target": str(arguments),
                "title": f"Confirm: {tool_name.replace('_', ' ').replace('.', ' ').title()}",
                "description": perm_check.reason,
                "detail": str(arguments),
                "requires_user_approval": True,
            }

        # 4. Execute atomic tool step
        res: ToolResult = await tool_registry.execute(
            name=tool_name,
            arguments=arguments,
            pre_authorized=is_pre_authorized,
        )

        task_manager.mark_step_completed(task.task_id, i, step, res.to_dict())
        executed_results.append(res.to_dict())

        # Emit VERIFYING state and Activity Log
        if on_task_event:
            await on_task_event(
                "STATE_CHANGE",
                {"status": "VERIFYING", "detail": f"Verifying result of {tool_name}..."},
            )
            await on_task_event(
                "ACTIVITY_LOG",
                {
                    "task_id": task.task_id,
                    "action": tool_name,
                    "tool": tool_name,
                    "target": str(arguments.get("target_description") or arguments.get("name") or arguments.get("url") or arguments.get("path") or ""),
                    "result": "success" if res.success else "failed",
                    "verified": res.verified,
                    "verification_detail": res.verification_detail,
                    "duration_ms": res.duration_ms,
                },
            )

        if not res.success:
            err_msg = res.error or "Action verification failed."
            task.status = TaskStatus.FAILED
            if on_task_event:
                await on_task_event(
                    "TASK_FAILED",
                    {
                        "task_id": task.task_id,
                        "status": "FAILED",
                        "error": err_msg,
                        "current_step": i + 1,
                    },
                )
            return {
                "status": "ERROR",
                "action": tool_name,
                "task_id": task.task_id,
                "error": err_msg,
                "response": f"Notice: {err_msg}",
                "tool_output": res.to_dict(),
                "verified": False,
            }

        if isinstance(res.result, dict) and "message" in res.result:
            messages.append(res.result["message"])
        elif res.verification_detail and res.verification_detail != "Action completed.":
            messages.append(res.verification_detail)
        else:
            messages.append(f"Completed {tool_name}.")

        # 5. Check if pause was signaled during this atomic operation
        if task_manager.is_pause_requested():
            task_manager.mark_task_paused(task.task_id)
            if on_task_event:
                await on_task_event(
                    "TASK_PAUSED",
                    {
                        "task_id": task.task_id,
                        "status": "PAUSED",
                        "current_step": task.current_step,
                        "total_steps": len(task.plan),
                        "description": f"Paused at step {task.current_step}/{len(task.plan)}",
                    },
                )
            ack_msg = "Paused. You can give me another task."
            tts_res = await synthesize(ack_msg, output_filename="response.mp3")
            return {
                "status": "PAUSED",
                "action": "task_pause",
                "task_id": task.task_id,
                "response": ack_msg,
                "current_step": task.current_step,
                "total_steps": len(task.plan),
                "audio_path": tts_res.get("file_path", "") if tts_res.get("success") else "",
            }

    # All steps completed successfully
    final_text = " ".join(messages) if messages else "Computer action executed and verified."
    task_manager.mark_task_completed(task.task_id, {"response": final_text})

    if on_task_event:
        await on_task_event(
            "TASK_COMPLETED",
            {
                "task_id": task.task_id,
                "status": "COMPLETED",
                "current_step": len(task.plan),
                "total_steps": len(task.plan),
                "description": f"Completed: {task.original_request}",
            },
        )

    tts_result = await synthesize(final_text, output_filename="response.mp3")

    return {
        "status": "SUCCESS",
        "action": last_action,
        "task_id": task.task_id,
        "model_used": "Local Engine",
        "response": final_text,
        "tool_output": executed_results[-1] if executed_results else {},
        "tool_steps": executed_results,
        "verified": True,
        "audio_path": tts_result.get("file_path", "") if tts_result.get("success") else "",
    }

async def execute_tool_steps(steps: List[Dict[str, Any]], confirmed_action: Optional[str] = None) -> Dict[str, Any]:
    """Compatibility wrapper executing planned steps through TaskManager."""
    task = task_manager.create_task("Computer Action", steps)
    return await execute_task_context(task, confirmed_action=confirmed_action)

async def orchestrate_task(
    user_input: str,
    preferred_model: str = "auto",
    confirmed_action: Optional[str] = None,
    on_task_event: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    General Task Execution Pipeline:
    INPUT → UNDERSTAND → PLAN → VALIDATE → PERMISSION CHECK → EXECUTE → VERIFY → RESPONSE → TTS
    """
    text = user_input.strip()
    lower = text.lower()

    # 1. Check for Task-Control Commands (PAUSE / RESUME / CANCEL)
    task_control = classify_task_control_intent(text)
    if task_control:
        action = task_control.get("action")
        target_id = task_control.get("target")

        if action == "PAUSE":
            active_task = task_manager.get_active_task()
            if active_task:
                task_manager.request_pause()
                task_manager.mark_task_paused(active_task.task_id)
                if on_task_event:
                    await on_task_event(
                        "TASK_PAUSED",
                        {
                            "task_id": active_task.task_id,
                            "status": "PAUSED",
                            "current_step": active_task.current_step,
                            "total_steps": len(active_task.plan),
                            "description": f"Paused: {active_task.original_request}",
                        },
                    )
                ack_msg = "Paused. You can give me another task."
            else:
                ack_msg = "There is no task currently running to pause."

            tts_res = await synthesize(ack_msg, output_filename="response.mp3")
            return {
                "status": "PAUSED" if active_task else "SUCCESS",
                "action": "task_pause",
                "task_id": active_task.task_id if active_task else None,
                "response": ack_msg,
                "audio_path": tts_res.get("file_path", "") if tts_res.get("success") else "",
            }

        elif action == "RESUME":
            target_task, err_msg = task_manager.resume_task(target_id)
            if err_msg:
                tts_res = await synthesize(err_msg, output_filename="response.mp3")
                return {
                    "status": "SUCCESS" if ("Which" in err_msg or "Multiple" in err_msg) else "ERROR",
                    "action": "task_resume",
                    "response": err_msg,
                    "audio_path": tts_res.get("file_path", "") if tts_res.get("success") else "",
                }

            if on_task_event:
                await on_task_event(
                    "TASK_RESUMED",
                    {
                        "task_id": target_task.task_id,
                        "status": "RUNNING",
                        "current_step": target_task.current_step + 1,
                        "total_steps": len(target_task.plan),
                        "description": f"Resuming: {target_task.original_request}",
                    },
                )
            return await execute_task_context(target_task, confirmed_action=confirmed_action, on_task_event=on_task_event)

        elif action == "CANCEL":
            cancelled = task_manager.request_cancel(target_id)
            if not cancelled:
                # Cancel the most recent paused task if no active task
                paused = task_manager.get_paused_tasks()
                if paused:
                    cancelled = task_manager.request_cancel(paused[-1].task_id)

            if cancelled:
                msg = f"Cancelled task '{cancelled.original_request}'."
                if on_task_event:
                    await on_task_event(
                        "TASK_CANCELLED",
                        {
                            "task_id": cancelled.task_id,
                            "status": "CANCELLED",
                            "description": msg,
                        },
                    )
            else:
                msg = "No task found to cancel."

            tts_res = await synthesize(msg, output_filename="response.mp3")
            return {
                "status": "CANCELLED" if cancelled else "SUCCESS",
                "action": "task_cancel",
                "response": msg,
                "audio_path": tts_res.get("file_path", "") if tts_res.get("success") else "",
            }

    # 2. Security Gate: Block dangerous command injections directly
    blocked_direct_patterns = ["format c:", "del /f", "rm -rf /", "drop table", "format disk", "eval(", "exec("]
    if any(p in lower for p in blocked_direct_patterns):
        return {
            "status": "ERROR",
            "action": "blocked_command",
            "error": "Prohibited command injection detected.",
            "response": "Security Alert: Action 'format_disk' is blocked by security policy.",
            "action_executed": False,
        }

    # 3. Memory retention commands ("remember ...")
    if lower.startswith("remember "):
        target_param = text.replace("remember ", "").replace("Remember ", "").strip()
        mem_output = await save_memory(category="User Note", text=target_param)
        assistant_text = "New context successfully retained in persistent memory."
        tts_result = await synthesize(assistant_text, output_filename="response.mp3")
        return {
            "status": "SUCCESS",
            "action": "save_memory",
            "model_used": "Local Engine",
            "response": assistant_text,
            "tool_output": mem_output,
            "audio_path": tts_result.get("file_path", "") if tts_result.get("success") else "",
        }

    # 4. Web Search command
    if (lower.startswith("search ") or lower.startswith("find on web ")) and not ("youtube" in lower or "google" in lower or "file" in lower):
        match = re.search(r'(?:search for|search|find on web|find|lookup)\s+(.+)', text, re.IGNORECASE)
        query = match.group(1) if match else text
        search_res = web_search(query, max_results=4)
        assistant_text = f"Retrieved {search_res.get('count', 0)} verified sources for your query."
        tts_result = await synthesize(assistant_text, output_filename="response.mp3")
        return {
            "status": "SUCCESS",
            "action": "web_search",
            "model_used": "Gemini",
            "response": assistant_text,
            "tool_output": search_res,
            "audio_path": tts_result.get("file_path", "") if tts_result.get("success") else "",
        }

    # 5. Primary AI Router with Full Registered Tool Schemas & Tool Calling
    model_choice = select_model_by_intent(text, preferred_model)
    tool_system_prompt = build_tool_system_prompt()

    routed = await route_inference(text, preferred_provider=model_choice, system_instruction=tool_system_prompt)
    assistant_text = routed.get("text", "").strip()
    model_used = routed.get("provider", model_choice)

    # Check if the AI returned a structured tool call
    llm_tool_calls = parse_llm_tool_calls(assistant_text)

    # Refusal & offline detection: If model incorrectly states it cannot browse/control computer,
    # or if all online providers failed and returned local fallback or no tool call for an actionable intent:
    refusal_markers = [
        "cannot directly browse", "cannot browse", "can't browse",
        "don't have access to your computer", "cannot control your computer",
        "unable to browse", "cannot play videos", "cannot open applications",
        "as an ai, i cannot", "as an ai language model, i don't have",
        "i do not have the ability to open", "i am unable to control",
        "are you sure you want to shut down", "confirm first",
        "reply with \"yes\" to confirm", "need your explicit confirmation",
    ]
    is_refusal = any(m in assistant_text.lower() for m in refusal_markers)

    # If the model appropriately asked clarification for an ambiguous request
    is_clarification = any(k in assistant_text.lower() for k in ["which video", "what video", "which song", "what song", "which one would you like", "which specific"])
    if is_clarification and not llm_tool_calls:
        tts_result = await synthesize(assistant_text, output_filename="response.mp3")
        return {
            "status": "SUCCESS",
            "action": "chat",
            "model_used": model_used,
            "response": assistant_text,
            "tool_output": None,
            "audio_path": tts_result.get("file_path", "") if tts_result.get("success") else "",
        }

    if not llm_tool_calls:
        # Check if natural language planner recognizes this as an actionable intent
        fallback_plan = plan_task_from_natural_language(text)
        if fallback_plan:
            llm_tool_calls = fallback_plan

    if llm_tool_calls:
        # Multi-Turn AI Tool Execution Loop
        task = task_manager.create_task(text, llm_tool_calls)
        if on_task_event:
            await on_task_event(
                "TASK_CREATED",
                {
                    "task_id": task.task_id,
                    "status": "RUNNING",
                    "total_steps": len(task.plan),
                    "description": text,
                },
            )

        exec_res = await execute_task_context(task, confirmed_action=confirmed_action, on_task_event=on_task_event)
        if exec_res.get("status") in ["CONFIRMATION_REQUIRED", "ERROR", "PAUSED", "CANCELLED"]:
            return exec_res

        # Check if user's intent is PLAY and playback has not yet been verified
        requires_playback = (
            lower.startswith("play ")
            or " play " in lower
            or "play song" in lower
            or "play the song" in lower
        ) and not any(k in lower for k in ["playlist", "playwright", "player info", "how to play", "what is", "play pause"])

        if requires_playback:
            executed_tools = [s.get("step", {}).get("tool") or s.get("tool") for s in task.completed_steps]
            if "browser.play_media" not in executed_tools and "browser.verify_playback" not in executed_tools:
                # User asked to play media, but so far only search or open occurred
                clean_q = re.sub(r'^(?:play\s+(?:the\s+)?(?:song\s+|video\s+of\s+|video\s+|track\s+)?)', '', text, flags=re.IGNORECASE)
                clean_q = re.sub(r'\s+on\s+youtube\s*$', '', clean_q, flags=re.IGNORECASE).strip()
                criteria = "first" if any(k in lower for k in ["first", "1st", "top"]) else "best_match"

                select_step = {
                    "tool": "browser.select_result",
                    "arguments": {"query": clean_q, "platform": "youtube", "criteria": criteria},
                    "thought": f"Select and open best result for '{clean_q}' on YouTube",
                }
                verify_step = {
                    "tool": "browser.verify_playback",
                    "arguments": {"expected_title": clean_q},
                    "thought": f"Verify active playback of '{clean_q}'",
                }
                task.plan.extend([select_step, verify_step])
                task.pending_steps.extend([select_step, verify_step])
                exec_res = await execute_task_context(task, confirmed_action=confirmed_action, on_task_event=on_task_event)
                if exec_res.get("status") in ["CONFIRMATION_REQUIRED", "ERROR", "PAUSED", "CANCELLED"]:
                    return exec_res

        # If it was a completed action without chained conjunctions, return directly
        has_chained = any(c in text.lower() for c in [" and ", " then ", " after that ", " next "])
        if not has_chained and task.current_step >= len(task.plan):
            return exec_res

        # Tool result -> Model feedback loop (multi-turn reasoning for compound tasks)
        max_steps = settings.MAX_ORCHESTRATION_STEPS
        current_turn = len(task.completed_steps)
        last_tool_output = exec_res.get("tool_output")

        while current_turn < max_steps:
            followup_prompt = (
                f"Original user instruction: {text}\n"
                f"Step {current_turn} executed: {exec_res.get('action')}\n"
                f"Execution status: {exec_res.get('status')}\n"
                f"Result: {last_tool_output or exec_res.get('response')}\n\n"
                "Is the user's request completely fulfilled? "
                "If yes, reply with a concise final summary message to speak to the user. "
                "If additional computer or browser actions are still required to satisfy the user's goal, "
                "return the next JSON tool call: {\"tool\": \"...\", \"arguments\": {...}}."
            )

            next_routed = await route_inference(
                followup_prompt,
                preferred_provider=model_choice,
                system_instruction=tool_system_prompt,
            )
            next_text = next_routed.get("text", "").strip()
            next_tool_calls = parse_llm_tool_calls(next_text)

            if not next_tool_calls:
                # Task complete according to model
                final_speech = next_text if next_text and not any(m in next_text.lower() for m in refusal_markers) else exec_res.get("response", "Task completed.")
                tts_res = await synthesize(final_speech, output_filename="response.mp3")
                return {
                    "status": "SUCCESS",
                    "action": exec_res.get("action", "task_completed"),
                    "task_id": task.task_id,
                    "model_used": next_routed.get("provider", model_used),
                    "response": final_speech,
                    "tool_output": last_tool_output,
                    "tool_steps": exec_res.get("tool_steps", []),
                    "verified": True,
                    "audio_path": tts_res.get("file_path", "") if tts_res.get("success") else "",
                }

            # Model produced next step
            current_turn += 1
            for n_call in next_tool_calls:
                task.plan.append(n_call)
                task.pending_steps.append(n_call)

            exec_res = await execute_task_context(task, confirmed_action=confirmed_action, on_task_event=on_task_event)
            if exec_res.get("status") in ["CONFIRMATION_REQUIRED", "ERROR", "PAUSED", "CANCELLED"]:
                return exec_res
            last_tool_output = exec_res.get("tool_output")

        return exec_res

    # Conversational response or clarifying question
    tts_result = await synthesize(assistant_text, output_filename="response.mp3")
    return {
        "status": "SUCCESS",
        "action": "chat",
        "model_used": model_used,
        "response": assistant_text,
        "tool_output": None,
        "audio_path": tts_result.get("file_path", "") if tts_result.get("success") else "",
    }
