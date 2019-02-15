from __future__ import print_function

from copy import deepcopy
from textwrap import dedent

from calibre.ebooks.txt.processor import convert_markdown
from calibre.gui2 import get_current_db, question_dialog
from calibre.gui2.complete2 import EditWithComplete
from calibre.gui2.metadata.config import ConfigWidget as DefaultConfigWidget
from calibre.utils.config import JSONConfig
try:
    from PyQt5 import Qt as QtGui
    import PyQt5.Qt as qt
except ImportError:
    from PyQt4 import QtGui
    import PyQt4.Qt as qt

__license__ = 'BSD 3-clause'
__copyright__ = '2019, Michon van Dooren <michon1992@gmail.com>'
__docformat__ = 'markdown en'

CONFIG_LOCATION = 'plugins/goodreads-more-tags'
STORE_NAME = 'options'

KEY_TRESHOLD_ABSOLUTE = 'tresholdAbsolute'
KEY_TRESHOLD_PERCENTAGE = 'tresholdPercentage'
KEY_TRESHOLD_PERCENTAGE_OF = 'tresholdPercentageOf'
KEY_SHELF_MAPPINGS = 'shelfMappings'

DEFAULT_TRESHOLD_ABSOLUTE = 10
DEFAULT_TRESHOLD_PERCENTAGE = 50
DEFAULT_TRESHOLD_PERCENTAGE_OF = [3, 4]
DEFAULT_SHELF_MAPPINGS = {
    'adult-fiction': ['Adult'],
    'adult': ['Adult'],
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
    'glbt': ['Gay'],
    'graphic-novels': ['Comics'],
    'graphic-novels-comics': ['Comics'],
    'graphic-novels-comics-manga': ['Comics'],
    'health': ['Health'],
    'historical-fiction': ['Historical', 'Fiction'],
    'history': ['History'],
    'horror': ['Horror'],
    'humor': ['Humour'],
    'inspirational': ['Inspirational'],
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
    'young-adult': ['Young Adult'],
    'ya': ['Young Adult'],
}

DEFAULT_STORE_VALUES = {
    KEY_TRESHOLD_ABSOLUTE: DEFAULT_TRESHOLD_ABSOLUTE,
    KEY_TRESHOLD_PERCENTAGE: DEFAULT_TRESHOLD_PERCENTAGE,
    KEY_TRESHOLD_PERCENTAGE_OF: DEFAULT_TRESHOLD_PERCENTAGE_OF,
    KEY_SHELF_MAPPINGS: deepcopy(DEFAULT_SHELF_MAPPINGS)
}

# Load/initialize preferences.
plugin_prefs = JSONConfig(CONFIG_LOCATION)
plugin_prefs.defaults[STORE_NAME] = DEFAULT_STORE_VALUES


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
            tags = filter(len, [t.strip() for t in self.cellWidget(i, 1).text().split(',')])
            mappings[label] = tags
        return mappings

    def set_mappings(self, mappings):
        # Get the tags.
        all_tags = get_current_db().all_tags()

        # Load data.
        self.setRowCount(len(mappings))
        for i, (shelf, tags) in enumerate(sorted(mappings.iteritems(), key = lambda x: x[0])):
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
        shelf = unicode(shelf).strip()
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
        shelf = self.get_selected_shelf()
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
        self.addWidget(label, row, 0)

        if description:
            pixmap = qt.QIcon(I('dialog_question.png')).pixmap(16, 16)
            tooltip_icon = ToolTipIcon(pixmap, description)
            self.addWidget(tooltip_icon, row, 1)

        self.addWidget(widget, row, 2)


class ConfigWidget(DefaultConfigWidget):
    def __init__(self, plugin):
        DefaultConfigWidget.__init__(self, plugin)
        config = plugin_prefs[STORE_NAME]

        # By default, the settings contain a single groupbox with a listview in it. We want to make this a bit more
        # efficient (and pretty), so we will create a new groupbox that will replace the existing groupbox, which
        # will contain all simple settings.
        self.gb_ext = qt.QGroupBox('Settings')
        self.gb_ext.l = PseudoFormLayoutWithHelp(self.gb_ext)
        self.l.addWidget(self.gb_ext, *self.l.getItemPosition(self.l.indexOf(self.gb)))
        self.l.removeWidget(self.gb)
        self.gb.hide()

        # Now we want to move over the listview into the new groupbox. We'll also style it a bit.
        self.gb.l.removeWidget(self.fields_view)
        self.gb_ext.l.addRow((self.gb.title() + ':').replace('::', ':'), self.fields_view)
        self.fields_view.setStyleSheet('QListView::item { margin: 2px 0; }')
        self.fields_view.setSelectionMode(qt.QAbstractItemView.NoSelection)

        # A setting to determine the treshold of the amount of people that need to have put a book in a shelf before it
        # is considered.
        self.treshold_abs = qt.QSpinBox()
        self.treshold_abs.setMinimum(0)
        self.treshold_abs.setValue(config[KEY_TRESHOLD_ABSOLUTE])
        self.gb_ext.l.addRow('Treshold (absolute)', self.treshold_abs, description = docmd2html('''
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

        # A setting to determine the treshold of the amount of people that need to have put a book in a shelf before it
        # is considered, as a percentage of something else.
        self.treshold_pct = qt.QDoubleSpinBox()
        self.treshold_pct.setMinimum(0)
        self.treshold_pct.setMaximum(100)
        self.treshold_pct.setSuffix('%')
        self.treshold_pct.setValue(config[KEY_TRESHOLD_PERCENTAGE])
        self.gb_ext.l.addRow('Treshold (percentage)', self.treshold_pct, description = docmd2html((
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
            were below the treshold, but because they both map to the `Young Adult` tag, this tag had enough votes to be
            included.
            '''
        )))

        # A setting to determine what the previous setting is based on.
        self.treshold_pct_of = qt.QLineEdit()
        self.treshold_pct_of.setValidator(qt.QRegExpValidator(qt.QRegExp(r'^[0-9]+(,\s*[0-9]+)*$')))
        self.treshold_pct_of.setText(', '.join([str(p) for p in config[KEY_TRESHOLD_PERCENTAGE_OF]]))
        self.gb_ext.l.addRow('Treshold percentage is based on', self.treshold_pct_of, description = docmd2html((
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

        # Finally, we add a custom widget to manage the shelf -> tags mappings.
        self.table = ShelfTagMappingWidget(self, config[KEY_SHELF_MAPPINGS])
        self.l.addWidget(self.table, self.l.rowCount(), 0, 1, self.l.columnCount())
        self.l.setRowStretch(self.l.rowCount() - 1, 1)

    def commit(self):
        DefaultConfigWidget.commit(self)

        # Store the custom settings.
        prefs = {}
        prefs[KEY_TRESHOLD_ABSOLUTE] = self.treshold_abs.value()
        prefs[KEY_TRESHOLD_PERCENTAGE] = self.treshold_pct.value()
        prefs[KEY_TRESHOLD_PERCENTAGE_OF] = [int(idx.strip()) for idx in self.treshold_pct_of.text().split(',')]
        prefs[KEY_SHELF_MAPPINGS] = self.table.get_mappings()
        plugin_prefs[STORE_NAME] = prefs

    def resizeEvent(self, event):
        DefaultConfigWidget.resizeEvent(self, event)

        # Shrink the section containing the fields-to-download checkboxes to create more space for the rest.
        fv = self.fields_view
        m = fv.model()
        lastIndex = m.index(m.rowCount() - 1, fv.modelColumn())
        rect = fv.rectForIndex(lastIndex)
        fv.setFixedHeight(rect.y() + rect.height() + 3)
