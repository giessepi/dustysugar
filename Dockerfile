FROM debian:bullseye-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl gnupg ca-certificates sbcl make git wget unzip libsqlite3-dev libpq-dev \
        && rm -rf /var/lib/apt/lists/*

RUN curl -L -o pgloader.zip https://github.com/dimitri/pgloader/archive/refs/tags/v3.6.7.zip && \
    unzip pgloader.zip && \
    cd pgloader-3.6.7 && \
    make && make install && \
    cd .. && rm -rf pgloader*

ENTRYPOINT ["pgloader"]
