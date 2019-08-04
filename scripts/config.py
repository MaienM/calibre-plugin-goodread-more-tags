#!./scripts/kill-and-run.sh

from calibre.gui2 import Application
from calibre_plugins.goodreads_more_tags import GoodreadsMoreTags

if __name__ == '__main__':
    app = Application([])
    plugin = GoodreadsMoreTags(__file__)
    config = plugin.config_widget()
    _locals = locals()

    def embed():
        import IPython
        app = _locals['app']
        plugin = _locals['plugin']
        config = _locals['config']
        IPython.embed()

    import threading
    thread = threading.Thread(target = embed)
    thread.daemon = True
    thread.start()

    config.show()
    app.exec_()
