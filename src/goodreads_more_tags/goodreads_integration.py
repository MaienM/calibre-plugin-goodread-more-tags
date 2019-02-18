from __future__ import unicode_literals

from Queue import Queue, Empty
from threading import Condition, Event, Lock


# The goals of is to be able to provide tags for all results of the Goodreads plugin.
# In order to do so, we want to start a Worker whenever the base Goodreads plugin starts a worker.
# This Worker has to run in our own plugin, so that the logs, results and time spent are attributed to the correct
# plugin.


class QueueHandler(object):
    """
    This class handles the TemporaryQueue instances, making sure one (and only one) exists for a session.

    The abort instance is used as identifier for the session, as this is a separate instance per session, but shared
    across all identify calls in said session.

    This is instended to be a singleton.
    """
    def __init__(self):
        self.lock = Lock()
        self.queues = {}

    @classmethod
    def get_instance(cls):
        """ Get the QueueHandler. Use this instead of creating a new instance. """
        if not hasattr(cls, '_instance'):
            cls._instance = QueueHandler()
        return cls._instance

    def get_queue(self, abort):
        """ Get a TemporaryQueue instance for the given session. """
        self.lock.acquire()
        try:
            if abort not in self.queues:
                self.queues[abort] = TemporaryQueue()
            return self.queues[abort]
        finally:
            self.lock.release()

    def remove_queue(self, abort):
        """ Remove a TemporaryQueue instance that is no longer needed. """
        self.lock.acquire()
        try:
            if abort not in self.queues:
                return
            queue = self.queues[abort]
            queue.kill()
            del self.queues[abort]
        finally:
            self.lock.release()


class TemporaryQueue(object):
    """
    Similar to a normal queue, but with a limited lifetime.

    Data can be added and read until the queue is killed, at which point all waiting consumers receive None, and no
    further data can be added.
    """
    def __init__(self):
        self.done = Event()
        self.condition = Condition()
        self.queue = Queue()

    def put(self, data):
        """ Add a piece of data to the queue. """
        if self.done.is_set():
            raise Exception('You cannot add data to a dead queue')
        self.condition.acquire()
        try:
            self.queue.put(data)
            self.condition.notify()
        finally:
            self.condition.release()

    def get(self):
        """
        Get a piece of data from the queue.

        If no data is available, this will wait until data becomes available, or until the queue is killed, in which case
        this will return None.
        """
        while not self.done.is_set():
            try:
                return self.queue.get_nowait()
            except Empty:
                self.condition.acquire()
                self.condition.wait()

    def kill(self):
        """ Indicates that no further data will arrive. """
        self.done.set()
        self.condition.acquire()
        try:
            self.condition.notifyAll()
        finally:
            self.condition.release()


def intercept_method(instance, method, interceptor):
    """
    A helper to create an intercept for a method.

    The instance and method describe where the original method can be found. That is, getattr(instance, method) should
    return the method.

    The interceptor will be called in place of the original method. The original method will be available as a property
    '_{method}_original' on the instance.
    """
    key = '_{}_original'.format(method)
    if not getattr(instance, key, False):
        setattr(instance, key, getattr(instance, method))
        setattr(instance, method, interceptor)


def intercept_Goodreads_identify(self, log, result_queue, abort, *args, **kwargs):
    # Store the abort instance, as it will be used as a session identifier.
    self.__abort_for_more_tags = abort

    # Run the original identify.
    return self._identify_original(log, result_queue, abort, *args, **kwargs)


def intercept_Goodreads_Worker_init(self, *args, **kwargs):
    # Run the regular init.
    self.___init___original(*args, **kwargs)

    # Put the data for this worker on the appropriate queue, so that the identify() can start corresponding workers.
    identifier = self.plugin.id_from_url(self.url)[1]
    queue = QueueHandler.get_instance().get_queue(self.plugin.__abort_for_more_tags)
    queue.put(identifier)


def intercept_Goodreads_Worker_run(self):
    # The Goodreads plugin will only start running the workers after creating all of them, so we know that the
    # TemporaryQueue can be closed at this time.
    QueueHandler.get_instance().remove_queue(self.plugin.__abort_for_more_tags)

    # Run the regular worker.
    return self._run_original()


def inject_into_goodreads():
    """
    Modifies the base Goodreads plugin in such a way our identify can run Workers for the same ids as found by the base
    plugin.

    It does this by modifying some of the methods to interact with the QueueHandler and TemporaryQueues to provide the
    needed data to the identify method of this plugin.
    """
    from calibre_plugins.goodreads import Goodreads
    from calibre_plugins.goodreads.worker import Worker as OriginalWorker

    intercept_method(Goodreads, 'identify', intercept_Goodreads_identify)
    intercept_method(OriginalWorker, '__init__', intercept_Goodreads_Worker_init)
    intercept_method(OriginalWorker, 'run', intercept_Goodreads_Worker_run)
