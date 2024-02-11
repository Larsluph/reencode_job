import argparse
import logging
import sys
from datetime import datetime
from enum import Enum
from os import remove, rename, walk
from os.path import exists, getsize, isfile, isdir, join, splitext
from pathlib import Path
from signal import signal, SIGINT, SIGTERM
from subprocess import Popen, PIPE, STDOUT
from sys import stdout

from command_generator import generate_ffmpeg_command
from config import LOG_LOCATION, LOG_DATE_FORMAT, LOG_MESSAGE_FORMAT
from filechecker import check_file_ext, check_file
from fileparser import probe_file


def format_bytes(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.2f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} Yi{suffix}"


def calc_ratio(isize, osize):
    return osize / isize


parser = argparse.ArgumentParser(description="Video re-encoder with ffmpeg")
parser.add_argument('path', type=Path, help='path to video content')
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
contentPath: Path = args.path

if contentPath.is_file():
    contentType = ContentType.FILE
    logging.debug("File detected")

elif contentPath.is_dir():
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
    is_valid, ext = check_file_ext(contentPath.name)
    if not is_valid:
        logging.error('Extension "%s" not in whitelist', ext)
        sys.exit(3)

    files = [contentPath]
else:
    # Search for files in the directory and all subdirectories matching the whitelisted extensions
    directories_count: int = 0
    files_count: int = 0
    files = []
    for root, _, filenames in contentPath.walk():
        directories_count += 1
        files_count += len(filenames)
        logging.debug('Scanned %s directories and %s files', directories_count, files_count)
        for filename in filenames:
            is_valid, ext = check_file_ext(filename)
            if is_valid:
                files.append(Path(root, filename))
            else:
                # TODO: Count extensions to display a summary at the end
                logging.info('Extension "%s" not in whitelist, skipping', ext)

for i, input_filename in enumerate(files, start=1):
    logging.info('[%d/%d] Processing "%s"', i, len(files), input_filename)

    file_metadata = probe_file(input_filename)
    if file_metadata is None:
        logging.info('Skipping')
        continue

    errors = check_file(file_metadata)
    output_filename = Path(input_filename.parent, f"{input_filename.stem}_reencoded.mp4")
    if output_filename.exists():
        logging.warning('Output file "%s" already exists, skipping', output_filename)
        continue
    cmd = generate_ffmpeg_command(input_filename, output_filename, file_metadata, errors)

    logging.debug(file_metadata)
    logging.info(errors)
    logging.debug(cmd)

    if not errors:
        logging.info('Video matches expectations, skipping')
        continue

    if is_dry_run_enabled:
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
                output_filename.unlink()

            if is_interrupted:
                logging.info('Interrupted')
                break
            continue

        in_size = file_metadata.file_size
        out_size = output_filename.stat().st_size

        logging.info('%s -> %s (ratio: %.2fx) (saved: %s)',
                     format_bytes(in_size), format_bytes(out_size),
                     calc_ratio(in_size, out_size), format_bytes(in_size - out_size))

        if is_replace_enabled:
            logging.info('Replacing "%s"', input_filename)
            # Replace the original file but keep the new extension
            rename(output_filename, Path(input_filename).with_suffix(output_filename.suffix))
            input_filename.unlink()
        elif is_remove_enabled:
            logging.info('Removing "%s"', input_filename)
            # Remove the original file
            input_filename.unlink()
