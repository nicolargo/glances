# Skill: Lint and Format

Run code formatting and linting on the Glances codebase.

## Instructions

1. Run formatting first, then linting:
   ```bash
   make format && make lint
   ```
2. If there are remaining issues that `--fix` could not resolve, list them and suggest manual fixes.
3. Optionally, if the user asks for a full check, run all pre-commit hooks:
   ```bash
   make pre-commit
   ```

## Tools used

- **Ruff** for both formatting and linting (configured in `pyproject.toml`)
- **Pre-commit hooks** include: ruff, gitleaks (secret detection), shellcheck, and others

## Notes

- The virtualenv must already exist (`.venv-uv/`). If not, run `make venv-dev` first.
- Never change ruff configuration without explicit approval — linting rules are shared across all contributors.
