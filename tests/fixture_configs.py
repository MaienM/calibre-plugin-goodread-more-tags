from __future__ import print_function
from __future__ import unicode_literals
from __future__ import with_statement

from copy import deepcopy

import pytest


class Configs(object):
    def __init__(self, calibre, more_tags, goodreads):
        self.calibre = calibre
        self.more_tags = more_tags
        self.goodreads = goodreads


@pytest.fixture(autouse = True)
def configs():
    """
    A fixture that resets the configs of Calibre, the Goodreads plugin, and the Goodreads More Tags plugin to their
    defaults while active.

    Any changes made to the configs in this time will be reset after the tests finish.
    """
    from calibre.utils.config import JSONConfig
    import calibre.ebooks.metadata.sources.prefs as calibre_config
    import calibre_plugins.goodreads.config as goodreads_config
    import calibre_plugins.goodreads_more_tags.config as more_tags_config

    msprefs_original = calibre_config.msprefs
    msprefs = JSONConfig('/dev/null')
    msprefs.defaults = deepcopy(msprefs_original.defaults)
    calibre_config.msprefs = msprefs

    more_tags_original = more_tags_config.plugin_prefs
    more_tags = JSONConfig('/dev/null')
    more_tags.defaults = deepcopy(more_tags_original.defaults)
    more_tags_config.plugin_prefs = more_tags

    goodreads_original = goodreads_config.plugin_prefs
    goodreads = JSONConfig('/dev/null')
    goodreads.defaults = deepcopy(goodreads_original.defaults)
    goodreads_config.plugin_prefs = goodreads

    # The tests were written when the default settings were different. For now, use the old defaults during the tests.
    more_tags.defaults[more_tags_config.STORE_NAME][more_tags_config.KEY_THRESHOLD_PERCENTAGE] = 50

    yield Configs(msprefs, more_tags, goodreads)

    calibre_config.msprefs = msprefs_original
    more_tags_config.plugin_prefs = more_tags_original
    goodreads_config.plugin_prefs = goodreads_original
