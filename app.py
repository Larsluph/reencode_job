import logging
import sys
from argparse import Namespace
from collections import Counter
from pathlib import Path

from filechecker import check_file_ext

logger = logging.getLogger('reencode_job.app')

class App:
    content_path: Path
    is_dry_run_enabled: bool
    is_remove_enabled: bool
    is_replace_enabled: bool
    is_clean_on_error_enabled: bool
    is_filelist_enabled: bool

    is_interrupted: bool
    files: list[Path]

    def __init__(self, args: Namespace):
        logger.info('Starting new job with params: %s', args)

        self.content_path = args.path
        self.is_dry_run_enabled = args.dry_run
        self.is_remove_enabled = args.remove
        self.is_replace_enabled = args.replace
        self.is_clean_on_error_enabled = args.clean_on_error
        self.is_filelist_enabled = args.filelist
        self.is_interrupted = False
        self.files = []

    def signal_handler(self, signum, _):
        self.is_interrupted = True
        logger.warning('Interrupted by signal %d', signum)

    def _log_ext_summary(self, ext_summary: Counter):
        if ext_summary:
            logger.info('Skipped extensions:\n%s',
                        '\n'.join(map(lambda x: f'{x[0]} -> {x[1]}',
                                        ext_summary.most_common())))

    def _scan_file(self):
        is_valid, ext = check_file_ext(self.content_path.name)
        if not is_valid:
            logger.error('Extension "%s" not in whitelist', ext)
            sys.exit(3)

        self.files.append(self.content_path)

    def _scan_filelist(self):
        ext_summary = Counter()

        with self.content_path.open() as filelist:
            for line in filelist:
                file_path = Path(line.strip())
                if not file_path.exists():
                    logger.warning('File "%s" does not exist', file_path)
                    continue

                is_valid, ext = check_file_ext(file_path)
                if is_valid:
                    self.files.append(file_path)
                else:
                    ext_summary.update((ext,))
        self._log_ext_summary(ext_summary)

    def _scan_directory(self):
        directories_count: int = 0
        files_count: int = 0
        ext_summary = Counter()

        for root, _, filenames in self.content_path.walk():
            directories_count += 1
            files_count += len(filenames)
            for filename in filenames:
                is_valid, ext = check_file_ext(filename)
                if is_valid:
                    self.files.append(Path(root, filename))
                else:
                    ext_summary.update((ext,))
            logger.debug('Scanned %s directories and %s files', directories_count, files_count)
        self._log_ext_summary(ext_summary)

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
