import argparse
import logging
import sys
from datetime import datetime
from enum import Enum
from os import rename, walk
from os.path import isfile, isdir, join, splitext
from subprocess import Popen, PIPE, STDOUT
from sys import stdout

from command_generator import generate_ffmpeg_command
from filechecker import check_file_ext, check_file
from fileparser import probe_file

# Create the parser
parser = argparse.ArgumentParser(description="Command parser for CLI")

# Add arguments
parser.add_argument('path', type=str, help='The path to the content')
parser.add_argument('-d', '--dry-run', action='store_true',
                    help='Using this flag will not affect the content, used for debugging')
parser.add_argument('-rm', '--remove', action='store_true',
                    help='Using this flag will remove the content after processing')

# Parse the arguments
args = parser.parse_args()

fh = logging.FileHandler(datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log"))
fh.setLevel(logging.DEBUG)

sh = logging.StreamHandler(stdout)
sh.setLevel(logging.INFO)

logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s]:%(asctime)s %(message)s',
                    handlers=(fh, sh))


class ContentType(Enum):
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

# Check if dry run flag is set
if is_dry_run_enabled:
    logging.info("Dry run enabled")

if contentType == ContentType.FILE:
    if not check_file_ext(contentPath):
        logging.error("File extension not in whitelist")
        sys.exit(3)

    files = [contentPath]
else:
    # Search for files in the directory and all subdirectories matching the whitelisted extensions
    directories_count = 0
    files_count = 0
    files = []
    for root, _, filenames in walk(contentPath):
        directories_count += 1
        files_count += len(filenames)
        logging.debug('Scanned %s directories and %s files', directories_count, files_count)
        files.extend(join(root, filename) for filename in filenames if check_file_ext(filename))

for input_filename in files:
    logging.info('Processing %s', input_filename)

    file_metadata = probe_file(input_filename)
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
        logging.info('Video matches expectations, skipping...')
        continue

    with Popen(cmd, stdout=PIPE, stderr=STDOUT, universal_newlines=True) as process:
        for line in process.stdout:
            logging.debug(line.rstrip())

        if process.returncode != 0:
            logging.error('Failed to process %s', input_filename)
            continue

        if is_remove_enabled:
            logging.info('Removing %s', input_filename)
            # Replace the original file
            rename(input_filename, output_filename)
