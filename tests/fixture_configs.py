from __future__ import print_function
from __future__ import unicode_literals
from __future__ import with_statement

from copy import deepcopy

import pytest


class Configs(object):
    def __init__(self, **configs):
        self.__dict__.update(configs)


class ConfigWrapper(object):
    """ Wrapper around a plugin's config that makes the settings available as properties. """
    def __init__(self, prefs, **attributes):
        self.prefs = prefs

        # To dynamically add properties we need to modify the class, so clone the class first to avoid sharing
        # properties between all plugins.
        cls = type(self)
        cls = type(cls.__name__, (cls,), {})
        self.__class__ = cls

        for name, key in attributes.items():
            prop = property(self.getter(key), self.setter(key))
            setattr(cls, name, prop)

    def getter(self, key):
        return lambda s: s.get(key)

    def setter(self, key):
        return lambda s, v: s.prefs.set(key, v)


@pytest.fixture(autouse = True, scope = 'session')
def config_dir(monkeypatch_s, tmpdir_s):
    """
    Use a clean config location.

    Without this the configs of the actual calibre instance are used (and modified), which is undesirable.
    """
    import calibre.constants
    config_dir = str(tmpdir_s.join('config'))
    monkeypatch_s.setattr(calibre.constants, 'config_dir', config_dir)


@pytest.fixture(autouse = True, scope = 'session')
def config_instances():
    _config_instances = []

    # Keep track of all configs, so that they can be reset to the defaults after every run.
    from calibre.utils.config import JSONConfig
    def __init__(self, *args, **kwargs):
        _config_instances.append(self)
        self._original___init__(*args, **kwargs)
    JSONConfig._original___init__ = JSONConfig.__init__
    JSONConfig.__init__ = __init__

    yield _config_instances

    JSONConfig.__init__ = JSONConfig._original___init__
    del JSONConfig._original___init__


@pytest.fixture(autouse = True)
def reset_config_instances(config_instances):
    def reset():
        for instance in config_instances:
            for k, v in instance.defaults.items():
                instance[k] = v
    reset()
    return reset


@pytest.fixture
def configs(monkeypatch, tmpdir):
    """
    A fixture that resets the configs of Calibre, the Goodreads plugin, and the Goodreads More Tags plugin to their
    defaults while active.

    Any changes made to the configs in this time will be reset after the tests finish.
    """
    # Wrap the config to make it easier to change.
    import calibre_plugins.goodreads_more_tags.config as gmt_configmodule
    gmt_config = ConfigWrapper(
        gmt_configmodule.plugin_prefs,
        treshold_absolute = gmt_configmodule.KEY_THRESHOLD_ABSOLUTE,
        treshold_percentage = gmt_configmodule.KEY_THRESHOLD_PERCENTAGE,
        treshold_percentage_of = gmt_configmodule.KEY_THRESHOLD_PERCENTAGE_OF,
        integration_enabled = gmt_configmodule.KEY_GOODREADS_INTEGRATION_ENABLED,
        integration_timeout = gmt_configmodule.KEY_GOODREADS_INTEGRATION_TIMEOUT,
    )

    return Configs(goodreads_more_tags = gmt_config)
