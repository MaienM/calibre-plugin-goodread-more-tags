from __future__ import division
from __future__ import unicode_literals

from collections import Counter
from threading import Thread

from lxml.html import fromstring

from calibre.ebooks.metadata.book.base import Metadata
from calibre.utils.cleantext import clean_ascii_chars

from .config import plugin_prefs, STORE_NAME, KEY_TRESHOLD_ABSOLUTE, KEY_TRESHOLD_PERCENTAGE, KEY_TRESHOLD_PERCENTAGE_OF, KEY_SHELF_MAPPINGS


__license__ = 'BSD 3-clause'
__copyright__ = '2019, Michon van Dooren <michon1992@gmail.com>'
__docformat__ = 'markdown en'

URL_TEMPLATE = 'https://www.goodreads.com/book/shelves/{identifier}'


class TagList(Counter):
    """ A list of tags with the amount of people that 'voted' for the tag. """
    def apply_treshold(self, treshold):
        """
        Apply a treshold, removing all items with a value below the treshold.

        >>> c = TagList(a = 20, b = 10, c = 5, d = 3, e = 2, f = 1)
        >>> c.apply_treshold(4)
        >>> sorted(c.keys())
        ['a', 'b', 'c']
        >>> c.apply_treshold(10)
        >>> sorted(c.keys())
        ['a', 'b']
        """
        for key, count in self.items():
            if count < treshold:
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
        self.prefs = plugin_prefs[STORE_NAME]

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
        mapping = self.prefs[KEY_SHELF_MAPPINGS]
        for name, count in shelves.items():
            if name not in mapping:
                continue
            for tag in mapping[name]:
                tags[tag] += count
        self.log.debug('[{}] Tags after mapping: {}'.format(self.identifier, tags))

        # Apply the absolute treshold.
        treshold_abs = self.prefs[KEY_TRESHOLD_ABSOLUTE]
        tags.apply_treshold(treshold_abs)
        self.log.debug('[{}] Tags after applying absolute treshold: {}'.format(self.identifier, tags))

        # Calculate the percentage treshold.
        treshold_pct_places = self.prefs[KEY_TRESHOLD_PERCENTAGE_OF]
        self.log.debug('[{}] Percentage treshold will be based on the tags in the following places: {}'.format(
            self.identifier,
            treshold_pct_places,
        ))
        treshold_pct_items = filter(bool, tags.get_places(treshold_pct_places))
        self.log.debug('[{}] Percentage treshold will be based on the following tags: {}'.format(
            self.identifier,
            treshold_pct_items,
        ))
        if treshold_pct_items:
            treshold_pct_base = sum([item[1] for item in treshold_pct_items]) / len(treshold_pct_items)
        else:
            treshold_pct_base = 0
        self.log.debug('[{}] Percentage treshold base is: {}'.format(self.identifier, treshold_pct_base))
        treshold_pct = treshold_pct_base * self.prefs[KEY_TRESHOLD_PERCENTAGE] / 100
        self.log.debug('[{}] Percentage treshold is: {}'.format(self.identifier, treshold_pct))

        # Apply the percentage treshold.
        tags.apply_treshold(treshold_pct)
        self.log.debug('[{}] Tags after applying percentage treshold: {}'.format(self.identifier, tags))

        # Store the results
        meta = Metadata(None)
        for k, v in self.data.items():
            meta.set(k, v)
        meta.set_identifier('goodreads', self.identifier)
        meta.tags = tags.keys()
        self.result_queue.put(meta)


