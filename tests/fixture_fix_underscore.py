from __future__ import print_function

from gettext import gettext
import sys

import pytest


@pytest.fixture(autouse = True)
def fix_underscore():
    """
    The doctests appear to use the _ variable, but calibre expects this to be a gettext function.

    This fixture sets the global _ in all modules to be exactly that, to avoid issues in calibre.
    """
    for name, module in sys.modules.items():
        if module is not None and hasattr(module, '_'):
            module._ = gettext
