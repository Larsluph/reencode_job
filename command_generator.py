from os.path import splitext

from filechecker import FileCheckError
from fileparser import FileMetadata, VideoMetadata


def check_flag_none(errors: FileCheckError, flag: FileCheckError):
    return ~errors & flag == flag

def generate_ffmpeg_command(input_file: str,
                            output_file: str,
                            metadata: FileMetadata,
                            errors: FileCheckError):
    params = []

    if check_flag_none(errors, FileCheckError.ANY):
        params.append("-c copy")
    else:
        # Audio errors
        if ~errors & FileCheckError.ANY_AUDIO == FileCheckError.ANY_AUDIO:
            params.append("-c:a copy")
        else:
            params.extend(generate_audio_params(errors))

        # Video errors
        if ~errors & FileCheckError.ANY_VIDEO == FileCheckError.ANY_VIDEO:
            params.append("-c:v copy")
        else:
            params.extend(generate_video_params(metadata.video, errors))

    name, _ = splitext(input_file)
    author, *titles = name.split(" - ")

    if len(titles) > 0:
        # Strip existing tags
        for tag_name in metadata.tags.keys():
            params.append(f"-metadata {tag_name}=")
        for tag_name in metadata.audio.tags.keys():
            params.append(f"-metadata:s:a {tag_name}=")
        for tag_name in metadata.video.tags.keys():
            params.append(f"-metadata:s:v {tag_name}=")

        params.extend((
            f'-metadata author={author}',
            f'-metadata title="{' - '.join(titles)}"',
        ))

    return f"ffmpeg -y -i \"{input_file}\" {' '.join(params)} \"{output_file}\""

def generate_audio_params(errors: FileCheckError):
    params = []

    if errors & FileCheckError.AUDIO_CODEC:
        params.append("-c:a aac")

    if errors & FileCheckError.AUDIO_SAMPLE_RATE:
        params.append("-ar 48000")

    if errors & FileCheckError.AUDIO_CHANNELS:
        params.append("-ac 2")

    if errors & FileCheckError.AUDIO_BITRATE:
        params.append("-b:a 192k")

    return params

def generate_video_params(metadata: VideoMetadata, errors: FileCheckError):
    params = []

    if errors & FileCheckError.VIDEO_CODEC:
        params.append("-c:v hevc")

    if errors & FileCheckError.VIDEO_RESOLUTION:
        params.append(f"-vf scale={'1080:1920' if metadata.is_portrait else '1920:1080'}")

    if errors & FileCheckError.VIDEO_FPS:
        params.append("-r 30")

    return params
