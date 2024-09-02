import logging
from dataclasses import dataclass
from json import loads as load_json
from math import gcd
from pathlib import Path
from subprocess import run, CalledProcessError
from typing import Optional

from colorized_logger import SKIP

logger = logging.getLogger('reencode_job.fileparser')


@dataclass
class AudioMetadata:
    """Stores audio stream metadata"""
    codec: str
    sample_rate: int
    channels: int
    bitrate: int
    tags: dict


@dataclass
class VideoMetadata:
    """Stores video stream metadata"""
    codec: str
    width: int
    height: int
    aspect_ratio: str
    frame_rate: float
    bitrate: int
    tags: dict

    @property
    def is_portrait(self):
        return self.width < self.height


@dataclass
class FileMetadata:
    """Stores video file metadata"""
    # General
    filepath: Path
    file_size: int
    duration: float

    audio: AudioMetadata
    video: VideoMetadata
    tags: dict


def parse_frame_rate(frame_rate: str) -> float:
    num, denom = map(int, frame_rate.split('/'))
    return num / denom


def calc_aspect_ratio(width: int, height: int):
    """Calculate the aspect ratio of the video by simplifying the fraction"""
    divisor = gcd(width, height)
    return f'{width // divisor}:{height // divisor}'


def probe_file(file_path: Path) -> Optional[FileMetadata]:
    """Parse the ffprobe output and return a dictionary of the metadata"""
    if not file_path.exists():
        logger.log(SKIP, "File doesn't exist anymore")
        return None

    try:
        result = run(['ffprobe', '-v', 'error', '-print_format', 'json',
                      '-show_format', '-show_streams', str(file_path)],
                     shell=False,
                     capture_output=True,
                     check=True,
                     text=True)
    except CalledProcessError:
        logger.exception("Unable to probe file")
        return None

    output = result.stdout
    json_output: dict = load_json(output)

    video_stream: dict
    audio_stream: dict

    # Detect video stream
    for stream in json_output['streams']:
        if stream['codec_type'] == 'video':
            video_stream = stream
            break
    else:
        logger.log(SKIP, "No video stream found")
        return None

    # Detect audio stream
    for stream in json_output['streams']:
        if stream['codec_type'] == 'audio':
            audio_stream = stream
            break
    else:
        logger.log(SKIP, "No audio stream found")
        return None

    video_width: int = video_stream['width']
    video_height: int = video_stream['height']

    format_stream: dict = json_output['format']

    return FileMetadata(
        filepath=Path(format_stream.get('filename', '')),
        file_size=int(format_stream.get('size', 0)),
        duration=float(format_stream.get('duration', 0)),
        audio=AudioMetadata(codec=audio_stream['codec_name'],
                            sample_rate=int(audio_stream.get('sample_rate', 0)),
                            channels=int(audio_stream.get('channels', 0)),
                            bitrate=int(audio_stream.get('bit_rate', 0)),
                            tags=audio_stream.get('tags', {})),
        video=VideoMetadata(codec=video_stream['codec_name'],
                            width=video_width,
                            height=video_height,
                            aspect_ratio=calc_aspect_ratio(video_width, video_height),
                            frame_rate=parse_frame_rate(video_stream.get('r_frame_rate', '0/1')),
                            bitrate=int(video_stream.get('bit_rate', 0)),
                            tags=video_stream.get('tags', {})),
        tags=format_stream.get('tags', {})
    )
