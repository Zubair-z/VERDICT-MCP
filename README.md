# Verdict MCP

An unbypassable MCP gatekeeper that enforces code completeness, test coverage,
and premium UI/UX standards on autonomous AI agents.

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

Then run the server:

```bash
python -m verdict_mcp
```

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

## Features

- **AST-level auditing** — detects `pass`, `# TODO`, missing exception handling, missing docstrings
- **UI dictatorship** — rejects unstyled components, enforces design tokens (glassmorphism, neon)
- **95% coverage gate** with **mutation testing** — tests must catch injected bugs
- **Git-backed snapshots** — auto-snapshot before audit, auto-rollback on test failure
- **Dependency DAG** — tasks cannot start until dependencies are complete
- **Plan hash chain** — SHA-256 integrity check prevents plan tampering
- **Coverage caching** — 30-second TTL avoids redundant test runs
- **Structured output** — tools return typed data (not just strings) for better agent integration
