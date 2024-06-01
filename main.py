import logging
from argparse import ArgumentParser
from datetime import datetime
from os.path import join
from pathlib import Path
from signal import signal, SIGINT, SIGTERM
from sys import stdout

from app import App
from config import LOG_LOCATION, LOG_DATE_FORMAT, LOG_MESSAGE_FORMAT, STOP_FILE
from worker import Worker


if __name__ == '__main__':
    parser = ArgumentParser(description="Video re-encoder with ffmpeg")
    parser.add_argument('path', type=Path, help='path to video content')
    parser.add_argument('-o', '--output', type=Path, help='path to output content')
    parser.add_argument('--overwrite', action='store_true',
                        help='Replace output if it already exists')
    parser.add_argument('--filter', help='glob pattern to filter input files to process')
    parser.add_argument('-f', '--filelist', action='store_true',
                        help='path is a file with a list of files to process')
    parser.add_argument('-d', '--dry-run', action='store_true',
                        help='perform a trial run without changes made')
    parser.add_argument('-rm', '--remove', action='store_true',
                        help='remove original content after processing')
    parser.add_argument('--replace', action='store_true',
                        help='replace original content with the processed one')
    parser.add_argument('--clean-on-error', action='store_true',
                        help='remove processed content if an error occurs')
    app = App(parser.parse_args())

    formatter = logging.Formatter(LOG_MESSAGE_FORMAT)

    fh = logging.FileHandler(join(LOG_LOCATION,
                                datetime.now().strftime(LOG_DATE_FORMAT)))
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)

    ch = logging.StreamHandler(stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)

    logger = logging.getLogger('reencode_job')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    logger.addHandler(ch)

    app.init_job()

    signal(SIGINT, app.signal_handler)
    signal(SIGTERM, app.signal_handler)

    for i, (input_filename, output_filename) in enumerate(zip(app.files, app.outs), start=1):
        worker = Worker(app, i, input_filename, output_filename)
        if not worker.work():
            break
        if STOP_FILE.exists():
            logger.info('Stop file found, exiting...')
            break
