import logging
import sys
from argparse import ArgumentParser, Namespace
from datetime import datetime
from os import rename
from os.path import join
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


class App:
    content_path: Path
    is_dry_run_enabled: bool
    is_remove_enabled: bool
    is_replace_enabled: bool
    is_clean_on_error_enabled: bool
    is_interrupted: bool
    files: list[Path]

    def __init__(self, args: Namespace):
        logging.info('Starting new job with params: %s', args)

        self.content_path = args.path
        self.is_dry_run_enabled = args.dry_run
        self.is_remove_enabled = args.remove
        self.is_replace_enabled = args.replace
        self.is_clean_on_error_enabled = args.clean_on_error
        self.is_interrupted = False

    def handler(self, signum, _):
        self.is_interrupted = True
        logging.warning('Interrupted by signal %d', signum)

    def init_job(self):
        # Check if dry run flag is set
        if self.is_dry_run_enabled:
            logging.info("Dry run enabled")

        if self.content_path.is_file():
            is_valid, ext = check_file_ext(self.content_path.name)
            if not is_valid:
                logging.error('Extension "%s" not in whitelist', ext)
                sys.exit(3)

            self.files = [self.content_path]
        else:
            directories_count: int = 0
            files_count: int = 0
            self.files = []
            for root, _, filenames in self.content_path.walk():
                directories_count += 1
                files_count += len(filenames)
                logging.debug('Scanned %s directories and %s files', directories_count, files_count)
                for filename in filenames:
                    is_valid, ext = check_file_ext(filename)
                    if is_valid:
                        self.files.append(Path(root, filename))
                    else:
                        # TODO: Count extensions to display a summary at the end
                        logging.info('Extension "%s" not in whitelist, skipping', ext)

    def run_job(self):
        signal(SIGINT, self.handler)
        signal(SIGTERM, self.handler)

        for i, input_filename in enumerate(self.files, start=1):
            logging.info('[%d/%d] Processing "%s"', i, len(self.files), input_filename)

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

            if self.is_dry_run_enabled:
                continue

            with Popen(cmd, stdout=PIPE, stderr=STDOUT, universal_newlines=True) as process:
                for line in process.stdout:
                    logging.debug(line.rstrip())
                    if self.is_interrupted:
                        process.terminate()
                        break

                if process.wait() != 0:
                    logging.error('Failed to process "%s": return code was %d',
                                input_filename, process.returncode)
                    if self.is_clean_on_error_enabled:
                        logging.info('Removing failed "%s"', output_filename)
                        output_filename.unlink()

                    if self.is_interrupted:
                        logging.info('Interrupted')
                        break
                    continue

                in_size = file_metadata.file_size
                out_size = output_filename.stat().st_size

                logging.info('%s -> %s (ratio: %.2fx) (saved: %s)',
                            format_bytes(in_size), format_bytes(out_size),
                            calc_ratio(in_size, out_size), format_bytes(in_size - out_size))

                if self.is_replace_enabled:
                    logging.info('Replacing "%s"', input_filename)
                    # Replace the original file but keep the new extension
                    rename(output_filename, Path(input_filename).with_suffix(output_filename.suffix))
                    input_filename.unlink()
                elif self.is_remove_enabled:
                    logging.info('Removing "%s"', input_filename)
                    # Remove the original file
                    input_filename.unlink()


if __name__ == '__main__':
    parser = ArgumentParser(description="Video re-encoder with ffmpeg")
    parser.add_argument('path', type=Path, help='path to video content')
    parser.add_argument('-d', '--dry-run', action='store_true',
                        help='perform a trial run without changes made')
    parser.add_argument('-rm', '--remove', action='store_true',
                        help='remove original content after processing')
    parser.add_argument('--replace', action='store_true',
                        help='replace original content with the processed one')
    parser.add_argument('--clean-on-error', action='store_true',
                        help='remove processed content if an error occurs')
    app = App(parser.parse_args())

    fh = logging.FileHandler(join(LOG_LOCATION,
                                datetime.now().strftime(LOG_DATE_FORMAT)))
    fh.setLevel(logging.DEBUG)
    sh = logging.StreamHandler(stdout)
    sh.setLevel(logging.INFO)
    logging.basicConfig(level=logging.DEBUG,
                        format=LOG_MESSAGE_FORMAT,
                        handlers=(fh, sh))

    app.init_job()
    app.run_job()
