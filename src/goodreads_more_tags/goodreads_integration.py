from __future__ import unicode_literals
from __future__ import with_statement

try:
    from queue import Queue, Empty
except:
    # Python 2.x
    from Queue import Queue, Empty
from threading import Condition, Event, RLock

from .config import plugin_prefs, KEY_INTEGRATION_ENABLED


# The goals of is to be able to provide tags for all results of the Goodreads plugin.
# In order to do so, we want to start a Worker whenever the base Goodreads plugin starts a worker.
# This Worker has to run in our own plugin, so that the logs, results and time spent are attributed to the correct
# plugin.


class QueueTimeoutError(Exception):
    pass


class QueueHandler(object):
    """
    This class handles the TemporaryQueue instances, making sure one (and only one) exists for a session.

    The abort instance is used as identifier for the session, as this is a separate instance per session, but shared
    across all identify calls in said session.

    This is intended to used as a singleton.
    """
    def __init__(self):
        self.lock = RLock()
        self.queues = {}
        self.conditions = {}

    @classmethod
    def get_instance(cls):
        """ Get the QueueHandler. Use this instead of creating a new instance. """
        if not hasattr(cls, '_instance'):
            cls._instance = QueueHandler()
        return cls._instance

    def create_queue(self, abort):
        """ Create a new TemporaryQueue instance for the given session. Will fail if one already exists. """
        with self.lock:
            if abort in self.queues:
                raise KeyError('A queue already exists for this instance.')
            self.queues[abort] = TemporaryQueue()
            if abort in self.conditions:
                condition = self.conditions[abort]
                with condition:
                    # Store queue on the condition so the waiting calls receive it even if it is immediately removed
                    condition.queue = self.queues[abort]
                    condition.notify_all()
                del self.conditions[abort]
            return self.queues[abort]

    def get_queue(self, abort, timeout = None):
        """ Get a TemporaryQueue instance for the given session. Will block if one has not yet been created. """
        with self.lock:
            if abort in self.queues:
                return self.queues[abort]
            if abort not in self.conditions:
                self.conditions[abort] = Condition(self.lock)
            condition = self.conditions[abort]
            with condition:
                if not condition.wait(timeout):
                    raise QueueTimeoutError()
            return condition.queue

    def remove_queue(self, abort):
        """ Remove a TemporaryQueue instance that is no longer needed. """
        with self.lock:
            if abort not in self.queues:
                return
            queue = self.queues[abort]
            queue.kill()
            del self.queues[abort]


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
        with self.condition:
            self.queue.put(data)
            self.condition.notify()

    def get(self, timeout = None):
        """
        Get a piece of data from the queue.

        If no data is available, this will wait until data becomes available, or until the queue is killed, in which case
        this will return None.
        """
        while not self.done.is_set() or not self.queue.empty():
            with self.condition:
                try:
                    result = self.queue.get_nowait()
                    return result
                except Empty:
                    self.condition.wait(timeout = timeout)
                    if not self.done.is_set() and self.queue.empty():
                        # This means we hit the timeout, which either means the goodreads plugin is not running, or it
                        # failed somehow.
                        raise QueueTimeoutError()

    def kill(self):
        """ Indicates that no further data will arrive. """
        self.done.set()
        with self.condition:
            self.condition.notifyAll()


class SharedData(object):
    """ Shared data between a goodreads worker and a goodreads more tags worker.  """
    def __init__(self, identifier):
        self.identifier = identifier
        self.results = Queue()
        self.is_done = Event()


def intercept_method(instance, method, interceptor):
    """
    A helper to create an intercept for a method.

    The instance and method describe where the original method can be found. That is, getattr(instance, method) should
    return the method.

    The interceptor will be called in place of the original method. The original method will be available as a property
    '_{method}_original' on the instance, and as a property `_original` on the interceptor.
    """
    key = '_{}_original'.format(method)
    if not getattr(instance, key, False):
        setattr(instance, key, getattr(instance, method))
    if getattr(instance, method) != interceptor:
        setattr(instance, method, interceptor)
    interceptor._original = getattr(instance, key)


def skip_if_disabled(func):
    """ A decorator for interceptor methods that skips the interceptor if the intergation is disabled. """
    def wrapper(*args, **kwargs):
        if not plugin_prefs.get(KEY_INTEGRATION_ENABLED):
            return func._original(*args, **kwargs)
        return func(*args, **kwargs)
    return wrapper


@skip_if_disabled
def intercept_Goodreads_identify(self, log, result_queue, abort, *args, **kwargs):
    log.debug('[GoodreadsMoreTags] Integration active')

    # Create the queue as a marker that Goodreads is active during this run.
    QueueHandler.get_instance().create_queue(abort)

    # Store the abort instance, as it will be used as a session identifier.
    self.__abort_for_more_tags = abort

    # Run the original identify.
    return self._identify_original(log, result_queue, abort, *args, **kwargs)


@skip_if_disabled
def intercept_Goodreads_Worker_init(self, *args, **kwargs):
    # Run the regular init.
    self.___init___original(*args, **kwargs)

    # Put the data for this worker on the appropriate queue, so that the identify() can start corresponding workers.
    identifier = self.plugin.id_from_url(self.url)[1]
    self.log.debug('[GoodreadsMoreTags] Captured identifier {}'.format(identifier))
    shared_data = self.__shared_data_for_more_tags = SharedData(identifier)
    queue = QueueHandler.get_instance().get_queue(self.plugin.__abort_for_more_tags)
    queue.put(shared_data)


@skip_if_disabled
def intercept_Goodreads_Worker_run(self):
    # The Goodreads plugin will only start running the workers after creating all of them, so we know that the
    # TemporaryQueue can be closed at this time. We cannot safely remove it yet though as we cannot be certain the GMT
    # plugin has grabbed it yet.
    QueueHandler.get_instance().get_queue(self.plugin.__abort_for_more_tags).kill()

    # Use a different queue to capture the results.
    shared_data = self.__shared_data_for_more_tags
    queue = self.result_queue
    self.result_queue = Queue()

    # Run the regular worker.
    result = self._run_original()
    self.log.debug('[GoodreadsMoreTags] Captured {} result(s) for {}'.format(
        self.result_queue.qsize(),
        shared_data.identifier,
    ))

    # Add the results to the real result queue, and to the shared data, and then mark as done in the shared data.
    while not self.result_queue.empty():
        result = self.result_queue.get()
        queue.put(result)
        shared_data.results.put(result)
    shared_data.is_done.set()
    self.result_queue = queue

    return result


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
