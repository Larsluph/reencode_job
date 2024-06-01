import logging
import sys
from argparse import Namespace
from collections import Counter
from pathlib import Path
from typing import Optional
from io import TextIOWrapper

from filechecker import check_file_ext

logger = logging.getLogger('reencode_job.app')


class App:
    content_path: Path
    output_path: Optional[Path]
    is_dry_run_enabled: bool
    is_remove_enabled: bool
    is_replace_enabled: bool
    is_overwrite_enabled: bool
    is_clean_on_error_enabled: bool
    is_filelist_enabled: bool

    is_interrupted: bool
    glob_filter: Optional[str]
    files: list[Path]
    outs: list[Path]

    def __init__(self, args: Namespace):
        logger.info('Starting new job with params: %s', args)

        self.content_path = args.path
        self.output_path = args.output
        self.glob_filter = args.filter
        self.is_dry_run_enabled = args.dry_run
        self.is_remove_enabled = args.remove
        self.is_replace_enabled = args.replace
        self.is_overwrite_enabled = args.overwrite
        self.is_clean_on_error_enabled = args.clean_on_error
        self.is_filelist_enabled = args.filelist
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
        is_valid, ext = check_file_ext(self.content_path)
        if not is_valid:
            logger.error('Extension "%s" not in whitelist', ext)
            sys.exit(3)

        self.files.append(self.content_path)
        if self.output_path:
            self.outs.append(self.output_path)
        else:
            self.outs.append(Path(self.content_path.parent,
                                  f"{self.content_path.stem}_reencoded.mp4"))

    def _scan_filelist(self):
        ext_summary = Counter()
        with self.content_path.open() as filelist:
            if self.output_path:
                self.__scan_filelist_inout(filelist, ext_summary)
            else:
                self.__scan_filelist_in(filelist, ext_summary)

        self._log_ext_summary(ext_summary)

    def __scan_filelist_in(self, filelist: TextIOWrapper, ext_summary: Counter):
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

    def __scan_filelist_inout(self, filelist: TextIOWrapper, ext_summary: Counter):
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
        for filename in self.content_path.glob(self.glob_filter):
            files_count += 1
            if not self._process_file(filename):
                ext_summary.update((filename.suffix,))
        logger.debug('Scanned %d files', files_count)
        self._log_ext_summary(ext_summary)

    def __scan_walk(self):
        directories_count: int = 0
        files_count: int = 0
        ext_summary = Counter()

        for root, _, filenames in self.content_path.walk():
            directories_count += 1
            files_count += len(filenames)
            for filename in filenames:
                if not self._process_file(Path(root, filename)):
                    ext_summary.update((filename.suffix,))
            logger.debug('Scanned %s directories and %s files',
                         directories_count, files_count)
        self._log_ext_summary(ext_summary)

    def _process_file(self, filename: Path):
        is_valid, _ = check_file_ext(filename)
        if is_valid:
            self.files.append(filename)
            if self.output_path:
                self.outs.append(
                            self.output_path /
                            filename.relative_to(self.content_path)
                        )
            else:
                self.outs.append(Path(filename.parent,
                                      f"{filename.stem}_reencoded.mp4"))
        return is_valid

    def init_job(self):
        # Check if dry run flag is set
        if self.is_dry_run_enabled:
            logger.info("Dry run enabled")

        self.files.clear()

        if self.content_path.is_file() and self.is_filelist_enabled:
            self._scan_filelist()
        elif self.content_path.is_file():
            self._scan_file()
        else:
            self._scan_directory()
            self.files.sort()
