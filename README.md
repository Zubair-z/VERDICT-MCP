# Verdict MCP

![CI](https://github.com/Zubair-z/VERDICT-MCP/actions/workflows/verdict.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com)

An unbypassable gatekeeper that enforces code completeness, test coverage,
and premium UI/UX standards on autonomous AI agents.

---

## The Problem

AI agents suffer from **Context Drift**, **Illusion of Completion (Hallucination)**,
and **Quality Degradation**:
- Mark tasks DONE but leave empty placeholders
- Skip critical error handling
- Generate unstyled "developer art" UIs
- Write superficial tests

## The Solution

**Verdict** sits between the AI agent and the file system as a
**programmatic gatekeeper**. The agent cannot mark a task as complete until
this server audits the code, validates design standards, and verifies 95%+
test coverage with 80%+ mutation score.

---

## Quick Start

```bash
pip install -r requirements.txt
```

Create a `plan.md` in your project root:

```markdown
# Project Plan
## TASK_001: Setup authentication
- [ ] Create auth_handler.py
- Status: PENDING
```

### Run as MCP Server (for MCP-compatible agents)

```bash
python -m verdict_mcp
```

### Run as REST API (for ANY agent — curl, HTTP clients, etc.)

```bash
python -m verdict_mcp.api_server
# → Server running at http://localhost:8000
```

```bash
# Try it:
curl http://localhost:8000/health
```

### Run as GitHub Action (CI/CD)

Add `.github/workflows/verdict.yml` (included in this repo) — Verdict
runs automatically on every push and PR.

---

## MCP Primitives

### Resources

| URI | Description |
|---|---|
| `project://master_plan` | Parsed plan.md as structured JSON with task states + SHA-256 hash |
| `project://task/{task_id}` | Individual task details (state, files, errors) |
| `project://ui_style_guide` | Premium design tokens (glassmorphism, neon accents, spacing) |
| `project://coverage_report` | Live pytest coverage metrics with caching (30s TTL) |

### Tools

| Tool | Parameters | What it does |
|---|---|---|
| `initialize_project_plan` | `plan_file_path` | Parses plan.md, verifies SHA-256 hash chain, builds state machine |
| `submit_task_for_audit` | `task_id`, `file_paths` | AST analysis — rejects `pass`, TODO, missing try-except, missing docstrings |
| `enforce_ui_standards` | `ui_file_path` | Validates premium stylesheets, glassmorphism, layout managers, color tokens |
| `run_strict_test_suite` | `test_file_path`, `target_file` | Sandboxed pytest with 95% coverage + 80% mutation score gate — auto-rollback on failure |
| `invalidate_cache` | — | Clears the coverage report cache |

### Prompts

| Name | Description |
|---|---|
| `validation_lifecycle` | Full lifecycle instructions for the executing agent |
| `audit_requirements` | What Verdict checks during AST audit |
| `ui_standards_requirements` | Premium UI requirements checklist |
| `test_requirements` | Test coverage + mutation score requirements |

---

## REST API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Server health check |
| POST | `/plan/init` | Initialize project plan |
| GET | `/plan/summary` | Get plan summary |
| GET | `/plan/task/{task_id}` | Get task details |
| POST | `/audit` | Submit files for AST audit |
| GET | `/ui/style-guide` | Get design tokens |
| POST | `/ui/validate` | Validate UI file |
| POST | `/tests/run` | Run tests with coverage + mutation |
| GET | `/coverage` | Get coverage report |
| POST | `/coverage/invalidate` | Clear coverage cache |
| POST | `/pipeline/run` | Run full validation lifecycle in one call |

### Full Pipeline Example

```bash
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "TASK_001",
    "source_files": ["auth_handler.py"],
    "test_file": "tests/test_auth_handler.py",
    "target_file": "auth_handler.py",
    "ui_file": "main_window.py"
  }'
```

---

## Validation Lifecycle

```
[Agent Writes Code]
       ⬇
[submit_task_for_audit]  → AST verification (pass/TODO rejected)
       ⬇
[enforce_ui_standards]   → Premium UI validation (glassmorphism enforced)
       ⬇
[run_strict_test_suite]  → pytest + 95% coverage + 80% mutation score
       ⬇
[Task → COMPLETED]
```

---

## Multi-Language Support

Verdict now audits **non-Python files** too:

| Language | Extensions | Checks |
|---|---|---|
| JavaScript | `.js` | TODO, empty functions, missing error handling |
| TypeScript | `.ts` | TODO, empty functions, missing error handling |
| React | `.jsx`, `.tsx` | TODO, empty components, missing error handling |
| Go | `.go` | TODO, empty funcs, missing error handling |
| Rust | `.rs` | TODO, empty fn, missing error handling |
| Java | `.java` | TODO, empty methods, missing try-catch |
| Kotlin | `.kt` | TODO, empty fun, missing error handling |

---

## Features

- **AST-level auditing** — detects `pass`, `# TODO`, missing exception handling, missing docstrings
- **Multi-language auditing** — JS, TS, Go, Rust, Java, Kotlin, React
- **UI dictatorship** — rejects unstyled components, enforces design tokens (glassmorphism, neon)
- **95% coverage gate** with **mutation testing** — tests must catch injected bugs
- **REST API** — agent-agnostic: use with curl, LangChain, AutoGPT, or any HTTP client
- **GitHub Actions** — zero-config CI/CD integration
- **Git-backed snapshots** — auto-snapshot before audit, auto-rollback on test failure
- **Dependency DAG** — tasks cannot start until dependencies are complete
- **Plan hash chain** — SHA-256 integrity check prevents plan tampering
- **Coverage caching** — 30-second TTL avoids redundant test runs
- **Structured output** — tools return typed data (not just strings) for better agent integration

---

## Development

```bash
git clone https://github.com/Zubair-z/VERDICT-MCP.git
cd VERDICT-MCP
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v --cov=verdict_mcp --cov-report=term-missing

# Start MCP server
python -m verdict_mcp

# Start REST API
python -m verdict_mcp.api_server
```
