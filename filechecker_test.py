from unittest import TestCase
from pathlib import Path

from filechecker import check_file_ext, check_file, FileCheckError
from fileparser import FileMetadata, AudioMetadata, VideoMetadata

class FileCheckerTest(TestCase):
    metadata = None

    def setUp(self):
        self.metadata = FileMetadata(
        "input_path",
        123,
        30.0,
        AudioMetadata("aac", 48_000, 2, 192_000, {}),
        VideoMetadata("hevc", 1920, 1080, "16/9", 30.0, 8000, {}),
        {}
    )

    def test_check_file_ext_returns_false(self):
        res, ext = check_file_ext(Path("/file/test.txt"))
        self.assertFalse(res)
        self.assertEqual(ext, ".txt")

    def test_check_file_ext_returns_true(self):
        res, ext = check_file_ext(Path("/file/test.mp4"))
        self.assertTrue(res)
        self.assertEqual(ext, ".mp4")

    def text_check_file_none(self):
        result = check_file(self.metadata)
        self.assertEqual(result, FileCheckError.NONE)

    def test_check_file_audio_codec(self):
        self.metadata.audio.codec = "flac"
        result = check_file(self.metadata)
        self.assertEqual(result, FileCheckError.AUDIO_CODEC)

    def test_check_file_audio_sample_rate(self):
        self.metadata.audio.sample_rate = 96_000
        result = check_file(self.metadata)
        self.assertEqual(result, FileCheckError.AUDIO_SAMPLE_RATE)

    def test_check_file_audio_channels(self):
        self.metadata.audio.channels = 5
        result = check_file(self.metadata)
        self.assertEqual(result, FileCheckError.AUDIO_CHANNELS)

    def test_check_file_audio_bitrate(self):
        self.metadata.audio.bitrate = 250_000
        result = check_file(self.metadata)
        self.assertEqual(result, FileCheckError.AUDIO_BITRATE)

    def test_check_file_video_codec(self):
        self.metadata.video.codec = "h264"
        result = check_file(self.metadata)
        self.assertEqual(result, FileCheckError.VIDEO_CODEC)

    def test_check_file_video_resolution_portrait(self):
        self.metadata.video.width = 1440
        self.metadata.video.height = 2560
        result = check_file(self.metadata)
        self.assertEqual(result, FileCheckError.VIDEO_RESOLUTION)

    def test_check_file_video_resolution_landscape(self):
        self.metadata.video.width = 2560
        self.metadata.video.height = 1440
        result = check_file(self.metadata)
        self.assertEqual(result, FileCheckError.VIDEO_RESOLUTION)

    def test_check_file_video_fps(self):
        self.metadata.video.frame_rate = 60
        result = check_file(self.metadata)
        self.assertEqual(result, FileCheckError.VIDEO_FPS)
