# coding=utf-8
""" Utility for splitting a video into smaller videos based on timestamps
"""
import click
import logging
import os
from subprocess import run
import sys
import tempfile

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


@click.group()
@click.version_option()
@click.option('--debug', '-d', is_flag=True, help='Enable Debug Mode')
@click.option('--verbose', '-v', count=True, help='Increase debug verbosity')
def cli(**kwargs):
    """ Easily work with video (via ffmpeg)
    """
    global ffmpeg, log
    if kwargs['debug']:
        if kwargs['verbose']:
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.INFO)
    locate_ffmpeg = run('which ffmpeg', shell=True, capture_output=True)
    if locate_ffmpeg.returncode == 0 and len(locate_ffmpeg.stdout) > 0:
        ffmpeg = locate_ffmpeg.stdout.strip().decode()
        log.info(f'ffmpeg binary located at: {ffmpeg}')
    else:
        raise click.UsageError('Unable to locate ffmpeg binary. Is it installed?')


@cli.command('split', short_help='Split a video file')
@click.option('--chunk', '-C', nargs=2, multiple=True, type=TimeStamp(),
              help='Start/Stop timestamps of video to extract')
@click.argument('file', type=click.Path(exists=True, dir_okay=False))
def cli_split(**kwargs):
    """ Chop a video into smaller videos based on timestamps
    """
    global ffmpeg, log
    input_file = kwargs['file']
    base_path, filename = os.path.split(input_file)
    file_ext = filename.split('.').pop()

    for idx, chunk in enumerate(kwargs['chunk']):
        start_time, end_time = chunk
        if end_time < start_time:
            click.secho(f'Cannot process chunk {idx} since {end_time} is before {start_time}')
        else:
            click.echo(f'Processing chunk {idx} from {start_time} to {end_time}...')
            new_file = filename.replace('.' + file_ext, '-' + str(idx)) + '.' + file_ext
            cmd = f'{ffmpeg} -y -ss {start_time} -to {end_time} -i \"{input_file}\" -c copy \"{new_file}\"'
            log.info(cmd)
            split_cmd = run(cmd, shell=True, capture_output=True)
            log.debug(split_cmd.stderr)
            if split_cmd.returncode != 0:
                click.secho('ffmpeg returned non-zero status', fg='red', err=True)
    click.secho(f'Split of file {input_file} completed...', fg='green')
    sys.exit(0)


@cli.command('join', short_help='Join video files')
@click.option('output', '-o', type=click.Path(exists=False, dir_okay=False), required=True,
              help='Path to output file')
@click.argument('file', nargs=-1, type=click.Path(exists=True, dir_okay=False))
def cli_join(**kwargs):
    """ Join multiple files into a single file without re-encoding
    """
    global ffmpeg, log

    with tempfile.NamedTemporaryFile('w', dir=os.getcwd(), delete=False) as tf:
        for f in kwargs['file']:
            tf.write(f"file '{f}'\n")

    cmd = f'{ffmpeg} -y -f concat -i {tf.name} -c copy \"{kwargs["output"]}\"'
    log.info(cmd)
    join_cmd = run(cmd, shell=True, capture_output=True)
    log.debug(join_cmd.stderr)
    if join_cmd.returncode != 0:
        click.secho('ffmpeg returned non-zero status', fg='red', err=True)
    os.remove(tf.name)
    click.secho('Joined %d files into %s' % (len(kwargs['file']), kwargs['output']), fg='green')
    sys.exit(0)
