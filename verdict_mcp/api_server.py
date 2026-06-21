import os
import sys
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verdict_mcp.core.state_machine import project_state, TaskState
from verdict_mcp.resources.master_plan import load_plan_into_state, parse_plan
from verdict_mcp.tools import audit_task, enforce_ui, initialize_plan
from verdict_mcp.core.sandbox import run_pytest_with_coverage, run_mutation_testing
from verdict_mcp.resources.ui_style_guide import get_style_guide
from verdict_mcp.resources.coverage_report import get_coverage_report, invalidate_cache

app = FastAPI(
    title="Verdict API",
    description="Agent-agnostic code quality gatekeeper — REST API for any AI agent",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PlanInitRequest(BaseModel):
    plan_file_path: str


class AuditRequest(BaseModel):
    task_id: str
    file_paths: list[str]


class UIRequest(BaseModel):
    ui_file_path: str


class TestRequest(BaseModel):
    test_file_path: str
    target_file: str


# ─── Health ──────────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "initialized": project_state.initialized,
    }


# ─── Plan ────────────────────────────────────────────────────────────────────


@app.post("/plan/init")
def plan_init(req: PlanInitRequest):
    if not os.path.isfile(req.plan_file_path):
        raise HTTPException(400, f"Plan file not found: {req.plan_file_path}")
    result = initialize_plan.execute(req.plan_file_path)
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Plan init failed"))
    return result


@app.get("/plan/summary")
def plan_summary():
    if not project_state.initialized:
        raise HTTPException(400, "Plan not initialized. Call /plan/init first.")
    return project_state.summary()


@app.get("/plan/task/{task_id}")
def get_task(task_id: str):
    if not project_state.initialized:
        raise HTTPException(400, "Plan not initialized.")
    try:
        task = project_state.get_task(task_id)
        return {
            "task_id": task.task_id,
            "title": task.title,
            "state": task.state.value,
            "files": task.files,
            "dependencies": task.dependencies,
            "audit_errors": task.audit_errors[:5],
            "ui_errors": task.ui_errors[:5],
            "test_errors": task.test_errors[:5],
        }
    except ValueError as e:
        raise HTTPException(404, str(e))


# ─── Audit ───────────────────────────────────────────────────────────────────


@app.post("/audit")
def audit(req: AuditRequest):
    if not project_state.initialized:
        raise HTTPException(400, "Plan not initialized. Call /plan/init first.")
    result = audit_task.execute(req.task_id, req.file_paths)
    return result


# ─── UI ──────────────────────────────────────────────────────────────────────


@app.get("/ui/style-guide")
def ui_style_guide():
    guide = get_style_guide()
    return guide


@app.post("/ui/validate")
def ui_validate(req: UIRequest):
    result = enforce_ui.execute(req.ui_file_path)
    return result


# ─── Tests ───────────────────────────────────────────────────────────────────


@app.post("/tests/run")
def run_tests(req: TestRequest):
    if not project_state.initialized or not project_state.plan_file_path:
        raise HTTPException(400, "Plan not initialized.")
    project_root = os.path.dirname(os.path.abspath(project_state.plan_file_path))
    abs_test = os.path.join(project_root, req.test_file_path) if not os.path.isabs(req.test_file_path) else req.test_file_path
    abs_target = os.path.join(project_root, req.target_file) if not os.path.isabs(req.target_file) else req.target_file

    cov_result = run_pytest_with_coverage(abs_test, abs_target, project_root)
    if cov_result["success"]:
        mut_result = run_mutation_testing(abs_test, abs_target, project_root)
        cov_result["mutation_score"] = mut_result.get("mutation_score", 0.0)
        cov_result["mutation_killed"] = mut_result.get("killed", 0)
        cov_result["mutation_survived"] = mut_result.get("survived", 0)
        cov_result["mutation_total"] = mut_result.get("total", 0)
        if not mut_result.get("success", False) and mut_result.get("total", 0) > 0:
            cov_result["success"] = False
            cov_result["error"] = (
                f"Mutation score {mut_result.get('mutation_score', 0)}% is below 80% threshold."
            )
    return cov_result


# ─── Coverage ────────────────────────────────────────────────────────────────


@app.get("/coverage")
def coverage():
    if not project_state.initialized or not project_state.plan_file_path:
        raise HTTPException(400, "Plan not initialized.")
    project_root = os.path.dirname(os.path.abspath(project_state.plan_file_path))
    report = get_coverage_report(project_root)
    return report


@app.post("/coverage/invalidate")
def coverage_invalidate():
    invalidate_cache()
    return {"success": True, "message": "Coverage cache invalidated"}


# ─── Full Pipeline ────────────────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    task_id: str
    source_files: list[str]
    test_file: str
    target_file: str
    ui_file: Optional[str] = None


@app.post("/pipeline/run")
def run_pipeline(req: PipelineRequest):
    results = {"steps": [], "overall_success": True}

    if not project_state.initialized:
        return {"error": "Plan not initialized. Call /plan/init first."}

    step_audit = audit_task.execute(req.task_id, req.source_files)
    results["steps"].append({"name": "audit", "success": step_audit["success"], "data": step_audit})
    if not step_audit["success"]:
        results["overall_success"] = False
        return results

    if req.ui_file:
        step_ui = enforce_ui.execute(req.ui_file)
        results["steps"].append({"name": "ui_validation", "success": step_ui["success"], "data": step_ui})
        if not step_ui["success"]:
            results["overall_success"] = False
            return results

    project_root = os.path.dirname(os.path.abspath(project_state.plan_file_path))
    abs_test = os.path.join(project_root, req.test_file) if not os.path.isabs(req.test_file) else req.test_file
    abs_target = os.path.join(project_root, req.target_file) if not os.path.isabs(req.target_file) else req.target_file

    step_test = run_pytest_with_coverage(abs_test, abs_target, project_root)
    if step_test["success"]:
        mut_result = run_mutation_testing(abs_test, abs_target, project_root)
        step_test["mutation_score"] = mut_result.get("mutation_score", 0.0)
        if not mut_result.get("success", False) and mut_result.get("total", 0) > 0:
            step_test["success"] = False

    results["steps"].append({"name": "tests", "success": step_test["success"], "data": step_test})
    if not step_test["success"]:
        results["overall_success"] = False
        return results

    task = project_state.get_task(req.task_id)
    task.state = TaskState.COMPLETED

    results["overall_success"] = True
    results["message"] = f"Task {req.task_id} completed successfully"
    return results


def run_server(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
