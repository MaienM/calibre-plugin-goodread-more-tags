#!/usr/bin/env sh

find . -type f -name '*.pyc' -delete
find . -type d -name '__pycache__' -delete
rm -rf ./.pytest_cache/
rm .coverage
