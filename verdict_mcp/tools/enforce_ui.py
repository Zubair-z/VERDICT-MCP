import os
import re
from ..core.state_machine import project_state, TaskState
from ..resources.ui_style_guide import DESIGN_TOKENS, ESSENTIAL_STYLE_PATTERNS


def execute(ui_file_path: str, log_func=None) -> dict:
    project_root = os.path.dirname(os.path.abspath(project_state.plan_file_path)) if project_state.plan_file_path else "."
    abs_path = os.path.join(project_root, ui_file_path) if not os.path.isabs(ui_file_path) else ui_file_path

    if not os.path.isfile(abs_path):
        return {
            "success": False,
            "error": f"UI file not found: {ui_file_path}"
        }

    try:
        with open(abs_path, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {
            "success": False,
            "error": f"Cannot read file: {e}"
        }

    errors = []
    warnings = []
    checks_passed = 0
    checks_total = len(ESSENTIAL_STYLE_PATTERNS)

    for pattern in ESSENTIAL_STYLE_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            checks_passed += 1
        else:
            errors.append(f"Missing required style pattern: {pattern}")

    if "setStyleSheet" not in content and "stylesheet" not in content.lower():
        errors.append("No setStyleSheet() call found — UI must use custom stylesheets")

    if DESIGN_TOKENS["glassmorphism"]["enabled"]:
        if "rgba" not in content:
            warnings.append("Glassmorphism enabled but no rgba() color found")

        if "backdrop-filter" not in content:
            warnings.append("Glassmorphism enabled but backdrop-filter not found")

    primary_color = DESIGN_TOKENS["colors"]["primary"]
    if primary_color.lower() in content.lower():
        checks_passed += 0.5
    else:
        warnings.append(f"Primary theme color {primary_color} not found in stylesheet")

    if DESIGN_TOKENS["pyside6_specific"]["disable_native_style"]:
        if "Fusion" in content or "QStyleFactory" in content:
            checks_passed += 0.5
        else:
            warnings.append("Native style may be active — consider setting Fusion style")

    layout_elements = ["QHBoxLayout", "QVBoxLayout", "QGridLayout"]
    found_layouts = [e for e in layout_elements if e in content]
    if not found_layouts:
        errors.append("No layout managers found (QHBoxLayout, QVBoxLayout, or QGridLayout)")

    if "QWidget" in content and "border-radius" not in content:
        warnings.append("QWidget found but no border-radius applied")

    style_checks = {
        "has_custom_stylesheet": bool(re.search(r"setStyleSheet|stylesheet", content, re.IGNORECASE)),
        "has_color": bool(re.search(r"color:\s*#", content)),
        "has_background": bool(re.search(r"background-color:\s*#", content)),
        "has_border_radius": bool(re.search(r"border-radius:\s*\d+px", content)),
        "has_rgba": "rgba" in content,
        "has_glassmorphism": "backdrop-filter" in content,
        "has_layout": len(found_layouts) > 0,
        "has_fusion_style": "Fusion" in content or "QStyleFactory" in content,
    }

    total_passed = sum(1 for v in style_checks.values() if v)
    total_checks = len(style_checks)
    score = round((total_passed / total_checks) * 100, 1)

    passed = len(errors) == 0 and score >= 70

    if log_func:
        log_func("info", f"UI validation: score={score}%, passed={passed}, errors={len(errors)}")

    if passed:
        tid = project_state.current_task_id
        if tid:
            t = project_state.get_task(tid)
            t.ui_errors = []
            t.state = TaskState.TESTING

    return {
        "success": passed,
        "ui_file": ui_file_path,
        "score": score,
        "checks_passed": checks_passed,
        "checks_total": checks_total,
        "style_checks": style_checks,
        "errors": errors,
        "warnings": warnings,
        "message": "UI standards validated successfully" if passed else "UI validation failed. Apply premium design tokens and resubmit.",
        "design_tokens_hint": {
            "primary_color": DESIGN_TOKENS["colors"]["primary"],
            "secondary_color": DESIGN_TOKENS["colors"]["secondary"],
            "base_bg": DESIGN_TOKENS["theme"]["base"],
            "surface_bg": DESIGN_TOKENS["theme"]["surface"],
            "glass_bg": DESIGN_TOKENS["glassmorphism"]["background"],
            "border_radius_card": DESIGN_TOKENS["border_radius"]["card"],
            "font_family": DESIGN_TOKENS["typography"]["font_family"],
        }
    }
