import logging
import math
import re
from datetime import timedelta
from os import makedirs, replace
from pathlib import Path
from subprocess import Popen, PIPE, STDOUT
from typing import Optional

from tqdm import tqdm

from app import App
from colorized_logger import PROGRESS, SKIP, DESTRUCTIVE, ROLLBACK
from command_generator import generate_ffmpeg_command
from filechecker import check_file
from fileparser import probe_file

logger = logging.getLogger('reencode_job.worker')
p_duration = re.compile(r"Duration: (?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})")
p_time = re.compile(r"time=(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})")


def safe_log(num: float, base: int):
    if num == 0:
        return num
    return math.log(math.fabs(num), base)


def format_float(num: float) -> str:
    digits = safe_log(num, 10)
    if digits >= 2:
        return str(int(num))

    if digits >= 1:
        return f"{num:0.1f}"

    return f"{num:0.2f}"


def format_bytes(num: int, suffix: str = "B"):
    units = ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi")
    unit_index = int(safe_log(num, 1024))
    value = num / pow(1024, unit_index)

    if unit_index >= len(units):
        return f"{format_float(value)} Yi{suffix}"
    return f"{format_float(value)} {units[unit_index]}{suffix}"


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

        self._input_duration: Optional[int] = None
        self._next_log = 0
        self._progress: Optional[tqdm] = None

    def __handle_ffmpeg_output(self, line: str):
        if not self._input_duration and (m := p_duration.search(line)):
            self._input_duration = timedelta(hours=int(m['hour']),
                                             minutes=int(m['min']),
                                             seconds=int(m['sec']),
                                             milliseconds=int(m['ms'])).total_seconds()
            self._progress = tqdm(total=self._input_duration,
                                  desc=self.input_filename.name,
                                  unit='sec',
                                  leave=False)

        if self._progress and (m := p_time.search(line)):
            out_time = timedelta(hours=int(m['hour']),
                                 minutes=int(m['min']),
                                 seconds=int(m['sec']),
                                 milliseconds=int(m['ms'])).total_seconds()
            self._progress.update(out_time - self._progress.n)

            progress = out_time / self._input_duration
            time_remaining = self._input_duration - out_time
            if progress * 10 >= self._next_log:
                logger.log(PROGRESS, "%d secs | %.2f%%", time_remaining, progress * 100)
                self._next_log = int(progress * 10) + 1

    def work(self):
        logger.log(PROGRESS, '[%d/%d] Processing "%s"', self.i, len(self.app.files), self.input_filename)

        file_metadata = probe_file(self.input_filename)
        if file_metadata is None:
            logger.log(SKIP, 'Skipping')
            return

        errors = check_file(file_metadata)
        if self.output_filename.exists() and self.app.args.is_overwrite_enabled:
            logger.log(DESTRUCTIVE, 'Overwriting "%s"', self.output_filename)
        elif self.output_filename.exists():
            logger.log(SKIP, 'Output file "%s" already exists, skipping', self.output_filename)
            return
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
            logger.log(SKIP, 'Video matches expectations, skipping')
            return

        if not self.app.args.is_dry_run_enabled:
            with Popen(cmd, stdout=PIPE, stderr=STDOUT, universal_newlines=True) as ffmpeg:
                while not self.app.is_interrupted and ffmpeg.poll() is None:
                    for line in ffmpeg.stdout:
                        logger.debug("[FFMPEG] %s", line.rstrip())
                        self.__handle_ffmpeg_output(line)
                    if self.app.is_interrupted:
                        logger.info("Sending termination signal to ffmpeg subprocess")
                        ffmpeg.terminate()

                if ffmpeg.wait() != 0:
                    logger.error('Failed to process "%s": return code was %d',
                                 self.input_filename, ffmpeg.returncode)
                    if self.app.args.is_clean_on_error_enabled:
                        logger.log(ROLLBACK, 'Removing job leftover "%s"', self.output_filename)
                        self.output_filename.unlink()

                    if self.app.is_interrupted:
                        logger.log(SKIP, 'Interrupted')
                    return

            in_size = file_metadata.file_size
            out_size = self.output_filename.stat().st_size

            logger.info('%s -> %s (ratio: %.2fx) (saved: %s)',
                        format_bytes(in_size), format_bytes(out_size),
                        calc_ratio(in_size, out_size), format_bytes(in_size - out_size))

            self._cleanup()

    def _cleanup(self):
        if self._progress:
            self._progress.close()

        if self.app.args.is_replace_enabled:
            logger.log(DESTRUCTIVE, 'Replacing "%s"', self.input_filename)
            # Replace the original file but keep the new extension
            new_name = Path(self.input_filename).with_suffix(self.output_filename.suffix)
            if not self.app.args.is_dry_run_enabled:
                try:
                    replace(self.output_filename, new_name)
                    if self.input_filename != new_name:
                        logger.log(DESTRUCTIVE, 'Extension has changed, removing original file')
                        self.input_filename.unlink()
                except OSError as e:
                    known_errors = {5}  # Access denied
                    logger.log(SKIP, 'Failed to replace "%s" with "%s"', self.input_filename, new_name, exc_info=e.winerror not in known_errors)
        elif self.app.args.is_remove_enabled:
            logger.log(DESTRUCTIVE, 'Removing "%s"', self.input_filename)
            # Remove the original file
            if not self.app.args.is_dry_run_enabled:
                self.input_filename.unlink()
