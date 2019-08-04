from __future__ import print_function
from __future__ import unicode_literals

from Queue import Queue

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
        print('Integration status:', self.is_integrated)

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
        shared_data = {}
        temp_queue = Queue()
        log.debug('*' * 20)

        if not self.is_integrated:
            # No integration, so only proceed if there is a known goodreads identifier.
            if 'goodreads' not in identifiers:
                log.warn('No goodreads identifier found, not grabbing extra tags')
                return
            # No need to use the temp_queue, as there will be no goodreads results to map to anyway.
            worker = Worker(self, identifiers['goodreads'], log = log, result_queue = result_queue, **kwargs)
            worker.start()
            workers.append(worker)

        else:
            # Integration is enabled, so get the identifiers from the shared data.
            from .goodreads_integration import QueueHandler
            queue = QueueHandler.get_instance().get_queue(abort)
            workers = []
            while not abort.is_set():
                shared_datum = queue.get()
                if shared_datum is None:
                    break
                worker = Worker(self, shared_datum.identifier, log = log, result_queue = temp_queue, **kwargs)
                worker.start()
                shared_data[shared_datum.identifier] = shared_datum
                workers.append(worker)

        while not abort.is_set():
            for worker in workers:
                if worker.is_alive():
                    worker.join(0.1)
                    break
            else:
                # All of the workers are done, so we can continue now
                break

        # Results are only merged if the title and authors are the same, so copy these values from the corresponding
        # goodreads results, if any.
        while not abort.is_set() and not temp_queue.empty():
            result = temp_queue.get()
            shared_datum = shared_data.get(result.identifiers['goodreads'])
            if shared_datum is None:
                result_queue.put(result)
                continue
            shared_datum.is_done.wait()

            goodreads_result = shared_datum.results.get()
            if goodreads_result is None:
                result_queue.put(result)
                continue

            result.title = goodreads_result.title
            result.authors = goodreads_result.authors
            result_queue.put(result)

