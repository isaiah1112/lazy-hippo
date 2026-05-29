""" Utility for manipulating video files without re-encoding
"""
import contextlib
import json
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path
from shlex import quote
from subprocess import CalledProcessError, CompletedProcess, run

import click

log = logging.getLogger(__name__)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(levelname)s:%(funcName)s:%(message)s'))
log.addHandler(log_handler)
log.setLevel(logging.CRITICAL)
log.propagate = False  # Keeps our messages out of the root logger.


class TimeStamp(click.ParamType):
    name = "timestamp"
    MAX_COMPONENTS = 3  # HH:MM:SS

    def convert(self, value, param, ctx):
        """Convert various timestamp formats to seconds.
        
        Accepts:
        - Integer (seconds, or -1 for auto-detect)
        - String in format 'SS', 'MM:SS', or 'HH:MM:SS'
        """
        if isinstance(value, int):
            if value < -1:
                self.fail(f'{value} must be non-negative or -1 for auto-detect', param, ctx)
            return value

        if not isinstance(value, str):
            self.fail(f'{value!r} must be a string or integer', param, ctx)

        value = value.strip()
        if value == '':
            self.fail(f'{value!r} is not a valid timestamp string', param, ctx)

        components = value.split(':')
        
        if len(components) > self.MAX_COMPONENTS:
            self.fail(f'{value!r} has too many components (max {self.MAX_COMPONENTS})', param, ctx)

        try:
            # Validate and convert each component
            int_components = []
            for component in components:
                val = int(component)
                if val < 0:
                    self.fail(f'timestamp component cannot be negative: {component!r}', param, ctx)
                int_components.append(val)
            
            # Convert to seconds (reverse the list: SS, MM:SS, HH:MM:SS)
            total_seconds = sum(val * (60 ** idx) for idx, val in enumerate(reversed(int_components)))
            return total_seconds
            
        except ValueError:
            self.fail(f'{value!r} is not a valid timestamp string', param, ctx)


TIME_STAMP = TimeStamp()

def locate_binary(command: str) -> str:
    """Attempt to locate a binary using the system PATH.

    :param command: The unix command to find by name
    :type command: str
    :returns: Full path to binary (if found)
    :rtype: str
    :raises: click.UsageError
    """
    path = shutil.which(command)
    if not path:
        raise click.UsageError(f'Unable to locate {command}. Is it installed?')
    log.info(path)
    return path
    
def probe_metadata(video_file: Path, short: bool = True) -> dict:
    """ Use `ffprobe` to extract video metadata
    
    :param video_file: Path to video file
    :type video_file: pathlib.Path
    :param short: Only return `format` info (Default: True)
    :type short: bool
    :returns: Output of `ffprobe`
    :rtype: dict
    :raises: subprocess.CalledProcessError
    """
    ffprobe = locate_binary('ffprobe')
    if short:
        cmd = [ffprobe, '-v', 'quiet', '-print_format', 'json', '-show_format', str(video_file)]
    else:
        cmd = [ffprobe, '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', str(video_file)]
    video_metadata = run_cmd(cmd)
    return json.loads(video_metadata.stdout)
    
    
def run_cmd(cmd: list[str] | str) -> CompletedProcess:
    """Run a command without a shell and capture its output.

    :param cmd: ffmpeg or ffprobe command to run
    :type cmd: list[str] | str
    :returns: CompletedProcess Object from `subprocess.run()`
    :rtype: CompletedProcess
    :raises: subprocess.CalledProcessError
    """
    log.info(cmd)
    process = run(cmd, shell=False, capture_output=True, text=True)
    log.debug(process)
    process.check_returncode()
    return process


def format_command_error(exc: CalledProcessError) -> str:
    stderr = getattr(exc, 'stderr', '')
    if stderr and log.level <= logging.INFO:
        return stderr.strip()
    return f'Command failed with exit code {exc.returncode}'


@click.group()
@click.version_option()
@click.option('--debug', '-d', is_flag=True, help='Enable Debug Mode')
@click.option('--verbose', '-v', count=True, help='Increase debug verbosity')
@click.pass_context
def cli(ctx, **kwargs):
    """ Easily work with video files
    """
    ctx.ensure_object(dict)
    debug_mode = kwargs['debug']
    verbose_count = kwargs['verbose']
    ctx.obj['debug'] = debug_mode
    if debug_mode:
        log.setLevel(logging.INFO)
    elif debug_mode and verbose_count > 0:
        log.setLevel(logging.DEBUG)


@cli.command('split', short_help='Split a video file')
@click.option('--chunk', '-C', nargs=2, multiple=True, type=TimeStamp(),
              help='Start/Stop timestamps of video to extract')
@click.option('--every', '-E', type=int, default=0, help='Length of each chunk')
@click.argument('file', type=click.Path(exists=True, dir_okay=False, path_type=Path))
def cli_split(**kwargs):
    """ Chop a video into smaller videos based on timestamps or every N seconds
    """
    ffmpeg = locate_binary('ffmpeg')
    if kwargs['every'] > 0 and len(kwargs['chunk']) > 0:
        raise click.UsageError('Multiple operations are not supported')
    
    input_file = str(kwargs['file'])
    if len(kwargs['chunk']) > 0:
        for idx, chunk in enumerate(kwargs['chunk']):
            start_time, end_time = chunk
            if end_time < start_time:
                raise click.UsageError(f'Chunk {idx} end time {end_time} is before start time {start_time}')
            click.echo(f'Processing chunk {idx} from {start_time} to {end_time}...')
            new_file = str(kwargs['file'].with_name(f'{kwargs["file"].stem}-{str(idx)}{kwargs["file"].suffix}'))
            cmd = [ffmpeg, '-y', '-ss', str(start_time), '-to', str(end_time), '-i', input_file, '-c', 'copy', new_file]
            try:
                run_cmd(cmd)
            except CalledProcessError as exc:
                raise click.ClickException(f'ffmpeg returned non-zero status: {format_command_error(exc)}') from exc
    elif kwargs['every'] > 0:
        click.secho(f'Splitting video every {kwargs["every"]} seconds...')
        new_file = str(kwargs['file'].with_name(f'{kwargs["file"].stem}-%03d{kwargs["file"].suffix}'))
        cmd = [ffmpeg, '-i', input_file, '-c', 'copy', '-map', '0', '-f', 'segment', '-segment_time', str(kwargs['every']), '-reset_timestamps', '1', '-segment_format_options', 'movflags=+faststart', new_file]
        try:
            run_cmd(cmd)
        except CalledProcessError as exc:
            raise click.ClickException(f'ffmpeg returned non-zero status: {format_command_error(exc)}') from exc
        else:
            click.secho(f'Split of file {input_file} completed...', fg='green')


@cli.command('join', short_help='Join video files')
@click.option('output', '-o', type=click.Path(exists=False, dir_okay=False, path_type=Path), required=True,
              help='Path to output file')
@click.argument('file', nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path))
def cli_join(**kwargs):
    """ Join multiple files into a single file without re-encoding
    """
    ffmpeg = locate_binary('ffmpeg')
    if len(kwargs['file']) == 0:
        raise click.UsageError('At least one input file is required')
    with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as tf:
        for f in kwargs['file']:
            tf.write(f"file {quote(str(f))}\n")
    new_file = str(kwargs['output'])
    cmd = [ffmpeg, '-y', '-f', 'concat', '-i', tf.name, '-c', 'copy', new_file]
    try:
        run_cmd(cmd)
    except CalledProcessError as exc:
        raise click.ClickException(f'ffmpeg returned non-zero status: {format_command_error(exc)}') from exc
    else:
        click.secho(f'Joined {len(kwargs["file"])} files into {kwargs["output"]}', fg='green')
    finally:
        os.remove(tf.name)  # Clean up our temporary file

@cli.command('info', short_help='Get Video Metadata')
@click.option('--format', '-f', type=click.Choice(['txt', 'json']), default='txt', help='Format of output')
@click.argument('file', nargs=1, type=click.Path(exists=True, dir_okay=False, path_type=Path))
def cli_info(**kwargs):
    """ Get video stream and format metadata from a file using 'ffprobe'
    """
    try:
        video_info = probe_metadata(kwargs['file'], short=False)
    except CalledProcessError as exc:
        raise click.ClickException(f'ffprobe returned non-zero status: {format_command_error(exc)}') from exc
    if kwargs['format'] == 'json':
        click.echo(json.dumps(video_info, indent=2))
    else:
        format_entries = ['filename', 'duration', 'size', 'bit_rate']
        for k, v in video_info['format'].items():
            if k in format_entries:
                if k == 'size':  # Convert to MB
                    v = str(round(int(v) / (1024 * 1024))) + "MB"
                elif k == 'duration':  # Display as seconds
                    v = str(round(float(v))) + "s"
                elif k == 'bit_rate':  # Convert to kb/s
                    v = str(round(int(v) / 1000)) + 'kb/s'
                click.echo(f'{k}: {v}')
        stream_entries = ['codec_name', 'height', 'width']
        video_stream = [x for x in video_info['streams'] if x['codec_type'] == 'video']
        if video_stream:
            for k, v in video_stream[0].items():
                if k in stream_entries:
                    click.echo(f'{k}: {v}')
        else:
            click.echo('No video stream found')
    
@cli.command('repack', short_help='Change Video Container')
@click.option('--format', '-f', type=click.Choice(['mkv', 'mp4']), default='mp4', help='Format of output')
@click.argument('file', nargs=1, type=click.Path(exists=True, dir_okay=False, path_type=Path))
def cli_repack(**kwargs):
    """ Repackage a video into a different container type
    """
    ffmpeg = locate_binary('ffmpeg')
    input_file = str(kwargs['file'])
    new_file = str(kwargs['file'].with_suffix('.' + kwargs['format']))
    cmd = [ffmpeg, '-i', input_file, '-c:v', 'copy', '-c:a', 'copy', new_file]
    try:
        run_cmd(cmd)
    except CalledProcessError as exc:
        with contextlib.suppress(OSError):
            os.remove(new_file)  # ffmpeg doesn't clean up files when repackaging fails
        raise click.ClickException(f'ffmpeg returned non-zero status: {format_command_error(exc)}') from exc
    click.secho(f'Repackaged: {kwargs["file"]} to: {new_file}', fg='green')
    
@cli.command('gif-preview', short_help='Create a GIF')
@click.option('--start', default=0, type=TimeStamp(), help='Starting timestamp')
@click.option('--stop', default=-1, type=TimeStamp(), help='Ending timestamp')
@click.option('--step', default=60, help='Seconds between extraction')
@click.option('--length', default=3, help='Seconds to extract')
@click.option('--fps', default=5, help="Frames Per Second")
@click.option('--scale', default=320, help='Height of GIF in pixels')
@click.argument('file', type=click.Path(exists=True, dir_okay=False, path_type=Path))
def cli_gif_preview(**kwargs):
    """ Generate a GIF from a video
    """
    ctx = click.get_current_context()
    debug_mode = (ctx.obj or {}).get('debug', False)
    ffmpeg = locate_binary('ffmpeg')
    input_file = str(kwargs['file'])
    output_file = str(kwargs['file'].with_suffix('.gif'))
    start = kwargs['start']
    stop = kwargs['stop']

    if start < 0:
        raise click.UsageError('--start must be non-negative')
    if stop != -1 and stop < 0:
        raise click.UsageError('--stop must be non-negative or -1')
    if kwargs['step'] <= 0:
        raise click.UsageError('--step must be greater than zero')
    if kwargs['length'] <= 0:
        raise click.UsageError('--length must be greater than zero')
    if kwargs['fps'] <= 0:
        raise click.UsageError('--fps must be greater than zero')
    if kwargs['scale'] <= 0:
        raise click.UsageError('--scale must be greater than zero')

    video_filter = f'fps={kwargs["fps"]},scale={kwargs["scale"]}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse'
    if stop == -1:
        try:
            video_info = probe_metadata(kwargs['file'])
        except CalledProcessError as err:
            raise click.BadArgumentUsage('Unable to determine duration of video file. Please specify --stop manually') from err
        stop = round(float(video_info['format']['duration']))
    if start >= stop:
        raise click.BadOptionUsage('start', '--start must be before --stop')
    gif_count = (stop - start + kwargs['step'] - 1) // kwargs['step']
    if os.path.exists(output_file):
        if click.confirm(f'{output_file} exists. Overwrite?'):
            os.remove(output_file)
        else:
            raise click.Abort()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        log.info(f'Generating gif previews in: {tmp_dir}')
        with open(tmp_dir / 'files.txt', 'w') as tmp_file, click.progressbar(length=gif_count, label='Generating gifs', hidden=debug_mode) as bar:
            while start < stop:
                gif_file = tmp_dir / f'{start}.gif'
                tmp_file.write(f'file {quote(str(gif_file))}\n')
                cmd = [ffmpeg, '-i', str(input_file), '-ss', str(start), '-t', str(kwargs['length']), '-vf', video_filter, '-loop', '1', str(gif_file)]
                try:
                    run_cmd(cmd)
                except CalledProcessError as exc:
                    raise click.ClickException(f'ffmpeg returned non-zero status building gifs: {format_command_error(exc)}') from exc
                log.info(f'Wrote: {gif_file}')
                start += kwargs['step']
                bar.update(1)
        log.info('Combining gif previews into single file')
        cmd = [ffmpeg, '-f', 'concat', '-safe', '0', '-i', tmp_file.name, '-ignore_loop', '1', str(output_file)]
        try:
            run_cmd(cmd)
        except CalledProcessError as exc:
            raise click.ClickException(f'ffmpeg returned non-zero status combining gifs: {format_command_error(exc)}') from exc
        click.secho(f'Created preview GIF: {output_file}', fg='green')

@cli.command('extract', short_help='Extract Frames')
@click.option('--step', '-s', default=60, help='Seconds between frames')
@click.option('--every-frame', default=False, is_flag=True, help='Extract every frame (ignores --step)')
@click.option('--timestamp/--no-timestamp', is_flag=True, default=True, help='Include timestamp on frame')
@click.option('--output', '-o', default=Path('extracted_frames'), type=click.Path(file_okay=False, exists=False, path_type=Path),
              help='Output directory')
@click.argument('file', type=click.Path(exists=True, dir_okay=False, path_type=Path))
def cli_extract(**kwargs):
    """ Extract screen captures on a timed interval
    """
    ctx = click.get_current_context()
    debug_mode = (ctx.obj or {}).get('debug', False)
    ffmpeg = locate_binary('ffmpeg')
    try:
        video_info = probe_metadata(kwargs['file'], short=False)
    except CalledProcessError as err:
        raise click.BadArgumentUsage('Unable to determine video duration') from err
    other_opts = ['-q:v', '2']
    if kwargs['every_frame']:
        total_frames = int(video_info['streams'][0].get('nb_frames', 0))
        click.echo(f'Extracting every frame will create a {total_frames} files.')
        if click.confirm('Do you wish to continue?', default=False):
            video_filter = 'format=yuvj420p'
            if kwargs['timestamp']:
                video_filter = r"format=yuvj420p,drawtext=fontsize=45:fontcolor=white:box=1:boxcolor=black:x=(W-tw)/2:y=(H-th-10):text='%{pts\:hms}'"
        else:
            raise click.Abort()
    else:
        if kwargs['step'] <= 0:
            raise click.UsageError('--step must be greater than zero')
        video_length = round(float(video_info['format']['duration']))
        total_frames = video_length // kwargs['step']
        video_filter = f'fps=1/{kwargs["step"]},format=yuvj420p'
        if kwargs['timestamp']:
            video_filter += r",drawtext=fontsize=45:fontcolor=white:box=1:boxcolor=black:x=(W-tw)/2:y=(H-th-10):text='%{pts\:hms}'"
    cmd = [ffmpeg, '-i', str(kwargs['file'])]
    if video_filter:
        cmd.extend(['-vf', video_filter])
    cmd.extend(other_opts)
    cmd.append(f'{str(kwargs["output"])}/img%03d.jpg')
    log.info('Creating output directory')
    kwargs['output'].mkdir(parents=True, exist_ok=True)
    log.info('Extracting frames')
    with click.progressbar(label=f'Extracting {total_frames} frames', length=total_frames, hidden=debug_mode) as bar:
        try:
            run_cmd(cmd)
        except CalledProcessError as exc:
            raise click.ClickException(f'ffmpeg returned non-zero status: {format_command_error(exc)}') from exc
        bar.update(n_steps=total_frames)
    click.secho(f'Wrote screencaps to: {kwargs["output"]}/', fg='green')