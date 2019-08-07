import re

import pytest


@pytest.fixture(scope = 'session')
def monkeypatch_s():
    from _pytest.monkeypatch import MonkeyPatch
    mpatch = MonkeyPatch()

    yield mpatch

    mpatch.undo()
    

@pytest.fixture(scope = 'session')
def tmpdir_s(request, tmpdir_factory):
    name = request.node.name
    name = re.sub(r"[\W]", "_", request.node.name)[:30]
    return tmpdir_factory.mktemp(name, numbered = True)
