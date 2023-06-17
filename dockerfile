FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    tzdata git vim python3 \
    make curl wget libpq-dev \
    python3-dev gcc ffmpeg libsm6 \
    libxext6 postgresql ghostscript \
    sudo tmux postgresql python-is-python3 \
    gunicorn nginx jq
RUN curl -Lo /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py
RUN python /tmp/get-pip.py && pip3 install \
    flask opencv-python Pillow psycopg2 xlsxwriter
WORKDIR /data
COPY simple_web /data/
COPY ./entrypoint.sh /entrypoint.sh
ENTRYPOINT [ "bash", "/entrypoint.sh" ]
