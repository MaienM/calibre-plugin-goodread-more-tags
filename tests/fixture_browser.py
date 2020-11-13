from __future__ import unicode_literals
from __future__ import with_statement

from io import BytesIO
import re
import time

import pytest


class MockBrowser(object):
    """ A class to mock calls to the calibre Browser. """
    def __init__(self):
        self._responses = []

    def add_response(self, url_regex, response):
        self._responses.append((re.compile(url_regex), response))

    def open_novisit(self, url, *args, **kwargs):
        for url_regex, response in self._responses:
            match = url_regex.match(url)
            if match:
                if callable(response):
                    response = response(match)
                if response is None:
                    continue
                return MockResponse(response)
        raise Exception('No mock response defined for ' + url)


class MockResponse(object):
    """ A mock response object for the mock browser. """
    def __init__(self, data):
        self.data = BytesIO(data)

        self._info = {}
        self._info['Content-Length'] = len(data)

    def info(self):
        return self._info

    def read(self, size=-1):
        return self.data.read(size)


@pytest.fixture
def browser(monkeypatch):
    """
    A fixture that will mock the browser instance of all plugins, making it possible to return static answers to the
    requests.
    """
    from calibre.utils.browser import Browser

    browser = MockBrowser()
    monkeypatch.setattr(Browser, 'open_novisit', browser.open_novisit)

    return browser
