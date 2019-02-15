from Queue import Queue

from calibre_plugins.goodreads.worker import Worker as OriginalWorker

from .worker import Worker as OurWorker


def run(self):
    print('>>> Starting custom worker')

    # We don't want the two workers to both add separate metadata entries, so replace the queue with a fake one so we
    # can merge the entries at the end.
    original_queue = self.result_queue
    their_queue = Queue()
    our_queue = Queue()
    # their_queue = our_queue = self.result_queue

    # Start our custom worker.
    identifier = self.plugin.id_from_url(self.url)[1]
    our_worker = OurWorker(self.plugin, identifier, self.log, our_queue, self.timeout)
    our_worker.start()

    # Run the regular worker.
    self.result_queue = their_queue
    run.original(self)

    # Wait for our custom worker to finish.
    our_worker.join()

    # Merge the metadata entries.
    their_metadata = their_queue.get_nowait()
    our_metadata = our_queue.get_nowait()
    their_metadata.tags = set(their_metadata.tags)
    their_metadata.tags.update(our_metadata.tags)
    original_queue.put(their_metadata)


def inject_into_goodreads():
    """
    Modifies the regular Worker class of the Goodreads plugin in such a way that creating a new instance of it actually
    result in an instance of the class created above.
    """
    if not getattr(OriginalWorker, '_more_tags_injected', False):
        run.original = OriginalWorker.run
        OriginalWorker.run = run
        OriginalWorker._more_tags_injected = True
