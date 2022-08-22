#!/usr/bin/env sh

# exit when any command fails
set -e

# debug purpose
set -x

if [ $# -eq 0 ] ; then
    echo "usage: ${0} full_version."
    exit 1
fi

# Install dependencies for legacy, google-chrome legacy depends on
# libcurl3 and libssl which are conflicts with libcur4, manual install
# libappindicator1 and libindicator7, manual install
legacy_deps () {
    for dep in "http://security.debian.org/debian-security/pool/updates/main/o/openssl1.0/libssl1.0.2_1.0.2u-1~deb9u7_amd64.deb" \
     "http://security.debian.org/debian-security/pool/updates/main/c/curl/libcurl3_7.52.1-5+deb9u16_amd64.deb" \
     "http://ftp.us.debian.org/debian/pool/main/libi/libindicator/libindicator7_0.5.0-4_amd64.deb" \
     "http://ftp.us.debian.org/debian/pool/main/liba/libappindicator/libappindicator1_0.4.92-7_amd64.deb" ; do
        SAVE=/tmp/dep.deb
        wget -O ${SAVE} ${dep}
        DEBIAN_FRONTEND=noninteractive apt-get install -yf ${SAVE}
        rm ${SAVE}
    done
}

# Download and Install Chrome
download_install_chrome () {
    if [ $2 -ge 88 ]; then
        DOWNLOAD=https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_$1_amd64.deb
    else
        DOWNLOAD=https://www.slimjetbrowser.com/chrome/lnx/chrome64_$1.deb
    fi
    wget  -O /tmp/$1.deb ${DOWNLOAD}
    DEBIAN_FRONTEND=noninteractive apt-get install -yf /tmp/$1.deb
    rm /tmp/$1.deb
}

BASEDIR=$(dirname $0)
VERSION=$(echo "$1" | awk -F. '{ print $1 }')

apt-get update

# Install deps for legacy browser
[ $VERSION -lt 88 ] && legacy_deps


# Turn off browser and component update
# https://support.google.com/chrome/a/answer/9052345?hl=en#zippy=%2Cstep-turn-off-chrome-browser-updates%2Cstep-turn-off-chrome-browser-component-updates-optional
cp ${BASEDIR}/browser_config/chrome/google-chrome /etc/default/

download_install_chrome $1 $VERSION

# Apply policies
mkdir -p /opt/google/chrome/policies/managed
cp ${BASEDIR}/browser_config/chrome/policies.json /opt/google/chrome/policies/managed/

# Markhold
apt-mark hold google-chrome-stable