import os
from ..core.state_machine import project_state, TaskState
from ..core.git_snapshot import ensure_git_repo
from ..resources.master_plan import load_plan_into_state


def execute(plan_file_path: str, log_func=None) -> dict:
    if not os.path.isfile(plan_file_path):
        return {
            "success": False,
            "error": f"Plan file not found at: {plan_file_path}"
        }

    if log_func:
        log_func("info", f"Initializing project plan from {plan_file_path}")

    project_root = os.path.dirname(os.path.abspath(plan_file_path))
    try:
        ensure_git_repo(project_root)
    except Exception as e:
        return {
            "success": False,
            "error": f"Git init failed: {str(e)}"
        }

    try:
        result = load_plan_into_state(plan_file_path)
        if "error" in result:
            return {"success": False, "error": result["error"]}

        return {
            "success": True,
            "message": f"Project plan initialized. {result['task_count']} tasks loaded from {os.path.basename(plan_file_path)}.",
            "task_count": result["task_count"],
            "tasks": result["tasks"],
            "all_tasks_pending": all(t.state == TaskState.PENDING for t in project_state.tasks.values())
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Plan initialization failed: {str(e)}"
        }
