LOG_LOCATION = '/app/logs'
LOG_DATE_FORMAT = '%Y-%m-%d_%H-%M-%S.log'
LOG_MESSAGE_FORMAT = '[%(levelname)s]:%(asctime)s %(message)s'

EXT_WHITELIST = ['.avi', '.mp4', '.mov', '.mkv', '.wmv']

CRITERIAS = {
    'audio': {
        'codec': 'aac',
        'sample_rate': 48_000,
        'channels': 2,
        'bitrate': 192_000
    },
    'video': {
        'codec': 'hevc',
        'resolution': (1920, 1080),
        'fps': 30
    }
}