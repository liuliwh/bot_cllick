#!/usr/bin/env sh

# exit when any command fails
set -e

# debug purpose
set -x

if [ $# -eq 0 ] ; then
    echo "usage: ${0} full_version."
    exit 1
fi

# Download and Install Chrome
# https://www.ubuntuupdates.org/package/google_chrome/stable/main/base/google-chrome-stable
# https://stackoverflow.com/questions/52217175/any-way-to-install-specific-older-chrome-BROWSER_NAME-version
download_install_ff () {
    DOWNLOAD=https://download-installer.cdn.mozilla.net/pub/firefox/releases/$1/linux-x86_64/en-US/firefox-$1.tar.bz2
    wget  -O /tmp/$1.tar.bz2 ${DOWNLOAD}
    tar -C /opt -xjf /tmp/$1.tar.bz2
    rm /tmp/$1.tar.bz2
    ln -fs /opt/firefox/firefox /usr/bin/firefox
}

BASEDIR=$(dirname $0)
VERSION=$(echo "$1" | awk -F. '{ print $1 }')

[ $VERSION -lt 60 ] && echo "FF only support 60+,exit.." && exit 1

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get -yf install libgtk-3-0 libasound2 libdbus-glib-1-2

download_install_ff $1

# Disable appupdate for firefix, default browser check
# https://github.com/mozilla/policy-templates/blob/master/README.md#disableappupdate
# https://gist.github.com/stephenharris/90bb468bf80e7f7b02e8b8afe694de4f
cp ${BASEDIR}/browser_config/firefox/defaults/pref/channel-prefs.js /opt/firefox/defaults/pref/channel-prefs.js
# Apply policies
mkdir /opt/firefox/distribution
cp ${BASEDIR}/browser_config/firefox/distribution/policies.json /opt/firefox/distribution/
