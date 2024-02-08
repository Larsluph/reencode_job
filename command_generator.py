from filechecker import FileCheckError


def generate_ffmpeg_command(input_file: str, output_file: str, errors: FileCheckError):
    params = []

    # Audio errors

    if errors & FileCheckError.AUDIO_CODEC:
        params.append("-c:a aac")

    if errors & FileCheckError.AUDIO_SAMPLE_RATE:
        params.append("-ar 48000")

    if errors & FileCheckError.AUDIO_CHANNELS:
        params.append("-ac 2")

    if errors & FileCheckError.AUDIO_BITRATE:
        params.append("-b:a 192k")

    if ~errors & FileCheckError.ANY_AUDIO == FileCheckError.ANY_AUDIO:
        params.append("-c:a copy")

    # Video errors

    if errors & FileCheckError.VIDEO_CODEC:
        params.append("-c:v hevc")

    if errors & FileCheckError.VIDEO_RESOLUTION:
        params.append("-vf scale=1920:1080")

    if errors & FileCheckError.VIDEO_FPS:
        params.append("-r 30")

    if ~errors & FileCheckError.ANY_VIDEO == FileCheckError.ANY_VIDEO:
        params.append("-c:v copy")

    return f"ffmpeg -y -i \"{input_file}\" {' '.join(params)} \"{output_file}\""
