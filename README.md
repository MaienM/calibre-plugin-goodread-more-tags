# Goodreads More Tags

This plugin scrapes the shelves page of Goodreads to provide more tags than the top 4 (which are shown on the main page
and scraped by the Goodreads plugin).

This plugin will only provide tags. It is meant to be used as a companion to the
[Goodreads plugin](https://www.mobileread.com/forums/showthread.php?t=130638), and it is essentially an extended version
of the genre -> tag mapping included in that plugin.

## Main Features

- Can retrieve the shelves page of Goodreads to provide more tags.
- Customizable mapping from shelf name -> tags. A shelf can be mapped to multiple tags, and multiple shelves can map to the same tag(s).
- Fine-grained filtering to only keep tags that enough people agree on.
- Integrates with the Goodreads plugin to provide tags for all of its results.

## Special Notes

- Requires Calibre 0.8 or later.
- If used without the base Goodreads plugin, it will only get tags for books that have a Goodreads identifier.

## Installation Notes

- Download the attached zip file and install the plugin as described in the [Introduction to plugins thread](https://www.mobileread.com/forums/showthread.php?t=118680).
- Note that this is not a GUI plugin so it is not intended/cannot be added to context menus/toolbars etc.
- Customize your desired genre -> tag mappings and other options from the metadata download configuration screen. Hover over the ? symbols to get an explanation of what the various options do.

## Version History

<b>Unreleased</b>  
Fixed an error in adding a new shelf to the mapping.

<b>Version 1.2.0</b> - 14 November 2020  
Update to work with Calibre 5/Python 3.  
Speed up the case where the Goodreads plugin is installed but not currently enabled as a metadata source.  
Don't provide any results if the list of tags after mapping + filtering is empty.

<b>Version 1.1.0</b> - 15 December 2019  
Large internal changes that should resolve the problems with hanging/reliability.  
There are now some settings for the integration with the base Goodreads plugin.

<b>Version 1.0.1</b> - 04 August 2019  
Fixed the spelling of threshold.

<b>Version 1.0.0</b> - 04 August 2019  
Initial release.

