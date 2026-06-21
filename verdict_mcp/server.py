import os
import json
from mcp.server.fastmcp import FastMCP

from .core.state_machine import project_state, TaskState
from .resources.master_plan import parse_plan
from .resources.ui_style_guide import get_style_guide
from .resources.coverage_report import get_coverage_report, invalidate_cache
from .tools import initialize_plan, audit_task, enforce_ui, run_tests
from .core.sandbox import run_mutation_testing

mcp = FastMCP(
    name="Verdict",
    instructions="""You are Verdict — the unbypassable MCP gatekeeper for code quality.

YOUR ROLE:
You enforce strict QA on every task an AI agent completes. You are the final authority
on whether code is complete, styled properly, and fully tested.

ABSOLUTE VALIDATION LIFECYCLE (must be followed for EVERY task):
  1. Agent writes code
  2. Call → submit_task_for_audit(task_id, file_paths)  [AST verification]
  3. Call → enforce_ui_standards(ui_file_path)           [UI design validation]
  4. Call → run_strict_test_suite(test_file_path, target_file) [95%+ coverage + mutation testing]
  5. Task is marked COMPLETED

RULE: No task can skip steps. If audit fails, fix and resubmit.
RULE: No default/native UI styles allowed — premium design tokens only.
RULE: Every source file MUST have a corresponding test file with 95%+ coverage.

Use project://master_plan to see the current state of all tasks.
Use project://task/{task_id} to see a specific task's details.
Use project://ui_style_guide to access design tokens.
Use project://coverage_report to check test coverage.
""",
)

# ─── RESOURCES ────────────────────────────────────────────────────────────────

@mcp.resource("project://master_plan")
def get_master_plan() -> str:
    if not project_state.initialized:
        return json.dumps({"error": "Project plan not initialized. Call initialize_project_plan first."}, indent=2)
    return json.dumps(project_state.summary(), indent=2)


@mcp.resource("project://task/{task_id}")
def get_task_resource(task_id: str) -> str:
    if not project_state.initialized:
        return json.dumps({"error": "Project plan not initialized."}, indent=2)
    try:
        task = project_state.get_task(task_id)
        return json.dumps({
            "task_id": task.task_id,
            "title": task.title,
            "description": task.description,
            "state": task.state.value,
            "files": task.files,
            "dependencies": task.dependencies,
            "audit_errors": task.audit_errors[:5],
            "ui_errors": task.ui_errors[:5],
            "test_errors": task.test_errors[:5],
        }, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.resource("project://ui_style_guide")
def get_ui_style_guide_resource() -> str:
    guide = get_style_guide()
    return json.dumps(guide, indent=2)


@mcp.resource("project://coverage_report")
def get_coverage_report_resource() -> str:
    if not project_state.plan_file_path:
        return json.dumps({"error": "Project not initialized. Call initialize_project_plan first."}, indent=2)
    project_root = os.path.dirname(os.path.abspath(project_state.plan_file_path))
    report = get_coverage_report(project_root)
    return json.dumps(report, indent=2)


# ─── TOOLS ────────────────────────────────────────────────────────────────────

@mcp.tool(
    name="initialize_project_plan",
    description="Parse a plan.md file and build the internal task state machine. All tasks start in PENDING state.",
)
def tool_initialize_project_plan(plan_file_path: str) -> dict:
    def log(level, msg):
        pass
    result = initialize_plan.execute(plan_file_path, log_func=log)
    return result


@mcp.tool(
    name="submit_task_for_audit",
    description="Submit code files for AST-based structural audit. Rejects pass statements, TODO placeholders, missing try-except on I/O operations, and missing docstrings. Must pass before UI or test checks.",
)
def tool_submit_task_for_audit(task_id: str, file_paths: list[str]) -> dict:
    def log(level, msg):
        pass
    result = audit_task.execute(task_id, file_paths, log_func=log)
    return result


@mcp.tool(
    name="enforce_ui_standards",
    description="Validate UI files against the premium design token system. Rejects default/native styles. Checks for glassmorphism, custom stylesheets, layout managers, and proper color usage.",
)
def tool_enforce_ui_standards(ui_file_path: str) -> dict:
    def log(level, msg):
        pass
    result = enforce_ui.execute(ui_file_path, log_func=log)
    return result


@mcp.tool(
    name="run_strict_test_suite",
    description="Execute tests in an isolated sandbox with coverage measurement and mutation testing. Requires 95%+ coverage and 80%+ mutation score to pass. Automatically rolls back to last snapshot on failure.",
)
def tool_run_strict_test_suite(test_file_path: str, target_file: str) -> dict:
    project_root = os.path.dirname(os.path.abspath(project_state.plan_file_path)) if project_state.plan_file_path else "."

    def log(level, msg):
        pass

    coverage_result = run_tests.execute(test_file_path, target_file, log_func=log)

    if coverage_result["success"]:
        abs_test = os.path.join(project_root, test_file_path) if not os.path.isabs(test_file_path) else test_file_path
        abs_target = os.path.join(project_root, target_file) if not os.path.isabs(target_file) else target_file
        mutation_result = run_mutation_testing(abs_test, abs_target, project_root)

        coverage_result["mutation_score"] = mutation_result.get("mutation_score", 0.0)
        coverage_result["mutation_killed"] = mutation_result.get("killed", 0)
        coverage_result["mutation_survived"] = mutation_result.get("survived", 0)
        coverage_result["mutation_total"] = mutation_result.get("total", 0)

        if not mutation_result.get("success", False) and mutation_result.get("total", 0) > 0:
            coverage_result["success"] = False
            coverage_result["error"] = (
                f"Mutation score {mutation_result.get('mutation_score', 0)}% is below 80% threshold. "
                f"{mutation_result.get('killed', 0)} mutants killed, {mutation_result.get('survived', 0)} survived."
            )

    return coverage_result


@mcp.tool(
    name="invalidate_cache",
    description="Clear the coverage report cache to force fresh computation on next read.",
)
def tool_invalidate_cache() -> dict:
    invalidate_cache()
    return {"success": True, "message": "Coverage cache invalidated"}


# ─── PROMPTS ──────────────────────────────────────────────────────────────────

@mcp.prompt(
    name="validation_lifecycle",
    description="Full Verdict validation lifecycle instructions for the executing agent",
)
def prompt_validation_lifecycle() -> list[dict]:
    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": """You must follow the Verdict Absolute Validation Lifecycle for EVERY task:

1. Write your code for the task
2. Call `submit_task_for_audit` with the task_id and all changed files
3. If UI file exists, call `enforce_ui_standards` with the UI file path
4. Call `run_strict_test_suite` with the test file and target file
5. Task is marked COMPLETED only after all steps pass

If any step fails — read the errors, fix the code, and resubmit.
Do NOT skip steps. Do NOT mark tasks done manually.

Use `project://master_plan` to see current task states.
Use `project://task/TASK_001` to see a specific task's details.
Use `project://ui_style_guide` to access premium design tokens before writing UI code.
"""
            }
        }
    ]


@mcp.prompt(
    name="audit_requirements",
    description="Requirements for passing the AST audit — what Verdict checks for",
)
def prompt_audit_requirements() -> list[dict]:
    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": """To pass the AST audit (submit_task_for_audit), your code MUST:
- Have NO empty `pass` statements in function bodies
- Have NO `# TODO` placeholders
- Have try-except wrappers around all I/O and network operations
- Have docstrings on every function
- Be syntactically valid Python

If audit fails, check the line numbers in the errors and fix each one."""
            }
        }
    ]


@mcp.prompt(
    name="ui_standards_requirements",
    description="Requirements for passing UI standards — what Verdict checks for in UI files",
)
def prompt_ui_standards() -> list[dict]:
    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": """To pass UI standards (enforce_ui_standards), your UI files MUST have:
- A custom stylesheet (setStyleSheet or stylesheet)
- Premium color scheme using the design tokens' primary/secondary colors
- border-radius applied to widgets
- rgba() colors for glassmorphism effect
- Layout managers (QHBoxLayout, QVBoxLayout, QGridLayout)
- Fusion style set (QStyleFactory.create('Fusion'))

Use `project://ui_style_guide` to see the full design token system."""
            }
        }
    ]


@mcp.prompt(
    name="test_requirements",
    description="Requirements for passing the test suite — 95% coverage + 80% mutation score",
)
def prompt_test_requirements() -> list[dict]:
    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": """To pass the test suite (run_strict_test_suite), your tests MUST:
- Achieve 95%+ line coverage on the target file
- Achieve 80%+ mutation score (tests must catch code mutations)
- Have ALL tests passing (zero failures)
- Every source file must have a corresponding test_<file>.py file

If tests fail, check the pytest output and coverage report.
Use `project://coverage_report` to see current coverage."""
            }
        }
    ]
