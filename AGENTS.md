# AGENTS.md

## Repository overview

This repository contains a small CLI utility for manipulating video files without re-encoding. The application logic is centered in `lazy_hippo.py`, with tests in `tests/test_lazy_hippo.py`.

## Required Python environment

This project is expected to run inside the repository-local virtual environment at `.venv`.

- Always use `.venv` for Python execution, package installation, and dependency management.
- Do not install Python packages globally.
- Prefer these commands when working with Python modules:

```bash
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
python -m pytest
```

If using `uv`, keep it scoped to the repo-local environment:

```bash
uv sync
source .venv/bin/activate
uv run --group test pytest
uv run --group test ruff check lazy_hippo.py
```

When invoking Python directly, use the venv interpreter explicitly when possible:

```bash
.venv/bin/python -m pip install <package>
.venv/bin/python -m pytest
```

## Development workflow

- Keep changes focused and minimal.
- Follow the project’s existing CLI and test patterns.
- Use the repo’s Makefile when appropriate:

```bash
make install
make test
make lint
```

## Validation

Before considering work complete:

- run the relevant tests with the project venv,
- prefer the repo-local environment instead of system Python,
- ensure any added dependency installation is done in `.venv`.

## Key project notes

- `lazy_hippo.py` is the single-file app entry point.
- The CLI is built with Click.
- Runtime dependencies include `ffmpeg` / `ffprobe` and Python packages from the project config.
- Use `uv` and `.venv` as the standard environment for script execution and module work.
