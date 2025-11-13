![logo](./logo.png "Lazy Hippo")
`lazy-hippo` is a command-line utility, written in Python, to allow easy access to `ffmpeg` or `ffprobe` for manipulating
video files.

## Getting Started
Before you begin, please be sure to install `ffmpeg` and `ffprobe` on your system either via [Brew](https://brew.sh), 
[MacPorts](http://macports.org), or directly from the [FFMpeg Website](https://ffmpeg.org).

To install `lazy-hippo` using a virtualenv created by `uv`:

```commandline
$ make install
```

If you'd prefer to not use a virtualenv or `uv`:
```commandline
$ make install UV_INSTALL=0
```

This will install/update all Python requirements and create a `lazy-hippo` command in your environment (or `virtualenv` if using
UV).

## Usage
Lazy Hippo contains the following sub-commands which can be used to manipulate video to your liking:
- `info`
- `join`
- `repack`
- `split`


### Info
Lazy Hippo allows you to get detailed info on a video file easily.  It does this via the `ffprobe` binary.
By default, it will return some basic information in human readable format. If you'd like every bit of metadata
available, simply add a `-f json` flag to your command.

```commandline
$ lazy-hippo info my-video
filename: my-video.mp4
duration: 1816s
size: 327MB
bit_rate: 1509kb/s
codec_name: h264
height: 480
```

### Split
Lazy Hippo uses "chunk" terminology for cutting out pieces of a video into smaller files. "Chunks" are specified by
a start and end timestamp either specified in seconds (e.g. `25 50`) or as timestamps (e.g. `1:25 3:45`).  In the examples
just provided the values would be interpreted as "video chunk starting at 25 seconds and ending at 50 seconds" and
"video chunk starting at 1 minute, 25 seconds and ending at 3 minutes, 45 seconds".  At this time Lazy Hippo can accept
up to hours in timestamps (e.g `1:24:00 1:25:30`).

```commandline
$ lazy-hippo split -C 5 25 my-video.mp4
```

This will create a new video called `my-video-0.mp4`.

#### Multiple Chunks
You can easily specify multiple chunks from the same video, and they don't even have to be in ascending order:
```commandline
$ lazy-hippo split -C 5 25 -C 3:30 4:55 -C 1:00 2:00 test.m4v
```

This command would output the following video files:
```shell
test-0.m4v
test-1.m4v
test-2.m4v
```

#### Segmentation
If you would like to split a video into multiple chunks of the same length, you can specify the `--every` option and
provide the length, in seconds, of each "chunk" of video:
```commandline
lazy-hippo split -E 6 my-video.mp4
```

This command would output the following video files (assuming the video is 18 second long):
```shell
my-video-0.m4v
my-video-1.m4v
my-video-2.m4v
```

### Join
```commandline
$ lazy-hippo join -o joined-video.mp4 my-video-0.mp4 my-video-1.mp4 my-video-2.mp4
```

This will create a new video called `joined-video.mp4`.

### Repack
If you would like to repackage a video file from one container type to another (e.g. `mkv` to `mp4`)
you can use the `repack` command.  Keep in mind though that this is **NOT** re-encoding the file but simply
changing the video container.
```commandline
$ lazy-hippo repack -f mp4 test.mkv
Repackaged: test.mkv to: test.mp4
```

# Supported Python Versions
At this time, the only suppported python versions are Python3.11 and later.
