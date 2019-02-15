from __future__ import print_function

from calibre.ebooks.metadata.sources.base import Source

__license__ = 'BSD 3-clause'
__copyright__ = '2019, Michon van Dooren <michon1992@gmail.com>'
__docformat__ = 'markdown en'


class GoodreadsMoreTags(Source):
    name = 'Goodreads More Tags'
    description = 'Scrape more tags from Goodreads'
    author = 'Michon van Dooren'

    version = (1, 0, 0)
    minimum_calibre_version = (0, 7, 53)
    supported_platforms = ['windows', 'osx', 'linux']

    capabilities = frozenset(['identify'])
    touched_fields = frozenset(['identifier:goodreads', 'tags'])

    def __init__(self, *args, **kwargs):
        Source.__init__(self, *args, **kwargs)

        # Try to inject into the regular Goodreads plugin. If this succeeds, this means our worker is integrated with
        # their worker, so we don't need to do anything in our identify. If this fails, we do want to perform our
        # identify as normal. The advantage of this integration is that it works for items that don't already have a
        # goodreads identifier.
        self.is_integrated = False
        try:
            from .goodreads_integration import inject_into_goodreads
            inject_into_goodreads()
            self.is_integrated = True
        except ImportError:
            pass
        print('Integration status: ', self.is_integrated)

    def config_widget(self):
        from .config import ConfigWidget
        return ConfigWidget(self)

    def identify(self, log, result_queue, abort, identifiers = {}, **kwargs):
        """
        Gets tags for the already known Goodreads identifier, if one exists.

        This will do nothing if the integration with the regular Goodreads plugin was successful.

        This will not get any information for new Goodreads items returned by the Goodreads plugin.
        """
        if self.is_integrated:
            return

        if 'goodreads' not in identifiers:
            log.warn('No goodreads identifier found, not grabbing extra tags')
            return

        from .worker import Worker
        worker = Worker(self, identifiers['goodreads'], log = log, result_queue = result_queue)
        worker.start()
        while worker.is_alive() and not abort.is_set():
            worker.join(0.1)

    def cli_main(self, *args, **kwargs):
        from calibre.gui2 import Application
        app = Application([])
        plugin = GoodreadsMoreTags(__file__)
        config = plugin.config_widget()
        config.show()

        _locals = locals()
        def embed():
            import IPython
            app = _locals['app']
            plugin = _locals['plugin']
            config = _locals['config']
            IPython.embed()
        import threading
        thread = threading.Thread(target = embed)
        thread.daemon = True
        thread.start()

        app.exec_()

