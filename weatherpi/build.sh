#!/bin/bash

set -euf 
set -o pipefail
set -o xtrace

rm /var/lib/apt/lists/* -vf

# # Base dependencies
apt-get -y update

#    apt-get -y dist-upgrade
apt-get -y --force-yes install apt-utils ca-certificates curl wget \
    git htop nano gnupg \
    libfontconfig net-tools supervisor \
    python3-minimal


apt-get -y --force-yes install libtool libusb-1.0-0-dev librtlsdr-dev rtl-sdr build-essential autoconf cmake pkg-config

git clone --recursive -b 20.02 https://github.com/sfahnens/rtl_433.git
mkdir -p rtl_433/build
cd rtl_433/build
cmake ..
make -j 16
make install

cd -
rm -rf rtl_433
apt-get -y --force-yes --purge remove build-essential autoconf cmake pkg-config

bash -c "curl -sL https://deb.nodesource.com/setup_10.x | bash -"
apt-get install -y nodejs
mkdir -p /var/log/supervisor
rm -rf .profile

# Install InfluxDB
wget "https://dl.influxdata.com/influxdb/releases/influxdb_${INFLUXDB_VERSION}_armhf.deb"
dpkg -i "influxdb_${INFLUXDB_VERSION}_armhf.deb"
rm influxdb_"${INFLUXDB_VERSION}_armhf.deb"

# Install Chronograf
wget "https://dl.influxdata.com/chronograf/releases/chronograf_${CHRONOGRAF_VERSION}_armhf.deb"
dpkg -i "chronograf_${CHRONOGRAF_VERSION}_armhf.deb"
rm "chronograf_${CHRONOGRAF_VERSION}_armhf.deb"

# Install Grafana
wget "https://dl.grafana.com/oss/release/grafana_${GRAFANA_VERSION}_armhf.deb"
dpkg -i "grafana_${GRAFANA_VERSION}_armhf.deb"
rm "grafana_${GRAFANA_VERSION}_armhf.deb"

# Cleanup
apt-get -y --force-yes autoremove --purge
apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
