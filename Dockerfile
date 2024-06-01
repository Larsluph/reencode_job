FROM python:3.12.2-alpine
RUN apk add ffmpeg tzdata
ENV TZ=Europe/Paris
WORKDIR /app
COPY . /app
ENTRYPOINT [ "python3", "/app/main.py" ]