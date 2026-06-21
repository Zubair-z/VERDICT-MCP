Thanks for taking the time to contribute! Here's how you can help:

## Setup

```bash
git clone https://github.com/Zubair-z/VERDICT-MCP.git
cd VERDICT-MCP
pip install -r requirements.txt
```

## Making Changes

1. Create a branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Run tests: `python -m pytest tests/ -v`
4. Run linter: `pip install ruff && ruff check .`
5. Commit with clear message: `git commit -m "feat: add your feature"`
6. Push and open a PR

## Code Style

- Follow existing patterns (docstrings, try-except, no pass/TODO)
- All functions must have docstrings
- I/O operations must be wrapped in try-except
- Tests must achieve 95%+ coverage on changed files

## PR Checklist

- [ ] Tests pass
- [ ] New tests added for new features
- [ ] Code follows Verdict's own standards (audit yourself!)
- [ ] Documentation updated

## Questions?

Open a Discussion or issue — we're friendly!
