from os.path import basename, splitext

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
        params.extend(('-c', 'copy'))
    else:
        # Audio errors
        if ~errors & FileCheckError.ANY_AUDIO == FileCheckError.ANY_AUDIO:
            params.extend(('-c:a', 'copy'))
        else:
            params.extend(generate_audio_params(errors))

        # Video errors
        if ~errors & FileCheckError.ANY_VIDEO == FileCheckError.ANY_VIDEO:
            params.extend(('-c:v', 'copy'))
        else:
            params.extend(generate_video_params(metadata.video, errors))

    name, _ = splitext(basename(input_file))
    author, *titles = name.split(' - ')

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

    return ['ffmpeg', '-y', '-i', input_file, *params, output_file]

def generate_audio_params(errors: FileCheckError):
    params = []

    if errors & FileCheckError.AUDIO_CODEC:
        params.extend(('-c:a', 'aac'))

    if errors & FileCheckError.AUDIO_SAMPLE_RATE:
        params.extend(('-ar', '48000'))

    if errors & FileCheckError.AUDIO_CHANNELS:
        params.extend(('-ac', '2'))

    if errors & FileCheckError.AUDIO_BITRATE:
        params.extend(('-b:a', '192k'))

    return params

def generate_video_params(metadata: VideoMetadata, errors: FileCheckError):
    params = []

    if errors & FileCheckError.VIDEO_CODEC:
        params.extend(('-c:v', 'hevc'))

    if errors & FileCheckError.VIDEO_RESOLUTION:
        params.extend(('-vf', f"scale={'1080:1920' if metadata.is_portrait else '1920:1080'}"))

    if errors & FileCheckError.VIDEO_FPS:
        params.extend(('-r', '30'))

    return params
