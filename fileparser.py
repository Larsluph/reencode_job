from dataclasses import dataclass
from json import loads as load_json
from math import gcd
from subprocess import run, CalledProcessError
from typing import Optional


@dataclass
class AudioMetadata:
    """Stores audio stream metadata"""
    codec: str
    sample_rate: int
    channels: int
    bitrate: int


@dataclass
class VideoMetadata:
    "Stores video stream metadata"
    codec: str
    width: int
    height: int
    aspect_ratio: str
    frame_rate: float
    bitrate: int

    @property
    def is_portrait(self):
        return self.width < self.height


@dataclass
class FileMetadata:
    "Stores video file metadata"
    # General
    filepath: str
    file_size: int
    duration: float

    audio: AudioMetadata
    video: VideoMetadata

    # TODO: Add tags
    tags: dict = None


def calc_aspect_ratio(width: int, height: int):
    """Calculate the aspect ratio of the video by simplifying the fraction"""
    divisor = gcd(width, height)
    return f'{width // divisor}:{height // divisor}'


def probe_file(file_path: str) -> Optional[FileMetadata]:
    """Parse the ffprobe output and return a dictionary of the metadata"""
    try:
        result = run('ffprobe -v error -print_format json -show_format -show_streams '
                     f'"{file_path}"',
                    shell=True,
                    capture_output=True,
                    check=True,
                    text=True)
    except CalledProcessError as e:
        print("Unable to probe file:", e.stderr)
        return None

    output = result.stdout
    json_output = load_json(output)

    video_stream: Optional[dict] = None
    audio_stream: Optional[dict] = None

    # Detect video stream
    for stream in json_output['streams']:
        if stream['codec_type'] == 'video':
            video_stream = stream
            break

    # Detect audio stream
    for stream in json_output['streams']:
        if stream['codec_type'] == 'audio':
            audio_stream = stream
            break

    video_width: int = video_stream['width']
    video_height: int = video_stream['height']

    return FileMetadata(
        filepath=json_output['format']['filename'],
        file_size=int(json_output['format']['size']),
        duration=float(json_output['format']['duration']),
        audio=AudioMetadata(codec=audio_stream['codec_name'],
                            sample_rate=int(audio_stream['sample_rate']),
                            channels=int(audio_stream['channels']),
                            bitrate=int(audio_stream['bit_rate'])),
        video=VideoMetadata(codec=video_stream['codec_name'],
                            width=video_width,
                            height=video_height,
                            aspect_ratio=calc_aspect_ratio(video_width, video_height),
                            frame_rate=eval(video_stream['r_frame_rate']),
                            bitrate=float(video_stream['bit_rate']))
    )
