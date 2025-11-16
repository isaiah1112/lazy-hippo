""" Utility for manipulating video files without re-encoding
"""
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from shlex import quote
from subprocess import CompletedProcess, SubprocessError, run

import click

log = logging.getLogger(__name__)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(levelname)s:%(funcName)s:%(message)s'))
log.addHandler(log_handler)
log.setLevel(logging.CRITICAL)
log.propagate = False  # Keeps our messages out of the root logger.


class TimeStamp(click.ParamType):
    name = "timestamp"

    def convert(self, value, param, ctx):
        if isinstance(value, int):
            return value

        try:
            if value.count(':') > 2:
                self.fail(f'{value!r} is not a valid timestamp string', param, ctx)
            ts = value.split(':')
            new_ts = 0
            for idx, x in enumerate(reversed(ts)):
                new_ts += (int(x) * (60 ** idx))
            return int(new_ts)
        except TypeError:
            self.fail(f'{value!r} is not a valid timestamp string', param, ctx)


TIME_STAMP = TimeStamp()

def locate_binary(command: str) -> str:
    """ Attempt to locate a binary using the 'which' command
    
    :param command: The unix command to find by name
    :type command: str
    :returns: Full UNIX path to binary (if found)
    :returntype: str
    :raises: click.UsageError
    """
    try:
        binary_path = run_cmd(f'which {command}')
    except SubprocessError as err:
        raise click.UsageError(f'Unable to locate {command}. Is it installed?') from err
    else:
        return binary_path.stdout.strip().decode()
    
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
    global log
    ffprobe = locate_binary('ffprobe')
    if short:
        cmd = f'{ffprobe} -v quiet -print_format json -show_format {quote(str(video_file))}'
    else:
        cmd = f'{ffprobe} -v quiet -print_format json -show_format -show_streams {quote(str(video_file))}'
    video_metadata = run_cmd(cmd)
    return json.loads(video_metadata.stdout)
    
    
def run_cmd(cmd: str) -> CompletedProcess:
    """ Run cmd in a shell, capturing the output
    
    :param cmd: ffmpeg or ffprobe command to run in shell
    :type cmd: str
    :returns: CompletedProcess Object from `subprocess.run()`
    :rtype: CompletedProcess
    :raises: subprocess.CalledProcessError
    """
    global log
    log.info(cmd)
    shell_cmd = run(cmd, shell=True, capture_output=True)
    log.debug(shell_cmd)
    shell_cmd.check_returncode()
    return shell_cmd
    

@click.group()
@click.version_option()
@click.option('--debug', '-d', is_flag=True, help='Enable Debug Mode')
@click.option('--verbose', '-v', count=True, help='Increase debug verbosity')
def cli(**kwargs):
    """ Easily work with video files
    """
    global log
    if kwargs['debug']:
        if kwargs['verbose']:
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.INFO)


@cli.command('split', short_help='Split a video file')
@click.option('--chunk', '-C', nargs=2, multiple=True, type=TimeStamp(),
              help='Start/Stop timestamps of video to extract')
@click.option('--every', '-E', type=int, default=0, help='Length of each chunk')
@click.argument('file', type=click.Path(exists=True, dir_okay=False, path_type=Path))
def cli_split(**kwargs):
    """ Chop a video into smaller videos based on timestamps or every N seconds
    """
    global log
    ffmpeg = locate_binary('ffmpeg')
    if kwargs['every'] > 0 and len(kwargs['chunk']) > 0:
        raise click.UsageError('Multiple operations are not supported')
    
    input_file = str(kwargs['file'])
    if len(kwargs['chunk']) > 0:
        for idx, chunk in enumerate(kwargs['chunk']):
            start_time, end_time = chunk
            if end_time < start_time:
                click.secho(f'Cannot process chunk {idx} since {end_time} is before {start_time}')
            else:
                click.echo(f'Processing chunk {idx} from {start_time} to {end_time}...')
                new_file = str(kwargs['file'].with_name(f'{kwargs["file"].stem}-{str(idx)}{kwargs["file"].suffix}'))
                cmd = f'{ffmpeg} -y -ss {start_time} -to {end_time} -i {quote(input_file)} -c copy {quote(new_file)}'
                try:
                    run_cmd(cmd)
                except SubprocessError:
                    click.secho('ffmpeg returned non-zero status', fg='red', err=True)
                    sys.exit(1)
    elif kwargs['every'] > 0:
        try:
            video_info = probe_metadata(kwargs['file'])
        except SubprocessError:
            click.secho('Unable to determine video duration', fg='red', err=True)
        else:
            padding = len(video_info['format']['duration'].split('.')[0])
            click.secho(f'Splitting video every {kwargs["every"]} seconds...')
            new_file = str(kwargs['file'].with_name(f'{kwargs["file"].stem}-%0{padding}d{kwargs["file"].suffix}'))
            cmd = f'{ffmpeg} -i {quote(input_file)} -c copy -map 0 -f segment -segment_time {kwargs["every"]} -reset_timestamps 1 -segment_format_options movflags=+faststart {quote(new_file)}'
            try:
                run_cmd(cmd)
            except SubprocessError:
                click.secho('ffmpeg returned non-zero status', fg='red', err=True)
                sys.exit(1)
            else:
                click.secho(f'Split of file {input_file} completed...', fg='green')
    sys.exit(0)


@cli.command('join', short_help='Join video files')
@click.option('output', '-o', type=click.Path(exists=False, dir_okay=False, path_type=Path), required=True,
              help='Path to output file')
@click.argument('file', nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path))
def cli_join(**kwargs):
    """ Join multiple files into a single file without re-encoding
    """
    global log
    ffmpeg = locate_binary('ffmpeg')
    with tempfile.NamedTemporaryFile('w', dir=os.getcwd(), delete=False) as tf:
        for f in kwargs['file']:
            tf.write(f"file {quote(str(f))}\n")
    new_file = str(kwargs['output'])
    cmd = f'{ffmpeg} -y -f concat -i {tf.name} -c copy {quote(new_file)}'
    try:
        run_cmd(cmd)
    except SubprocessError:
        click.secho('ffmpeg returned non-zero status', fg='red', err=True)
        sys.exit(1)
    else:
        click.secho(f'Joined {len(kwargs["file"])} files into {kwargs["output"]}', fg='green')
        sys.exit(0)
    finally:
        os.remove(tf.name)  # Clean up our temporary file

@cli.command('info', short_help='Get Video Metadata')
@click.option('--format', '-f', type=click.Choice(['txt', 'json']), default='txt', help='Format of output')
@click.argument('file', nargs=1, type=click.Path(exists=True, dir_okay=False))
def cli_info(**kwargs):
    """ Get video stream and format metadata from a file using 'ffprobe'
    """
    global log
    try:
        video_info = probe_metadata(kwargs['file'], short=False)
    except SubprocessError:
        click.secho('ffprobe returned non-zero status', fg='red', err=True)
        sys.exit(1)
    else:
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
            for k, v in video_stream[0].items():
                if k in stream_entries:
                    click.echo(f'{k}: {v}')
        sys.exit(0)
    
@cli.command('repack', short_help='Change Video Container')
@click.option('--format', '-f', type=click.Choice(['mkv', 'mp4']), default='mp4', help='Format of output')
@click.argument('file', nargs=1, type=click.Path(exists=True, dir_okay=False, path_type=Path))
def cli_repack(**kwargs):
    """ Repackage a video into a different container type
    """
    global log
    ffmpeg = locate_binary('ffmpeg')
    input_file = str(kwargs['file'])
    new_file = str(kwargs['file'].with_suffix('.' + kwargs['format']))
    cmd = f'{ffmpeg} -i {quote(input_file)} -c:v copy -c:a copy {quote(new_file)}'
    try:
        run_cmd(cmd)
    except SubprocessError:
        try:
            os.remove(new_file)  # ffmpeg doesn't clean up files when repackaging fails
        finally:
            click.secho('ffmpeg returned non-zero status', fg='red', err=True)
            sys.exit(1)
    else:
        click.secho(f'Repackaged: {kwargs["file"]} to: {new_file}', fg='green')
        sys.exit(0)
    
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
    global log
    ffmpeg = locate_binary('ffmpeg')
    input_file = str(kwargs['file'])
    output_file = str(kwargs['file'].with_suffix('.gif'))
    # This is where the magic happens
    video_filter = f'fps={kwargs["fps"]},scale={kwargs["scale"]}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse'
    if kwargs['stop'] == -1:
        try:
            video_info = probe_metadata(kwargs['file'])
        except SubprocessError as err:
            raise click.BadArgumentUsage('Unable to detrmine duration of video file. Please specify --stop manually') from err
        else:
            kwargs['stop'] = round(float(video_info['format']['duration']))
    if kwargs['start'] >= kwargs['stop']:
        raise click.BadOptionUsage('start', '--start must be before --stop')
    if os.path.exists(output_file):
        if click.confirm(f'{output_file} exists. Overwrite?'):
            os.remove(output_file)
        else:
            sys.exit(0)
    with tempfile.TemporaryDirectory() as tmp:
        log.info(f'Generating gif previews in: {tmp}')
        with open(tmp + '/files.txt', 'w') as tmp_file, click.progressbar(length=kwargs['stop'], label='Generating gifs') as bar:
            while kwargs['start'] < kwargs['stop']:
                gif_file = f'{tmp}/{kwargs["start"]}.gif'
                tmp_file.write(f'file {gif_file}\n')
                cmd = f'{ffmpeg} -i {input_file} -ss {kwargs["start"]} -t {kwargs["length"]} -vf {quote(video_filter)} -loop 1 {gif_file}'
                try:
                    mkgif = run_cmd(cmd)
                except SubprocessError:
                    click.secho('ffmpeg returned non-zero status building gifs', fg='red', err=True)
                    sys.exit(mkgif.returncode)
                else:
                    log.info(f'Wrote: {gif_file}')
                    kwargs['start'] += kwargs['step']
                    bar.update(kwargs['step'], current_item=kwargs['start'])
        log.info('Combining gif previews into single file')
        cmd = f'{ffmpeg} -f concat -safe 0 -i {tmp_file.name} -ignore_loop 1 {output_file}'
        try:
            run_cmd(cmd)
        except SubprocessError:
            click.secho('ffmpeg returned non-zero status combining gifs', fg='red', err=True)
            sys.exit(1)
        else:
            click.secho(f'Created preview GIF: {output_file}', fg='green')
            sys.exit(0)
    
@cli.command('extract', short_help='Extract Screencaps')
@click.option('--step', '-s', default=60, help='Seconds between frames')
@click.option('--output', '-o', default=Path('screencaps'), type=click.Path(file_okay=False, exists=False, path_type=Path),
              help='Output directory')
@click.argument('file', type=click.Path(exists=True, dir_okay=False, path_type=Path))
def cli_extract(**kwargs):
    """ Extract screen captures on a timed interval
    """
    global log
    ffmpeg = locate_binary('ffmpeg')
    try:
        video_info = probe_metadata(kwargs['file'])
    except SubprocessError as err:
        raise click.BadArgumentUsage('Unable to determine video duration') from err
    else:
        video_length = round(float(video_info['format']['duration']))
        padding = len(str(video_length))
        total_frames = video_length // kwargs['step']
        video_filter = f'fps=1/{kwargs["step"]},drawtext=fontfile=/Library/Fonts/Arial.ttf:fontsize=45:fontcolor=yellow:box=1:boxcolor=black:x=(W-tw)/2:y=H-th-10:' + r'text="%{pts\:hms}"'
        cmd = f'{ffmpeg} -i {quote(str(kwargs["file"]))} -vf {quote(video_filter)} {str(kwargs["output"])}/img%0{padding}d.jpg'
        log.info('Creating output directory')
        kwargs['output'].mkdir(exist_ok=True)
        log.info('Extracting frames')
        with click.progressbar(label='Extracting frames', length=video_length) as bar:
            try:
                run_cmd(cmd)
            except SubprocessError:
                click.secho('ffmpeg returned non-zero status', fg='red', err=True)
                sys.exit(1)
            else:
                # I dislike doing this but click does not have an indeterminate progress bar 
                bar.update(n_steps=video_length)
        click.secho(f'Wrote {total_frames} screencaps to: {kwargs["output"]}/', fg='green')
        sys.exit(0)