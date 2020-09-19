# FROM [--platform=<platform>] <image>[:<tag>] [AS <name>]
FROM debian:buster-slim
LABEL maintainer="noone"

ENV DEBIAN_FRONTEND noninteractive
ENV LANG C.UTF-8

# Default versions
ENV INFLUXDB_VERSION=1.8.2
ENV CHRONOGRAF_VERSION=1.8.6
ENV GRAFANA_VERSION=7.1.5

# Grafana database type
ENV GF_DATABASE_TYPE=sqlite3

# Fix bad proxy issue
# COPY system/99fixbadproxy /etc/apt/apt.conf.d/99fixbadproxy

WORKDIR /root

SHELL ["/bin/bash", "-c"] 
COPY build.sh build.sh
RUN bash build.sh

# Configure Supervisord and base env
COPY supervisord/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY bash/profile .profile

# Configure InfluxDB
COPY influxdb/influxdb.conf /etc/influxdb/influxdb.conf

# Configure Grafana
COPY grafana/grafana.ini /etc/grafana/grafana.ini

COPY adapter/weatherpi.py /root/weatherpi.py

COPY run.sh /run.sh
RUN ["chmod", "+x", "/run.sh"]
CMD ["/run.sh"]
