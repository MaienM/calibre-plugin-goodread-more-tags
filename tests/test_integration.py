from __future__ import unicode_literals

import pytest

from calibre.customize.ui import find_plugin
from calibre_plugins.goodreads import Goodreads
from calibre_plugins.goodreads.config import STORE_NAME, KEY_GENRE_MAPPINGS
from calibre_plugins.goodreads_more_tags import GoodreadsMoreTags
from calibre_plugins.goodreads_more_tags.goodreads_integration import inject_into_goodreads


@pytest.fixture(autouse = True)
def enable_integration():
    inject_into_goodreads()
    plugin = find_plugin(GoodreadsMoreTags.name)
    plugin.is_integrated = True


@pytest.fixture(autouse = True)
def no_base_tags(configs):
    configs.goodreads[STORE_NAME][KEY_GENRE_MAPPINGS] = {}


class TestIdentifyIntegrated(object):
    def test_goodreads_id(self, identify):
        results = identify(plugins = [Goodreads, GoodreadsMoreTags], identifiers = { 'goodreads': '902715' })
        assert len(results) == 1
        assert sorted(results[0].tags) == [
            'Adventure',
            'Fantasy',
            'Science Fiction',
            'War',
        ]

    def test_isbn(self, identify):
        results = identify(plugins = [Goodreads, GoodreadsMoreTags], identifiers = { 'isbn': '9780575077881' })
        assert len(results) == 1
        assert sorted(results[0].tags) == [
            'Adventure',
            'Fantasy',
            'Science Fiction',
            'War',
        ]
