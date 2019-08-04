#!/usr/bin/env sh

# Kill running instance.
echo '===== Killing running instance ====='
pkill -9 -f calibre

# Reinstall the plugin.
echo '===== Removing old version ====='
calibre-customize -r 'Goodreads More Tags'
echo '===== Installing new version ====='
calibre-customize -b src/goodreads_more_tags

# Run the passed script(s).
for script in "$@"; do
	echo "===== Running $script ====="
	calibre-debug -e "$script"
done
