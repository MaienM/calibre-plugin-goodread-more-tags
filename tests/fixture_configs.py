from __future__ import print_function
from __future__ import unicode_literals
from __future__ import with_statement

import collections
from copy import deepcopy
import os.path

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
def config_dir(monkeypatch_s, tmpdir_s, config_instances):
    """
    Use a clean config location.

    Without this the configs of the actual calibre instance are used (and modified), which is undesirable.
    """
    import calibre.constants
    config_dir = tmpdir_s.join('config')
    monkeypatch_s.setattr(calibre.constants, 'config_dir', str(config_dir))

    # Change the file paths of existing instances.
    for instance in config_instances:
        if getattr(instance, 'file_path', None) is not None:
            try:
                instance.file_path = str(config_dir.join(os.path.basename(instance.file_path)))
            except AttributeError:
                pass # DynamicConfig has a dynamically calculated file_path.


@pytest.fixture(autouse = True, scope = 'session')
def config_instances():
    """ Keep track of all config instances, so that they can be reset to the defaults after every run. """
    instances = collections.defaultdict(lambda: [])
    def capture_instance(instance):
        cls = instance.__class__
        instances[cls].append(instance)
        # Mark with unique id, for debugging purposes.
        instance._test_id = '{}/{}'.format(cls.__name__, len(instances[cls]))

    import calibre.utils.config
    config_classes = [calibre.utils.config.DynamicConfig, calibre.utils.config.XMLConfig]

    # Setup capture for all new instances.
    for cls in config_classes:
        def __init__(self, *args, **kwargs):
            capture_instance(self)
            self._original___init__(*args, **kwargs)
        cls._original___init__ = cls.__init__
        cls.__init__ = __init__

    # Capture existing instances.
    import sys
    for name, module in sys.modules.items():
        if not name.startswith('calibre'):
            continue
        if module is None:
            continue
        for vname, var in vars(module).items():
            for cls in config_classes:
                if isinstance(var, cls):
                    capture_instance(var)
                    break

    yield [instance for cls_instances in instances.values() for instance in cls_instances]

    for cls in config_classes:
        cls.__init__ = cls._original___init__
        del cls._original___init__


@pytest.fixture(autouse = True)
def reset_config_instances(config_instances):
    def reset():
        for instance in config_instances:
            instance.clear()
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
        integration_enabled = gmt_configmodule.KEY_INTEGRATION_ENABLED,
        integration_timeout = gmt_configmodule.KEY_INTEGRATION_TIMEOUT,
    )

    return Configs(goodreads_more_tags = gmt_config)
