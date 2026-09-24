import time
import uuid
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

class TaskStatus(str, Enum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

@dataclass
class TaskContext:
    task_id: str
    original_request: str
    plan: List[Dict[str, Any]]
    current_step: int = 0
    completed_steps: List[Dict[str, Any]] = field(default_factory=list)
    pending_steps: List[Dict[str, Any]] = field(default_factory=list)
    status: TaskStatus = TaskStatus.RUNNING
    execution_context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    last_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "original_request": self.original_request,
            "plan": self.plan,
            "current_step": self.current_step,
            "total_steps": len(self.plan),
            "completed_steps": self.completed_steps,
            "pending_steps": self.pending_steps,
            "status": self.status.value,
            "execution_context": self.execution_context,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "last_result": self.last_result,
        }

class TaskManager:
    """
    Lightweight Task Manager for NOVA.
    Enables:
    - Task creation, tracking, and multi-step execution context
    - Atomic pause between steps without leaving inconsistent state
    - New task execution while previous tasks remain paused
    - Resumption strictly from the next pending step
    - Permanent task cancellation
    """
    def __init__(self):
        self.tasks: Dict[str, TaskContext] = {}
        self.task_history: List[str] = []
        self.active_task_id: Optional[str] = None
        self._pause_requested: bool = False
        self._cancel_requested: bool = False

    def create_task(self, request: str, plan: List[Dict[str, Any]]) -> TaskContext:
        """Create and register a new multi-step computer task context."""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        ctx = TaskContext(
            task_id=task_id,
            original_request=request,
            plan=list(plan),
            current_step=0,
            completed_steps=[],
            pending_steps=list(plan),
            status=TaskStatus.RUNNING,
        )
        self.tasks[task_id] = ctx
        self.task_history.append(task_id)
        self.active_task_id = task_id
        self._pause_requested = False
        self._cancel_requested = False
        return ctx

    def get_task(self, task_id: str) -> Optional[TaskContext]:
        """Retrieve task by ID."""
        return self.tasks.get(task_id)

    def get_active_task(self) -> Optional[TaskContext]:
        """Retrieve currently active task if running."""
        if self.active_task_id:
            t = self.tasks.get(self.active_task_id)
            if t and t.status == TaskStatus.RUNNING:
                return t
        return None

    def get_paused_tasks(self) -> List[TaskContext]:
        """List all currently paused tasks in chronological order."""
        return [t for t in self.tasks.values() if t.status == TaskStatus.PAUSED]

    def request_pause(self) -> Optional[TaskContext]:
        """Signal the executor to pause after the current atomic tool step completes."""
        self._pause_requested = True
        active = self.get_active_task()
        if active:
            active.status = TaskStatus.PAUSED
            active.updated_at = datetime.now(timezone.utc).isoformat()
            return active
        return None

    def request_cancel(self, task_id: Optional[str] = None) -> Optional[TaskContext]:
        """Signal cancellation of the active or target task."""
        self._cancel_requested = True
        target_id = task_id or self.active_task_id
        if target_id and target_id in self.tasks:
            t = self.tasks[target_id]
            t.status = TaskStatus.CANCELLED
            t.updated_at = datetime.now(timezone.utc).isoformat()
            t.completed_at = datetime.now(timezone.utc).isoformat()
            if self.active_task_id == target_id:
                self.active_task_id = None
            return t
        return None

    def is_pause_requested(self) -> bool:
        return self._pause_requested

    def is_cancel_requested(self) -> bool:
        return self._cancel_requested

    def clear_flags(self):
        self._pause_requested = False
        self._cancel_requested = False

    def mark_step_completed(self, task_id: str, step_index: int, step_data: Dict[str, Any], result: Dict[str, Any]):
        """Record completion of a single atomic tool step."""
        t = self.tasks.get(task_id)
        if not t:
            return
        t.completed_steps.append({
            "step_index": step_index,
            "step": step_data,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        t.current_step = step_index + 1
        t.pending_steps = t.plan[t.current_step:]
        t.updated_at = datetime.now(timezone.utc).isoformat()
        t.last_result = result

    def mark_task_completed(self, task_id: str, final_result: Optional[Dict[str, Any]] = None):
        """Mark task as successfully completed."""
        t = self.tasks.get(task_id)
        if not t:
            return
        t.status = TaskStatus.COMPLETED
        t.pending_steps = []
        t.completed_at = datetime.now(timezone.utc).isoformat()
        t.updated_at = datetime.now(timezone.utc).isoformat()
        if final_result:
            t.last_result = final_result
        if self.active_task_id == task_id:
            self.active_task_id = None

    def mark_task_paused(self, task_id: str):
        """Mark task state as paused."""
        t = self.tasks.get(task_id)
        if not t:
            return
        t.status = TaskStatus.PAUSED
        t.updated_at = datetime.now(timezone.utc).isoformat()
        self._pause_requested = False
        if self.active_task_id == task_id:
            self.active_task_id = None

    def resume_task(self, task_id: Optional[str] = None) -> Tuple[Optional[TaskContext], Optional[str]]:
        """
        Resume a paused task.
        If task_id is None and multiple paused tasks exist, return an ambiguity prompt.
        """
        paused_tasks = self.get_paused_tasks()
        if not paused_tasks:
            return None, "There are no paused tasks to resume."

        target: Optional[TaskContext] = None

        if task_id:
            target = self.tasks.get(task_id)
            if not target or target.status != TaskStatus.PAUSED:
                return None, f"Task '{task_id}' was not found or is not currently paused."
        else:
            if len(paused_tasks) == 1:
                target = paused_tasks[0]
            else:
                # Ambiguous: multiple paused tasks exist
                descriptions = [
                    f"- Task {t.task_id}: '{t.original_request}' (at step {t.current_step + 1}/{len(t.plan)})"
                    for t in paused_tasks
                ]
                msg = (
                    "Multiple paused tasks found. Which one would you like to resume?\n"
                    + "\n".join(descriptions)
                )
                return None, msg

        # Prepare target task for resumption
        target.status = TaskStatus.RUNNING
        target.updated_at = datetime.now(timezone.utc).isoformat()
        self.active_task_id = target.task_id
        self._pause_requested = False
        self._cancel_requested = False
        return target, None

# Global TaskManager singleton
task_manager = TaskManager()

