FROM python:3.12.2-alpine
RUN apk add ffmpeg tzdata
ENV TZ=Europe/Paris
WORKDIR /app
VOLUME [ "/app", "/data" ]