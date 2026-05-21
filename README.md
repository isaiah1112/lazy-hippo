![logo](./logo.png "Lazy Hippo")

[![Python Tests](https://github.com/isaiah1112/lazy-hippo/actions/workflows/lint-and-test.yml/badge.svg)](https://github.com/isaiah1112/lazy-hippo/actions/workflows/lint-and-test.yml)

# lazy-hippo

`lazy-hippo` is a small command-line utility for manipulating video files without re-encoding, built on top of `ffmpeg` and `ffprobe`.

## Table of Contents
- Getting Started
- Installation
- Dependencies
- Usage
  - info
  - split
  - join
  - repack
  - gif-preview
  - extract
- Contributing
- License
- Supported Python Versions

## Getting Started
Before using lazy-hippo, install the native tools it depends on:

- ffmpeg — https://ffmpeg.org
- ffprobe — included with ffmpeg

On macOS you can install with Homebrew:
```bash
brew install ffmpeg
```

## Installation
Recommended (uses the repository Makefile to create a venv with `uv`):

```bash
make install
```

Skip virtualenv creation:

```bash
make install UV_INSTALL=0
```

Alternatively, install with pip in an existing venv:

```bash
pip install -e .
```

## Dependencies
- ffmpeg
- ffprobe

## Usage
Run `lazy-hippo --help` or any subcommand with `--help` for full options.

Subcommands:
- info — print video metadata
- split — extract chunks from a video
- join — concatenate multiple files
- repack — change container (no re-encoding)
- gif-preview — generate a preview GIF
- extract — save periodic frames (default output directory is `extracted_frames/`)

### Info
Get basic human-readable metadata (use `-f json` for full JSON output):

```bash
lazy-hippo info my-video.mp4
```

Example:
```
filename: my-video.mp4
duration: 1816s
size: 327MB
bit_rate: 1509kb/s
codec_name: h264
height: 480
```

### Split
Specify chunks using start/stop pairs. Times may be seconds (e.g., `25 50`) or timecodes (`1:25 3:45`). Supports hh:mm:ss.

Single chunk:
```bash
lazy-hippo split -C 5 25 my-video.mp4
# -> my-video-0.mp4
```

Multiple chunks (order doesn't matter):
```bash
lazy-hippo split -C 5 25 -C 3:30 4:55 -C 1:00 2:00 test.m4v
# -> test-0.m4v, test-1.m4v, test-2.m4v
```

Fixed-length chunks:
```bash
lazy-hippo split -E 6 my-video.mp4
# splits video into 6-second segments
```

Notes:
- Uses stream-copying (no re-encode) where possible.
- Filenames preserve the original suffix by default.

### Join
Concatenate multiple files into one (container-compatible inputs):

```bash
lazy-hippo join -o joined-video.mp4 part1.mp4 part2.mp4 part3.mp4
```

### Repack
Change the container without re-encoding:

```bash
lazy-hippo repack -f mp4 input.mkv
# -> input.mp4
```

### GIF-Preview
Create a preview GIF composed of short clips across the video. Defaults: 3s clips, 5 fps, 320px height, 60s intervals.

```bash
lazy-hippo gif-preview input.mp4
```

Options include `--start`, `--stop`, `--length`, `--fps`, `--scale`, and `--step`. Use `--help` for details.

### Extract
Extract frames at specified intervals into an `extracted_frames/` directory by default. You can also specify a custom output directory with `-o`, including nested paths:

```bash
lazy-hippo extract input.mp4
```

```bash
lazy-hippo extract -o outputs/frames input.mp4
```

## Contributing
- Fork the repo, create a feature branch, add tests, and open a PR.
- Run unit tests with your preferred test runner (project uses unittest).
- Keep changes small and focused; update README and add usage examples for new features.

## License
MIT License

## Supported Python Versions
This project runs on the [latest supported Python versions.](https://devguide.python.org/versions/)

## Contact / Support
Open an issue on the repository for bugs and feature requests.