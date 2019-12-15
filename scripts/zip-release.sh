#!/usr/bin/env sh

rm Goodreads.More.Tags.zip
(
	set -e
	cd src/goodreads_more_tags
	zip ../../Goodreads.More.Tags.zip -r . --exclude '*.pyc'
)
