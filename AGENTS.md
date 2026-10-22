# Project Instructions

These instructions apply to all work in this repository. Keep them as the source of truth for project-specific guidance.

## Project Overview

`lazy-hippo` is a Click-based CLI for manipulating video files without re-encoding, using `ffmpeg` and `ffprobe`. The application is intentionally centered in `lazy_hippo.py`.

Key files:

- `lazy_hippo.py` — CLI commands, helpers, and native-tool wrappers
- `tests/test_lazy_hippo.py` — unit tests (written with `unittest`, run with pytest)
- `pyproject.toml` — package metadata, dependencies, and Ruff configuration
- `Makefile` — install, lint, test, and coverage targets
- `README.md` — user-facing installation and usage documentation

## Python and Environment

- Supported Python versions are 3.11 through 3.15 (`requires-python = ">=3.11,<3.16"`).
- Use the repository-local `.venv` for Python execution and dependency management. Do not install packages globally.
- Prefer `uv` for environment setup and project commands:

  ```bash
  uv sync --group test
  uv run --group test pytest
  uv run --group test ruff check lazy_hippo.py
  uv run --group test ty check lazy_hippo.py
  ```

- The Makefile provides `make install`, `make test`, `make lint`, and `make coverage`.
- For pip installation into an existing environment, use `make install UV_INSTALL=0 PYTHON=.venv/bin/python`.
- Runtime commands require `ffmpeg` and `ffprobe` on `PATH`. On macOS, install them with `brew install ffmpeg`.

## Implementation Conventions

- Keep application logic in `lazy_hippo.py`; avoid new modules unless necessary.
- Follow the existing Click command patterns. Report user-facing CLI failures with `click.UsageError` or `click.ClickException`.
- Use `run_cmd(...)` for subprocess execution and `locate_binary("ffmpeg")` / `locate_binary("ffprobe")` before invoking native tools.
- Use `probe_metadata(path, short=True/False)` for ffprobe JSON.
- Keep subprocess arguments as lists, not shell strings. Use `shlex.quote()` for paths embedded in ffmpeg concat-list files.
- Send status and diagnostic output through the module logger `log`; avoid `print()` for status output.
- `TimeStamp` accepts `SS`, `MM:SS`, and `HH:MM:SS`; `-1` is reserved as the auto-detect sentinel.
- Preserve stream-copy behavior where possible; these commands intentionally avoid re-encoding.

## CLI Behavior to Preserve

- Commands are `info`, `split`, `join`, `repack`, `gif-preview`, and `extract`.
- `split --chunk` and `split --every` are mutually exclusive.
- `extract` defaults to the `extracted_frames/` output directory.
- `gif-preview` writes a `.gif` next to the input unless a target path is provided.
- The CLI intentionally reuses global logger state alongside Click context flags.

## Testing and Quality

- For behavior changes, add or update a focused test in `tests/test_lazy_hippo.py`.
- Run the relevant tests and quality checks with the repo-local environment before finishing. Prefer:

  ```bash
  make test
  make lint
  ```

- Ruff is configured in `pyproject.toml` with `E`, `F`, `B`, `UP`, `SIM`, and `I`; `E501` and `F401` are ignored.
- Keep changes focused, follow existing formatting and patterns, and update the README when user-facing behavior changes.
