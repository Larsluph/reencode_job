import argparse
import logging
import sys
from datetime import datetime
from enum import Enum
from os import remove, rename, walk
from os.path import isfile, isdir, join, splitext
from signal import signal, SIGINT, SIGTERM
from subprocess import Popen, PIPE, STDOUT
from sys import stdout

from command_generator import generate_ffmpeg_command
from config import LOG_LOCATION, LOG_DATE_FORMAT, LOG_MESSAGE_FORMAT
from filechecker import check_file_ext, check_file
from fileparser import probe_file

parser = argparse.ArgumentParser(description="Video re-encoder with ffmpeg")
parser.add_argument('path', type=str, help='path to video content')
parser.add_argument('-d', '--dry-run', action='store_true',
                    help='perform a trial run without changes made')
parser.add_argument('-rm', '--remove', action='store_true',
                    help='remove original content after processing')
parser.add_argument('--replace', action='store_true',
                    help='replace original content with the processed one')
parser.add_argument('--clean-on-error', action='store_true',
                    help='remove processed content if an error occurs')
args = parser.parse_args()

fh = logging.FileHandler(join(LOG_LOCATION,
                              datetime.now().strftime(LOG_DATE_FORMAT)))
fh.setLevel(logging.DEBUG)
sh = logging.StreamHandler(stdout)
sh.setLevel(logging.INFO)
logging.basicConfig(level=logging.DEBUG,
                    format=LOG_MESSAGE_FORMAT,
                    handlers=(fh, sh))

logging.info('Starting new job with params: %s', args)


class ContentType(Enum):
    """Content type enum"""
    FILE = 1
    DIRECTORY = 2


contentType: ContentType
contentPath = args.path

if isfile(contentPath):
    contentType = ContentType.FILE
    logging.debug("File detected")

elif isdir(contentPath):
    contentType = ContentType.DIRECTORY
    logging.debug("Directory detected")

else:
    logging.error("Unknown content type")
    sys.exit(2)

is_dry_run_enabled: bool = args.dry_run
is_remove_enabled: bool = args.remove
is_replace_enabled: bool = args.replace
is_clean_on_error_enabled: bool = args.clean_on_error
is_interrupted: bool = False

def handler(signum, _):
    global is_interrupted
    is_interrupted = True
    logging.warning('Interrupted by signal %d', signum)

signal(SIGINT, handler)
signal(SIGTERM, handler)

# Check if dry run flag is set
if is_dry_run_enabled:
    logging.info("Dry run enabled")

if contentType == ContentType.FILE:
    is_valid, ext = check_file_ext(contentPath)
    if not is_valid:
        logging.error('Extension "%s" not in whitelist', ext)
        sys.exit(3)

    files = [contentPath]
else:
    # Search for files in the directory and all subdirectories matching the whitelisted extensions
    directories_count: int = 0
    files_count: int = 0
    files = []
    for root, _, filenames in walk(contentPath):
        directories_count += 1
        files_count += len(filenames)
        logging.debug('Scanned %s directories and %s files', directories_count, files_count)
        for filename in filenames:
            is_valid, ext = check_file_ext(filename)
            if is_valid:
                files.append(join(root, filename))
            else:
                logging.info('Extension "%s" not in whitelist, skipping', ext)

for i, input_filename in enumerate(files, start=1):
    logging.info('[%d/%d] Processing "%s"', i, len(files), input_filename)

    file_metadata = probe_file(input_filename)
    if file_metadata is None:
        logging.info('Skipping')
        continue

    errors = check_file(file_metadata)
    name, ext = splitext(input_filename)
    output_filename = f"{name}_reencoded.mp4"
    cmd = generate_ffmpeg_command(input_filename, output_filename, file_metadata, errors)

    logging.debug(file_metadata)
    logging.debug(errors)
    logging.debug(cmd)

    if is_dry_run_enabled:
        continue

    if not errors:
        logging.info('Video matches expectations, skipping')
        continue

    with Popen(cmd, stdout=PIPE, stderr=STDOUT, universal_newlines=True) as process:
        for line in process.stdout:
            logging.debug(line.rstrip())
            if is_interrupted:
                process.terminate()
                break

        if process.wait() != 0:
            logging.error('Failed to process "%s": return code was %d',
                          input_filename, process.returncode)
            if is_clean_on_error_enabled:
                logging.info('Removing failed "%s"', output_filename)
                remove(output_filename)

            if is_interrupted:
                logging.info('Interrupted')
                break
            continue

        if is_replace_enabled:
            logging.info('Replacing "%s"', input_filename)
            # Replace the original file
            rename(output_filename, input_filename)
        elif is_remove_enabled:
            logging.info('Removing "%s"', input_filename)
            # Remove the original file
            remove(input_filename)
