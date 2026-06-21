from enum import Enum


class TaskState(str, Enum):
    PENDING = "PENDING"
    AUDITING = "AUDITING"
    AUDIT_FAILED = "AUDIT_FAILED"
    UI_REVIEW = "UI_REVIEW"
    UI_FAILED = "UI_FAILED"
    TESTING = "TESTING"
    TEST_FAILED = "TEST_FAILED"
    COMPLETED = "COMPLETED"
    ROLLED_BACK = "ROLLED_BACK"


class Task:
    def __init__(self, task_id: str, title: str, description: str, files: list[str] | None = None):
        self.task_id = task_id
        self.title = title
        self.description = description
        self.files = files or []
        self.state = TaskState.PENDING
        self.audit_errors: list[str] = []
        self.ui_errors: list[str] = []
        self.test_errors: list[str] = []
        self.dependencies: list[str] = []


class ProjectState:
    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self.current_task_id: str | None = None
        self.plan_file_path: str | None = None
        self.plan_hash: str = ""
        self.initialized = False

    def get_task(self, task_id: str) -> Task:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found in project plan")
        return task

    def can_proceed_to(self, task_id: str) -> tuple[bool, str]:
        task = self.get_task(task_id)
        for dep_id in task.dependencies:
            dep = self.get_task(dep_id)
            if dep.state != TaskState.COMPLETED:
                return False, f"Dependency {dep_id} ({dep.title}) is not completed yet (state: {dep.state.value})"
        if task.state == TaskState.COMPLETED:
            return False, f"Task {task_id} is already completed"
        return True, ""

    def summary(self) -> dict:
        return {
            "initialized": self.initialized,
            "plan_file": self.plan_file_path,
            "tasks": {
                tid: {
                    "title": t.title,
                    "state": t.state.value,
                    "files": t.files,
                    "dependencies": t.dependencies,
                    "audit_errors": t.audit_errors,
                    "ui_errors": t.ui_errors,
                    "test_errors": t.test_errors,
                }
                for tid, t in self.tasks.items()
            }
        }


project_state = ProjectState()
