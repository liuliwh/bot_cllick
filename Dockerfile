FROM python:3.10-bullseye AS runtime

ARG BROWSER_NAME
ARG BROWSER_VERSION

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get -y install \
    wget xauth xvfb \
    tesseract-ocr scrot \
    python3-xlib python3-tk python3-dev

RUN mkdir /app /tmp/installer

# Runtime
COPY bot_click /app/bot_click/
COPY examples /app/examples/
COPY setup* /app

# Installer related
COPY requirements/prod.txt installer /tmp/installer

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app

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


# Install pip deps as non-root user
USER appuser
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install --user -r /tmp/installer/prod.txt
RUN pip install --user /app

CMD ["python3", "examples/test_browser_standalone.py"]
