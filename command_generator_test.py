from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from command_generator import check_flag_none, check_flag_any, generate_ffmpeg_command
from filechecker import FileCheckError
from fileparser import FileMetadata, AudioMetadata, VideoMetadata


class TestCommandGenerator(TestCase):
    metadata = FileMetadata(
        Path("input_path"),
        123,
        30.0,
        AudioMetadata("aac", 48_000, 2, 256_000, {}),
        VideoMetadata("h264", 1920, 1080, "16/9", 60.0, 8000, {}),
        {}
    )

    def test_check_flag_none_should_return_false(self):
        result = check_flag_none(FileCheckError.AUDIO_BITRATE,
                                 FileCheckError.ANY_AUDIO)
        self.assertFalse(result, "check_flag_none should return False")

    def test_check_flag_none_should_return_true(self):
        result = check_flag_none(FileCheckError.VIDEO_CODEC,
                                 FileCheckError.ANY_AUDIO)
        self.assertTrue(result, "check_flag_none should return True")

    def test_check_flag_any_should_return_false(self):
        result = check_flag_any(FileCheckError.VIDEO_CODEC,
                                FileCheckError.ANY_AUDIO)
        self.assertFalse(result, "check_flag_any should return False")

    def test_check_flag_any_should_return_true(self):
        result = check_flag_any(FileCheckError.AUDIO_BITRATE,
                                FileCheckError.ANY_AUDIO)
        self.assertTrue(result, "check_flag_any should return True")

    def test_generate_ffmpeg_command_returns_copy(self):
        with patch('command_generator.generate_tag_params'):
            result = generate_ffmpeg_command(Path("input_path"),
                                             Path("output_path"),
                                             self.metadata,
                                             FileCheckError.NONE)
            self.assertEqual(result, ['ffmpeg', '-hide_banner', '-y',
                                      '-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda',
                                      '-i', 'input_path',
                                      '-c', 'copy',
                                      'output_path'])

    def test_generate_ffmpeg_command_returns_audio_with_vcopy(self):
        with patch('command_generator.generate_tag_params'):
            result = generate_ffmpeg_command(Path("input_path"),
                                             Path("output_path"),
                                             self.metadata,
                                             FileCheckError.AUDIO_BITRATE)
            self.assertEqual(result, ['ffmpeg', '-hide_banner', '-y',
                                      '-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda',
                                      '-i', 'input_path',
                                      '-c:a', 'aac',
                                      '-b:a', '192000',
                                      '-c:v', 'copy',
                                      'output_path'])

    def test_generate_ffmpeg_command_returns_video_with_acopy(self):
        with patch('command_generator.generate_tag_params'):
            result = generate_ffmpeg_command(
                Path("input_path"), Path("output_path"), self.metadata, FileCheckError.VIDEO_RESOLUTION)
            self.assertEqual(result, ['ffmpeg', '-hide_banner', '-y',
                                      '-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda',
                                      '-i', 'input_path',
                                      '-c:a', 'copy',
                                      '-c:v', 'hevc_nvenc',
                                      '-vf', 'scale=1920:1080',
                                      'output_path'])
