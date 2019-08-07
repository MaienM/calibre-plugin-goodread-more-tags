from __future__ import print_function
from __future__ import unicode_literals
from __future__ import with_statement

import sys
from threading import Event

import pytest


@pytest.fixture
def identify():
    from calibre.customize.ui import enable_plugin
    from calibre.ebooks.metadata.sources.identify import identify as calibre_identify
    from calibre.ebooks.metadata.sources.test import create_log

    def identify(plugins = None, **kwargs):
        """ Run an identify with the given options, and return the list of results. """
        if plugins:
            for plugin in plugins:
                enable_plugin(plugin)
            kwargs['allowed_plugins'] = [p.name for p in plugins]

        # Get required parameters to run identify.
        log = create_log(sys.stdout)
        abort = Event()

        # Run the regular identify function.
        results = calibre_identify(log, abort, **kwargs)

        # Output the log. Pytest will swallow this output unless a test fails.
        log.close()

        return results
    return identify
