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

    def config_widget(self):
        from .config import ConfigWidget
        return ConfigWidget(self)

    def identify(self, log, result_queue, abort, identifiers = {}, **kwargs):
        """
        Gets tags for the already known Goodreads identifier, if one exists.

        This will not get any information for new Goodreads items returned by the Goodreads plugin.
        """
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

