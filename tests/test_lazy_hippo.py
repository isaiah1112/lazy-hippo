import json
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import MagicMock, Mock, patch

import click
from click.testing import CliRunner

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import contextlib

import lazy_hippo


class TestTimeStamp(unittest.TestCase):
    """Test the TimeStamp click parameter type"""

    def setUp(self):
        self.ts = lazy_hippo.TimeStamp()

    def test_convert_int_input(self):
        """Test converting an integer input (seconds)"""
        result = self.ts.convert(100, None, None)
        self.assertEqual(result, 100)

    def test_convert_seconds_string(self):
        """Test converting seconds as a string"""
        result = self.ts.convert('45', None, None)
        self.assertEqual(result, 45)

    def test_convert_mm_ss(self):
        """Test converting mm:ss format"""
        result = self.ts.convert('1:30', None, None)
        self.assertEqual(result, 90)

    def test_convert_hh_mm_ss(self):
        """Test converting hh:mm:ss format"""
        result = self.ts.convert('1:02:30', None, None)
        self.assertEqual(result, 3750)

    def test_convert_invalid_too_many_colons(self):
        """Test that too many colons raises an error"""
        with self.assertRaises(click.BadParameter):
            self.ts.convert('1:2:3:4', None, Mock(fail=Mock(side_effect=click.BadParameter)))

    def test_convert_invalid_non_numeric(self):
        """Test that non-numeric input raises an error"""
        with self.assertRaises(click.BadParameter):
            self.ts.convert('abc:def', None, Mock(fail=Mock(side_effect=click.BadParameter)))

    def test_convert_negative_integer(self):
        """Test that integer values less than -1 are rejected"""
        with self.assertRaises(click.BadParameter):
            self.ts.convert(-10, None, Mock(fail=Mock(side_effect=click.BadParameter)))

    def test_convert_negative_one_allowed(self):
        """Test that -1 is allowed (auto-detect sentinel value)"""
        result = self.ts.convert(-1, None, None)
        self.assertEqual(result, -1)

    def test_convert_negative_component(self):
        """Test that negative timestamp component raises an error"""
        with self.assertRaises(click.BadParameter):
            self.ts.convert('5:-30', None, Mock(fail=Mock(side_effect=click.BadParameter)))

    def test_convert_invalid_type(self):
        """Test that non-string, non-integer input raises an error"""
        with self.assertRaises(click.BadParameter):
            self.ts.convert(3.14, None, Mock(fail=Mock(side_effect=click.BadParameter)))

    def test_convert_empty_string(self):
        """Test that empty string raises an error"""
        with self.assertRaises(click.BadParameter):
            self.ts.convert('', None, Mock(fail=Mock(side_effect=click.BadParameter)))

    def test_convert_zero(self):
        """Test that zero is valid"""
        result = self.ts.convert(0, None, None)
        self.assertEqual(result, 0)

    def test_convert_zero_string(self):
        """Test that '0' string is valid"""
        result = self.ts.convert('0', None, None)
        self.assertEqual(result, 0)


class TestLocateBinary(unittest.TestCase):
    """Test the locate_binary function"""

    @patch('lazy_hippo.shutil.which')
    def test_locate_binary_found(self, mock_which):
        """Test locating a binary that exists"""
        mock_which.return_value = '/usr/bin/ffmpeg'

        result = lazy_hippo.locate_binary('ffmpeg')
        self.assertEqual(result, '/usr/bin/ffmpeg')
        mock_which.assert_called_once_with('ffmpeg')

    @patch('lazy_hippo.shutil.which')
    def test_locate_binary_not_found(self, mock_which):
        """Test that UsageError is raised when binary is not found"""
        mock_which.return_value = None

        with self.assertRaises(click.UsageError):
            lazy_hippo.locate_binary('nonexistent')


class TestProbeMetadata(unittest.TestCase):
    """Test the probe_metadata function"""

    @patch('lazy_hippo.locate_binary')
    @patch('lazy_hippo.run_cmd')
    def test_probe_metadata_short(self, mock_run_cmd, mock_locate):
        """Test probing metadata with short=True"""
        mock_locate.return_value = '/usr/bin/ffprobe'
        mock_result = Mock()
        mock_result.stdout = json.dumps({
            'format': {'duration': '100.5', 'size': '1024000'}
        })
        mock_run_cmd.return_value = mock_result

        result = lazy_hippo.probe_metadata(Path('test.mp4'), short=True)

        self.assertIn('format', result)
        self.assertEqual(result['format']['duration'], '100.5')
        cmd_args = mock_run_cmd.call_args[0][0]
        self.assertEqual(cmd_args[0], '/usr/bin/ffprobe')
        self.assertIn('-print_format', cmd_args)
        self.assertNotIn('-show_streams', cmd_args)

    @patch('lazy_hippo.locate_binary')
    @patch('lazy_hippo.run_cmd')
    def test_probe_metadata_full(self, mock_run_cmd, mock_locate):
        """Test probing metadata with short=False"""
        mock_locate.return_value = '/usr/bin/ffprobe'
        mock_result = Mock()
        mock_result.stdout = json.dumps({
            'format': {'duration': '100.5'},
            'streams': [{'codec_type': 'video'}]
        })
        mock_run_cmd.return_value = mock_result

        result = lazy_hippo.probe_metadata(Path('test.mp4'), short=False)

        self.assertIn('streams', result)
        cmd_args = mock_run_cmd.call_args[0][0]
        self.assertIn('-show_streams', cmd_args)


class TestRunCmd(unittest.TestCase):
    """Test the run_cmd function"""

    @patch('lazy_hippo.run')
    def test_run_cmd_success(self, mock_run):
        """Test running a command successfully"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = 'output'
        mock_result.check_returncode = Mock()
        mock_run.return_value = mock_result

        result = lazy_hippo.run_cmd('echo test')

        self.assertEqual(result, mock_result)
        mock_run.assert_called_once_with('echo test', shell=False, capture_output=True, text=True)
        mock_result.check_returncode.assert_called_once()

    @patch('lazy_hippo.run')
    def test_run_cmd_failure(self, mock_run):
        """Test running a command that fails"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.check_returncode.side_effect = CalledProcessError(1,'Non-zero return code')
        mock_run.return_value = mock_result

        with self.assertRaises(CalledProcessError):
            lazy_hippo.run_cmd('false')


class TestFormatCommandError(unittest.TestCase):
    """Test formatting of subprocess command errors"""

    def test_format_command_error_with_stderr(self):
        exc = CalledProcessError(1, 'cmd', stderr='something went wrong\n')
        lazy_hippo.log.setLevel(logging.INFO)
        try:
            self.assertEqual(lazy_hippo.format_command_error(exc), 'something went wrong')
        finally:
            lazy_hippo.log.setLevel(logging.CRITICAL)

    def test_format_command_error_without_stderr(self):
        exc = CalledProcessError(2, 'cmd', stderr='')
        self.assertEqual(lazy_hippo.format_command_error(exc), 'Command failed with exit code 2')


class TestTimestampOverlayHelpers(unittest.TestCase):
    """Test the Pillow timestamp overlay helper functions"""

    def test_format_hms_formats_minutes_and_seconds(self):
        self.assertEqual(lazy_hippo.format_hms(90), '1:30')
        self.assertEqual(lazy_hippo.format_hms(3605), '1:00:05')

    def test_draw_timestamp_on_image_writes_image(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = Path(tmpdir) / 'frame.jpg'
            Image.new('RGB', (100, 100), color='blue').save(img_path)
            original_bytes = img_path.read_bytes()

            lazy_hippo.draw_timestamp_on_image(img_path, '0:01')

            self.assertTrue(img_path.exists())
            self.assertNotEqual(img_path.read_bytes(), original_bytes)

    def test_get_frame_rate_parses_fractional_rate(self):
        stream = {'avg_frame_rate': '30000/1001'}
        self.assertAlmostEqual(lazy_hippo.get_frame_rate(stream), 29.97, places=2)


class TestCliCompletion(unittest.TestCase):
    """Test Click shell completion integration"""

    def test_cli_uses_project_name_for_completion(self):
        self.assertEqual(lazy_hippo.cli.name, 'lazy-hippo')

        result = CliRunner().invoke(
            lazy_hippo.cli,
            [],
            prog_name='lazy-hippo',
            env={
                '_LAZY_HIPPO_COMPLETE': 'bash_complete',
                'COMP_WORDS': 'lazy-hippo ',
                'COMP_CWORD': '1',
            },
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn('extract', result.output)
        self.assertIn('gif-preview', result.output)


class TestCliSplit(unittest.TestCase):
    """Test the cli_split command"""

    def setUp(self):
        self.runner = CliRunner()
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        self.temp_file.close()
        self.temp_path = Path(self.temp_file.name)

    def tearDown(self):
        with contextlib.suppress(OSError):
            os.remove(self.temp_path)

    @patch('lazy_hippo.locate_binary')
    @patch('lazy_hippo.run_cmd')
    def test_split_single_chunk(self, mock_run_cmd, mock_locate):
        """Test splitting a single chunk"""
        mock_locate.return_value = '/usr/bin/ffmpeg'
        mock_run_cmd.return_value = Mock(returncode=0)

        result = self.runner.invoke(lazy_hippo.cli_split, [
            '-C', '5', '25',
            str(self.temp_path)
        ])

        self.assertEqual(result.exit_code, 0)
        mock_run_cmd.assert_called()

    @patch('lazy_hippo.locate_binary')
    @patch('lazy_hippo.run_cmd')
    def test_split_multiple_chunks(self, mock_run_cmd, mock_locate):
        """Test splitting multiple chunks"""
        mock_locate.return_value = '/usr/bin/ffmpeg'
        mock_run_cmd.return_value = Mock(returncode=0)

        result = self.runner.invoke(lazy_hippo.cli_split, [
            '-C', '5', '25',
            '-C', '30', '45',
            str(self.temp_path)
        ])

        self.assertEqual(result.exit_code, 0)
        self.assertGreaterEqual(mock_run_cmd.call_count, 2)

    @patch('lazy_hippo.locate_binary')
    def test_split_chunk_and_every_error(self, mock_locate):
        """Test that using both -C and -E raises an error"""
        mock_locate.return_value = '/usr/bin/ffmpeg'

        result = self.runner.invoke(lazy_hippo.cli_split, [
            '-C', '5', '25',
            '-E', '10',
            str(self.temp_path)
        ])

        self.assertNotEqual(result.exit_code, 0)

    @patch('lazy_hippo.locate_binary')
    @patch('lazy_hippo.probe_metadata')
    @patch('lazy_hippo.run_cmd')
    def test_split_every_fixed_length(self, mock_run_cmd, mock_probe, mock_locate):
        """Test splitting with fixed-length chunks (-E)"""
        mock_locate.return_value = '/usr/bin/ffmpeg'
        mock_probe.return_value = {'format': {'duration': '120.5'}}
        mock_run_cmd.return_value = Mock(returncode=0)

        result = self.runner.invoke(lazy_hippo.cli_split, [
            '-E', '30',
            str(self.temp_path)
        ])

        self.assertEqual(result.exit_code, 0)
        mock_run_cmd.assert_called()


class TestCliJoin(unittest.TestCase):
    """Test the cli_join command"""

    def setUp(self):
        self.runner = CliRunner()
        self.temp_files = []
        for i in range(2):
            tf = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            tf.close()
            self.temp_files.append(tf.name)
        self.output_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=True).name

    def tearDown(self):
        for f in self.temp_files:
            with contextlib.suppress(OSError):
                os.remove(f)
        with contextlib.suppress(OSError):
            os.remove(self.output_file)

    @patch('lazy_hippo.locate_binary')
    @patch('lazy_hippo.run_cmd')
    def test_join_files(self, mock_run_cmd, mock_locate):
        """Test joining multiple files"""
        mock_locate.return_value = '/usr/bin/ffmpeg'
        mock_run_cmd.return_value = Mock(returncode=0)

        result = self.runner.invoke(lazy_hippo.cli_join, [
            '-o', self.output_file,
            *self.temp_files
        ])

        self.assertEqual(result.exit_code, 0)
        mock_run_cmd.assert_called()


class TestCliInfo(unittest.TestCase):
    """Test the cli_info command"""

    def setUp(self):
        self.runner = CliRunner()
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        self.temp_file.close()

    def tearDown(self):
        with contextlib.suppress(OSError):
            os.remove(self.temp_file.name)

    @patch('lazy_hippo.probe_metadata')
    def test_info_txt_output(self, mock_probe):
        """Test info command with text output"""
        mock_probe.return_value = {
            'format': {
                'filename': 'test.mp4',
                'duration': '100.5',
                'size': '1024000',
                'bit_rate': '1000000'
            },
            'streams': [
                {
                    'codec_type': 'video',
                    'codec_name': 'h264',
                    'height': 1080,
                    'width': 1920
                }
            ]
        }

        result = self.runner.invoke(lazy_hippo.cli_info, [
            self.temp_file.name
        ])

        self.assertEqual(result.exit_code, 0)
        self.assertIn('duration', result.output)
        self.assertIn('h264', result.output)

    @patch('lazy_hippo.probe_metadata')
    def test_info_json_output(self, mock_probe):
        """Test info command with JSON output"""
        mock_probe.return_value = {
            'format': {'duration': '100.5'},
            'streams': []
        }

        result = self.runner.invoke(lazy_hippo.cli_info, [
            '-f', 'json',
            self.temp_file.name
        ])

        self.assertEqual(result.exit_code, 0)
        output_json = json.loads(result.output)
        self.assertIn('format', output_json)

    @patch('lazy_hippo.probe_metadata')
    def test_info_txt_output_no_video_stream(self, mock_probe):
        """Test info command when no video stream exists"""
        mock_probe.return_value = {
            'format': {
                'filename': 'test.mp4',
                'duration': '100.5',
                'size': '1024000',
                'bit_rate': '1000000'
            },
            'streams': []
        }

        result = self.runner.invoke(lazy_hippo.cli_info, [
            self.temp_file.name
        ])

        self.assertEqual(result.exit_code, 0)
        self.assertIn('No video stream found', result.output)


class TestCliRepack(unittest.TestCase):
    """Test the cli_repack command"""

    def setUp(self):
        self.runner = CliRunner()
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        self.temp_file.close()
        self.temp_path = Path(self.temp_file.name)

    def tearDown(self):
        for ext in ['.mp4', '.mkv']:
            with contextlib.suppress(OSError):
                os.remove(self.temp_path.with_suffix(ext))

    @patch('lazy_hippo.locate_binary')
    @patch('lazy_hippo.run_cmd')
    def test_repack_to_mkv(self, mock_run_cmd, mock_locate):
        """Test repacking to MKV"""
        mock_locate.return_value = '/usr/bin/ffmpeg'
        mock_run_cmd.return_value = Mock(returncode=0)

        result = self.runner.invoke(lazy_hippo.cli_repack, [
            '-f', 'mkv',
            str(self.temp_path)
        ])

        self.assertEqual(result.exit_code, 0)
        self.assertIn('Repackaged', result.output)


class TestCliGifPreview(unittest.TestCase):
    """Test the cli_gif_preview command"""

    def setUp(self):
        self.runner = CliRunner()
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        self.temp_file.close()
        self.temp_path = Path(self.temp_file.name)

    def tearDown(self):
        try:
            os.remove(self.temp_path)
            os.remove(self.temp_path.with_suffix('.gif'))
        except OSError:
            pass

    @patch('lazy_hippo.click.progressbar')
    @patch('lazy_hippo.locate_binary')
    @patch('lazy_hippo.probe_metadata')
    @patch('lazy_hippo.run_cmd')
    def test_gif_preview_with_auto_duration(self, mock_run_cmd, mock_probe, mock_locate, mock_progressbar):
        """Test GIF preview with automatic duration detection"""
        mock_locate.return_value = '/usr/bin/ffmpeg'
        mock_probe.return_value = {'format': {'duration': '120.5'}}
        mock_run_cmd.return_value = Mock(returncode=0)
        mock_progressbar.return_value.__enter__.return_value = Mock()
        mock_progressbar.return_value.__exit__.return_value = False

        result = self.runner.invoke(lazy_hippo.cli_gif_preview, [
            str(self.temp_path)
        ])

        self.assertEqual(result.exit_code, 0)
        self.assertGreaterEqual(mock_run_cmd.call_count, 2)
        mock_progressbar.assert_called_once()
        self.assertEqual(mock_progressbar.call_args.kwargs['length'], 2)


class TestCliExtract(unittest.TestCase):
    """Test the cli_extract command"""

    def setUp(self):
        self.runner = CliRunner()
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        self.temp_file.close()
        self.output_dir = tempfile.mkdtemp()

    def tearDown(self):
        with contextlib.suppress(OSError):
            os.remove(self.temp_file.name)
        import shutil
        shutil.rmtree(self.output_dir, ignore_errors=True)

    @patch('lazy_hippo.locate_binary')
    @patch('lazy_hippo.probe_metadata')
    @patch('lazy_hippo.run_cmd')
    def test_extract_frames(self, mock_run_cmd, mock_probe, mock_locate):
        """Test extracting frames"""
        mock_locate.return_value = '/usr/bin/ffmpeg'
        mock_probe.return_value = {'format': {'duration': '120.5'}}
        mock_run_cmd.return_value = Mock(returncode=0)

        result = self.runner.invoke(lazy_hippo.cli_extract, [
            '-o', self.output_dir,
            self.temp_file.name
        ])

        self.assertEqual(result.exit_code, 0)
        mock_run_cmd.assert_called()

    @patch('lazy_hippo.locate_binary')
    @patch('lazy_hippo.probe_metadata')
    @patch('lazy_hippo.run_cmd')
    def test_extract_nested_output_path(self, mock_run_cmd, mock_probe, mock_locate):
        """Test that nested output directories are created"""
        mock_locate.return_value = '/usr/bin/ffmpeg'
        mock_probe.return_value = {'format': {'duration': '120.5'}}
        mock_run_cmd.return_value = Mock(returncode=0)

        nested_output = Path(self.output_dir) / 'nested' / 'frames'
        result = self.runner.invoke(lazy_hippo.cli_extract, [
            '-o', str(nested_output),
            self.temp_file.name
        ])

        self.assertEqual(result.exit_code, 0)
        self.assertTrue(nested_output.exists())

    @patch('lazy_hippo.locate_binary')
    @patch('lazy_hippo.probe_metadata')
    @patch('lazy_hippo.draw_timestamp_on_image')
    @patch('lazy_hippo.run_cmd')
    def test_extract_timestamp_overlay(self, mock_run_cmd, mock_draw, mock_probe, mock_locate):
        """Test that timestamp overlay is applied to each extracted frame"""
        from PIL import Image

        mock_locate.return_value = '/usr/bin/ffmpeg'
        mock_probe.return_value = {'format': {'duration': '120.5'}}

        def fake_run(cmd):
            out_pattern = Path(cmd[-1])
            out_dir = out_pattern.parent
            out_dir.mkdir(parents=True, exist_ok=True)
            for i in range(1, 3):
                Image.new('RGB', (10, 10), color='red').save(out_dir / f'img{i:03d}.jpg')
            return Mock(returncode=0)

        mock_run_cmd.side_effect = fake_run

        result = self.runner.invoke(lazy_hippo.cli_extract, [
            '-o', self.output_dir,
            self.temp_file.name
        ])

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(mock_draw.call_count, 2)


if __name__ == '__main__':
    unittest.main()