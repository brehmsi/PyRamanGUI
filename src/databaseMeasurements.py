import os
import platform
import sqlite3
import subprocess
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QMessageBox, QLineEdit, QPushButton, QWidget, QTreeWidget,
                             QTreeWidgetItem, QDockWidget, QListWidget, QLabel)
from datetime import date


class DatabaseMeasurements(QMainWindow):
    """ Creating the main window containing the list of all measurements """

    def __init__(self):
        super().__init__()
        self.path_of_database = os.path.join(os.path.dirname(__file__), 'sampleDatabase.db')
        self.date = str(date.today())
        self.sample = ''
        self.material_class = ''
        self.wavelength = ''
        self.donor = ''
        self.loc = ''  # memory location

        self.header_list = None
        self.entry_list = None
        self.searchbar = None
        self.search_checklist = None
        self.ew = None

        self.setWindowTitle('Data base Raman measurements')
        self.entries()
        self.create_menubar()
        self.create_searchbar()

    def entries(self):
        # Connection to databank and create table if not existing
        if os.path.exists(self.path_of_database):
            conn = sqlite3.connect(self.path_of_database)
            c = conn.cursor()
        else:
            conn = sqlite3.connect(self.path_of_database)
            c = conn.cursor()
            c.execute(
                '''CREATE TABLE stocks (ID int, Date text, Sample text, Material text, Wavelength text, Donor text, 
                Location text)''')
        c.execute('SELECT * FROM stocks')
        all_entries = c.fetchall()  # get all entries stored in databank
        self.header_list = list(map(lambda x: x[0], c.description))  # get header stored in databank as description
        conn.close()

        # Build a QTreeWidget to display databank
        twi = []  # List of TreeWidgetItems
        for j in all_entries:
            zs = list(map(str, j))
            twi.append(QTreeWidgetItem(zs))
        w = QWidget()
        self.entry_list = QTreeWidget(w)
        self.entry_list.setColumnCount(len(self.header_list))
        self.entry_list.setHeaderLabels(self.header_list)  # ID only for programming reason
        self.entry_list.hideColumn(0)  # Hide column with ID
        self.entry_list.setSortingEnabled(True)
        self.entry_list.setSelectionMode(QTreeWidget.ExtendedSelection)
        for j in twi:
            self.entry_list.addTopLevelItem(j)
        self.entry_list.itemDoubleClicked.connect(self.on_item_clicked)
        self.setCentralWidget(self.entry_list)

    def create_menubar(self):
        # create a menubar
        menubar = self.menuBar()
        menubar.addAction('New Entry', self.open_entry_window)
        menubar.addAction('Edit Entry', self.open_entry_window)
        menubar.addAction('Delete Entry', self.delete_entry)
        menubar.addAction('Undo', self.undo)

    def create_searchbar(self):
        # create a searchbar
        dock_widget = QDockWidget('Searchbar', self)
        layout = QVBoxLayout()
        self.searchbar = QLineEdit()
        layout.addWidget(self.searchbar)
        self.addDockWidget(Qt.RightDockWidgetArea, dock_widget)
        self.searchbar.textChanged.connect(self.search)

        self.search_checklist = QListWidget()
        i = 0
        for j in self.header_list:
            self.search_checklist.insertItem(i, j)
            i = i + 1

        self.search_checklist.item(0).setHidden(True)
        layout.addWidget(self.search_checklist)

        empty_widget = QtWidgets.QWidget()
        dock_widget.setWidget(empty_widget)
        empty_widget.setLayout(layout)

    def open_entry_window(self):
        # opens a new window to insert a new databank entry
        sel = self.entry_list.selectedItems()  # check if a databank entry is selected
        if sel:  # and sets selected entry as default for new entry
            self.date = sel[0].text(1)
            self.sample = sel[0].text(2)
            self.material_class = sel[0].text(3)
            self.wavelength = sel[0].text(4)
            self.donor = sel[0].text(5)
            self.loc = sel[0].text(6)
        else:
            pass

        action = self.sender()  # check if entry should overwrite an old one
        self.ew = EntryWindow(self)  # or create a new entry
        self.ew.show()
        if action.text() == 'New Entry':
            self.ew.entryUpdateSignal.connect(self.new_entry)
        elif action.text() == 'Edit Entry':
            self.ew.entryUpdateSignal.connect(self.change_entry)
        else:
            print('Something is wrong!')

    def new_entry(self):
        # transfers entry of entry window into an entry of the database
        ew = self.ew
        conn = sqlite3.connect(self.path_of_database)
        c = conn.cursor()
        c.execute('SELECT * FROM stocks')
        a = c.fetchall()
        if not a:
            id_new = 0
        else:
            id_new = max([j[0] for j in a]) + 1
        c.execute(
            " INSERT INTO stocks (ID, Date, Sample, Material, Wavelength, Donor, Location) VALUES "
            "(?, ?, ?, ?, ?, ?, ?)", (id_new, ew.date, ew.sample, ew.material_class, ew.wavelength, ew.donor, ew.loc))
        conn.commit()
        conn.close()
        self.entries()

    def change_entry(self):
        # change entry of the database into entry of the entry window
        ew = self.ew
        id_change = []
        for j in self.entry_list.selectedItems():
            id_change.append(j.text(0))

        conn = sqlite3.connect(self.path_of_database)
        c = conn.cursor()
        sqlite_update_query = 'UPDATE stocks set Date=?, Sample=?, Material=?, Wavelength=?, Donor=?, Location=? ' \
                              ' where ID = ?'
        for j in id_change:
            column_values = (ew.date, ew.sample, ew.material_class, ew.wavelength, ew.donor, ew.loc, j)
            c.execute(sqlite_update_query, column_values)
        conn.commit()
        conn.close()
        self.ew.close()
        self.entries()

    def delete_entry(self):
        # deletes entry of the databank
        id_delete = []
        for j in self.entry_list.selectedItems():
            id_delete.append(j.text(0))

        conn = sqlite3.connect(self.path_of_database)
        c = conn.cursor()
        for j in id_delete:
            c.execute('DELETE FROM stocks WHERE ID = ?', (j,))
        conn.commit()
        conn.close()

        self.entries()

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def on_item_clicked(self, item, col):
        # opens file folder of clicked path
        if col == 6:
            path = item.text(col)
            if platform.system() == "Windows":
                try:
                    os.startfile(path)
                except FileNotFoundError:
                    print('File not found')
                    return
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        else:
            return

    def search(self, text):
        # search function
        black = QtGui.QBrush()  # define black color
        red = QtGui.QBrush()  # define red color
        red_color = QtGui.QColor()
        red_color.setRgb(255, 0, 0, alpha=255)
        red.setColor(red_color)

        col = self.search_checklist.currentRow()  # get Column to search in

        root = self.entry_list.invisibleRootItem()  # loop over all items and set color black
        child_count = root.childCount()
        for i in range(child_count):
            item = root.child(i)
            item.setForeground(col, black)

        if text == '':
            return
        else:
            for j in self.entry_list.findItems(text, QtCore.Qt.MatchContains, column=col):
                j.setForeground(col, red)

    def undo(self):
        # undo function
        print("This function doesn't work yet!")

    # rollback()

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Question', "Should the application be closed?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


class EntryWindow(QMainWindow):
    """ entry window """
    entryUpdateSignal = QtCore.pyqtSignal()

    def __init__(self, mw, parent=None):
        super(EntryWindow, self).__init__(parent)
        self.mw = mw
        self.date = mw.date
        self.sample = mw.sample
        self.material_class = mw.material_class
        self.wavelength = mw.wavelength
        self.donor = mw.donor
        self.loc = mw.loc

        self.setGeometry(400, 400, 200, 200)
        self.setWindowTitle('Database entry')
        wid = QtWidgets.QWidget(self)
        self.setCentralWidget(wid)
        self.layout = QtWidgets.QGridLayout()

        self.label_date = QLabel('Date:')
        self.layout.addWidget(self.label_date, 1, 0)
        self.DateWidget = QLineEdit(self)
        self.DateWidget.resize(400, 40)
        self.DateWidget.setText(self.date)
        self.layout.addWidget(self.DateWidget, 1, 1)

        self.label_sample = QLabel('Sample:')
        self.layout.addWidget(self.label_sample, 2, 0)
        self.SampleWidget = QLineEdit(self)
        self.SampleWidget.resize(280, 40)
        self.SampleWidget.setText(self.sample)
        self.layout.addWidget(self.SampleWidget, 2, 1)

        self.label_material_class = QLabel('Material Class:')
        self.layout.addWidget(self.label_material_class, 3, 0)
        self.material_class_widget = QLineEdit(self)
        self.material_class_widget.resize(280, 40)
        self.material_class_widget.setText(self.material_class)
        self.layout.addWidget(self.material_class_widget, 3, 1)

        self.label_wavelength = QLabel('Wavelength:')
        self.layout.addWidget(self.label_wavelength, 4, 0)
        self.WavelengthWidget = QLineEdit(self)
        self.WavelengthWidget.resize(280, 40)
        self.WavelengthWidget.setText(self.wavelength)
        self.layout.addWidget(self.WavelengthWidget, 4, 1)

        self.label_Donor = QLabel('Sample Donor:')
        self.layout.addWidget(self.label_Donor, 5, 0)
        self.DonorWidget = QLineEdit(self)
        self.DonorWidget.resize(280, 40)
        self.DonorWidget.setText(self.donor)
        self.layout.addWidget(self.DonorWidget, 5, 1)

        self.label_Loc = QLabel('Memory Location:')
        self.layout.addWidget(self.label_Loc, 6, 0)
        self.LocWidget = QLineEdit(self)
        self.LocWidget.resize(280, 40)
        self.LocWidget.setText(self.loc)
        self.layout.addWidget(self.LocWidget, 6, 1)

        self.buttonNewEntry = QPushButton('Insert', self)
        self.buttonNewEntry.setToolTip("Entry is added")
        self.layout.addWidget(self.buttonNewEntry, 7, 0)
        self.buttonNewEntry.clicked.connect(self.new_entry)

        self.buttonCancel = QPushButton('Cancel', self)
        self.buttonCancel.setToolTip("Cancel")
        self.layout.addWidget(self.buttonCancel, 7, 1)
        self.buttonCancel.clicked.connect(self.cancel)

        wid.setLayout(self.layout)

    def new_entry(self):
        self.date = str(self.DateWidget.text())
        self.sample = self.SampleWidget.text()
        self.material_class = self.material_class_widget.text()
        self.wavelength = self.WavelengthWidget.text()
        self.donor = self.DonorWidget.text()
        self.loc = self.LocWidget.text()
        self.entryUpdateSignal.emit()

    def cancel(self):
        self.close()
