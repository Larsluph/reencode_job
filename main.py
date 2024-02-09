import argparse
import sys
from enum import Enum
from os import walk
from os.path import isfile, isdir, join, splitext
from pprint import pprint
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

# Parse the arguments
args = parser.parse_args()


class ContentType(Enum):
    FILE = 1
    DIRECTORY = 2


contentType: ContentType
contentPath = args.path

if isfile(contentPath):
    contentType = ContentType.FILE
    print("File detected")

elif isdir(contentPath):
    contentType = ContentType.DIRECTORY
    print("Directory detected")

else:
    print("Unknown content type")
    sys.exit(2)

is_dry_run = args.dry_run

# Check if dry run flag is set
if is_dry_run:
    print("Dry run enabled")

if contentType == ContentType.FILE:
    if not check_file_ext(contentPath):
        print("File extension not in whitelist")
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
        print(
            f'\rScanned {directories_count} directories and {files_count} files', end='')
        files.extend(join(root, filename) for filename in filenames if check_file_ext(filename))
    print()

for file in files:
    print(f'Processing {file}')

    file_metadata = probe_file(file)
    errors = check_file(file_metadata)
    name, ext = splitext(file)
    cmd = generate_ffmpeg_command(file, f"{name}_reencoded.mp4", file_metadata, errors)

    pprint(file_metadata)
    pprint(errors)
    print(cmd)

    if is_dry_run:
        continue

    with Popen(cmd, stdout=PIPE, stderr=STDOUT, universal_newlines=True) as process:
        for line in process.stdout:
            stdout.write(line)
