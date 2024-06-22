from enum import Flag, auto
from pathlib import Path

from config import EXT_WHITELIST, CRITERIAS
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
    VIDEO_BITRATE = auto()

    # Combined errors
    NONE = 0
    ANY_AUDIO = AUDIO_CODEC | AUDIO_SAMPLE_RATE | AUDIO_CHANNELS | AUDIO_BITRATE
    ANY_VIDEO = VIDEO_CODEC | VIDEO_RESOLUTION | VIDEO_FPS | VIDEO_BITRATE
    ANY = ANY_AUDIO | ANY_VIDEO


def check_file_ext(file_path: Path) -> tuple[bool, str]:
    """Check if the file extension is in the whitelist"""
    ext = file_path.suffix
    return ext in EXT_WHITELIST, ext


def check_file(metadata: FileMetadata) -> FileCheckError:
    """Check if the file meets the requirements"""
    errors = FileCheckError.NONE

    audio = metadata.audio

    if CRITERIAS['audio']['codec'] and audio.codec != CRITERIAS['audio']['codec']:
        errors |= FileCheckError.AUDIO_CODEC

    if CRITERIAS['audio']['sample_rate'] and audio.sample_rate > CRITERIAS['audio']['sample_rate']:
        errors |= FileCheckError.AUDIO_SAMPLE_RATE

    if CRITERIAS['audio']['channels'] and audio.channels > CRITERIAS['audio']['channels']:
        errors |= FileCheckError.AUDIO_CHANNELS

    if CRITERIAS['audio']['bitrate'] and audio.bitrate > CRITERIAS['audio']['bitrate']['threshold']:
        errors |= FileCheckError.AUDIO_BITRATE

    video = metadata.video

    if CRITERIAS['video']['codec'] and video.codec != CRITERIAS['video']['codec']:
        errors |= FileCheckError.VIDEO_CODEC

    width, height = (video.width, video.height)
    if video.is_portrait:
        width, height = height, width

    target_resolution = CRITERIAS['video']['resolution']
    if target_resolution and (width > target_resolution[0] or height > target_resolution[1]):
        errors |= FileCheckError.VIDEO_RESOLUTION

    if CRITERIAS['video']['fps'] and video.frame_rate > CRITERIAS['video']['fps']:
        errors |= FileCheckError.VIDEO_FPS

    if CRITERIAS['video']['bitrate'] and video.bitrate > CRITERIAS['video']['bitrate']['threshold']:
        errors |= FileCheckError.VIDEO_BITRATE

    return errors
