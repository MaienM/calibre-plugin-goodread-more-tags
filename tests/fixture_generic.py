import pytest


@pytest.fixture(scope = 'session')
def monkeypatch_s():
    from _pytest.monkeypatch import MonkeyPatch

    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()

@pytest.fixture(scope = 'session')
def tmpdir_s(request, tmpdir_factory):
    import re

    name = request.node.name
    name = re.sub(r"[\W]", "_", request.node.name)[:30]
    return tmpdir_factory.mktemp(name, numbered = True)


@pytest.fixture(scope = 'session')
def logger():
    import logging
    import sys

    formatter = logging.Formatter('%(asctime)s %(message)s')

    handler = logging.FileHandler('test.log', 'w')
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)

    root = logging.getLogger(None)
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)

    return root


@pytest.fixture(scope = 'session')
def debuglog(request, logger):
    import collections
    import inspect
    import logging
    import os.path
    import pprint
    import threading
    import traceback

    lock = threading.Lock()
    rootpath = os.path.join(os.path.dirname(__file__), '..')
    last_header = [None]

    CallerInfo = collections.namedtuple('CallerInfo', ['func_name', 'file', 'lineno'])

    def get_caller_info(caller):
        func_name = caller.f_code.co_name
        source_lineno = caller.f_lineno
        source_file_abs = caller.f_code.co_filename
        source_file_rel = os.path.relpath(source_file_abs, rootpath)
        source_file = source_file_abs if '../' in source_file_rel else source_file_rel
        return CallerInfo(func_name, source_file, source_lineno)

    def log_block(caller, level, block, max_line_length = None):
        test_name = request._pyfuncitem.name
        cinfo = get_caller_info(caller)
        header = '==> {test_name} - {cinfo.file} - {cinfo.func_name} <=='.format(**locals())

        with lock:
            if header != last_header[0]:
                logger.debug(header)
                last_header[0] = header
            for line in block.split('\n'):
                if max_line_length is not None and len(line) > max_line_length:
                    line = '{}...'.format(line[:max_line_length])
                logger.debug(':{cinfo.lineno} {line}'.format(**locals()))

    def log_exceptions(func):
        def with_exception_handler(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except Exception as e:
                caller = inspect.currentframe(1)
                log_block(caller, logging.ERROR, traceback.format_exc())
        return with_exception_handler

    @log_exceptions
    def p(*args, **kwargs):
        caller = inspect.currentframe(2)
        log_block(caller, logging.DEBUG, ' '.join(str(a) for a in args), **kwargs)

    @log_exceptions
    def pp(obj, indent = 1, width = 80, depth = 2, max_line_length = 200):
        caller = inspect.currentframe(2)
        obj = pprint.pformat(obj, indent = indent, width = width, depth = depth)
        log_block(caller, logging.DEBUG, obj.strip(), max_line_length = max_line_length)

    @log_exceptions
    def callinfo(depth):
        caller = inspect.currentframe(2)
        requested_caller = inspect.currentframe(depth + 2)
        cinfo = get_caller_info(requested_caller)
        log_block(caller, logging.DEBUG, '{i.file}:{i.lineno} ({i.func_name})'.format(i = cinfo))

    return collections.namedtuple('DebugLog', ['p', 'pp', 'callinfo'])(p, pp, callinfo)
