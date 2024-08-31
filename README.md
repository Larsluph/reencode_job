# reencode_job

This project aims at providing an automated way to reencode video based on static criterias:

- Audio
  - Codec
  - Sample rate
  - Channel count
  - Bitrate
- Video
  - Codec
  - Resolution
  - FPS

```txt
usage: main.py [-h] [-o OUTPUT] [--overwrite] [--filter FILTER] [-f] [-d] [-rm] [--replace] [--clean-on-error] path

Video re-encoder with ffmpeg

positional arguments:
  path                  path to video content

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        path to output content
  --overwrite           Replace output if it already exists
  --filter FILTER       glob pattern to filter input files to process
  -f, --filelist        path is a file with a list of files to process, if OUTPUT is specified the file list should be composed of alternating lines of input and output filenames
  -d, --dry-run         perform a trial run without changes made
  -rm, --remove         remove original content after processing
  --replace             replace original content with the processed one
  --clean-on-error      remove processed content if an error occurs
```

## Requirements

- Python 3.12+
- ffmpeg

## Installation

Everything in this project only uses core python library, no dependencies needed!

```sh
git clone git@github.com:Larsluph/reencode_job.git
cd reencode_job
```

> [!IMPORTANT]
> To ensure correct log level is applied to tqdm's redirected logger, you have to edit the tqdm files directly.
> See [PR](https://github.com/tqdm/tqdm/pull/1333) for changes.

## Configuration

Everything is configurable from the `config.py` file.

## Running

### From source

```sh
python3 main.py [-h] [-d] [-rm] [--replace] [--clean-on-error] path
```

### Using docker

```sh
docker pull ghcr.io/larsluph/reencode_job
```

Make sure to use valid volume mounts to run the job:

| Volume mount     | Description                    |
|------------------|--------------------------------|
| `/app/config.py` | Project configuration override |
| `/app/logs`      | Logs directory (by default)    |
| `/app/lock`      | Locks directory (by default)   |

All default paths can be changed in the configuration override.

Don't forget to also mount your data directory containing every files you want to run the job on.

#### Docker run command

```sh
docker run\
 --privileged\
 --name reencode_job\
 -v "/home/larsluph/videos:/data"\
 ghcr.io/larsluph/reencode_job\
 /data
```

#### Docker compose file

```yml
services:
  reencode_job:
    image: ghcr.io/larsluph/reencode_job
    container_name: reencode_job
    privileged: true
    volumes:
      - /home/larsluph/videos:/data
    command: ['/data']
```
