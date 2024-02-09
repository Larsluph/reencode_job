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
    NONE = 0
    ANY_AUDIO = AUDIO_CODEC | AUDIO_SAMPLE_RATE | AUDIO_CHANNELS | AUDIO_BITRATE
    ANY_VIDEO = VIDEO_CODEC | VIDEO_RESOLUTION | VIDEO_FPS
    ANY = ANY_AUDIO | ANY_VIDEO


def check_file_ext(file_path: str) -> bool:
    """Check if the file extension is in the whitelist"""
    ext_whitelist = ['.avi', '.mp4', '.mov', '.mkv', '.wmv']
    ext = splitext(file_path)[1]
    return ext in ext_whitelist, ext


def check_file(metadata: FileMetadata) -> FileCheckError:
    """Check if the file meets the requirements"""
    errors = FileCheckError.NONE

    ### Check audio
    audio = metadata.audio

    if audio.codec != 'aac':
        errors |= FileCheckError.AUDIO_CODEC

    if audio.sample_rate > 48000:
        errors |= FileCheckError.AUDIO_SAMPLE_RATE

    if audio.channels > 2:
        errors |= FileCheckError.AUDIO_CHANNELS

    if audio.bitrate > 192000:
        errors |= FileCheckError.AUDIO_BITRATE

    ### Check video
    video = metadata.video

    if video.codec != 'hevc':
        errors |= FileCheckError.VIDEO_CODEC

    width, height = (video.width, video.height)
    if video.is_portrait:
        width, height = height, width

    if width > 1920 or height > 1080:
        errors |= FileCheckError.VIDEO_RESOLUTION

    if video.frame_rate > 30:
        errors |= FileCheckError.VIDEO_FPS

    return errors
