#!/usr/bin/env sh

echo '===== Killing running instance ====='
pkill -9 -f calibre

echo '===== Removing old version ====='
calibre-customize -r 'Goodreads More Tags'
echo '===== Installing new version ====='
calibre-customize -b src/goodreads_more_tags

for script in "$@"; do
	echo "===== Running $script ====="
	calibre-debug -e "$script"
done
