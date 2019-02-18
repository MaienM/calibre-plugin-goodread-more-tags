from __future__ import print_function
from __future__ import unicode_literals

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
        Gets additional tags for Goodreads results.
        
        If the integration with the base Goodreads plugin was successful, this will get tags for all results returned by
        that. If not, it will only get tags if the current set of identifiers contains one for Goodreads.
        """
        from .worker import Worker
        workers = []
        log.debug('*' * 20)

        if not self.is_integrated:
            if 'goodreads' not in identifiers:
                log.warn('No goodreads identifier found, not grabbing extra tags')
                return
            worker = Worker(self, identifiers['goodreads'], log = log, result_queue = result_queue)
            worker.start()
            workers.append(worker)

        else:
            from .goodreads_integration import QueueHandler
            queue = QueueHandler.get_instance().get_queue(abort)
            workers = []
            while True:
                identifier = queue.get()
                if identifier is None:
                    break
                worker = Worker(self, identifier, log = log, result_queue = result_queue)
                worker.start()
                workers.append(worker)

        while not abort.is_set():
            for worker in workers:
                if worker.is_alive():
                    worker.join(0.1)
                    break
            else:
                # All of the workers are done, so we can continue now
                break

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
