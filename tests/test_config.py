import pytest


class TestNestingJSONConfig(object):
    @pytest.fixture
    def create(self, tmpdir):
        import json
        from calibre_plugins.goodreads_more_tags.config import NestingJSONConfig

        def create(data):
            tmpdir.join('config.json').write(json.dumps(data))
            return NestingJSONConfig('config.json', str(tmpdir))
        return create

    def test_get__simple(self, create):
        config = create({
            'name': 'foo',
        })
        assert config.get(['name']) == 'foo'

    def test_get__nested(self, create):
        config = create({
            'options': {
                'name': 'foo',
            },
        })
        assert config.get(['options', 'name']) == 'foo'

    def test_get__nested_missing_using_default(self, create):
        config = create({
            'options': {},
        })
        config.defaults = {
            'options': {
                'name': 'bar',
            },
        }
        assert config.get(['options', 'name']) == 'bar'

    def test_get__nested_parent_missing_using_default(self, create):
        config = create({})
        config.defaults = {
            'options': {
                'name': 'bar',
            },
        }
        assert config.get(['options', 'name']) == 'bar'

    def test_get__nested_missing_no_default(self, create):
        config = create({
            'options': {},
        })
        with pytest.raises(KeyError):
            config.get(['options', 'name'])

    def test_get__nested_parent_missing_no_default(self, create):
        config = create({})
        with pytest.raises(KeyError):
            config.get(['options', 'name'])

    def test_set__simple(self, create):
        config = create({})
        config.set(['name'], 'foo')
        assert config == { 'name': 'foo' }

    def test_set__nested(self, create):
        config = create({ 'options': {} })
        config.set(['options', 'name'], 'foo')
        assert config == { 'options': { 'name': 'foo' } }

    def test_set__nested_parent_missing(self, create):
        config = create({})
        config.set(['options', 'name'], 'foo')
        assert config == { 'options': { 'name': 'foo' } }

    def test_get_default__simple(self, create):
        config = create({})
        config.defaults = { 'name': 'foo' }
        assert config.get_default(['name']) == 'foo'

    def test_get_default__nested(self, create):
        config = create({})
        config.defaults = { 'options': { 'name': 'foo' } }
        assert config.get_default(['options', 'name']) == 'foo'

    def test_get_default__missing(self, create):
        config = create({})
        config.defaults = {}
        with pytest.raises(KeyError):
            config.get_default(['name'])
        assert config == {}
        assert config.defaults == {}

    def test_get_default__nested_missing(self, create):
        config = create({})
        config.defaults = { 'options': {} }
        with pytest.raises(KeyError):
            config.get_default(['options', 'name'])
        assert config == {}
        assert config.defaults == { 'options': {} }

    def test_get_default__nested_parent_missing(self, create):
        config = create({})
        config.defaults = {}
        with pytest.raises(KeyError):
            config.get_default(['options', 'name'])
        assert config == {}
        assert config.defaults == {}

    def test_rename__simple(self, create):
        config = create({ 'name': 'foo' })
        config.rename(['name'], ['title'])
        assert config == { 'title': 'foo' }

    def test_rename__missing(self, create):
        config = create({ 'name': 'foo' })
        config.rename(['label'], ['title'])
        assert config == { 'name': 'foo' }

    def test_rename__nested(self, create):
        config = create({ 'options': { 'name': 'foo' } })
        config.rename(['options', 'name'], ['options', 'title'])
        assert config == { 'options': { 'title': 'foo' } }

    def test_rename__nested_missing(self, create):
        config = create({ 'options': { 'name': 'foo' } })
        config.rename(['options', 'label'], ['options', 'title'])
        assert config == { 'options': { 'name': 'foo' } }

    def test_rename__nested_parent_missing(self, create):
        config = create({ 'options': { 'name': 'foo' } })
        config.rename(['foo', 'label'], ['options', 'title'])
        assert config == { 'options': { 'name': 'foo' } }

    def test_rename__nested_existing_section(self, create):
        config = create({ 'options': { 'name': 'foo' }, 'other': {} })
        config.rename(['options', 'name'], ['other', 'title'])
        assert config == { 'other': { 'title': 'foo' } }

    def test_rename__nested_new_section(self, create):
        config = create({ 'options': { 'name': 'foo' } })
        config.rename(['options', 'name'], ['other', 'title'])
        assert config == { 'other': { 'title': 'foo' } }

    def test_rename__nested_keep_nonempty_section(self, create):
        config = create({ 'options': { 'name': 'foo', 'title': 'bar' } })
        config.rename(['options', 'name'], ['other', 'name'])
        assert config == { 'options': { 'title': 'bar' }, 'other': { 'name': 'foo' } }
