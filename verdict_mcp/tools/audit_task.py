import os
import ast
import tokenize
import io
from ..core.state_machine import project_state, TaskState
from ..core.multilang_audit import audit_multi_lang


class CodeAuditor(ast.NodeVisitor):
    def __init__(self):
        self.errors: list[dict] = []
        self.function_count = 0
        self.class_count = 0

    def visit_FunctionDef(self, node):
        self.function_count += 1
        self._check_for_placeholders(node)
        self._check_for_exception_handling(node)
        self._check_for_docstring(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.function_count += 1
        self._check_for_placeholders(node)
        self._check_for_exception_handling(node)
        self._check_for_docstring(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.class_count += 1
        self.generic_visit(node)

    def _check_for_placeholders(self, node):
        for child in ast.walk(node):
            if isinstance(child, ast.Pass):
                self.errors.append({
                    "line": child.lineno,
                    "type": "PLACEHOLDER",
                    "message": f"Function '{node.name}' contains empty 'pass' statement at line {child.lineno}"
                })
                break

        if node.body and hasattr(node.body[0], 'value'):
            first_expr = node.body[0]
            if isinstance(first_expr, ast.Expr) and isinstance(first_expr.value, ast.Constant):
                val = str(first_expr.value.value)
                if val.strip().upper().startswith("TODO"):
                    self.errors.append({
                        "line": first_expr.lineno,
                        "type": "PLACEHOLDER",
                        "message": f"Function '{node.name}' contains TODO placeholder at line {first_expr.lineno}"
                    })

    def _check_for_exception_handling(self, node):
        has_try = False
        has_raise = False
        io_or_network = False

        for child in ast.walk(node):
            if isinstance(child, ast.Try):
                has_try = True
            if isinstance(child, ast.Raise):
                has_raise = True
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    name = child.func.attr.lower()
                    if name in ("open", "connect", "request", "get", "post", "put", "delete", "query", "execute"):
                        io_or_network = True
                    obj = child.func.value
                    if isinstance(obj, ast.Name) and obj.id.lower() in ("db", "database", "conn", "connection", "client", "session", "file"):
                        io_or_network = True

        if io_or_network and not has_try:
            self.errors.append({
                "line": node.lineno,
                "type": "MISSING_EXCEPTION_HANDLING",
                "message": f"Function '{node.name}' performs I/O or network operations but lacks try-except at line {node.lineno}"
            })

    def _check_for_docstring(self, node):
        docstring = ast.get_docstring(node)
        if not docstring:
            self.errors.append({
                "line": node.lineno,
                "type": "MISSING_DOCSTRING",
                "message": f"Function '{node.name}' is missing a docstring at line {node.lineno}"
            })


def check_forbidden_tokens(file_path: str) -> list[dict]:
    errors = []
    with open(file_path, encoding="utf-8") as f:
        source = f.read()

    for i, line in enumerate(source.split("\n"), 1):
        stripped = line.strip()
        if stripped == "# TODO" or stripped.startswith("# TODO "):
            errors.append({
                "line": i,
                "type": "TODO_COMMENT",
                "message": f"TODO comment found at line {i}"
            })
        if stripped == "pass" and not stripped.startswith("def ") and not stripped.startswith("class "):
            pass

    return errors


def execute(task_id: str, file_paths: list[str], log_func=None) -> dict:
    task = project_state.get_task(task_id)

    can_proceed, reason = project_state.can_proceed_to(task_id)
    if not can_proceed:
        return {"success": False, "error": reason}

    if log_func:
        log_func("info", f"Starting AST audit for {task_id}: {', '.join(file_paths)}")

    project_root = os.path.dirname(os.path.abspath(project_state.plan_file_path)) if project_state.plan_file_path else "."
    all_errors = []
    file_results = []

    for file_path in file_paths:
        abs_path = os.path.join(project_root, file_path) if not os.path.isabs(file_path) else file_path
        file_result = {
            "file": file_path,
            "audit_passed": False,
            "errors": [],
            "function_count": 0,
            "class_count": 0,
        }

        if not os.path.isfile(abs_path):
            file_result["errors"].append(f"File not found: {file_path}")
            file_result["audit_passed"] = False
            file_results.append(file_result)
            all_errors.append(file_result["errors"])
            continue

        if not file_path.endswith(".py"):
            ml_result = audit_multi_lang(abs_path)
            file_result["audit_passed"] = ml_result["audit_passed"]
            file_result["errors"] = ml_result["errors"]
            file_result["language"] = ml_result.get("language", "unknown")
            if ml_result["audit_passed"]:
                file_result["message"] = f"Multi-language audit passed ({ml_result.get('language', 'unknown')})"
            else:
                file_result["message"] = f"Multi-language audit failed ({ml_result.get('language', 'unknown')})"
            file_results.append(file_result)
            all_errors.extend(ml_result["errors"])
            continue

        try:
            with open(abs_path, encoding="utf-8") as f:
                source = f.read()
        except Exception as e:
            file_result["errors"].append(f"Cannot read file: {e}")
            file_results.append(file_result)
            all_errors.append(file_result["errors"])
            continue

        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError as e:
            file_result["errors"].append(f"Syntax error: {e.msg} at line {e.lineno}")
            file_results.append(file_result)
            all_errors.append(file_result["errors"])
            continue

        auditor = CodeAuditor()
        auditor.visit(tree)

        file_result["function_count"] = auditor.function_count
        file_result["class_count"] = auditor.class_count

        forbidden = check_forbidden_tokens(abs_path)
        auditor.errors.extend(forbidden)

        if auditor.errors:
            file_result["errors"] = [
                f"[{e['type']}] Line {e['line']}: {e['message']}" for e in auditor.errors
            ]
            file_result["audit_passed"] = False
        else:
            file_result["audit_passed"] = True

        all_errors.extend(auditor.errors)
        file_results.append(file_result)

    overall_passed = all(r["audit_passed"] for r in file_results)

    task.state = TaskState.AUDIT_FAILED if not overall_passed else TaskState.UI_REVIEW
    task.audit_errors = [str(e) for e in all_errors]

    if log_func:
        log_func("info", f"Audit {'PASSED' if overall_passed else 'FAILED'} for {task_id} ({len(all_errors)} errors)")

    # Take snapshot on audit pass
    if overall_passed:
        try:
            from ..core.git_snapshot import take_snapshot
            sha = take_snapshot(project_root, task_id)
        except Exception:
            sha = None

    return {
        "success": overall_passed,
        "task_id": task_id,
        "task_title": task.title,
        "audit_result": "PASSED" if overall_passed else "FAILED",
        "file_results": file_results,
        "total_errors": len(all_errors),
        "new_state": task.state.value,
        "snapshot_taken": overall_passed,
        "message": "All files passed AST audit" if overall_passed else "Audit failed. Fix errors and resubmit."
    }
