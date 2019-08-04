from __future__ import unicode_literals
from __future__ import with_statement

from io import StringIO, BytesIO
import mimetools
import time

import pytest


class MockBrowser(object):
    """ A class to mock calls to the calibre Browser. """
    def __init__(self):
        self._responses = []

    def add_response(self, url_regex, response):
        self._responses.append((url_regex, response))

    def open_novisit(self, url, *args, **kwargs):
        for url_regex, response in self._responses:
            match = url_regex.match(url)
            if match:
                return MockResponse(url, 200, response)
        raise Exception('No mock response defined for ' + url)


class MockResponse(object):
    """ A mock response object for the mock browser. """
    def __init__(self, url, status, data):
        if isinstance(data, bytes):
            self._data = BytesIO(data)
        else:
            data = str(data)
            self._data = StringIO(data)

        self._url = url
        self._status = status
        self._headers = mimetools.Message(StringIO('Content-Length: ' + str(len(data))))

    def read(self, *args):
        return self._data.read(*args)

    def geturl(self):
        return self._url

    def info(self):
        return self._headers

    def getcode(self):
        return self._status


@pytest.fixture
def browser(monkeypatch):
    """
    A fixture that will mock the browser instance of all plugins, making it possible to return static answers to the
    requests.
    """
    from calibre.utils.browser import Browser
    from calibre.customize.ui import all_metadata_plugins

    browser = MockBrowser()
    monkeypatch.setattr(Browser, 'open_novisit', browser.open_novisit)

    return browser
