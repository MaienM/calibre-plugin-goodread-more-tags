from __future__ import unicode_literals

import pytest

from calibre.customize.ui import find_plugin
from calibre_plugins.goodreads_more_tags import GoodreadsMoreTags


@pytest.fixture(autouse = True)
def disable_integration():
    plugin = find_plugin(GoodreadsMoreTags.name)
    plugin.is_integrated = False


class TestIdentify(object):
    def test_goodreads_id(self, identify):
        results = identify(plugins = [GoodreadsMoreTags], identifiers = { 'goodreads': '902715' })
        assert len(results) == 1
        assert sorted(results[0].tags) == [
            'Adventure',
            'Fantasy',
            'Science Fiction',
            'War',
        ]

    def test_isbn(self, identify):
        results = identify(plugins = [GoodreadsMoreTags], identifiers = { 'isbn': '9780575077881' })
        assert len(results) == 0
