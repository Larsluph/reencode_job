import logging
import sys
from argparse import Namespace
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TextIO
from io import TextIOWrapper

from filechecker import check_file_ext

logger = logging.getLogger('reencode_job.app')


@dataclass
class Args:
    "App arguments parsed by argparse"
    content_path: Path
    output_path: Optional[Path]
    is_dry_run_enabled: bool
    is_remove_enabled: bool
    is_replace_enabled: bool
    is_overwrite_enabled: bool
    is_clean_on_error_enabled: bool
    is_filelist_enabled: bool


class App:
    "App class contains all appdata necessary for the job"
    args: Args

    is_interrupted: bool
    glob_filter: Optional[str]
    files: list[Path]
    outs: list[Path]

    def __init__(self, args: Namespace):
        logger.info('Starting new job with params: %s', args)

        self.args = Args(args.path,
                         args.output,
                         args.dry_run,
                         args.remove,
                         args.replace,
                         args.overwrite,
                         args.clean_on_error,
                         args.filelist)

        self.glob_filter = args.filter
        self.is_interrupted = False
        self.files = []
        self.outs = []

    def signal_handler(self, signum, _):
        self.is_interrupted = True
        logger.warning('Interrupted by signal %d', signum)

    def _log_ext_summary(self, ext_summary: Counter):
        if ext_summary:
            logger.info('Skipped extensions:\n%s',
                        '\n'.join(map(lambda x: f'{x[0]} -> {x[1]}',
                                      ext_summary.most_common())))

    def _scan_file(self):
        is_valid, ext = check_file_ext(self.args.content_path)
        if not is_valid:
            logger.error('Extension "%s" not in whitelist', ext)
            sys.exit(3)

        self.files.append(self.args.content_path)
        if self.args.output_path:
            self.outs.append(self.args.output_path)
        else:
            self.outs.append(Path(self.args.content_path.parent,
                                  f"{self.args.content_path.stem}_reencoded.mp4"))

    def _scan_filelist(self):
        ext_summary = Counter()
        with self.args.content_path.open(encoding='ascii') as filelist:
            if self.args.output_path:
                self.__scan_filelist_inout(filelist, ext_summary)
            else:
                self.__scan_filelist_in(filelist, ext_summary)

        self._log_ext_summary(ext_summary)

    def __scan_filelist_in(self, filelist: TextIO, ext_summary: Counter):
        for line in filelist:
            file_path = Path(line.strip())
            if not file_path.exists():
                logger.warning('File "%s" does not exist', file_path)
                continue

            is_valid, ext = check_file_ext(file_path)
            if is_valid:
                self.files.append(file_path)
                self.outs.append(Path(file_path.parent,
                                      f"{file_path.stem}_reencoded.mp4"))
            else:
                ext_summary.update((ext,))

    def __scan_filelist_inout(self, filelist: TextIO, ext_summary: Counter):
        for i, line in enumerate(filelist):
            file_path = Path(line.strip())

            if i % 2 == 0:
                # Read input file
                if not file_path.exists():
                    logger.warning('File "%s" does not exist', file_path)
                    continue

                is_valid, ext = check_file_ext(file_path)
                if is_valid:
                    self.files.append(file_path)
                else:
                    ext_summary.update((ext,))
            else:
                # Read output file
                self.outs.append(file_path)

    def _scan_directory(self):
        if self.glob_filter:
            self.__scan_glob()
        else:
            self.__scan_walk()

    def __scan_glob(self):
        files_count: int = 0
        ext_summary = Counter()
        logger.debug("Discovering files")
        for filename in self.args.content_path.glob(self.glob_filter):
            files_count += 1
            if not self._process_file(filename):
                ext_summary.update((filename.suffix,))
        logger.debug('Scanned %d files', files_count)
        self._log_ext_summary(ext_summary)

    def __scan_walk(self):
        directories_count: int = 0
        files_count: int = 0
        ext_summary = Counter()

        for root, _, filenames in self.args.content_path.walk():
            directories_count += 1
            files_count += len(filenames)
            for filename in filenames:
                fname = Path(root, filename)
                if not self._process_file(fname):
                    ext_summary.update((fname.suffix,))
            logger.debug('Scanned %s directories and %s files',
                         directories_count, files_count)
        self._log_ext_summary(ext_summary)

    def _process_file(self, filename: Path):
        is_valid, _ = check_file_ext(filename)
        if not is_valid:
            return False

        self.files.append(filename)
        if self.args.output_path:
            self.outs.append(
                self.args.output_path /
                filename.relative_to(self.args.content_path)
            )
        else:
            self.outs.append(Path(filename.parent,
                                  f"{filename.stem}_reencoded.mp4"))
        return True

    def init_job(self):
        # Check if dry run flag is set
        if self.args.is_dry_run_enabled:
            logger.info("Dry run enabled")

        self.files.clear()

        if self.args.content_path.is_file() and self.args.is_filelist_enabled:
            self._scan_filelist()
        elif self.args.content_path.is_file():
            self._scan_file()
        else:
            self._scan_directory()
            self.files.sort()
