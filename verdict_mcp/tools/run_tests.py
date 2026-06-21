import os
from ..core.state_machine import project_state, TaskState
from ..core.sandbox import run_pytest_with_coverage
from ..core.git_snapshot import rollback_to_last_snapshot


def execute(test_file_path: str, target_file: str, log_func=None) -> dict:
    task = project_state.current_task_id
    if task:
        t = project_state.get_task(task)
    else:
        return {"success": False, "error": "No active task. Run submit_task_for_audit first."}

    project_root = os.path.dirname(os.path.abspath(project_state.plan_file_path)) if project_state.plan_file_path else "."
    abs_test = os.path.join(project_root, test_file_path) if not os.path.isabs(test_file_path) else test_file_path
    abs_target = os.path.join(project_root, target_file) if not os.path.isabs(target_file) else target_file

    if log_func:
        log_func("info", f"Running test suite: {test_file_path} → {target_file}")

    result = run_pytest_with_coverage(abs_test, abs_target, project_root)

    if log_func:
        log_func("info", f"Test results: coverage={result.get('coverage',0)}%, passed={result.get('passed',0)}, failed={result.get('failed',0)}")

    if result["success"]:
        t.state = TaskState.COMPLETED
        t.test_errors = []
        try:
            from ..core.git_snapshot import take_snapshot
            take_snapshot(project_root, task)
        except Exception:
            pass
    else:
        t.state = TaskState.TEST_FAILED
        t.test_errors = [result.get("error", "Test suite failed")]
        try:
            sha = rollback_to_last_snapshot(project_root)
            result["rollback_sha"] = sha
            result["rolled_back"] = True
        except Exception as e:
            result["rolled_back"] = False
            result["rollback_error"] = str(e)

    return {
        "success": result["success"],
        "task_id": task,
        "task_title": t.title if t else "",
        "coverage": result.get("coverage", 0.0),
        "passed": result.get("passed", 0),
        "failed": result.get("failed", 0),
        "errors": result.get("errors", 0),
        "output": result.get("output", ""),
        "error": result.get("error", ""),
        "new_state": t.state.value,
        "rolled_back": result.get("rolled_back", False),
        "message": (
            f"All tests passed with {result.get('coverage', 0)}% coverage. Task {task} marked COMPLETED."
            if result["success"]
            else f"Tests failed. Coverage: {result.get('coverage', 0)}%. Task returned to {t.state.value}."
        )
    }
