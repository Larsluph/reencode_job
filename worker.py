import logging
from os import rename, makedirs
from pathlib import Path
from subprocess import Popen, PIPE, TimeoutExpired

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
    """Worker class that processes a file"""
    app: App
    i: int
    max_i: int
    input_filename: Path
    output_filename: Path
    process: Popen = None

    def __init__(self, app: App, i: int, input_filename: Path, output_filename: Path):
        self.app = app
        self.i = i
        self.input_filename = input_filename
        self.output_filename = output_filename

    def work(self) -> bool:
        logger.info('[%d/%d] Processing "%s"', self.i, len(self.app.files), self.input_filename)

        file_metadata = probe_file(self.input_filename)
        if file_metadata is None:
            logger.info('Skipping')
            return True

        errors = check_file(file_metadata)
        if self.output_filename.exists():
            logger.warning('Output file "%s" already exists, skipping', self.output_filename)
            return True
        elif not (parent := self.output_filename.parent).exists():
            makedirs(parent)
        cmd = generate_ffmpeg_command(self.input_filename,
                                      self.output_filename,
                                      file_metadata,
                                      errors)

        logger.debug(file_metadata)
        logger.info(errors)
        logger.debug(cmd)

        if not errors:
            logger.info('Video matches expectations, skipping')
            return True

        if not self.app.is_dry_run_enabled:
            with Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True) as self.process:
                while not self.app.is_interrupted and self.process.poll() is not None:
                    try:
                        outs, errs = self.process.communicate(timeout=1)
                        for line in outs.split():
                            logger.debug(line.rstrip())
                        for line in errs.split():
                            logger.error(line.rstrip())
                    except TimeoutExpired:
                        pass

                    if self.app.is_interrupted:
                        self.process.terminate()

                if self.process.wait() != 0:
                    logger.error('Failed to process "%s": return code was %d',
                                self.input_filename, self.process.returncode)
                    if self.app.is_clean_on_error_enabled:
                        logger.info('Removing failed "%s"', self.output_filename)
                        self.output_filename.unlink()

                    if self.app.is_interrupted:
                        logger.info('Interrupted')
                        return False
                    return True

            in_size = file_metadata.file_size
            out_size = self.output_filename.stat().st_size

            logger.info('%s -> %s (ratio: %.2fx) (saved: %s)',
                        format_bytes(in_size), format_bytes(out_size),
                        calc_ratio(in_size, out_size), format_bytes(in_size - out_size))

        return True

    def terminate_job(self):
        if self.process is not None:
            self.process.terminate()
            return self.process.poll()
        return None

    def _cleanup(self):
        if self.app.is_replace_enabled:
            logger.info('Replacing "%s"', self.input_filename)
            # Replace the original file but keep the new extension
            new_name = Path(self.input_filename).with_suffix(self.output_filename.suffix)
            if not self.app.is_dry_run_enabled:
                rename(self.output_filename, new_name)
                if self.input_filename != new_name:
                    self.input_filename.unlink()
        elif self.app.is_remove_enabled:
            logger.info('Removing "%s"', self.input_filename)
            # Remove the original file
            if not self.app.is_dry_run_enabled:
                self.input_filename.unlink()
