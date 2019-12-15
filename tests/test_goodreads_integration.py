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
from calibre.ebooks.metadata.sources.amazon import Amazon
from calibre_plugins.goodreads import Goodreads
from calibre_plugins.goodreads_more_tags import GoodreadsMoreTags
import calibre_plugins.goodreads_more_tags.goodreads_integration as tm


@pytest.fixture(autouse = True)
def enable_integration():
    tm.inject_into_goodreads()
    plugin = find_plugin(GoodreadsMoreTags.name)
    plugin.is_integrated = True


@pytest.fixture(autouse = True)
def no_tags_from_other_plugins():
    from calibre.customize.ui import all_metadata_plugins
    for plugin in all_metadata_plugins():
        if plugin.name == GoodreadsMoreTags.name:
            continue

        if 'ignore_fields' not in plugin.prefs:
            plugin.prefs['ignore_fields'] = []
        plugin.prefs['ignore_fields'].append('tags')


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

    def test_intercept__is_not_called_if_disabled(self, configs):
        intercept = Mock()
        decorated = tm.skip_if_disabled(intercept)
        tm.intercept_method(TestInterceptMethod, 'sum', decorated)
        configs.goodreads_more_tags.integration_enabled = False
        self.sum(1, 2)
        assert not intercept.called

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


@pytest.mark.parametrize('execution_number', range(10))
@pytest.mark.timeout(30)
class TestIdentifyIntegrated(object):
    @pytest.fixture(autouse = True)
    def setup_browser_mock(self, browser):
        failed_response = False

        basedir = os.path.join(os.path.dirname(__file__), '_responses')

        def add(url_regex, filename_pattern):
            def read_file(match):
                filename = filename_pattern.format(**match.groupdict())
                try:
                    with open(os.path.join(basedir, filename), 'rb') as file:
                        return file.read()
                except IOError:
                    print('Response file {} not found, not providing response for {}'.format(filename, match.group(0)))
                    failed_response = True
                    return None
            browser.add_response(url_regex, read_file)

        pre = r'^https?://(www\.)?'

        # Goodreads
        add(pre + r'goodreads\.com/book/show/(?P<id>\d+)\D*$', 'goodreads-book-{id}.html')
        add(pre + r'goodreads\.com/book/shelves/(?P<id>\d+)\D*$', 'goodreads-shelves-{id}.html')
        add(pre + r'goodreads\.com/book/auto_complete\?.*&q=(?P<id>\d+)$', 'goodreads-autocomplete-{id}.json')
        add(pre + r'i\.gr-assets\.com/images/.*/books/.*/\d+\..*\.jpg$', 'cover.jpg')

        # Amazon/Amazon Multiple Countries
        query_pattern = r'(%28)?(?P<id>\d+)\+.*site%3A(www\.)?amazon\.(?P<tld>[a-z.]+)'
        add(pre + r'google\.com/search\?q=' + query_pattern, 'google-{id}-amazon.{tld}.html')
        add(pre + r'webcache\.googleusercontent\.com/search\?q=cache:(?P<id>[^:]+):', 'google-result-{id}.html')
        add(pre + r'bing\.com/search\?q=' + query_pattern, 'bing-{id}-amazon.{tld}.html')
        add(pre + r'cc.bingj.com/cache.aspx\?.*&d=(?P<id>\d+)&', 'bing-result-{id}.html')

        yield

        assert not failed_response

    @pytest.fixture(autouse = True)
    def detect_deadlock(self, configs, identify):
        # Since all browser results are mocked, everything should complete fairly quickly. The main factor here is
        # system load/speed, so set generous timeouts to avoid those from being issues, without risking being killed by
        # the pytest timeouts.
        from calibre.ebooks.metadata.sources.prefs import msprefs
        msprefs['wait_after_first_identify_result'] = 20
        configs.goodreads_more_tags.integration_timeout = 10

        yield

        # Detect if a timeout was hit.
        for capture in identify.captures:
            match = re.search(r'Still running sources:(\n.*)\n\n', capture.getvalue(), re.MULTILINE)
            if match:
                pytest.fail('Identify timed out, plugins not done: ' + match.group(1))

    def test_goodreads_id(self, identify, execution_number):
        results = identify(plugins = [Goodreads, GoodreadsMoreTags], identifiers = { 'goodreads': '902715' })
        assert len(results) == 1
        assert sorted(results[0].tags) == ['Adult', 'Adventure', 'Fantasy', 'Science Fiction', 'War']

    def test_isbn(self, identify, execution_number):
        results = identify(plugins = [Goodreads, GoodreadsMoreTags], identifiers = { 'isbn': '9780575077881' })
        assert len(results) == 1
        assert sorted(results[0].tags) == ['Adult', 'Adventure', 'Fantasy', 'Science Fiction', 'War']

    def test_other_source_no_goodreads_id(self, identify, execution_number):
        """
        I found that when adding in a different source that will return an isbn, but not a goodreads id, merging
        sometimes failes. Including all identifiers that goodreads returns in the goodreads more tags result resolves
        this.
        """
        results = identify(
            plugins = [Goodreads, GoodreadsMoreTags, Amazon],
            identifiers = {
                'amazon': '0385347308',
                'goodreads': '18133416',
            },
        )
        assert len(results) == 1

    def test_other_source_no_goodreads_id_without_goodreads_plugin(self, identify, execution_number):
        """
        Similar to the previous test, but now without the goodreads plugin present. Merging should still succeed due to
        the isbn being included in the returned identifiers.
        """
        results = identify(
            plugins = [GoodreadsMoreTags, Amazon],
            identifiers = {
                'isbn': '9780385347303',
                'goodreads': '18133416',
            },
        )
        assert len(results) == 1
