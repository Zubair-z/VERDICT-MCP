import os
import re
import hashlib
from ..core.state_machine import Task, TaskState, project_state


TASK_PATTERN = re.compile(
    r"^##\s+(?P<id>TASK_\d{3}):\s*(?P<title>.+)$",
    re.MULTILINE
)
DEP_PATTERN = re.compile(r"Depends on:\s*(TASK_\d{3}(?:\s*,\s*TASK_\d{3})*)", re.IGNORECASE)
FILE_PATTERN = re.compile(r"`([^`]+)`")
STATUS_PATTERN = re.compile(r"Status:\s*(\S+)", re.IGNORECASE)


def _compute_plan_hash(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def parse_plan(plan_file_path: str) -> dict:
    if not os.path.isfile(plan_file_path):
        return {"error": f"Plan file not found: {plan_file_path}", "tasks": {}}

    content = open(plan_file_path, encoding="utf-8").read()
    plan_hash = _compute_plan_hash(plan_file_path)

    tasks = {}
    current_id = None
    current_title = ""
    current_desc_lines = []
    current_files = []
    current_deps = []
    current_status = TaskState.PENDING

    lines = content.split("\n")

    for line in lines:
        task_match = TASK_PATTERN.match(line)
        if task_match:
            if current_id:
                task = Task(task_id=current_id, title=current_title, description="\n".join(current_desc_lines).strip())
                task.files = current_files
                task.dependencies = current_deps
                task.state = TaskState(current_status) if isinstance(current_status, str) and current_status.upper() in TaskState._value2member_map_ else TaskState.PENDING
                tasks[current_id] = task

            current_id = task_match.group("id").strip()
            current_title = task_match.group("title").strip()
            current_desc_lines = []
            current_files = []
            current_deps = []
            current_status = TaskState.PENDING
            continue

        if current_id:
            dep_match = DEP_PATTERN.search(line)
            if dep_match:
                current_deps = [d.strip() for d in dep_match.group(1).split(",")]
                continue

            status_match = STATUS_PATTERN.search(line)
            if status_match:
                raw = status_match.group(1).upper()
                if raw in TaskState._value2member_map_:
                    current_status = TaskState(raw)
                continue

            files = FILE_PATTERN.findall(line)
            current_files.extend(files)

            stripped = line.strip()
            if stripped and not stripped.startswith("- [") and not stripped.startswith("Status:"):
                current_desc_lines.append(stripped)

    if current_id:
        task = Task(task_id=current_id, title=current_title, description="\n".join(current_desc_lines).strip())
        task.files = current_files
        task.dependencies = current_deps
        task.state = TaskState(current_status) if isinstance(current_status, str) and current_status.upper() in TaskState._value2member_map_ else TaskState.PENDING
        tasks[current_id] = task

    return {
        "task_count": len(tasks),
        "plan_hash": plan_hash,
        "tasks": {
            tid: {
                "title": t.title,
                "description": t.description[:200] + "..." if len(t.description) > 200 else t.description,
                "state": t.state.value,
                "files": t.files,
                "dependencies": t.dependencies,
            }
            for tid, t in tasks.items()
        }
    }


def load_plan_into_state(plan_file_path: str) -> dict:
    result = parse_plan(plan_file_path)
    if "error" in result:
        return result

    if project_state.initialized and project_state.plan_hash:
        current_hash = _compute_plan_hash(plan_file_path)
        if current_hash != project_state.plan_hash:
            return {
                "error": "Plan hash mismatch — plan.md has been modified since initialization. Re-initialize required.",
                "expected_hash": project_state.plan_hash,
                "actual_hash": current_hash
            }

    project_state.tasks.clear()
    project_state.plan_file_path = plan_file_path
    project_state.plan_hash = result.get("plan_hash", "")

    for tid, tdata in result["tasks"].items():
        task = Task(
            task_id=tid,
            title=tdata["title"],
            description=tdata.get("description", ""),
            files=tdata.get("files", [])
        )
        task.dependencies = tdata.get("dependencies", [])
        project_state.tasks[tid] = task

    project_state.initialized = True

    return {
        "message": f"Project plan loaded with {result['task_count']} tasks",
        "task_count": result["task_count"],
        "plan_hash": project_state.plan_hash,
        "tasks": result["tasks"]
    }
