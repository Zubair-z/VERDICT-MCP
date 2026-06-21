import os
import re
from typing import Any


LANGUAGE_PATTERNS = {
    ".js": {
        "name": "JavaScript",
        "comment_line": re.compile(r"^\s*//"),
        "comment_block": re.compile(r"/\*[\s\S]*?\*/"),
        "function_pattern": re.compile(
            r"(?:function\s+(\w+)|(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\(|(\w+)\s*\([^)]*\)\s*\{)",
            re.MULTILINE,
        ),
        "todo_pattern": re.compile(r"//\s*TODO\b", re.IGNORECASE),
        "pass_placeholder": re.compile(r"\b(function|async\s+function)\s+\w+\s*\([^)]*\)\s*\{\s*\}"),
    },
    ".ts": {
        "name": "TypeScript",
        "comment_line": re.compile(r"^\s*//"),
        "comment_block": re.compile(r"/\*[\s\S]*?\*/"),
        "function_pattern": re.compile(
            r"(?:function\s+(\w+)|(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\(|(\w+)\s*\([^)]*\)\s*(?::\s*\w+)?\s*\{)",
            re.MULTILINE,
        ),
        "todo_pattern": re.compile(r"//\s*TODO\b", re.IGNORECASE),
        "pass_placeholder": re.compile(r"\b(function|async\s+function)\s+\w+\s*\([^)]*\)\s*\{\s*\}"),
    },
    ".jsx": {
        "name": "JSX (React)",
        "comment_line": re.compile(r"^\s*//"),
        "comment_block": re.compile(r"/\*[\s\S]*?\*/"),
        "function_pattern": re.compile(
            r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\(|export\s+default\s+(?:function\s+)?(\w+))",
            re.MULTILINE,
        ),
        "todo_pattern": re.compile(r"//\s*TODO\b", re.IGNORECASE),
        "pass_placeholder": re.compile(r"\b(function|const)\s+\w+\s*=\s*\([^)]*\)\s*=>\s*\{\s*\}"),
    },
    ".tsx": {
        "name": "TSX (React)",
        "comment_line": re.compile(r"^\s*//"),
        "comment_block": re.compile(r"/\*[\s\S]*?\*/"),
        "function_pattern": re.compile(
            r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\(|export\s+default\s+(?:function\s+)?(\w+))",
            re.MULTILINE,
        ),
        "todo_pattern": re.compile(r"//\s*TODO\b", re.IGNORECASE),
        "pass_placeholder": re.compile(r"\b(function|const)\s+\w+\s*=\s*\([^)]*\)\s*=>\s*\{\s*\}"),
    },
    ".go": {
        "name": "Go",
        "comment_line": re.compile(r"^\s*//"),
        "function_pattern": re.compile(r"(?:func\s+(\w+))\s*\("),
        "todo_pattern": re.compile(r"//\s*TODO\b", re.IGNORECASE),
        "pass_placeholder": re.compile(r"func\s+\w+\s*\([^)]*\)\s*\{\s*\}"),
    },
    ".rs": {
        "name": "Rust",
        "comment_line": re.compile(r"^\s*//"),
        "function_pattern": re.compile(r"(?:fn\s+(\w+))\s*\("),
        "todo_pattern": re.compile(r"//\s*TODO\b", re.IGNORECASE),
        "pass_placeholder": re.compile(r"fn\s+\w+\s*\([^)]*\)\s*\{\s*\}"),
    },
    ".java": {
        "name": "Java",
        "comment_line": re.compile(r"^\s*//"),
        "comment_block": re.compile(r"/\*[\s\S]*?\*/"),
        "function_pattern": re.compile(
            r"(?:public|private|protected|static|\s)\s+(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*(?:throws\s+\w+)?\s*\{",
        ),
        "todo_pattern": re.compile(r"//\s*TODO\b", re.IGNORECASE),
        "pass_placeholder": re.compile(r"\{\s*\}"),
    },
    ".kt": {
        "name": "Kotlin",
        "comment_line": re.compile(r"^\s*//"),
        "function_pattern": re.compile(r"(?:fun\s+(\w+))\s*\("),
        "todo_pattern": re.compile(r"//\s*TODO\b", re.IGNORECASE),
        "pass_placeholder": re.compile(r"fun\s+\w+\s*\([^)]*\)\s*\{\s*\}"),
    },
}


def detect_language(file_path: str) -> dict[str, Any] | None:
    ext = os.path.splitext(file_path)[1].lower()
    return LANGUAGE_PATTERNS.get(ext)


def _check_io_operations(source: str, lang: str) -> bool:
    io_keywords = {
        "JavaScript": [r"fetch\s*\(", r"axios\.", r"\.get\s*\(", r"\.post\s*\(", r"fs\.\w+", r"XMLHttpRequest"],
        "TypeScript": [r"fetch\s*\(", r"axios\.", r"\.get\s*\(", r"\.post\s*\(", r"fs\.\w+", r"XMLHttpRequest"],
        "Go": [r"http\.", r"net\.", r"os\.", r"io\.", r"sql\.", r"db\.\w+"],
        "Rust": [r"std::fs", r"std::net", r"std::io", r"tokio::", r"reqwest::"],
        "Java": [r"java\.io\.", r"java\.net\.", r"java\.sql\.", r"File", r"Connection"],
        "Kotlin": [r"java\.io\.", r"java\.net\.", r"java\.sql\.", r"File", r"coroutines"],
    }
    patterns = io_keywords.get(lang, [])
    for pat in patterns:
        if re.search(pat, source):
            return True
    return False


def _check_try_catch(source: str, lang: str) -> bool:
    patterns = {
        "JavaScript": [r"try\s*\{", r"\.catch\s*\(", r"\.then\s*\("],
        "TypeScript": [r"try\s*\{", r"\.catch\s*\(", r"\.then\s*\("],
        "Go": [r"if\s+err\s*!=\s*nil"],
        "Rust": [r"\.unwrap\s*\(", r"\.expect\s*\(", r"match\s+.*\{", r"if\s+let\s+Err"],
        "Java": [r"try\s*\{", r"catch\s*\("],
        "Kotlin": [r"try\s*\{", r"catch\s*\("],
    }
    lang_patterns = patterns.get(lang, [])
    for pat in lang_patterns:
        if re.search(pat, source):
            return True
    return False


def audit_multi_lang(file_path: str) -> dict[str, Any]:
    """
    Audit a non-Python source file for quality issues.
    Returns structured result similar to Python's CodeAuditor.
    """
    ext = os.path.splitext(file_path)[1].lower()
    lang_info = detect_language(file_path)
    if not lang_info:
        return {
            "file": file_path,
            "audit_passed": True,
            "errors": [],
            "note": f"Unsupported language for extension '{ext}' — skipped",
        }

    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        return {
            "file": file_path,
            "audit_passed": False,
            "errors": [f"Cannot read file: {e}"],
        }

    errors = []
    lines = source.split("\n")
    lang_name = lang_info["name"]

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if lang_info["todo_pattern"].search(stripped):
            errors.append(f"[TODO_COMMENT] Line {i}: TODO comment found")
        if lang_info.get("pass_placeholder"):
            if re.match(r"^\s*$", stripped) and i < len(lines):
                prev = lines[i - 1].strip() if i > 1 else ""
                if re.search(r"\{$", prev) and re.match(r"^\s*\}$", lines[i].strip()):
                    errors.append(f"[PLACEHOLDER] Line {i}: Empty function body detected")

    if lang_info.get("pass_placeholder"):
        for match in lang_info["pass_placeholder"].finditer(source):
            errors.append(f"[PLACEHOLDER] Line {source[:match.start()].count(chr(10)) + 1}: Empty function placeholder")

    has_try = _check_try_catch(source, lang_name)
    has_io = _check_io_operations(source, lang_name)

    if has_io and not has_try:
        errors.append(f"[MISSING_EXCEPTION_HANDLING] I/O operations found but no try-catch/error handling detected")

    return {
        "file": file_path,
        "audit_passed": len(errors) == 0,
        "errors": errors,
        "language": lang_name,
    }
