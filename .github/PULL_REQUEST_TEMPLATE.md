## Summary

Describe what this PR changes and why.

## Type of Change

- [ ] Bug fix
- [ ] New feature / integration
- [ ] Refactoring / performance
- [ ] Documentation / eval dataset

## Verification Checklist

- [ ] `ruff check .` and `ruff format --check .` pass
- [ ] `pytest -v` passes
- [ ] `python -m evals.run_eval --min-category-accuracy 0.95` passes
- [ ] `cd frontend && npm run typecheck && npm run build` passes
- [ ] No secrets, `.env` files, or local `*.db` artifacts included
