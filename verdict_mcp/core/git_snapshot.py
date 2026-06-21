import subprocess
import os
from pathlib import Path


SNAPSHOT_BRANCH = "sentinel-snapshot"


def _run_git(cmd: list[str], cwd: str) -> str:
    result = subprocess.run(
        ["git"] + cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git error: {result.stderr.strip()}")
    return result.stdout.strip()


def ensure_git_repo(project_root: str) -> bool:
    git_dir = Path(project_root) / ".git"
    if not git_dir.exists():
        _run_git(["init"], project_root)
        _run_git(["config", "user.email", "sentinel@supervisor.local"], project_root)
        _run_git(["config", "user.name", "Sentinel Supervisor"], project_root)
        return True
    return False


def take_snapshot(project_root: str, task_id: str) -> str:
    _run_git(["add", "-A"], project_root)
    try:
        msg = f"sentinel-snapshot before {task_id}"
        _run_git(["commit", "--allow-empty", "-m", msg], project_root)
        sha = _run_git(["rev-parse", "HEAD"], project_root)
        _run_git(["branch", "-f", SNAPSHOT_BRANCH, "HEAD"], project_root)
        return sha
    except RuntimeError:
        sha = _run_git(["rev-parse", "HEAD"], project_root)
        return sha


def rollback_to_last_snapshot(project_root: str) -> str:
    branches = _run_git(["branch", "--list", SNAPSHOT_BRANCH], project_root)
    if not branches:
        raise RuntimeError("No snapshot branch found for rollback")
    sha = _run_git(["rev-parse", SNAPSHOT_BRANCH], project_root)
    _run_git(["checkout", "--force", SNAPSHOT_BRANCH], project_root)
    _run_git(["clean", "-fd"], project_root)
    return sha


def get_current_sha(project_root: str) -> str:
    try:
        return _run_git(["rev-parse", "--short", "HEAD"], project_root)
    except RuntimeError:
        return "no-commits"
