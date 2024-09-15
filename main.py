import logging
import sys
from argparse import ArgumentParser
from datetime import datetime
from os.path import join
from pathlib import Path
from signal import signal, SIGINT, SIGTERM

from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

import colorized_logger
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
                        help='path is a file with a list of files to process, '
                             'if OUTPUT is specified the file list should be composed of '
                             'alternating lines of input and output filenames')
    parser.add_argument('-d', '--dry-run', action='store_true',
                        help='perform a trial run without changes made')
    parser.add_argument('-rm', '--remove', action='store_true',
                        help='remove original content after processing')
    parser.add_argument('--replace', action='store_true',
                        help='replace original content with the processed one')
    parser.add_argument('--clean-on-error', action='store_true',
                        help='remove processed content if an error occurs')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='increase console output verbosity')
    app = App(parser.parse_args())

    fh = logging.FileHandler(filename=join(LOG_LOCATION,
                                           datetime.now().strftime(LOG_DATE_FORMAT)),
                             mode='w',
                             encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(LOG_MESSAGE_FORMAT))

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG if app.args.is_verbose_enabled else logging.INFO)
    ch.setFormatter(colorized_logger.ColoredFormatter(LOG_MESSAGE_FORMAT))

    logger = logging.getLogger('reencode_job')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    logger.addHandler(ch)

    def add_log_level(lvl): return logging.addLevelName(getattr(colorized_logger, lvl), lvl)
    add_log_level('PROGRESS')
    add_log_level('SKIP')
    add_log_level('DESTRUCTIVE')
    add_log_level('STOP')
    add_log_level('ROLLBACK')

    app.init_job()

    signal(SIGINT, app.signal_handler)
    signal(SIGTERM, app.signal_handler)

    with logging_redirect_tqdm(loggers=[logger]):
        for i, (input_filename, output_filename) in tqdm(enumerate(zip(app.files, app.outs), start=1),
                                                         total=len(app.files),
                                                         unit='file',
                                                         desc='Files processed'):
            worker = Worker(app, i, input_filename, output_filename)
            try:
                worker.work()
            except Exception as e:
                logger.exception('Unhandled exception', exc_info=e)

            if STOP_FILE.exists():
                logger.log(colorized_logger.STOP, 'Stop file found, exiting...')
                break

            if app.is_interrupted:
                logger.log(colorized_logger.STOP, 'Interrupted, exiting...')
                break
