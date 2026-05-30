# AGENT.md

Repo workflow for any new session or subagent.

## Scope
- Main code: `qoi.py`
- Tests: `tests/test_qoi_unittest.py`
- Plan files:
  - `OPTIMIZATION_PLAN.md`
  - `OPTIMIZATION_CHECKLIST.md`

## Rules
1. Before making any code change, read `OPTIMIZATION_PLAN.md` and `OPTIMIZATION_CHECKLIST.md`.
2. Follow the checklist order unless the user asks for a different task.
3. After each round of code changes, run unittests.
4. Only mark a checklist task complete after the related unittests pass.
5. Keep changes small and focused.

## Test command
Run after every code-change round:

```sh
python -m unittest discover -s tests -p "test_*.py"
```

If the environment uses uv, use:

```sh
uv run python -m unittest discover -s tests -p "test_*.py"
```

## When updating progress
- Update `OPTIMIZATION_CHECKLIST.md`
- Mark completed items with `[x]` only when tests pass
- Do not delete or replace `OPTIMIZATION_PLAN.md`
