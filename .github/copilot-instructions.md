# Custom Instructions for lazy-hippo

## Repository overview

`lazy-hippo` is a small CLI utility for manipulating video files without re-encoding. The project is built around `ffmpeg` and `ffprobe`, and the application logic is centered in a single file: `lazy_hippo.py`.

## Project layout

- `lazy_hippo.py` — main CLI implementation and ffmpeg/ffprobe wrappers
- `tests/test_lazy_hippo.py` — unit tests for the CLI and helpers
- `README.md` — user-facing usage documentation
- `pyproject.toml` — package metadata, dependencies, and Ruff config
- `Makefile` — local dev tasks (`install`, `test`, `lint`, etc.)
- `.venv/` — repository-local virtual environment preferred for Python work

## Environment and tooling

- Use the repo-local environment for Python execution and package installation.
- Prefer commands such as:

```bash
source .venv/bin/activate
.venv/bin/python -m pytest
uv run --group test pytest
uv run --group test ruff check lazy_hippo.py
```

- Do not install packages globally.
- This project targets Python `>=3.11,<4.0`.
- Native dependencies must be available on `PATH`: `ffmpeg` and `ffprobe`.
- On macOS, the usual install is:

```bash
brew install ffmpeg
```

## CLI shape

The entry point is `lazy-hippo`, implemented with Click. Common behavior:

- `info` — print metadata about a video
- `split` — extract time-based chunks or fixed-length segments
- `join` — concatenate compatible input files
- `repack` — change container without re-encoding
- `gif-preview` — build a preview GIF from a video
- `extract` — save frames from a video to disk

Common options:

- `-v, --verbose` — increases verbosity
- `-d, --debug` — enables debug logging
- `--help` — shows command-specific usage

## Coding patterns and conventions

- Keep the app in `lazy_hippo.py`; avoid adding submodules unless necessary.
- Follow the existing Click command structure and reuse `click.UsageError` / `click.ClickException` for user-facing CLI failures.
- Prefer `run_cmd(...)` for subprocess execution rather than ad hoc `subprocess.run()` calls.
- Use `locate_binary("ffmpeg")` and `locate_binary("ffprobe")` before invoking native commands.
- Use `probe_metadata(path, short=True/False)` to fetch ffprobe JSON.
- `TimeStamp` is the custom Click parameter type for `SS`, `MM:SS`, and `HH:MM:SS`; `-1` is reserved as a sentinel for auto-detect.
- Logging should go through the module logger `log`; avoid `print()` for status output.
- Keep command arguments as lists, not shell strings, and use `shlex.quote()` when quoting file paths inside concat lists.

## Testing and validation

- Tests are written in `unittest` style and live in `tests/test_lazy_hippo.py`.
- The repository also supports `pytest`/`ty` for running the suite.
- Preferred validation commands:

```bash
make test
make lint
.venv/bin/python -m pytest
uv run --group test pytest
```

- When changing behavior, add or update a focused test before finalizing the fix.
- Keep changes small and targeted; match the file-level conventions already present in the project.

## Code quality and linting

- Linter: `ruff`
- Configured rules: `E`, `F`, `B`, `UP`, `SIM`, `I`
- Ignored rules: `E501` and `F401`

```bash
ruff check .
ruff format .
```

## Project-specific gotchas

- This is a stream-copying tool: many commands avoid re-encoding whenever possible.
- `split --chunk` and `split --every` are mutually exclusive.
- The default `extract` output directory is `extracted_frames/`.
- `gif-preview` outputs a `.gif` next to the input file unless the caller overrides the target path.
- The CLI is intentionally single-file and reuses global logger state alongside Click context flags.

## Preferred workflow for repo work

1. Check the relevant command implementation in `lazy_hippo.py`.
2. Reuse the project’s existing Click and ffmpeg patterns.
3. Update or add focused tests in `tests/test_lazy_hippo.py` when behavior changes.
4. Validate with the repo-local environment and the project’s standard lint/test commands.
5. Keep user-facing documentation in sync with CLI changes.