from __future__ import print_function
from __future__ import unicode_literals

try:
    from queue import Queue
except:
    # Python 2.x
    from Queue import Queue

from calibre.ebooks.metadata.sources.base import Source

from .config import plugin_prefs, KEY_INTEGRATION_ENABLED, KEY_INTEGRATION_TIMEOUT

__license__ = 'BSD 3-clause'
__copyright__ = '2019, Michon van Dooren <michon1992@gmail.com>'
__docformat__ = 'markdown en'


class GoodreadsMoreTags(Source):
    name = 'Goodreads More Tags'
    description = 'Scrape more tags from Goodreads'
    author = 'Michon van Dooren'

    version = (1, 2, 1)
    minimum_calibre_version = (0, 7, 53)
    supported_platforms = ['windows', 'osx', 'linux']

    capabilities = frozenset(['identify'])
    touched_fields = frozenset(['identifier:goodreads', 'tags'])

    def __init__(self, *args, **kwargs):
        Source.__init__(self, *args, **kwargs)

        # Try to inject into the regular Goodreads plugin. If this succeeds, this will provide data for use in our
        # identify (identifiers and results for all Goodreads results). If this fails, we do want to perform our
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
        use_integration = self.is_integrated and plugin_prefs.get(KEY_INTEGRATION_ENABLED)

        if use_integration:
            # Integration is enabled, so get the identifiers from the shared data.
            from .goodreads_integration import QueueHandler, QueueTimeoutError
            try:
                queue = QueueHandler.get_instance().get_queue(abort, 1)
            except QueueTimeoutError:
                use_integration = False
                log.debug((
                    'Goodreads plugin seems to not be active for this identify, '
                    'skipping integration for this run.'
                ))
        if use_integration:
            workers = []
            timeout = plugin_prefs.get(KEY_INTEGRATION_TIMEOUT)
            while not abort.is_set():
                try:
                    shared_datum = queue.get(timeout = timeout)
                except QueueTimeoutError:
                    log.warn((
                        'Timeout hit ({}s) while waiting for results from the Goodreads plugin. '
                        'Continuing with what we have, some results may not have tags.'
                    ).format(timeout))
                    break
                if shared_datum is None:
                    # The queue is done, so it can now be removed.
                    QueueHandler.get_instance().remove_queue(abort)
                    break
                log.debug('Received identifier from Goodreads plugin: {}'.format(shared_datum.identifier))
                worker = Worker(self, shared_datum.identifier, log = log, result_queue = temp_queue, **kwargs)
                worker.start()
                shared_data[shared_datum.identifier] = shared_datum
                workers.append(worker)

        if len(workers) == 0:
            # It's possible to end up here when integration is enabled when it fails to find any results.
            if use_integration:
                log.warn('Got no results from the Goodreads plugin, proceeding without integration')
            # No integration, so only proceed if there is a known goodreads identifier.
            if 'goodreads' not in identifiers:
                log.error('No goodreads identifier found, not grabbing extra tags')
                return
            log.debug('Using existing goodreads identifier from metadata: {}'.format(identifiers['goodreads']))
            worker = Worker(self, identifiers['goodreads'], log = log, result_queue = temp_queue, **kwargs)
            worker.start()
            workers.append(worker)

        while not abort.is_set():
            for worker in workers:
                if worker.is_alive():
                    worker.join(0.1)
                    break
            else:
                # All of the workers are done, so we can continue now.
                break

        # Copy the isbn to the results, as this plays an important role in merging. If integration is available, the
        # goodreads results may overwrite this with a different isbn.
        extra_identifiers = {}
        if 'isbn' in identifiers:
            extra_identifiers['isbn'] = identifiers['isbn']

        # Results are only merged if the title and authors are the same, so copy these values from the corresponding
        # goodreads results, if any.
        while not abort.is_set() and not temp_queue.empty():
            result = temp_queue.get()
            identifier = result.identifiers['goodreads']
            result.identifiers.update(extra_identifiers)

            shared_datum = shared_data.get(identifier)
            if shared_datum is None:
                log.warn('[{}] No goodreads result found (1), not copying id, title & author'.format(identifier))
                result_queue.put(result)
                continue
            shared_datum.is_done.wait()

            goodreads_result = shared_datum.results.get()
            if goodreads_result is None:
                log.warn('[{}] No goodreads result found (2), not copying id, title & author'.format(identifier))
                result_queue.put(result)
                continue

            log.debug('[{}] Goodreads result found, copying id, title & author'.format(identifier))
            result.identifiers = goodreads_result.identifiers
            result.title = goodreads_result.title
            result.authors = goodreads_result.authors
            result_queue.put(result)

