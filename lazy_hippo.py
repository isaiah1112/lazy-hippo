""" Utility for manipulating video files without re-encoding
"""
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from shlex import quote
from subprocess import run

import click

global ffmpeg

log = logging.getLogger(__name__)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(levelname)s:%(funcName)s:%(message)s'))
log.addHandler(log_handler)
log.setLevel(logging.WARNING)
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
    global log
    locate_binary = run('which ' + command, shell=True, capture_output=True)
    if locate_binary.returncode == 0 and len(locate_binary.stdout) > 0:
        return locate_binary.stdout.strip().decode()
    else:
        raise click.UsageError(f'Unable to locate {command} binary. Is it installed?')

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
                log.info(cmd)
                split_cmd = run(cmd, shell=True, capture_output=True)
                log.debug(split_cmd.stderr)
                if split_cmd.returncode != 0:
                    click.secho('ffmpeg returned non-zero status', fg='red', err=True)
    elif kwargs['every'] > 0:
        click.secho(f'Splitting video every {kwargs["every"]} seconds...')
        new_file = str(kwargs['file'].with_name(f'{kwargs["file"].stem}-%03d{kwargs["file"].suffix}'))
        cmd = f'{ffmpeg} -i {quote(input_file)} -c copy -map 0 -f segment -segment_time {kwargs["every"]} -reset_timestamps 1 -segment_format_options movflags=+faststart {quote(new_file)}'
        log.info(cmd)
        split_cmd = run(cmd, shell=True, capture_output=True)
        log.debug(split_cmd.stderr)
        if split_cmd.returncode!= 0:
            click.secho('ffmpeg returned non-zero status', fg='red', err=True)
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
    log.info(cmd)
    join_cmd = run(cmd, shell=True, capture_output=True)
    log.debug(join_cmd.stderr)
    os.remove(tf.name)
    if join_cmd.returncode != 0:
        click.secho('ffmpeg returned non-zero status', fg='red', err=True)
    else:
        click.secho(f'Joined {len(kwargs["file"])} files into {kwargs["output"]}', fg='green')
    sys.exit(0)

@cli.command('info', short_help='Get Video Metadata')
@click.option('--format', '-f', type=click.Choice(['txt', 'json']), default='txt', help='Format of output')
@click.argument('file', nargs=1, type=click.Path(exists=True, dir_okay=False))
def cli_info(**kwargs):
    """ Get video stream and format metadata from a file using 'ffprobe'
    """
    global log
    ffprobe = locate_binary('ffprobe')
    cmd = f'{ffprobe} -v quiet -print_format json -show_format -show_streams ' + quote(kwargs['file'])
    log.info(cmd)
    probe_cmd = run(cmd, shell=True, capture_output=True)
    log.debug(probe_cmd.stderr)
    if probe_cmd.returncode == 0:
        if kwargs['format'] == 'json':
            click.echo(probe_cmd.stdout)
        else:
            cmd_json = json.loads(probe_cmd.stdout)
            format_entries = ['filename', 'duration', 'size', 'bit_rate']
            for k, v in cmd_json['format'].items():
                if k in format_entries:
                    if k == 'size':  # Convert to MB
                        v = str(round(int(v) / (1024 * 1024))) + "MB"
                    elif k == 'duration':  # Display as seconds
                        v = str(round(float(v))) + "s"
                    elif k == 'bit_rate':  # Convert to kb/s
                        v = str(round(int(v) / 1000)) + 'kb/s'
                    click.echo(f'{k}: {v}')
            stream_entries = ['codec_name', 'height', 'width']
            video_stream = [x for x in cmd_json['streams'] if x['codec_type'] == 'video']
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
    new_file = kwargs['file'].with_suffix('.' + kwargs['format'])
    cmd = f'{ffmpeg} -i {quote(str(kwargs["file"]))} -c:v copy -c:a copy ' + quote(str(new_file))
    log.info(cmd)
    repack_cmd = run(cmd, shell=True, capture_output=True)
    log.debug(repack_cmd.stderr)
    if repack_cmd.returncode == 0:
        click.secho(f'Repackaged: {kwargs["file"]} to: {new_file}', fg='green')
    else:
        try:
            os.remove(new_file)
        finally:
            click.secho('ffmpeg returned non-zero status', fg='red', err=True)
    sys.exit(0)