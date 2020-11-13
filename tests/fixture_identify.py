from __future__ import print_function
from __future__ import unicode_literals
from __future__ import with_statement

import sys
from io import StringIO
from threading import Event

import pytest


@pytest.fixture
def identify():
    from calibre.customize.ui import enable_plugin
    from calibre.ebooks.metadata.sources.identify import identify as calibre_identify
    from calibre.ebooks.metadata.sources.test import create_log

    captures = []

    def identify(plugins = None, **kwargs):
        """ Run an identify with the given options, and return the list of results. """
        # Enable the desired plugins and convert to the expected format.
        if plugins:
            for plugin in plugins:
                enable_plugin(plugin)
            kwargs['allowed_plugins'] = [p.name for p in plugins]

        # Create a log that both outputs to stdout as well as a capture.
        # capsys/capfs do not work, unfortunately.
        from calibre.utils.logging import FileStream
        log = create_log(sys.stdout)
        capture = StringIO()
        captures.append(capture)
        log.outputs.append(FileStream(capture))

        # Run the regular identify function.
        abort = Event()
        results = calibre_identify(log, abort, **kwargs)

        # Output the log. Pytest will swallow this output unless a test fails.
        log.close()

        # Log the results.
        print()
        print('Results:')
        print('-' * 40)
        for result in results:
            print(result)
            print('-' * 40)

        return results

    identify.captures = captures
    return identify
