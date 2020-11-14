from __future__ import division
from __future__ import unicode_literals

from collections import Counter
from threading import Thread

from lxml.html import fromstring

from calibre.ebooks.metadata.book.base import Metadata
from calibre.utils.cleantext import clean_ascii_chars

from .config import plugin_prefs, KEY_THRESHOLD_ABSOLUTE, KEY_THRESHOLD_PERCENTAGE, KEY_THRESHOLD_PERCENTAGE_OF, KEY_SHELF_MAPPINGS


__license__ = 'BSD 3-clause'
__copyright__ = '2019, Michon van Dooren <michon1992@gmail.com>'
__docformat__ = 'markdown en'

URL_TEMPLATE = 'https://www.goodreads.com/book/shelves/{identifier}'


class TagList(Counter):
    """ A list of tags with the amount of people that 'voted' for the tag. """
    def apply_threshold(self, threshold):
        """
        Apply a threshold, removing all items with a value below the threshold.

        >>> c = TagList(a = 20, b = 10, c = 5, d = 3, e = 2, f = 1)
        >>> c.apply_threshold(4)
        >>> sorted(c.keys())
        ['a', 'b', 'c']
        >>> c.apply_threshold(10)
        >>> sorted(c.keys())
        ['a', 'b']
        """
        for key, count in list(self.items()):
            if count < threshold:
                del self[key]

    def get_places(self, places):
        """
        Get the items in the given places.

        Like most_common, but doesn't have to be continuous.

        The item in 1st place is the item with the most votes, in 2nd place with the second most votes, and so on. This
        means this is _not_ an index, and there is no such thing as the 0th place.

        If a place is requested that is not present, the result will be None.

        >>> c = TagList(a = 20, b = 10, c = 5, d = 3, e = 2, f = 1)
        >>> c.get_places([1])
        [('a', 20)]
        >>> c.get_places([3, 5])
        [('c', 5), ('e', 2)]
        >>> c.get_places([4, 20])
        [('d', 3), None]
        """
        items = self.most_common(max(places))
        return [items[p - 1] if p <= len(items) else None for p in places]


class Worker(Thread):
    """ Get shelves that a Goodreads book belongs to, and convert these to tags. """

    def __init__(self, plugin, identifier, log = None, result_queue = None, timeout = 30, **data):
        Thread.__init__(self)
        self.daemon = True

        self.plugin = plugin
        self.identifier = identifier
        self.log = log
        self.result_queue = result_queue
        self.timeout = timeout
        self.data = data

        self.browser = plugin.browser.clone_browser()
        self.url = URL_TEMPLATE.format(identifier = identifier)

        self.log.debug('[{}] Created worker {}'.format(self.identifier, self.url))

    def run(self):
        # Try to grab the page contents.
        try:
            self.log.info('[{}] Retrieving shelves from {}'.format(self.identifier, self.url))
            data = self.browser.open_novisit(self.url, timeout = self.timeout).read()
        except Exception as e:
            self.log.error('[{identifier}] Failed to retrieve {url}: {error}'.format(
                identifier = self.identifier,
                url = self.url,
                error = e.message,
            ))
            return

        # Try to parse the page contents.
        try:
            data = data.decode('utf-8', errors = 'replace').strip()
            root = fromstring(clean_ascii_chars(data))
        except Exception as e:
            self.log.error('[{identifier}] Failed to parse result of {url}: {error}'.format(
                identifier = self.identifier,
                url = self.url,
                error = e.message,
            ))
            return

        # Grab the shelves counters.
        shelves = {}
        for shelf in root.xpath('//div[contains(@class, "shelfStat")]'):
            name = shelf.xpath('.//a[contains(@class, "actionLinkLite")]')[0].text_content().strip()
            count = shelf.xpath('.//div[contains(@class, "smallText")]/a')[0].text_content().strip()
            count = int(count.split()[0].replace(',', ''))
            shelves[name] = count
        if not shelves:
            self.log.error('[{}] Failed to find any shelf info on {}'.format(self.identifier, self.url))
            return
        self.log.debug('[{}] Found shelves: {}'.format(self.identifier, shelves))

        # Map the shelves to the corresponding tags.
        tags = TagList()
        mapping = plugin_prefs.get(KEY_SHELF_MAPPINGS)
        for name, count in shelves.items():
            if name not in mapping:
                continue
            for tag in mapping[name]:
                tags[tag] += count
        self.log.debug('[{}] Tags after mapping: {}'.format(self.identifier, tags))

        # Apply the absolute threshold.
        threshold_abs = plugin_prefs.get(KEY_THRESHOLD_ABSOLUTE)
        tags.apply_threshold(threshold_abs)
        self.log.debug('[{}] Tags after applying absolute threshold ({}): {}'.format(
            self.identifier,
            threshold_abs,
            tags,
        ))

        # Calculate the percentage threshold.
        threshold_pct_places = plugin_prefs.get(KEY_THRESHOLD_PERCENTAGE_OF)
        threshold_pct_items = list(filter(bool, tags.get_places(threshold_pct_places)))
        self.log.debug('[{}] Percentage threshold will be based on the following tags ({}): {}'.format(
            self.identifier,
            threshold_pct_places,
            threshold_pct_items,
        ))
        if threshold_pct_items:
            threshold_pct_base = sum([item[1] for item in threshold_pct_items]) / len(threshold_pct_items)
        else:
            threshold_pct_base = 0
        threshold_pct = threshold_pct_base * plugin_prefs.get(KEY_THRESHOLD_PERCENTAGE) / 100
        self.log.debug('[{}] Percentage threshold is {}% of {}'.format(
            self.identifier,
            plugin_prefs.get(KEY_THRESHOLD_PERCENTAGE),
            threshold_pct_base,
        ))

        # Apply the percentage threshold.
        tags.apply_threshold(threshold_pct)
        self.log.debug('[{}] Tags after applying percentage threshold ({}): {}'.format(
            self.identifier,
            threshold_pct,
            tags,
        ))

        if len(tags) == 0:
            self.log.debug('[{}] No tags remain after mapping + filtering, skipping this one'.format(
                self.identifier,
            ))
            return

        # Store the results
        meta = Metadata(None)
        for k, v in self.data.items():
            meta.set(k, v)
        meta.set_identifier('goodreads', self.identifier)
        meta.tags = list(tags.keys())
        self.result_queue.put(meta)

