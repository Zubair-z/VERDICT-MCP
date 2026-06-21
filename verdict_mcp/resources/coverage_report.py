import os
import time
from ..core.sandbox import run_pytest_with_coverage


_cache: dict[str, dict] = {}
_cache_ttl: float = 30.0


def _get_cached(key: str) -> dict | None:
    entry = _cache.get(key)
    if entry and time.time() - entry["timestamp"] < _cache_ttl:
        return entry["data"]
    return None


def _set_cache(key: str, data: dict) -> None:
    _cache[key] = {"data": data, "timestamp": time.time()}
    if len(_cache) > 100:
        oldest = min(_cache.keys(), key=lambda k: _cache[k]["timestamp"])
        del _cache[oldest]


def invalidate_cache() -> None:
    _cache.clear()


def get_coverage_report(project_root: str) -> dict:
    test_dir = os.path.join(project_root, "tests")
    if not os.path.isdir(test_dir):
        return {
            "available": False,
            "error": "No tests/ directory found in project",
            "coverage": 0.0,
            "files_tested": 0,
            "details": []
        }

    source_files = []
    for root, dirs, files in os.walk(project_root):
        if "tests" in root or ".git" in root or "__pycache__" in root:
            continue
        for f in files:
            if f.endswith(".py"):
                source_files.append(os.path.join(root, f))

    matched_tests = 0
    total_source = len(source_files)
    details = []

    for src_file in source_files:
        basename = os.path.basename(src_file)
        test_name = f"test_{basename}"
        test_file = None
        for root, dirs, files in os.walk(test_dir):
            for f in files:
                if f == test_name:
                    test_file = os.path.join(root, f)
                    break
            if test_file:
                break

        cache_key = f"{src_file}:{test_file}"
        cached = _get_cached(cache_key) if test_file else None

        if cached:
            details.append(cached)
            if cached["status"] == "PASS":
                matched_tests += 1
        elif test_file:
            matched_tests += 1
            result = run_pytest_with_coverage(test_file, src_file, project_root)
            entry = {
                "source": basename,
                "test": os.path.basename(test_file),
                "coverage": result["coverage"],
                "passed": result["passed"],
                "failed": result["failed"],
                "status": "PASS" if result["success"] else "FAIL",
            }
            _set_cache(cache_key, entry)
            details.append(entry)
        else:
            details.append({
                "source": basename,
                "test": None,
                "coverage": 0.0,
                "passed": 0,
                "failed": 0,
                "status": "NO_TEST",
            })

    avg_coverage = 0.0
    if details:
        cov_values = [d["coverage"] for d in details if d["coverage"] > 0]
        if cov_values:
            avg_coverage = round(sum(cov_values) / len(cov_values), 2)

    return {
        "available": True,
        "average_coverage": avg_coverage,
        "total_source_files": total_source,
        "matched_tests": matched_tests,
        "files_tested": len([d for d in details if d["status"] == "PASS"]),
        "cached": any(_get_cached(f"{s}:test_{os.path.basename(s)}") for s in source_files),
        "details": details
    }
