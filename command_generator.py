from pathlib import Path

from config import CRITERIAS
from filechecker import FileCheckError
from fileparser import AudioMetadata, FileMetadata, VideoMetadata


def check_flag_none(errors: FileCheckError, flag: FileCheckError):
    return (~errors & flag) == flag

def check_flag_any(errors: FileCheckError, flag: FileCheckError):
    return (errors & flag) != FileCheckError.NONE

def generate_audio_params(metadata: AudioMetadata, errors: FileCheckError):
    params = []

    if check_flag_any(errors, FileCheckError.ANY_AUDIO):
        audio_codec = CRITERIAS['audio']['codec']
        params.extend(('-c:a', audio_codec if audio_codec else metadata.codec))

    if errors & FileCheckError.AUDIO_SAMPLE_RATE:
        params.extend(('-ar', CRITERIAS['audio']['sample_rate']))

    if errors & FileCheckError.AUDIO_CHANNELS:
        params.extend(('-ac', CRITERIAS['audio']['channels']))

    if errors & FileCheckError.AUDIO_BITRATE:
        params.extend(('-b:a', CRITERIAS['audio']['bitrate']['target']))

    return params

def generate_video_params(metadata: VideoMetadata, errors: FileCheckError):
    params = []

    if check_flag_any(errors, FileCheckError.ANY_VIDEO):
        video_codec = CRITERIAS['video']['codec']
        params.extend(('-c:v', video_codec if video_codec else metadata.codec))

    if errors & FileCheckError.VIDEO_RESOLUTION:
        width, height = CRITERIAS['video']['resolution']
        resolution = f'{height}:{width}' if metadata.is_portrait else f'{width}:{height}'
        params.extend(('-vf', f"scale={resolution}"))

    if errors & FileCheckError.VIDEO_FPS:
        params.extend(('-r', CRITERIAS['video']['fps']))

    return params

def generate_tag_params(input_file: Path):
    params = []

    author, *titles = input_file.stem.split(' - ')

    if len(titles) > 0:
        # Strip existing tags
        # for tag_name in metadata.tags.keys():
        #     params.extend('-metadata', f'{tag_name}=')
        # for tag_name in metadata.audio.tags.keys():
        #     params.extend('-metadata:s:a', f'{tag_name}=')
        # for tag_name in metadata.video.tags.keys():
        #     params.extend('-metadata:s:v', f'{tag_name}=')

        params.extend((
            '-metadata', f'author={author}',
            '-metadata', f'title={titles[0]}',
        ))

    return params

def generate_ffmpeg_command(input_file: Path,
                            output_file: Path,
                            metadata: FileMetadata,
                            errors: FileCheckError):
    params = []

    if errors == FileCheckError.NONE:
        params.extend(('-c', 'copy'))
    else:
        # Audio errors
        if check_flag_none(errors, FileCheckError.ANY_AUDIO):
            params.extend(('-c:a', 'copy'))
        else:
            params.extend(generate_audio_params(metadata.audio, errors))

        # Video errors
        if check_flag_none(errors, FileCheckError.ANY_VIDEO):
            params.extend(('-c:v', 'copy'))
        else:
            params.extend(generate_video_params(metadata.video, errors))

    params.extend(generate_tag_params(input_file))

    return list(map(str, ('ffmpeg', '-hide_banner', '-y',
                          '-i', input_file,
                          *params,
                          output_file)))
