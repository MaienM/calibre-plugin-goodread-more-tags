from __future__ import unicode_literals

import sys

from tests.fixture_browser import browser
from tests.fixture_configs import *
from tests.fixture_fix_underscore import fix_underscore
from tests.fixture_generic import *
from tests.fixture_identify import identify

# Setup calibre paths.
sys.path.insert(0, '/usr/lib/calibre')
sys.resources_location = '/usr/share/calibre'
sys.extensions_location = '/usr/lib/calibre/calibre/plugins'

# Import all plugins. Without this, calibre_plugins imports don't work.
from calibre.customize.ui import all_metadata_plugins  # noqa


collect_ignore = [
    'scripts/',
]

