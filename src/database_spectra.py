import os
import sqlite3
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt


class DatabasePeakPosition(QtWidgets.QMainWindow):
    """ Creating the main window containing list with all peak positions in database """
    closeSignal = QtCore.pyqtSignal()
    plot_peak_position_signal = QtCore.pyqtSignal(list, int, int)
    remove_peak_position_signal = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.path_of_database = os.path.join(os.path.dirname(__file__), 'database_peakpositions.db')
        self.n_materials = 0    # number of plotted materials

        self.setWindowTitle('Data base peak positions')
        self.resize(QtCore.QSize(900, 450))
        self.entries()
        self.create_menubar()
        self.create_searchbar()

    def entries(self):
        """ Connection to databank and create table if not existing """
        if os.path.exists(self.path_of_database):
            conn = sqlite3.connect(self.path_of_database)
            c = conn.cursor()
        else:
            conn = sqlite3.connect(self.path_of_database)
            c = conn.cursor()
            c.execute('''CREATE TABLE stocks (ID int, material text, comments text, peak_positions text, reference text, 
            doi text)''')
        c.execute('SELECT * FROM stocks')
        allentries = c.fetchall()  # get all entries stored in databank
        self.headerList = list(map(lambda x: x[0], c.description))  # get header stored in databank as description
        conn.close()

        # Build a QTreeWidget to display databank
        w = QtWidgets.QWidget()
        self.entryList = QtWidgets.QTreeWidget(w)

        tree_widget_items = []  # List of TreeWidgetItems
        for j in allentries:
            zs = list(map(str, j))
            tree_widget_items.append(QtWidgets.QTreeWidgetItem(self.entryList, zs))

        self.entryList.setColumnCount(len(self.headerList))
        self.entryList.setHeaderLabels(self.headerList)  # ID only for programming reason
        self.entryList.hideColumn(0)  # Hide column with ID
        self.entryList.setSortingEnabled(True)
        self.entryList.setSelectionMode(QtWidgets.QTreeWidget.ExtendedSelection)
        for twi in tree_widget_items:
            self.entryList.addTopLevelItem(twi)
            twi.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable |
                         QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsTristate)
            twi.setCheckState(1, QtCore.Qt.Unchecked)

        self.entryList.itemChanged.connect(self.update_entry)
        self.entryList.itemChanged.connect(self.plot_peak_position)
        self.setCentralWidget(self.entryList)

    def create_menubar(self):
        """ create a menubar """
        menubar = self.menuBar()
        menubar.addAction("New Entry", self.new_entry)

    def create_searchbar(self):
        """ create a searchbar """
        dockWidget = QtWidgets.QDockWidget('Searchbar', self)
        layout = QtWidgets.QVBoxLayout()
        self.searchbar = QtWidgets.QLineEdit()
        layout.addWidget(self.searchbar)
        self.addDockWidget(Qt.RightDockWidgetArea, dockWidget)
        self.searchbar.textChanged.connect(self.search)

        self.search_checklist = QtWidgets.QListWidget()
        i = 0
        for j in self.headerList:
            self.search_checklist.insertItem(i, j)
            i = i + 1

        self.search_checklist.item(0).setHidden(True)
        layout.addWidget(self.search_checklist)

        emptywidget = QtWidgets.QWidget()
        dockWidget.setWidget(emptywidget)
        emptywidget.setLayout(layout)

    def search(self, text):
        # search function
        black = QtGui.QBrush()  # define black color
        red = QtGui.QBrush()  # define red color
        redC = QtGui.QColor()
        redC.setRgb(255, 0, 0, alpha=255)
        red.setColor(redC)

        col = self.search_checklist.currentRow()  # get Column to search in

        root = self.entryList.invisibleRootItem()  # loop over all items and set color black
        child_count = root.childCount()
        for i in range(child_count):
            item = root.child(i)
            item.setForeground(col, black)

        if text == '':
            return
        else:
            for j in self.entryList.findItems(text, QtCore.Qt.MatchContains, column=col):
                j.setForeground(col, red)

    def keyPressEvent(self, event):
        if event.matches(QtGui.QKeySequence.Delete):
            item = self.entryList.currentItem()
            self.remove_entry(item)
        else:
            super(DatabasePeakPosition, self).keyPressEvent(event)

    def new_entry(self):
        item = QtWidgets.QTreeWidgetItem(self.entryList)
        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsUserCheckable |
                      QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsTristate)
        item.setCheckState(1, QtCore.Qt.Unchecked)
        self.entryList.addTopLevelItem(item)
        item.setText(0, str(self.entryList.topLevelItemCount()-1))
        conn = sqlite3.connect(self.path_of_database)
        c = conn.cursor()
        query = "INSERT INTO stocks (ID, material, comments, peak_positions, reference, doi) VALUES (?, ?, ?, ?, ?, ?)"
        columnValues = (item.text(0), item.text(1), item.text(2), item.text(3), item.text(4), item.text(5))
        c.execute(query, columnValues)
        conn.commit()
        conn.close()

    def remove_entry(self, item):
        id = item.text(0)
        conn = sqlite3.connect(self.path_of_database)
        c = conn.cursor()

        # delete entry
        c.execute('DELETE FROM stocks WHERE ID = ?', (id,))

        # get all remaining entries
        c.execute('SELECT * FROM stocks')
        all_entries = c.fetchall()
        # reorder them, so there is no gap in ID numbers
        new_id = range(len(all_entries))
        for a, ni in zip(all_entries, new_id):
            c.execute('UPDATE stocks SET ID=?  where ID=?', (ni, a[0]))

        conn.commit()
        conn.close()

        self.entryList.takeTopLevelItem(self.entryList.indexOfTopLevelItem(item))

        self.remove_peak_position_signal.emit(-1)
        self.entries()

    def update_entry(self, item, col):
        conn = sqlite3.connect(self.path_of_database)
        c = conn.cursor()
        query = 'UPDATE stocks SET material=?, comments=?, peak_positions=?, reference=?, doi=?  where ID=?'
        content = (item.text(1), item.text(2), item.text(3), item.text(4), item.text(5), item.text(0))
        c.execute(query, content)
        conn.commit()
        conn.close()

    def plot_peak_position(self, item, column):
        if item.text(3) != "":
            peak_pos = item.text(3).split(",")
            peak_pos = [float(pp) for pp in peak_pos]
            id = int(item.text(0))
        else:
            return

        if item.checkState(column) == Qt.Checked:
            self.plot_peak_position_signal.emit(peak_pos, id, self.n_materials)
            self.n_materials += 1
        if item.checkState(column) == Qt.Unchecked:
            self.remove_peak_position_signal.emit(id)
            self.n_materials -= 1

    def closeEvent(self, event):
        self.closeSignal.emit()
        event.accept()