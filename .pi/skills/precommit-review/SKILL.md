---
name: precommit-review
description: Review only the currently staged code changes before a commit. Use this for pre-commit review, ruff formatting, ruff lint fixes, and a short summary, while leaving the final commit decision to the user.
---

# Precommit Review

Use this skill when the user asks for code review or pre-commit cleanup of staged changes.

## Rules

1. **Do not commit by default.** Never run `git commit`, `git commit --amend`, or `git push` unless the user explicitly asks. Always leave the commit decision to the user.
2. **Only review currently staged changes.** Use `git diff --cached` and `git diff --cached --name-only --diff-filter=ACMR`. Do not review unstaged changes.
3. **Only run tools on staged Python files.** Limit `ruff` work to staged `*.py` and `*.pyi` files.
4. **Protect partially staged files.** Before running `ruff`, check whether any staged Python file also has unstaged changes. If so, stop and warn the user instead of formatting that file.
5. **Use `ruff` for both formatting and checks.** Run:
   - `ruff format <files>`
   - `ruff check --fix <files>`
   - `ruff format <files>`
   If `ruff` is not on PATH, use `uvx ruff ...`.
6. **Re-stage modified files.** If `ruff` changes a staged file, run `git add -- <files>`.
7. **Generate a commit message suggestion.** After review, suggest a commit message following Conventional Commits rules based only on the currently staged changes.
8. **Report clearly.** Summarize reviewed staged files, fixes made, any remaining issues, whether the staged diff changed after formatting/fixing, and include the suggested commit message.

## Recommended workflow

1. List staged files:
   ```sh
   git diff --cached --name-only --diff-filter=ACMR
   ```
2. Review only the staged diff:
   ```sh
   git diff --cached -- <files>
   ```
3. Filter to staged Python files.
4. Check for partially staged Python files:
   ```sh
   git diff --name-only -- <files>
   ```
   If any file appears here, stop and tell the user that `ruff` would touch unstaged work.
5. Run `ruff` on the staged Python files only.
6. Re-stage any modified files.
7. Show the updated staged diff if helpful.
8. Draft a Conventional Commits style commit message suggestion based on the staged diff only.
9. Give a short review summary, include the commit message suggestion, and ask the user whether they want to commit.

## Output expectations

Keep the response short and include:
- staged files reviewed
- issues found
- files changed by `ruff`
- remaining concerns, if any
- a suggested commit message following Conventional Commits
- a reminder that the user decides whether to commit
