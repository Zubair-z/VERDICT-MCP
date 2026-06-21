import subprocess
import sys
import os
import tempfile
import json
import random
import ast
import copy


MUTATION_OPERATORS = [
    ("replace_gt_with_lt", lambda src: src.replace("> ", "< ")),
    ("replace_eq_with_neq", lambda src: src.replace("==", "!=")),
    ("replace_and_with_or", lambda src: src.replace(" and ", " or ")),
    ("remove_not", lambda src: src.replace("not ", "")),
    ("replace_true_with_false", lambda src: src.replace("True", "False")),
]


def run_pytest_with_coverage(
    test_file_path: str,
    target_file: str,
    project_root: str,
    timeout: int = 120
) -> dict:
    if not os.path.isfile(test_file_path):
        return {
            "success": False,
            "error": f"Test file not found: {test_file_path}",
            "coverage": 0.0,
            "passed": 0,
            "failed": 0,
            "output": ""
        }

    if not os.path.isfile(target_file):
        return {
            "success": False,
            "error": f"Target source file not found: {target_file}",
            "coverage": 0.0,
            "passed": 0,
            "failed": 0,
            "output": ""
        }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        cov_path = f.name

    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                test_file_path,
                "--cov", target_file,
                "--cov-report", f"json:{cov_path}",
                "--tb=short",
                "-q",
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=timeout,
        )

        output = result.stdout + result.stderr

        passed = output.count("PASSED")
        failed_count = output.count("FAILED")
        errors = output.count("ERRORS")

        coverage = 0.0
        if os.path.isfile(cov_path):
            with open(cov_path, encoding="utf-8") as f:
                cov_data = json.load(f)
            files_data = cov_data.get("files", {})
            target_abs = os.path.abspath(target_file)
            for file_path, file_cov in files_data.items():
                file_abs = os.path.abspath(file_path)
                if file_abs == target_abs:
                    summary = file_cov.get("summary", {})
                    coverage = summary.get("percent_covered", 0.0)
                    break
            os.unlink(cov_path)

        success = result.returncode == 0 and coverage >= 95.0

        return {
            "success": success,
            "error": "" if success else (f"Tests failed ({failed_count} failed) or coverage below 95%" if coverage < 95.0 else result.stderr[:500]),
            "coverage": round(coverage, 2),
            "passed": passed,
            "failed": failed_count,
            "errors": errors,
            "output": output[:2000]
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Test suite timed out",
            "coverage": 0.0,
            "passed": 0,
            "failed": 0,
            "output": ""
        }
    except FileNotFoundError as e:
        return {
            "success": False,
            "error": f"pytest not found: {e}",
            "coverage": 0.0,
            "passed": 0,
            "failed": 0,
            "output": ""
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "coverage": 0.0,
            "passed": 0,
            "failed": 0,
            "output": ""
        }
    finally:
        if os.path.isfile(cov_path):
            try:
                os.unlink(cov_path)
            except OSError:
                pass


def run_mutation_testing(
    test_file_path: str,
    target_file: str,
    project_root: str,
    timeout: int = 60
) -> dict:
    if not os.path.isfile(target_file):
        return {
            "success": False,
            "error": f"Target file not found: {target_file}",
            "mutation_score": 0.0,
            "killed": 0,
            "survived": 0,
            "total": 0,
            "details": []
        }

    with open(target_file, encoding="utf-8") as f:
        original_source = f.read()

    try:
        ast.parse(original_source)
    except SyntaxError:
        return {
            "success": False,
            "error": "Target file has syntax errors",
            "mutation_score": 0.0,
            "killed": 0,
            "survived": 0,
            "total": 0,
            "details": []
        }

    killed = 0
    survived = 0
    details = []

    for op_name, mutator in MUTATION_OPERATORS:
        mutated = mutator(original_source)
        if mutated == original_source:
            continue

        try:
            ast.parse(mutated)
        except SyntaxError:
            continue

        mutant_path = target_file + ".mutant"
        try:
            with open(mutant_path, "w", encoding="utf-8") as f:
                f.write(mutated)

            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_file_path, "--tb=line", "-q"],
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=timeout,
            )

            mutation_killed = result.returncode != 0

            if mutation_killed:
                killed += 1
            else:
                survived += 1

            details.append({
                "operator": op_name,
                "killed": mutation_killed,
                "output": result.stdout[:200] if not mutation_killed else ""
            })

        except subprocess.TimeoutExpired:
            details.append({
                "operator": op_name,
                "killed": False,
                "error": "timed out"
            })
            survived += 1
        finally:
            if os.path.isfile(mutant_path):
                os.unlink(mutant_path)

    total = killed + survived
    score = round((killed / total * 100), 2) if total > 0 else 0.0

    return {
        "success": score >= 80.0,
        "mutation_score": score,
        "killed": killed,
        "survived": survived,
        "total": total,
        "details": details
    }
