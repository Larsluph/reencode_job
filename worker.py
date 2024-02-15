import logging
from os import rename
from pathlib import Path
from subprocess import Popen, PIPE, STDOUT

from app import App
from command_generator import generate_ffmpeg_command
from filechecker import check_file
from fileparser import probe_file


logger = logging.getLogger('reencode_job.worker')


def format_bytes(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.2f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} Yi{suffix}"


def calc_ratio(isize, osize):
    return osize / isize


class Worker:
    app: App
    i: int
    max_i: int
    input_filename: Path

    def __init__(self, app, i: int, input_filename: Path):
        self.app = app
        self.i = i
        self.input_filename = input_filename

    def work(self) -> bool:
        logger.info('[%d/%d] Processing "%s"', self.i, len(self.app.files), self.input_filename)

        file_metadata = probe_file(self.input_filename)
        if file_metadata is None:
            logger.info('Skipping')
            return True

        errors = check_file(file_metadata)
        output_filename = Path(self.input_filename.parent,
                               f"{self.input_filename.stem}_reencoded.mp4")
        if output_filename.exists():
            logger.warning('Output file "%s" already exists, skipping', output_filename)
            return True
        cmd = generate_ffmpeg_command(self.input_filename, output_filename, file_metadata, errors)

        logger.debug(file_metadata)
        logger.info(errors)
        logger.debug(cmd)

        if not errors:
            logger.info('Video matches expectations, skipping')
            return True

        if self.app.is_dry_run_enabled:
            return True

        with Popen(cmd, stdout=PIPE, stderr=STDOUT, universal_newlines=True) as process:
            for line in process.stdout:
                logger.debug(line.rstrip())
                if self.app.is_interrupted:
                    process.terminate()
                    return False

            if process.wait() != 0:
                logger.error('Failed to process "%s": return code was %d',
                            self.input_filename, process.returncode)
                if self.app.is_clean_on_error_enabled:
                    logger.info('Removing failed "%s"', output_filename)
                    output_filename.unlink()

                if self.app.is_interrupted:
                    logger.info('Interrupted')
                    return False
                return True

            in_size = file_metadata.file_size
            out_size = output_filename.stat().st_size

            logger.info('%s -> %s (ratio: %.2fx) (saved: %s)',
                        format_bytes(in_size), format_bytes(out_size),
                        calc_ratio(in_size, out_size), format_bytes(in_size - out_size))

            if self.app.is_replace_enabled:
                logger.info('Replacing "%s"', self.input_filename)
                # Replace the original file but keep the new extension
                rename(output_filename,
                       Path(self.input_filename).with_suffix(output_filename.suffix))
                self.input_filename.unlink()
            elif self.app.is_remove_enabled:
                logger.info('Removing "%s"', self.input_filename)
                # Remove the original file
                self.input_filename.unlink()
