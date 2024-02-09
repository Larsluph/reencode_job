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

## Requirements

- Python 3.12+
- ffmpeg

## Installation

Everything in this project only uses core python library, no dependencies needed!

```sh
git clone git@github.com:Larsluph/reencode_job.git
cd reencode_job
```

## Running

### From source

```sh
python3 main.py [-h] [-d] path
```

### Using docker

You'll need a docker image with python 3.12 and ffmpeg installed.

For practical reasons, a Dockerfile is available to build such image:

```sh
docker build -t python-ffmpeg .
```

Once you have a valid docker image (either the one built or another with both requirements fulfilled), you can run the project.

Make sure to update both volume mounts to match your environment:

| Volume mount | Description         |
|--------------|---------------------|
| `/app`       | Project source code |
| `/data`      | Videos directory    |

#### Docker run command

```sh
docker run\
 --privileged\
 --name reencode_job\
 -v "/home/larsluph/reencode_job:/app"\
 -v "/home/larsluph/videos:/data"\
 python-ffmpeg\
 python3 /app/main.py /data
```

#### Docker compose file

```yml
version: '3.8'
services:
  reencode_job:
    image: python-ffmpeg
    container_name: reencode_job
    privileged: true
    volumes:
      - /home/larsluph/reencode_job:/app
      - /home/larsluph/videos:/data
    command: ['python3', '/app/main.py', '/data']

```
