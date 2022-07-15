# coding=utf-8
""" Utility for splitting a video into smaller videos based on timestamps
"""
import click
import os
import sys
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip


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


@click.command()
@click.version_option()
@click.option('--chunk', '-C', nargs=2, multiple=True, type=TimeStamp(), help='Specify timestamps of video to extract')
@click.argument('file', type=click.Path(exists=True, dir_okay=False))
def cli(**kwargs):
    """ Chop a video into smaller videos based on timestamps
    """
    base_path, filename = os.path.split(kwargs['file'])
    file_ext = filename.split('.').pop()

    for idx, chunk in enumerate(kwargs['chunk']):
        start_time, end_time = chunk
        if end_time < start_time:
            click.secho(f'Cannot process chunk {idx} since {end_time} is before {start_time}')
        else:
            click.echo(f'Processing chunk {idx} from {start_time} to {end_time}...')
            new_file = filename.replace('.' + file_ext, '-' + str(idx)) + '.' + file_ext
            ffmpeg_extract_subclip(kwargs['file'], start_time, end_time, targetname=new_file)
    sys.exit(0)
