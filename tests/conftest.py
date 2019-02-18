from __future__ import unicode_literals

import sys

from tests.fixture_identify import identify
from tests.fixture_configs import configs

# Setup calibre paths.
sys.path.insert(0, '/usr/lib/calibre')
sys.resources_location = '/usr/share/calibre'
sys.extensions_location = '/usr/lib/calibre/calibre/plugins'

# Import all plugins. Without this, calibre_plugins imports don't work.
from calibre.customize.ui import all_metadata_plugins  # noqa


__all__ = [
    all_metadata_plugins,
    configs,
    identify,
]
