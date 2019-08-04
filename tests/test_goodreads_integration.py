from __future__ import unicode_literals
from __future__ import with_statement

import os.path
import re
import time
from threading import Event, Thread

import pytest

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

from calibre.customize.ui import find_plugin
from calibre_plugins.goodreads import Goodreads
from calibre_plugins.goodreads.config import STORE_NAME, KEY_GENRE_MAPPINGS
from calibre_plugins.goodreads_more_tags import GoodreadsMoreTags
import calibre_plugins.goodreads_more_tags.goodreads_integration as tm


@pytest.fixture(autouse = True)
def enable_integration():
    tm.inject_into_goodreads()
    plugin = find_plugin(GoodreadsMoreTags.name)
    plugin.is_integrated = True


@pytest.fixture(autouse = True)
def no_base_tags(configs):
    configs.goodreads[STORE_NAME][KEY_GENRE_MAPPINGS] = {}


class TestQueueHandler(object):
    def test_get_instance__type(self):
        assert isinstance(tm.QueueHandler.get_instance(), tm.QueueHandler)

    def test_get_instance__same(self):
        assert tm.QueueHandler.get_instance() == tm.QueueHandler.get_instance()

    def test_get_queue__type(self):
        handler = tm.QueueHandler.get_instance()
        abort = Event()
        assert isinstance(handler.get_queue(abort), tm.TemporaryQueue)

    def test_get_queue__same_instance_for_key(self):
        handler = tm.QueueHandler.get_instance()
        abort = Event()
        assert handler.get_queue(abort) == handler.get_queue(abort)

    def test_get_queue__different_instance_per_key(self):
        handler = tm.QueueHandler.get_instance()
        abort1 = Event()
        abort2 = Event()
        assert handler.get_queue(abort1) != handler.get_queue(abort2)

    def test_remove_queue__new_instance(self):
        handler = tm.QueueHandler.get_instance()
        abort = Event()
        oldqueue = handler.get_queue(abort)
        handler.remove_queue(abort)
        newqueue = handler.get_queue(abort)
        assert newqueue is not None
        assert newqueue != oldqueue

    def test_remove_queue__kill(self):
        handler = tm.QueueHandler.get_instance()
        abort = Event()
        queue = handler.get_queue(abort)
        queue.kill = Mock()
        handler.remove_queue(abort)
        assert queue.kill.called


class TestTemporaryQueue(object):
    def test_put_get__can_consume(self):
        queue = tm.TemporaryQueue()
        queue.put(12)
        assert queue.get() == 12

    def test_put_get__can_wait(self):
        queue = tm.TemporaryQueue()

        def add_delayed():
            time.sleep(0.2)
            queue.put(13)

        Thread(target = add_delayed).start()

        assert queue.get() == 13

    def test_kill__cannot_put(self):
        queue = tm.TemporaryQueue()
        queue.kill()
        with pytest.raises(Exception):
            queue.put(14)

    def test_kill__finishes_remaining_gets(self):
        queue = tm.TemporaryQueue()

        def kill_delayed():
            time.sleep(0.2)
            queue.kill()

        Thread(target = kill_delayed).start()

        assert queue.get() is None


class TestInterceptMethod(object):
    def sum(self, a, b):
        return a + b

    def test_intercept__is_called(self):
        intercept = Mock()
        tm.intercept_method(TestInterceptMethod, 'sum', intercept)
        self.sum(1, 2)
        assert intercept.called

    def test_intercept__is_returned(self):
        def times(self, a, b):
            return a * b

        tm.intercept_method(TestInterceptMethod, 'sum', times)
        assert self.sum(2, 4) == 8

    def test_intercept__has_original(self):
        def sumext(self, a, b):
            return self._sum_original(a, b) + 10

        tm.intercept_method(TestInterceptMethod, 'sum', sumext)
        assert self.sum(2, 4) == 16


class TestIdentifyIntegrated(object):
    def add_browser_mock(self, browser, url_regex, filename):
        basedir = os.path.join(os.path.dirname(__file__), '_responses')
        with open(os.path.join(basedir, filename), 'rb') as file:
            browser.add_response(re.compile(url_regex), file.read())

    def setup_browser_mock(self, browser):
        basedir = os.path.join(os.path.dirname(__file__), '_responses')
        self.add_browser_mock(browser, r'^https?://(www\.)?goodreads\.com/book/show/\d+\D*$', 'book-902715.html')
        self.add_browser_mock(browser, r'^https?://(www\.)?goodreads\.com/book/shelves/\d+\D*$', 'shelves-902715.html')
        self.add_browser_mock(browser, r'^https?://i\.gr-assets\.com/images/.*/books/.*/\d+\..*\.jpg$', 'cover-902715.jpg')
        self.add_browser_mock(
            browser,
            r'^https?://(www\.)?goodreads\.com/book/auto_complete\?format=json&q=9780575077881$',
            'autocomplete-9780575077881.json',
        )

    @pytest.mark.parametrize('execution_number', range(5))
    def test_goodreads_id(self, identify, browser, execution_number):
        self.setup_browser_mock(browser)
        results = identify(plugins = [Goodreads, GoodreadsMoreTags], identifiers = { 'goodreads': '902715' })
        assert len(results) == 1
        assert sorted(results[0].tags) == [
            'Adventure',
            'Fantasy',
            'Science Fiction',
            'War',
        ]

    @pytest.mark.parametrize('execution_number', range(5))
    def test_isbn(self, identify, browser, execution_number):
        self.setup_browser_mock(browser)
        results = identify(plugins = [Goodreads, GoodreadsMoreTags], identifiers = { 'isbn': '9780575077881' })
        assert len(results) == 1
        assert sorted(results[0].tags) == [
            'Adventure',
            'Fantasy',
            'Science Fiction',
            'War',
        ]
