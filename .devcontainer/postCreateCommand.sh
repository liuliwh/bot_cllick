#!/usr/bin/env sh
pip install --upgrade pip
pip install --user -r requirements/dev.txt
pip install --user -e .
pre-commit install
