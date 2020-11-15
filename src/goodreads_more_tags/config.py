from __future__ import print_function

from copy import deepcopy
from textwrap import dedent

from calibre.ebooks.txt.processor import convert_markdown
from calibre.gui2 import get_current_db, question_dialog
from calibre.gui2.complete2 import EditWithComplete
from calibre.gui2.metadata.config import ConfigWidget as DefaultConfigWidget
from calibre.utils.config import JSONConfig
try:
    from PyQt5 import Qt as QtGui, QtCore, QtWidgets
    import PyQt5.Qt as qt
except ImportError:
    from PyQt4 import QtGui, QtCore, QtWidgets
    import PyQt4.Qt as qt

__license__ = 'BSD 3-clause'
__copyright__ = '2019, Michon van Dooren <michon1992@gmail.com>'
__docformat__ = 'markdown en'


class NestingJSONConfig(JSONConfig):
    """ A JSONConfig that allows passing keys like ['foo', 'bar'] to mean ['foo']['bar']. """
    def _get_option_root(self, root, keys, create_as_needed = True):
        for key in keys[:-1]:
            if key not in root and create_as_needed:
                root[key] = {}
            root = root[key]
        return root

    def get(self, keys):
        root = self._get_option_root(self, keys)
        if keys[-1] not in root:
            root[keys[-1]] = self.get_default(keys)
        return root[keys[-1]]

    def set(self, keys, value):
        root = self._get_option_root(self, keys)
        root[keys[-1]] = value

    def get_default(self, keys):
        root = self._get_option_root(self.defaults, keys, False)
        return root[keys[-1]]

    def set_default(self, keys, value):
        root = self._get_option_root(self.defaults, keys)
        root[keys[-1]] = value

    def rename(self, old, new):
        try:
            old_root = self._get_option_root(self, old, False)
            self.set(new, old_root[old[-1]])
            del old_root[old[-1]]
        except KeyError:
            return

        old.pop()
        old_root = self._get_option_root(self, old, False)
        while old and len(old_root[old[-1]]) == 0:
            remove = old.pop()
            del old_root[remove]
            old_root = self._get_option_root(self, old, False)


CONFIG_LOCATION = 'plugins/goodreads-more-tags'

CATEGORY_THRESHOLD = 'thresholds'
CATEGORY_INTEGRATION = 'goodreadsPluginIntegration'

KEY_THRESHOLD_ABSOLUTE = [CATEGORY_THRESHOLD, 'absolute']
KEY_THRESHOLD_PERCENTAGE = [CATEGORY_THRESHOLD, 'percentage']
KEY_THRESHOLD_PERCENTAGE_OF = [CATEGORY_THRESHOLD, 'percentageOf']
KEY_INTEGRATION_ENABLED = [CATEGORY_INTEGRATION, 'enabled']
KEY_INTEGRATION_TIMEOUT = [CATEGORY_INTEGRATION, 'timeout']
KEY_SHELF_MAPPINGS = ['shelfMappings']

DEFAULT_THRESHOLD_ABSOLUTE = 10
DEFAULT_THRESHOLD_PERCENTAGE = 30
DEFAULT_THRESHOLD_PERCENTAGE_OF = [3, 4]
DEFAULT_INTEGRATION_ENABLED = True
DEFAULT_INTEGRATION_TIMEOUT = 10
DEFAULT_SHELF_MAPPINGS = {
    'adult': ['Adult'],
    'adult-fiction': ['Adult'],
    'adventure': ['Adventure'],
    'anthologies': ['Anthologies'],
    'art': ['Art'],
    'biography': ['Biography'],
    'business': ['Business'],
    'chick-lit': ['Chick-lit'],
    'childrens': ['Childrens'],
    'classics': ['Classics'],
    'comedy': ['Humour'],
    'comics': ['Comics'],
    'comics-manga': ['Comics'],
    'contemporary': ['Contemporary'],
    'cookbooks': ['Cookbooks'],
    'crime': ['Crime'],
    'essays': ['Writing'],
    'fantasy': ['Fantasy'],
    'feminism': ['Feminism'],
    'gardening': ['Gardening'],
    'gay': ['Gay'],
    'graphic-novels': ['Comics'],
    'graphic-novels-comics': ['Comics'],
    'graphic-novels-comics-manga': ['Comics'],
    'health': ['Health'],
    'historical-fiction': ['Historical', 'Fiction'],
    'history': ['History'],
    'horror': ['Horror'],
    'humor': ['Humour'],
    'inspirational': ['Inspirational'],
    'lgbt': ['Gay'],
    'manga': ['Comics'],
    'memoir': ['Biography'],
    'modern': ['Modern'],
    'music': ['Music'],
    'mystery': ['Mystery'],
    'non-fiction': ['Non-Fiction'],
    'paranormal': ['Paranormal'],
    'philosophy': ['Philosophy'],
    'poetry': ['Poetry'],
    'politics': ['Politics'],
    'psychology': ['Psychology'],
    'reference': ['Reference'],
    'religion': ['Religion'],
    'romance': ['Romance'],
    'sci-fi-and-fantasy': ['Science Fiction', 'Fantasy'],
    'sci-fi-fantasy': ['Science Fiction', 'Fantasy'],
    'science': ['Science'],
    'science-fiction': ['Science Fiction'],
    'science-fiction-fantasy': ['Science Fiction', 'Fantasy'],
    'self-help': ['Self Help'],
    'sf-fantasy': ['Science Fiction', 'Fantasy'],
    'sociology': ['Sociology'],
    'spirituality': ['Spirituality'],
    'suspense': ['Suspense'],
    'thriller': ['Thriller'],
    'travel': ['Travel'],
    'vampires': ['Vampires'],
    'war': ['War'],
    'western': ['Western'],
    'writing': ['Writing'],
    'ya': ['Young Adult'],
    'young-adult': ['Young Adult'],
}

# Load/initialize preferences.
plugin_prefs = NestingJSONConfig(CONFIG_LOCATION)
plugin_prefs.set_default(KEY_THRESHOLD_ABSOLUTE, DEFAULT_THRESHOLD_ABSOLUTE)
plugin_prefs.set_default(KEY_THRESHOLD_PERCENTAGE, DEFAULT_THRESHOLD_PERCENTAGE)
plugin_prefs.set_default(KEY_THRESHOLD_PERCENTAGE_OF, DEFAULT_THRESHOLD_PERCENTAGE_OF)
plugin_prefs.set_default(KEY_INTEGRATION_ENABLED, DEFAULT_INTEGRATION_ENABLED)
plugin_prefs.set_default(KEY_INTEGRATION_TIMEOUT, DEFAULT_INTEGRATION_TIMEOUT)
plugin_prefs.set_default(KEY_SHELF_MAPPINGS, deepcopy(DEFAULT_SHELF_MAPPINGS))

# Migrate settings.
renamed = (
    # Old, misspelled options.
    (['options', 'tresholdAbsolute'], KEY_THRESHOLD_ABSOLUTE),
    (['options', 'tresholdPercentage'], KEY_THRESHOLD_PERCENTAGE),
    (['options', 'tresholdPercentageOf'], KEY_THRESHOLD_PERCENTAGE_OF),
    # Options from when everything was a single category.
    (['options', 'thresholdAbsolute'], KEY_THRESHOLD_ABSOLUTE),
    (['options', 'thresholdPercentage'], KEY_THRESHOLD_PERCENTAGE),
    (['options', 'thresholdPercentageOf'], KEY_THRESHOLD_PERCENTAGE_OF),
    (['options', 'shelfMappings'], KEY_SHELF_MAPPINGS),
)
for old, new in renamed:
    plugin_prefs.rename(old, new)


def docmd2html(text):
    """ Process a docstring with markdown to html. """
    html = convert_markdown(dedent(text))
    html = html.replace('<td', '<td style="padding-right: 8px"')
    return html


class ScrollEventFilter(qt.QObject):
    """ An event filter that ignores scroll events. """
    def eventFilter(self, obj, event):
        return event.type() == qt.QEvent.Wheel


class EditWithCompleteWithoutScroll(EditWithComplete):
    """ Like EditWithComplete, but doesn't touch scroll events. """
    def __init__(self, *args, **kwargs):
        EditWithComplete.__init__(self, *args, **kwargs)
        self.setFocusPolicy(qt.Qt.StrongFocus)
        self.installEventFilter(ScrollEventFilter(self))


class ShelfTagMappingTableWidget(qt.QTableWidget):
    """ A widget to show a list of shelf name -> tag list mappings, and to edit the tag lists. """
    def __init__(self, parent, mappings):
        qt.QTableWidget.__init__(self, parent)

        # General look and feel.
        self.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)

        # Setup the columns.
        header_labels = ['Goodreads Shelf', 'Calibre Tag(s)']
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.setColumnWidth(0, 200)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().hide()

        # Load data.
        self.set_mappings(mappings)

    def get_mappings(self):
        mappings = {}
        for i in range(0, self.rowCount()):
            label = self.item(i, 0).text().strip()
            tags = list(filter(len, [t.strip() for t in self.cellWidget(i, 1).text().split(',')]))
            mappings[label] = tags
        return mappings

    def set_mappings(self, mappings):
        # Get the tags.
        all_tags = get_current_db().all_tags()

        # Load data.
        self.setRowCount(len(mappings))
        for i, (shelf, tags) in enumerate(sorted(mappings.items(), key = lambda x: x[0])):
            # Set the label for the shelf name.
            label = qt.QTableWidgetItem(shelf, qt.QTableWidgetItem.UserType)
            label.setFlags(qt.Qt.ItemIsSelectable | qt.Qt.ItemIsEnabled)
            self.setItem(i, 0, label)

            # Set an editable field for the tags cell.
            tbtags = EditWithCompleteWithoutScroll(self)
            tbtags.setText(', '.join(tags))
            tbtags.update_items_cache(all_tags)
            self.setCellWidget(i, 1, tbtags)

    def get_selected_shelf(self):
        row = self.currentRow()
        if row >= 0:
            return self.item(row, 0).text().strip()

    def set_selected_shelf(self, shelf):
        for i in range(0, self.rowCount()):
            label = self.item(i, 0).text().strip()
            if label == shelf:
                self.setCurrentCell(i, 0)
                return
        raise ValueError('Shelf not found')


class ShelfTagMappingWidget(qt.QWidget):
    """ A widget to manage a list of shelf name -> tag list mappings. """
    def __init__(self, parent, mapping):
        qt.QWidget.__init__(self, parent)
        self.layout = qt.QHBoxLayout(self)

        # Add the table.
        self.table = ShelfTagMappingTableWidget(self, mapping)
        self.layout.addWidget(self.table)

        # Add buttons next to the tag table to add/remove tags.
        self.button_layout = qt.QVBoxLayout()
        self.layout.addLayout(self.button_layout)

        # Button to add a new mapping.
        add_mapping_button = QtGui.QToolButton(self)
        add_mapping_button.setToolTip('Add mapping')
        add_mapping_button.setIcon(qt.QIcon(I('plus.png')))
        add_mapping_button.clicked.connect(self.add_mapping)
        self.button_layout.addWidget(add_mapping_button)

        # Button to remove a mapping.
        remove_mapping_button = QtGui.QToolButton(self)
        remove_mapping_button.setToolTip('Remove mapping')
        remove_mapping_button.setIcon(qt.QIcon(I('minus.png')))
        remove_mapping_button.clicked.connect(self.delete_mapping)
        self.button_layout.addWidget(remove_mapping_button)

        # Button to reset the mappings to the default set.
        reset_defaults_button = QtGui.QToolButton(self)
        reset_defaults_button.setToolTip('Reset to default mappings')
        reset_defaults_button.setIcon(qt.QIcon(I('edit-undo.png')))
        reset_defaults_button.clicked.connect(self.reset_to_defaults)
        self.button_layout.addWidget(reset_defaults_button)

        # Add stretch to position the buttons at the top.
        self.button_layout.addStretch()

    def get_mappings(self):
        return self.table.get_mappings()

    def add_mapping(self):
        # Prompt for the shelf name.
        shelf, ok = qt.QInputDialog.getText(
            self,
            'Add new mapping',
            'Enter the Goodreads shelf name to create a mapping for:',
        )
        if not ok:
            return
        shelf = shelf.strip()
        if not shelf:
            return

        # Add an empty mapping, unless one already exists for this shelf.
        mappings = self.get_mappings()
        if shelf not in mappings:
            mappings[shelf] = []
            self.table.set_mappings(mappings)

        # Select the (possibly new) mapping.
        self.table.set_selected_shelf(shelf)

    def delete_mapping(self):
        # Check whether anything is selected.
        shelf = self.table.get_selected_shelf()
        if not shelf:
            return

        # Prompt for confirmation.
        if not question_dialog(
            self,
            _('Are you sure?'),
            'Are you sure you want to delete the mapping for Goodreads shelf "{}"?'.format(shelf),
        ):
            return

        # Remove the mapping.
        mappings = self.get_mappings()
        del mappings[shelf]
        self.table.set_mappings(mappings)

    def reset_to_defaults(self):
        # Prompt for confirmation.
        if not question_dialog(
            self,
            _('Are you sure?'),
            'Are you sure you want to reset the mappings to the defaults?',
        ):
            return

        # Reset the mappings.
        self.table.set_mappings(DEFAULT_SHELF_MAPPINGS)


class ToolTipIcon(qt.QLabel):
    """ An icon that shows a tooltip when hovered over. """
    def __init__(self, pixmap, tooltip, *args, **kwargs):
        qt.QLabel.__init__(self, *args, **kwargs)
        self.setPixmap(pixmap)
        self.tooltip = tooltip
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        qt.QToolTip.showText(event.globalPos(), self.tooltip, self)


class PseudoFormLayoutWithHelp(qt.QGridLayout):
    """
    A QGridLayout that has been modified to work sort of like a QFormLayout, but with a third element in each row to
    provide "help" text for the row.
    """
    def addRow(self, label, widget, description = None):
        row = self.rowCount()

        if not isinstance(label, qt.QLabel):
            label = qt.QLabel(label)
        label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.addWidget(label, row, 0)

        if description:
            pixmap = qt.QIcon(I('dialog_question.png')).pixmap(16, 16)
            tooltip_icon = ToolTipIcon(pixmap, description)
            tooltip_icon.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
            self.addWidget(tooltip_icon, row, 1)

        self.addWidget(widget, row, 2)


class CollapsibleGroupBox(QtWidgets.QWidget):
    """
    A groupbox that can be collapsed.

    Based on https://stackoverflow.com/a/52617714.
    """
    def __init__(self, title = '', parent = None):
        super(CollapsibleGroupBox, self).__init__(parent)

        self.toggle_button = QtWidgets.QToolButton(text = title, checkable = True, checked = True)
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(QtCore.Qt.RightArrow)
        self.toggle_button.pressed.connect(self.onPressed)

        self.content_area = QtWidgets.QScrollArea(maximumHeight = 0, minimumHeight = 0)
        self.content_area.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.content_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.toggle_animation = QtCore.QParallelAnimationGroup(self)
        self.toggle_animation.addAnimation(QtCore.QPropertyAnimation(self, b'minimumHeight'))
        self.toggle_animation.addAnimation(QtCore.QPropertyAnimation(self, b'maximumHeight'))
        self.toggle_animation.addAnimation(QtCore.QPropertyAnimation(self.content_area, b'maximumHeight'))

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content_area)

    @QtCore.pyqtSlot()
    def onPressed(self):
        self.setOpen(self.toggle_button.isChecked())

    def setOpen(self, should_be_open):
        original_height = self.toggle_button.sizeHint().height()

        if should_be_open:
            self.toggle_button.setArrowType(QtCore.Qt.DownArrow)
            self.toggle_animation.setDirection(QtCore.QAbstractAnimation.Forward)
        else:
            self.toggle_button.setArrowType(QtCore.Qt.RightArrow)
            self.toggle_animation.setDirection(QtCore.QAbstractAnimation.Backward)

        content_height = self.content_area.layout().sizeHint().height()
        self.setAnimation(0, original_height, original_height + content_height)
        self.setAnimation(1, original_height, original_height + content_height)
        self.setAnimation(2, 0, content_height)

        self.toggle_animation.start()

    def setContentLayout(self, layout):
        oldLayout = self.content_area.layout()
        del oldLayout
        self.content_area.setLayout(layout)

    def setAnimation(self, animationIndex, start, end):
        animation = self.toggle_animation.animationAt(animationIndex)
        animation.setDuration(500)
        animation.setStartValue(start)
        animation.setEndValue(end)


class ConfigWidget(DefaultConfigWidget):
    def __init__(self, plugin):
        DefaultConfigWidget.__init__(self, plugin)

        # By default, the settings contain a single groupbox with a listview in it. We want to make this a bit more
        # efficient (and pretty), so we will create a new hlayout for bot the default listview, as well as our custom
        # groups.
        self.w_ext = qt.QWidget()
        self.l_ext = qt.QVBoxLayout(self.w_ext)
        self.l.addWidget(self.w_ext, *self.l.getItemPosition(self.l.indexOf(self.gb)))
        self.l.removeWidget(self.gb)
        self.gb.hide()

        # Now we want to move over the listview into the new layout. We'll also style it a bit.
        self.gb.l.removeWidget(self.fields_view)
        self.l_ext.addWidget(self.fields_view)
        self.fields_view.setStyleSheet('QListView::item { margin: 2px 0; }')
        self.fields_view.setSelectionMode(qt.QAbstractItemView.NoSelection)

        # Add all groupboxes for the various settings.
        self.add_groupbox_thresholds()
        self.add_groupbox_goodreads_plugin_integration()

        # Finally, we add a custom widget to manage the shelf -> tags mappings.
        self.table = ShelfTagMappingWidget(self, plugin_prefs.get(KEY_SHELF_MAPPINGS))
        self.l.addWidget(self.table, self.l.rowCount(), 0, 1, self.l.columnCount())
        self.l.setRowStretch(self.l.rowCount() - 1, 1)

        # Open default groupboxes now. Cannot be done earlier because doing so before all items are laid out results in
        # some calculations returning the wrong values, messing up the layout.
        self.gb_thresholds.setOpen(True)

    def add_groupbox(self, name):
        gb = CollapsibleGroupBox(name)
        gb.l = PseudoFormLayoutWithHelp()
        gb.setContentLayout(gb.l)
        self.l_ext.addWidget(gb)
        return gb

    def add_groupbox_thresholds(self):
        gb = self.gb_thresholds = self.add_groupbox('Thresholds')

        # A setting to determine the threshold of the amount of people that need to have put a book in a shelf before it
        # is considered.
        self.threshold_abs = qt.QSpinBox()
        self.threshold_abs.setMinimum(0)
        self.threshold_abs.setValue(plugin_prefs.get(KEY_THRESHOLD_ABSOLUTE))
        gb.l.addRow('Threshold (absolute)', self.threshold_abs, description = docmd2html('''
            The minimum amount of people that have to have provided a tag before it will be included.
        '''))

        shelves_example = '''
            Let's take a book with the following shelves as example:<br />

            Shelf             | Votes
            :---              |:---
            `to-read`         | 1,000
            `fantasy`         | 300
            `fiction`         | 200
            `classics`        | 150
            `sci-fi-fantasy`  | 70
            `science-fiction` | 50
            `young-adult`     | 30
            `ya`              | 15
            `non-fiction`     | 7
            `self-help`       | 4

            This results in the following tags when using the default mappings:<br />

            Tag               | Votes
            :---              |:---
            `Fantasy`         | 370 (300 + 70)
            `Fiction`         | 200
            `Classics`        | 150
            `Science Fiction` | 120 (70 + 50)
            `Young Adult`     | 45 (30 + 15)
            `Non-Fiction`     | 7
            `Self Help`       | 4
        '''

        # A setting to determine the threshold of the amount of people that need to have put a book in a shelf before it
        # is considered, as a percentage of something else.
        self.threshold_pct = qt.QDoubleSpinBox()
        self.threshold_pct.setMinimum(0)
        self.threshold_pct.setMaximum(100)
        self.threshold_pct.setSuffix('%')
        self.threshold_pct.setValue(plugin_prefs.get(KEY_THRESHOLD_PERCENTAGE))
        gb.l.addRow('Threshold (percentage)', self.threshold_pct, description = docmd2html((
            '''
            The minimum amount of people that have to have provided a tag before it will be included, as a percentage
            of the total amount of people that have provided the top tag (or another metric, see the next setting).
            ''' +
            shelves_example +
            '''
            Using just the top tag as base, the percentage specified here will be relative to the `Fantasy` tag. Let's
            pretend this setting is set to 10%. This means that the `Fantasy`, `Fiction`, `Classics`, `Science Fiction`,
            and `Young Adult` tags will be included, but the `Non-Fiction` and `Self Help` tags will be ignored.

            Notice that this is tag based, not shelf based. In the above example, the `young-adult` and `ya` shelves
            were below the threshold, but because they both map to the `Young Adult` tag, this tag had enough votes to be
            included.
            '''
        )))

        # A setting to determine what the previous setting is based on.
        self.threshold_pct_of = qt.QLineEdit()
        self.threshold_pct_of.setValidator(qt.QRegExpValidator(qt.QRegExp(r'^[0-9]+(,\s*[0-9]+)*$')))
        self.threshold_pct_of.setText(', '.join([str(p) for p in plugin_prefs.get(KEY_THRESHOLD_PERCENTAGE_OF)]))
        gb.l.addRow('Threshold percentage is based on', self.threshold_pct_of, description = docmd2html((
            '''
            What the percentage specified in the previous setting is based on. This is expressed as a comma-separated
            list of numbers indicating the places that should be used. The average of the tags in these places will be
            used.
            ''' +
            shelves_example +
            '''
            Using these tags, some examples of values for this field would be:<br />

            Value     | Included Tags                        | Math                 | Result
            :---      |:---                                  |:---                  |:---
            `1`       | `Fantasy`                            | `avg(370)`           | 370
            `1, 2`    | `Fantasy`, `Fiction`                 | `avg(370, 200)`      | 285
            `1, 2, 3` | `Fantasy`, `Fiction`, `Classics`     | `avg(370, 200, 150)` | 240
            `1, 3, 5` | `Fantasy`, `Classics`, `Young Adult` | `avg(370, 150, 45)`  | 188
            `3, 4`    | `Classics`, `Science Fiction`        | `avg(150, 120)`      | 135
            `1, 20`   | `Fantasy` (no tag in position 20)    | `avg(370)`           | 370

            The `Result` column contains the value that that the previous setting will be a percentage of.
            '''
        )))

    def add_groupbox_goodreads_plugin_integration(self):
        gb = self.gb_integration = self.add_groupbox('Goodreads Plugin Integration')

        # A setting to enable/disable the integration entirely.
        self.goodreads_enabled = qt.QCheckBox()
        self.goodreads_enabled.setChecked(plugin_prefs.get(KEY_INTEGRATION_ENABLED))
        gb.l.addRow('Enabled', self.goodreads_enabled, description = docmd2html('''
            Whether to enable the integration with the Goodreads plugin (if present).

            If this is enabled, this plugin will attempt to grab any new goodreads ids found by the Goodreads plugin,
            and will then lookup tags for these. This allows getting tags for books in the first metadata download.

            If this is not enabled, this plugin will only get tags for books that already have a goodreads id when the
            metadata download starts, based on this goodreads id. This means that a second metadata download will be
            required if the goodreads id is added or changed in a download.
        '''))

        # A setting to determine how long to wait for the base Goodreads plugin to get results.
        self.goodreads_timeout = qt.QSpinBox()
        self.goodreads_timeout.setMinimum(0.1)
        self.goodreads_timeout.setValue(plugin_prefs.get(KEY_INTEGRATION_TIMEOUT))
        gb.l.addRow('Timeout', self.goodreads_timeout, description = docmd2html('''
            The amount of time (in seconds) to wait for the base Goodreads plugin to provide us with goodreads id(s).

            If the Goodreads plugin is still running after this time, we will continue with any ids it has provided us with
            already. If we've not received any ids from it, we will continue as if integration were not enabled.
        '''))

    def commit(self):
        DefaultConfigWidget.commit(self)

        # Store the custom settings.
        plugin_prefs.set(KEY_THRESHOLD_ABSOLUTE, self.threshold_abs.value())
        plugin_prefs.set(KEY_THRESHOLD_PERCENTAGE, self.threshold_pct.value())
        plugin_prefs.set(KEY_THRESHOLD_PERCENTAGE_OF, [int(idx.strip()) for idx in self.threshold_pct_of.text().split(',')])
        plugin_prefs.set(KEY_SHELF_MAPPINGS, self.table.get_mappings())

    def resizeEvent(self, event):
        DefaultConfigWidget.resizeEvent(self, event)

        # Shrink the section containing the fields-to-download checkboxes to create more space for the rest.
        fv = self.fields_view
        m = fv.model()
        lastIndex = m.index(m.rowCount() - 1, fv.modelColumn())
        rect = fv.rectForIndex(lastIndex)
        fv.setFixedHeight(rect.y() + rect.height() + 3)
