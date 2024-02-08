from enum import Flag, auto
from os.path import splitext

from fileparser import FileMetadata


class FileCheckError(Flag):
    """Enumeration of file check errors"""

    # Audio errors
    AUDIO_CODEC = auto()
    AUDIO_SAMPLE_RATE = auto()
    AUDIO_CHANNELS = auto()
    AUDIO_BITRATE = auto()

    # Video errors
    VIDEO_CODEC = auto()
    VIDEO_RESOLUTION = auto()
    VIDEO_FPS = auto()

    # Combined errors
    ANY_AUDIO = AUDIO_CODEC | AUDIO_SAMPLE_RATE | AUDIO_CHANNELS | AUDIO_BITRATE
    ANY_VIDEO = VIDEO_CODEC | VIDEO_RESOLUTION | VIDEO_FPS


def check_file_ext(file_path: str) -> bool:
    """Check if the file extension is in the whitelist"""
    ext_whitelist = ['.mp4', '.mov', '.mkv', '.wmv']
    return splitext(file_path)[1] in ext_whitelist


def check_file(metadata: FileMetadata) -> FileCheckError:
    """Check if the file meets the requirements"""
    errors = FileCheckError(0)

    ### Check audio

    if metadata.audio.codec != 'aac':
        errors |= FileCheckError.AUDIO_CODEC

    if metadata.audio.sample_rate > 48000:
        errors |= FileCheckError.AUDIO_SAMPLE_RATE

    if metadata.audio.channels > 2:
        errors |= FileCheckError.AUDIO_CHANNELS

    if metadata.audio.bitrate > 192000:
        errors |= FileCheckError.AUDIO_BITRATE

    ### Check video

    if metadata.video.codec != 'hevc':
        errors |= FileCheckError.VIDEO_CODEC

    if metadata.video.width > 1920 or metadata.video.height > 1080:
        errors |= FileCheckError.VIDEO_RESOLUTION

    if metadata.video.frame_rate > 30:
        errors |= FileCheckError.VIDEO_FPS

    return errors
