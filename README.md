![logo](lazy-hippo.png "Lazy Hippo")
The `lazy-hippo` utility was written in Python to help quickly split or join video files via `ffmpeg` without re-encoding them.

## Getting Started
Before you begin, please be sure to install `ffmpeg` on your system either via [Brew](https://brew.sh), 
[MacPorts](http://macports.org), or directly from the [FFMpeg Website](https://ffmpeg.org).  To install or update 
Lazy Hippo, you can use `pip`, `make`, or [`uv`](https://docs.astral.sh/uv/):

### Using Pip
```commandline
pip install .
```

### Using make
```commandline
make install
```

### Using UV
```commandline
uv run lazy-hippo
```

This will install/update all Python requirements and create a `lazy-hippo` command in your environment (or `virtualenv` if using
UV).

## Usage
Lazy Hippo contains two primary subcommands: `split` and `join`.  These two commands can be used to manipulate video files
to your liking.

### Splitting Video
Lazy Hippo uses "chunk" terminology for cutting out pieces of a video into smaller files. "Chunks" are specified by
a start and end timestamp either specified in seconds (e.g. `25 50`) or as timestamps (e.g. `1:25 3:45`).  In the examples
just provided the values would be interpreted as "video chunk starting at 25 seconds and ending at 50 seconds" and
"video chunk starting at 1 minute, 25 seconds and ending at 3 minutes, 45 seconds".  At this time Lazy Hippo can accept
up to hours in timestamps (e.g `1:24:00 1:25:30`).

```commandline
lazy-hippo split -C 5 25 my-video.mp4
```

This will create a new video called `my-video-0.mp4`.

#### Multiple Chunks
You can easily specify multiple chunks from the same video, and they don't even have to be in ascending order:
```commandline
lazy-hippo split -C 5 25 -C 3:30 4:55 -C 1:00 2:00 test.m4v
```

This command would output the following video files:
```shell
test-0.m4v
test-1.m4v
test-2.m4v
```

#### Segmentation
If you would like to split a video into multiple chunks of the same length, you can specify the `--every` option and
provide the size of each "chunk" of video:
```commandline
lazy-hippo split -E 6 my-video.mp4
```

This command would output the following video files (assuming the video is 18 second long):
```shell
test-0.m4v
test-1.m4v
test-2.m4v
```


### Joining Video
```commandline
lazy-hippo join -o joined-video.mp4 my-video-0.mp4 my-video-1.mp4 my-video-2.mp4
```

This will create a new video called `joined-video.mp4`.

# Supported Python Versions
At this time, the only suppported python versions are:

* Python3.11

