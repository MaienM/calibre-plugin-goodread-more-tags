from calibre.ebooks.metadata.sources.base import Source, fixcase, fixauthors

__license__   = 'BSD 3-clause'
__copyright__ = '2019, Michon van Dooren <michon1992@gmail.com>'
__docformat__ = 'markdown en'


class GoodreadsMoreTags(Source):
    name = 'Goodreads More Tags'
    description = 'Scrape more tags from Goodreads'
    author = 'Michon van Dooren'

    version = (1, 0, 0)
    minimum_calibre_version = (0, 7, 53)
    supported_platforms = ['windows', 'osx', 'linux']

    capabilities = frozenset(['identify'])
    touched_fields = frozenset(['identifier:goodreads', 'tags'])

    def config_widget(self):
        """
        Overriding the default configuration screen for our own custom configuration.
        """
        from .config import ConfigWidget
        return ConfigWidget(self)

    def cli_main(self, *args, **kwargs):
        from calibre.gui2 import Application
        app = Application([])
        plugin = GoodreadsMoreTags(__file__)
        config = plugin.config_widget()
        config.show()

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

        app.exec_()

