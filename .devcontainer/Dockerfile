
FROM python:3.10-bullseye

ARG BROWSER_NAME
ARG BROWSER_VERSION

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get -y install \
    wget xauth xvfb \
    tesseract-ocr scrot \
    python3-xlib python3-tk python3-dev


# all output to terminal to be flushed immediately without buffering
ENV PYTHONUNBUFFERED=1
# Prevents Python from writing out pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Add sudoer into the dev container
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install sudo
RUN adduser appuser &&  \
    echo "appuser:appuser"  | chpasswd && \
    usermod -aG sudo appuser

# Comment out below if you always install through dev container
COPY installer /tmp/installer

# Install browser
# Chrome 88+ versions
# https://www.ubuntuupdates.org/package/google_chrome/stable/main/base/google-chrome-stable
# Chome 88- versions
# https://www.slimjet.com/chrome/google-chrome-old-version.php
RUN if [ "$BROWSER_NAME" = "Chrome" ]; then \
    chmod u+x /tmp/installer/install.chrome.sh \
    && /tmp/installer/install.chrome.sh ${BROWSER_VERSION}; fi

# Firefox
# https://download-installer.cdn.mozilla.net/pub/firefox/releases/
# Only support 60+
RUN if [ "$BROWSER_NAME" = "Firefox" ]; then \
    chmod u+x /tmp/installer/install.firefox.sh \
    && /tmp/installer/install.firefox.sh ${BROWSER_VERSION}; fi


