# Custom Instructions for lazy-hippo

## Repository Overview

`lazy-hippo` is a CLI utility for manipulating video files without re-encoding, built on top of `ffmpeg` and `ffprobe`.

## Project Structure

- `lazy_hippo.py` — Main CLI application (single-file module)
- `tests/test_lazy_hippo.py` — Unit tests using unittest
- `pyproject.toml` — Project configuration (hatchling build system)
- `Makefile` — Development tasks (install, test, lint, etc.)

## CLI Commands

The main entry point is `lazy-hippo` with these subcommands:

| Command | Description |
|---------|-------------|
| `info` | Display video file metadata |
| `split` | Split video into segments |
| `join` | Concatenate multiple videos |
| `repack` | Remux video without re-encoding |
| `gif-preview` | Convert video to GIF |
| `extract` | Extract audio/video streams |

### Common Options

- `-v, --verbose` — Increase verbosity (can be repeated)
- `--debug` — Enable debug logging

## Key Patterns

### Click CLI Structure

The CLI uses Click with a group and subcommands. Key patterns:

```python
import click

@click.group()
@click.option('-v', '--verbose', count=True)
@click.option('--debug', is_flag=True)
def cli():
    pass

@cli.command()
@click.argument('file', type=click.Path(exists=True))
def info(file):
    pass
```

### Custom Parameter Types

`TimeStamp` is a custom Click `ParamType` for parsing timestamps:

- Integer: seconds (or -1 for auto-detect)
- String: `SS`, `MM:SS`, or `HH:MM:SS` formats

### Binary Discovery

`locate_binary(command)` finds system binaries using `which`:

```python
ffmpeg = locate_binary('ffmpeg')
```

### Metadata Extraction

`probe_metadata(video_file, short=True)` uses ffprobe to get video info.

## Testing

- Framework: `unittest` (not pytest)
- Test runner: `ty` (CLI test runner)
- Run tests: `make test` or `ty`

### Running Tests

```bash
make test        # Run all tests
ty               # Run with ty CLI
python -m unittest tests.test_lazy_hippo
```

## Code Quality

- Linter: `ruff`
- Configuration: `[tool.ruff.lint]` in `pyproject.toml`
- Selected rules: `E`, `F`, `B`, `UP`, `SIM`, `I`
- Ignored: `E501` (line too long), `F401` (unused import)

### Linting

```bash
make lint        # Run ruff
ruff check .     # Direct ruff
ruff format .    # Format code
```

## Development Commands

```bash
make install     # Create venv and install dependencies
make test        # Run tests
make lint        # Run linter
make format      # Format code
make clean       # Clean build artifacts
```

## Dependencies

- `click>=8.1.3,<9` — CLI framework
- `colorama>=0.4.6,<0.5` — Colored output
- Runtime requires: `ffmpeg` and `ffprobe` (system binaries)

## Gotchas

1. **System dependencies required**: ffmpeg/ffprobe must be installed separately (`brew install ffmpeg`)
2. **No re-encoding**: Commands remux without re-encoding (fast but limited)
3. **Single-file module**: All code in `lazy_hippo.py` — no submodules
4. **Custom TimeStamp type**: Accepts -1 as sentinel for auto-detect
5. **Global state**: Uses global `debug` and `verbose` variables

## Style Notes

- Logging via `log` module (not print statements)
- Use `click.UsageError` for CLI errors
- Use `quote()` from shlex for safe subprocess arguments
- Return `CompletedProcess` objects from subprocess calls