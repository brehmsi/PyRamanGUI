#Autor: Simon Brehm
import beepy
import io
import math
import matplotlib
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches

import numpy as np
import operator
import os
import pickle
import rampy as rp
import re
import scipy
import sympy as sp
import sys
from packaging import version

from collections import ChainMap
from matplotlib import *
from matplotlib.figure import Figure
from matplotlib.backend_bases import MouseEvent
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
import matplotlib.backends.qt_editor.figureoptions as figureoptions
if version.parse(matplotlib.__version__) <= version.parse('3.3.3'):
    from matplotlib.backends.qt_compat import _setDevicePixelRatioF as _setDevicePixelRatio
else:
    from matplotlib.backends.qt_compat import _setDevicePixelRatio as _setDevicePixelRatio
    print("This version of matplotlib will most likely not support all functions of PyRaman. Best version is 3.3.0")
from matplotlib.backends.qt_compat import _devicePixelRatioF
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSlot, QObject
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QMessageBox, QPushButton, QCheckBox,
                             QTreeWidgetItem, QTableWidgetItem, QItemDelegate, QLineEdit, QPushButton, QWidget, QMenu,
                             QAction, QDialog, QFileDialog, QAbstractItemView)
from matplotlib.backends.qt_editor import _formlayout as formlayout
from scipy import sparse
from scipy import signal
from scipy.optimize import curve_fit
from scipy.sparse.linalg import spsolve
from sympy.utilities.lambdify import lambdify
from tabulate import tabulate

# Import files
import myfigureoptions  # see file 'myfigureoptions.py'
import Database_Measurements  # see file Database_Measurements


# This file essentially consists of three parts:
# 1. Main Window
# 2. Text Window
# 3. Spreadsheet
# 4. Plot


########################################################################################################################
# 1. Main window
########################################################################################################################
class RamanTreeWidget(QtWidgets.QTreeWidget):
    """
    A reimplementation of the PyQt QTreeWidget.

    the mouseDoubleClickEvent, mousePressEvent, startDrag and DropEvent are modified

    Attributes
    ----------
    itemDoubleClicked : pyqtSignal
        signal emitted by doubleclick on QTreeWidgetItem
    itemClicked : pyqtSignal
        signal emitted by click on QTreeWidgetItem
    itemDropped : pyqtSignal
        signal emitted by dropping QTreeWidgetItem
    dragged_item : QTreeWidgetItem
        QTreeWidgetItem, which was selected by a mouseclick

    Methods
    -------
    mouseDoubleClickEvent(event)
        emits signal if QTreeWidgetItem was doubleclicked
    mousePressEvent(event)
        emits signal if QTreeWidgetItem was clicked
    startDrag(action)
        assigns selected QTreeWidgetItem to drag_item
    dropEvent(event)
        emits pyqtSignal if QTreeWidgetItem is dropped
    """
    itemDoubleClicked = QtCore.pyqtSignal(object)
    itemClicked = QtCore.pyqtSignal(object, object)
    itemDropped = QtCore.pyqtSignal(object, object)

    def __init__(self, parent=None):
        """
        Parameters
        ----------
        parent : class, optional
            (default is None)
        """
        super(RamanTreeWidget, self).__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setHeaderHidden(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(self.InternalMove)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def mouseDoubleClickEvent(self, event):
        """
        Parameters
        ----------
        event : QMouseEvent            #The mouse event.
        """
        item = self.itemAt(event.pos())
        if item is not None:
            self.itemDoubleClicked.emit(item)
        else:
            return

    def mousePressEvent(self, event):
        """
        Parameters
        ----------
        event : QMouseEvent           #The mouse event.
        """
        item = self.itemAt(event.pos())
        if item is not None:
            self.setCurrentItem(item)
        else:
            pass
        self.itemClicked.emit(event, item)

        # keep the default behaviour
        super(RamanTreeWidget, self).mousePressEvent(event)

    def startDrag(self, action):
        """
        Parameters
        ----------
        action : Qt.DropAction
        """
        self.dragged_item = self.selectedItems()[0]

        # keep the default behaviour
        super(RamanTreeWidget, self).startDrag(action)

    def dropEvent(self, event):
        """
        Paramters
        ---------
        event : QDropEvent
        """
        event.setDropAction(Qt.MoveAction)
        itemAtDropLocation = self.itemAt(event.pos())

        if itemAtDropLocation is None:
            # no drops outside of folders
            return
        elif itemAtDropLocation.parent() != self.dragged_item.parent():
            # send signal if parents (folder) of item changes during drag-drop-event
            self.itemDropped.emit(self.dragged_item, itemAtDropLocation)

        # keep the default behaviour
        super(RamanTreeWidget, self).dropEvent(event)


class MainWindow(QMainWindow):
    """
    Creating the main window
    """

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.window_types = ['Folder', 'Spreadsheet', 'Plotwindow', 'Textwindow']
        self.window = {}  # dictionary with windows
        self.windowWidget = {}
        for j in self.window_types:
            self.window[j] = {}
            self.windowWidget[j] = {}
        self.folder = {}  # key = foldername, value = [Qtreewidgetitem, QmdiArea]
        self.FileName = os.path.dirname(__file__)  # path of this python file
        self.PyramanIcon = QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/PyRaman_logo.png")
        self.pHomeRmn = None  # path of Raman File associated to the open project
        self.db_measurements = None
        self.mainWidget = QtWidgets.QSplitter(self)
        self.treeWidget = RamanTreeWidget(self)  # Qtreewidget, to controll open windows
        self.tabWidget = QtWidgets.QTabWidget()
        self.statusBar = QtWidgets.QStatusBar()

        self.create_mainwindow()

    def create_mainwindow(self):
        """
        Create the main window
        """
        self.setWindowIcon(self.PyramanIcon)
        self.setWindowTitle('PyRaman')  # set window title

        # the user can control the size of child widgets by dragging the boundary between them
        self.mainWidget.setHandleWidth(10)

        self.tabWidget.setTabsClosable(True)
        self.tabWidget.setMovable(True)
        self.tabWidget.tabCloseRequested.connect(self.close_tab)
        self.treeWidget.itemDoubleClicked.connect(self.activate_window)
        self.treeWidget.itemClicked.connect(self.tree_window_options)
        self.treeWidget.itemDropped.connect(self.change_folder)
        self.new_Folder(None)

        self.mainWidget.addWidget(self.treeWidget)
        self.mainWidget.addWidget(self.tabWidget)
        self.setCentralWidget(self.mainWidget)

        self.setStatusBar(self.statusBar)
        self.show_statusbar_message('Welcome to PyRaman', 3000)

        self.create_menubar()

    def create_menubar(self):
        """
        create a menu bar
        """
        menu = self.menuBar()
        File = menu.addMenu('File')
        FileNew = File.addMenu('New')
        FileNew.addAction('Spreadsheet', lambda: self.new_window(None, 'Spreadsheet', None, None))
        FileNew.addAction('Textwindow', lambda: self.new_window(None, 'Textwindow', '', None))
        FileNew.addAction('Folder', lambda: self.new_Folder(None))
        File.addAction('Open Project', self.open)
        File.addAction('Save Project As ...', lambda: self.save('Save As'))
        File.addAction('Save Project', lambda: self.save('Save'))

        medit = menu.addMenu('Edit')
        medit.addAction('Cascade')
        medit.addAction('Tiled')
        medit.triggered[QAction].connect(self.rearange)

        menu_tools = menu.addMenu('Tools')
        menu_tools.addAction('Database for measurements', self.execute_database_measurements)

    def show_statusbar_message(self, message, time, error_sound=False):
        self.statusBar.showMessage(message, time)
        if error_sound:
            beepy.beep(sound=3)

    def keyPressEvent(self, event):
        """
        A few shortcuts
        """
        key = event.key()
        if key == (Qt.Key_Control and Qt.Key_S):
            self.save('Save')
            self.show_statusbar_message('The project was saved', 2000)
        else:
            super(MainWindow, self).keyPressEvent(event)

    def open(self):
        # Load project in new MainWindow or in existing MW, if empty
        if self.window['Spreadsheet'] == {} and self.window['Plotwindow'] == {}:
            self.load()
        else:
            new_MainWindow()

    def load(self):
        """
        Load project from rmn file with pickle
        @return: None
        """
        fileName = QtWidgets.QFileDialog.getOpenFileName(self, 'Load',  # get file name
                                                         self.pHomeRmn, 'All Files (*);;Raman Files (*.rmn)')

        if fileName[0] != '':  # if fileName is not empty save in pHomeRmn
            self.pHomeRmn = fileName[0]
        else:
            self.close()
            return

        # open file and save content in variable 'v' with pickle
        with open(self.pHomeRmn, 'rb') as file:
            v = pickle.load(file)

        self.treeWidget.clear()
        self.tabWidget.clear()
        self.folder = {}
        for foldername, foldercontent in v.items():
            self.new_Folder(foldername)
            for key, val in foldercontent.items():
                self.new_window(foldername, val[0], val[1], key)

    def save(self, q):
        """
        function to save complete project in rmn-File with pickle

        Parameters:
        -----------
        q: str

        """

        # Ask for directory, if none is deposite or 'Save Project As' was pressed
        if self.pHomeRmn is None or q == 'Save As':
            fileName = QtWidgets.QFileDialog.getSaveFileName(self, 'Save as', self.pHomeRmn,
                                                             'All Files (*);;Raman Files (*.rmn)')
            if fileName[0] != '':
                self.pHomeRmn = fileName[0]
            else:
                return

        save_dict = {}
        for key, val in self.folder.items():
            save_dict[key] = {}
            for j in range(val[0].childCount()):
                win_name = val[0].child(j).text(0)
                win_type = self.window_types[val[0].child(j).type()]
                window = self.window[win_type][win_name]
                if win_type == 'Spreadsheet':
                    save_dict[key][win_name] = [win_type, window.data]
                elif win_type == 'Plotwindow':
                    save_dict[key][win_name] = [win_type, [window.data, window.fig]]
                elif win_type == 'Textwindow':
                    save_dict[key][win_name] = [win_type, window.text]

        # Test if file can be saved
        saveControllParam = 0
        file = open(os.path.splitext(self.pHomeRmn)[0] + '_test' +
                    os.path.splitext(self.pHomeRmn)[1], 'wb')
        try:
            pickle.dump(save_dict, file)
        except TypeError as e:
            self.show_statusbar_message('TypeError \n Someting went wrong. The file is not saved \n' + str(e), 4000)
            print(str(e))
            saveControllParam = 1
        file.close()

        if saveControllParam == 0:
            file = open(self.pHomeRmn, 'wb')
            try:
                pickle.dump(save_dict, file)
            except TypeError as e:
                self.show_statusbar_message('TypeError \n Someting went wrong. The file is not saved \n' + str(e), 4000)
            file.close()
            os.remove(os.path.splitext(self.pHomeRmn)[0] + '_test' +
                      os.path.splitext(self.pHomeRmn)[1])
        else:
            saveControllParam = 0

    def execute_database_measurements(self):
        title = 'Database'
        self.db_measurements = Database_Measurements.DatabaseMeasurements()
        DBM_tab = self.tabWidget.addTab(self.db_measurements, self.PyramanIcon, title)

    def create_sidetree_structure(self, structure):
        self.treeWidget.clear()
        for key, val in structure.items():
            self.new_Folder(key)

    def activate_window(self, item):
        text = item.text(0)
        winTypInt = item.type()  # 0 - Folder, 1 - Spreadsheet, 2 - Plotwindow, 3 - Textwindow

        if winTypInt == 0:  #
            self.tabWidget.setCurrentWidget(self.folder[text][1])
        else:
            windowtype = self.window_types[winTypInt]
            win = self.windowWidget[windowtype][text]
            currentFolder = item.parent().text(0)
            self.tabWidget.setCurrentWidget(self.folder[currentFolder][1])
            self.folder[currentFolder][1].setActiveSubWindow(win)
            win.showMaximized()

    def tree_window_options(self, event, tree_item):
        if tree_item is not None:
            if event.button() == QtCore.Qt.RightButton:
                item_text = tree_item.text(0)
                TreeItemMenu = QMenu()
                ActRename = TreeItemMenu.addAction('Rename')
                ActDelete = TreeItemMenu.addAction('Delete')
                ActCopy = TreeItemMenu.addAction('Copy')
                ac = TreeItemMenu.exec_(self.treeWidget.mapToGlobal(event.pos()))
                window_type = self.window_types[tree_item.type()]

                if ac == ActRename:
                    self.treeWidget.editItem(tree_item)
                    self.treeWidget.itemChanged.connect(lambda item, column:
                                                        self.rename_window(item, column, item_text))
                elif ac == ActDelete:
                    if tree_item.type() == 0:  # if item is folder:
                        self.close_folder(foldername=tree_item.text(0))
                    else:
                        title = tree_item.text(0)
                        self.windowWidget[window_type][title].close()
                elif ac == ActCopy:
                    window_name = tree_item.text(0)
                    window = self.window[window_type][window_name]
                    if window_type == 'Spreadsheet':
                        data = [window_type, window.data.copy()]
                    elif window_type == 'Plotwindow':
                        # no deepcopy of figure possible => pickle
                        buf = io.BytesIO()
                        pickle.dump(window.fig, buf)
                        buf.seek(0)
                        fig_copy = pickle.load(buf)
                        data = [window_type, [window.data.copy(), fig_copy]]
                    elif window_type == 'Textwindow':
                        data = [window_type, window.text]
                    else:
                        return
                    folder_name = self.tabWidget.tabText(self.tabWidget.currentIndex())
                    self.new_window(folder_name, data[0], data[1], window_name+"_Copy")

        else:
            if event.button() == QtCore.Qt.RightButton:
                TreeItemMenu = QMenu()
                MenuNew = TreeItemMenu.addMenu('&New')
                ActNewFolder = MenuNew.addAction('Folder')
                ActNewSpreadsheet = MenuNew.addAction('Spreadsheet')
                ActNewText = MenuNew.addAction('Text window')
                ac = TreeItemMenu.exec_(self.treeWidget.mapToGlobal(event.pos()))
                # Rename
                if ac == ActNewFolder:
                    self.new_Folder(None)
                elif ac == ActNewSpreadsheet:
                    self.new_window(None, 'Spreadsheet', None, None)
                elif ac == ActNewText:
                    self.new_window(None, 'Textwindow', '', None)

    def change_folder(self, droppedItem, itemAtDropLocation):
        """function is called every time a qtreewidgetitem is dropped"""
        if itemAtDropLocation.parent() is None:
            new_folder = itemAtDropLocation
        else:
            new_folder = itemAtDropLocation.parent()
        foldername = new_folder.text(0)
        windowtyp = droppedItem.type()
        windowname = droppedItem.text(0)
        if new_folder.type() == 0 and droppedItem.type() != 0:  # dropevent in folder
            previous_folder = droppedItem.parent().text(0)
            self.tabWidget.setCurrentWidget(self.folder[previous_folder][1])
            wind = self.window[self.window_types[windowtyp]][windowname]
            mdi = self.folder[foldername][1]
            new_subwindow = mdi.addSubWindow(wind)
            previous_mdi = self.folder[previous_folder][1]
            previous_mdi.removeSubWindow(wind)
            self.windowWidget[self.window_types[windowtyp]][windowname] = new_subwindow
            self.delete_empty_subwindows(previous_mdi)
        else:
            return

    def delete_empty_subwindows(self, mdi):
        sub_win_list = mdi.subWindowList()
        for j in sub_win_list:
            if j.widget() is None:
                mdi.removeSubWindow(j)

    def rename_window(self, item, column, old_text):
        new_text = item.text(column)
        windowtype = self.window_types[item.type()]

        if new_text == old_text:
            self.show_statusbar_message('Something went wrong', 4000)
            i = 1
            while i <= 100:
                new_text = "{} {}".format(windowtype, i)
                if new_text in self.window[windowtype].keys():
                    i += 1
                else:
                    break
            item.setText(0, new_text)
            window_names = []
            for wt in self.window_types:
                window_names.append(self.window[wt].keys())
            window_names = [item for sublist in window_names for item in sublist]
            tree_items_names = []
            for i in range(self.treeWidget.topLevelItemCount()):
                c = self.treeWidget.topLevelItem(i)
                for j in range(c.childCount()):
                    tree_items_names.append(c.child(j).text(0))
            old_text = set(window_names).difference(set(tree_items_names)).pop()
            new_text = set(tree_items_names).difference(set(window_names)).pop()

        if new_text in self.window[windowtype].keys():  # in case name is already assigned
            try:
                self.treeWidget.itemChanged.disconnect()
            except TypeError as e:
                print(e)
            item.setText(0, old_text)
            self.show_statusbar_message('Name is already assigned', 4000)
        else:
            if windowtype == 'Folder':
                self.folder[new_text] = self.folder.pop(old_text)
                index = self.tabWidget.indexOf(self.folder[new_text][1])
                self.tabWidget.setTabText(index, new_text)
            else:
                try:
                    win = self.windowWidget[windowtype][old_text]
                except KeyError as e:
                    self.treeWidget.itemChanged.disconnect()
                    return
                win.setWindowTitle(new_text)
                self.window[windowtype][new_text] = self.window[windowtype].pop(old_text)
                self.windowWidget[windowtype][new_text] = self.windowWidget[windowtype].pop(old_text)
                self.window[windowtype][new_text].setWindowTitle(new_text)
                self.update_spreadsheet_menubar()
            try:
                self.treeWidget.itemChanged.disconnect()
            except TypeError as e:
                print(e)

    def rearange(self, q):
        # rearange open windows
        if q.text() == "Cascade":
            self.tabWidget.currentWidget().cascadeSubWindows()

        if q.text() == "Tiled":
            self.tabWidget.currentWidget().tileSubWindows()

    def new_window(self, foldername, windowtype, windowcontent, title):
        if foldername is None:
            foldername = self.tabWidget.tabText(self.tabWidget.currentIndex())
            if foldername == 'Database':
                self.show_statusbar_message('please open window in other folder', 4000)
                return

        if title is None:
            i = 1
            while i <= 100:
                title = windowtype + ' ' + str(i)
                if title in self.window[windowtype].keys():
                    i += 1
                else:
                    break

        if windowtype == 'Spreadsheet':
            if windowcontent is None:
                ssd = windowcontent
            else:
                # change old data format to new format
                if isinstance(windowcontent, dict):
                    ssd = []
                    for key, val in windowcontent.items():
                        ssd.append({"data": val[0], "shortname": val[1], "type": val[2], "filename": val[3],
                                    "longname": None, "unit": None, "comments": None, "formula": None})
                else:
                    ssd = windowcontent

            windowtypeInt = 1
            self.window[windowtype][title] = SpreadSheetWindow(ssd, parent=self)
            newSS = self.window[windowtype][title]
            newSS.new_pw_signal.connect(lambda: self.new_window(None, 'Plotwindow', [newSS.plot_data, None], None))
            newSS.add_pw_signal.connect(lambda pw_name: self.add_Plot(pw_name, newSS.plot_data))
            icon = QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/Icon_spreadsheet.png")
        elif windowtype == 'Plotwindow':
            windowtypeInt = 2
            plotData, fig = windowcontent
            # change old data format to new format
            if not isinstance(plotData[0], dict):
                for idx, pd in enumerate(plotData):
                    plotData[idx] = {"x": pd[0],
                                     "y": pd[1],
                                     "yerr": pd[5],
                                     "plot type": pd[4],
                                     "label": pd[2],
                                     "xaxis": None,
                                     "yaxis": None,
                                     "filename": pd[3],
                                     "spreadsheet title": pd[6]
                                     }

            if fig is not None:
                # necessary to avoid weird error:
                # (ValueError: figure size must be positive finite not [ 4.58 -0.09])
                fig.set_size_inches([10, 10])
            self.window[windowtype][title] = PlotWindow(plotData, fig, self)
            self.update_spreadsheet_menubar()
            icon = QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/Icon_plotwindow.png")
        elif windowtype == 'Textwindow':
            windowtypeInt = 3
            txt = windowcontent
            self.window[windowtype][title] = TextWindow(self, txt)
            icon = QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/Icon_textwindow.png")
        else:
            return

        self.windowWidget[windowtype][title] = self.folder[foldername][1].addSubWindow(self.window[windowtype][title])
        self.window[windowtype][title].setWindowTitle(title)
        self.window[windowtype][title].show()

        item = QTreeWidgetItem([title], type=windowtypeInt)
        item.setIcon(0, icon)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled |
                      Qt.ItemIsUserCheckable)

        self.folder[foldername][0].addChild(item)
        self.window[windowtype][title].closeWindowSignal.connect(self.close_window)

    def new_Folder(self, title):
        if title is None:
            i = 1
            while i <= 100:
                title = 'Folder ' + str(i)
                if title in self.folder.keys():
                    i += 1
                else:
                    break

        self.folder[title] = []  # first entry contains QTreeWidgetItem (Folder), second contains QMdiArea
        self.folder[title].append(QTreeWidgetItem([title]))
        self.folder[title][0].setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable |
                                       Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
        self.folder[title][0].setIcon(0, QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/folder.png"))
        self.treeWidget.addTopLevelItem(self.folder[title][0])
        self.treeWidget.expandItem(self.folder[title][0])
        self.folder[title].append(QtWidgets.QMdiArea(self))  # widget for multi document interface area
        self.tabWidget.addTab(self.folder[title][1], self.PyramanIcon, title)

    def add_Plot(self, pw_name, plotData):
        """ add spectrum to existing plotwindow """
        for j in plotData:
            j[4] = self.window['Plotwindow'][pw_name].spectrum[0].get_linestyle()
        self.window['Plotwindow'][pw_name].add_plot(plotData)

    def close_window(self, windowtype, title):
        del self.window[windowtype][title]
        del self.windowWidget[windowtype][title]
        items = self.treeWidget.findItems(title, Qt.MatchFixedString | Qt.MatchRecursive)

        self.folder[items[0].parent().text(0)][0].removeChild(items[0])
        self.update_spreadsheet_menubar()

    def close_folder(self, foldername):
        # self.folder
        # key = foldername, value = [Qtreewidgetitem, QmdiArea]

        # Close all windows in the folder
        self.folder[foldername][1].closeAllSubWindows()

        # Close tab
        idx = self.tabWidget.indexOf(self.folder[foldername][1])
        self.tabWidget.removeTab(idx)

        # Remove TreewidgetItem
        root = self.treeWidget.invisibleRootItem()
        root.removeChild(self.folder[foldername][0])

        # delete dictionary entry in self.folder
        del self.folder[foldername]

    def close_tab(self, index):
        if self.tabWidget.widget(index) == self.db_measurements:
            self.tabWidget.removeTab(index)
        else:
            for key, val in self.folder.items():
                if val[1] == self.tabWidget.widget(index):
                    self.close_folder(key)
                    break

    def update_spreadsheet_menubar(self):
        for j in self.window['Spreadsheet'].values():
            j.update_menubar()

    def closeEvent(self, event):
        # close mainwindow
        close = QMessageBox()
        close.setWindowTitle('Quit')
        close.setText("You sure?")
        close.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        close = close.exec_()

        if close == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


#####################################################################################################################################################
### 2. Text - Window
#####################################################################################################################################################

class TextWindow(QMainWindow):
    closeWindowSignal = QtCore.pyqtSignal(str, str)

    def __init__(self, mainwindow, text, parent=None):
        super(TextWindow, self).__init__(parent)
        self.text = text
        self.mw = mainwindow

        self.create_textwidget()
        self.create_menubar()

    def create_textwidget(self):
        self.textfield = QtWidgets.QPlainTextEdit()
        self.textfield.setPlainText(self.text)
        self.textfield.createStandardContextMenu()
        self.setCentralWidget(self.textfield)
        self.textfield.textChanged.connect(self.text_change)

    def create_menubar(self):
        # create the menubar
        self.menubar = self.menuBar()

        # 1. Menu item: File
        fileMenu = self.menubar.addMenu('&File')
        fileMenu.addAction('Save Text', self.file_save)
        fileMenu.addAction('Load Text', self.load_file)

        ### 2. Menu item: Edit
        editMenu = self.menubar.addMenu('&Edit')

        self.show()

    def text_change(self):
        self.text = self.textfield.toPlainText()

    def file_save(self):
        fileName = QtWidgets.QFileDialog.getSaveFileName(self, 'Load', filter='All Files (*);; Txt Files (*.txt)')

        if fileName[0] != '':
            fileName = fileName[0]
        else:
            return

        file = open(fileName, 'w')
        try:
            file.write(self.text)
        except UnicodeEncodeError as e:
            self.mw.show_statusbar_message(''.format(e), 4000)
        file.close()

    def load_file(self):
        fileName = QtWidgets.QFileDialog.getOpenFileName(self, 'Load', filter='All Files (*);; Txt Files (*.txt)')

        if fileName[0] != '':
            fileName = fileName[0]
        else:
            return

        file = open(fileName, 'rb')
        bintext = file.read()
        file.close()

        self.text = bintext.decode("utf-8")
        self.textfield.setPlainText(self.text)

    def closeEvent(self, event):
        close = QMessageBox()
        close.setWindowTitle('Quit')
        close.setText("You sure?")
        close.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        close = close.exec_()

        if close == QMessageBox.Yes:
            self.closeWindowSignal.emit('Textwindow', self.windowTitle())
            event.accept()
        else:
            event.ignore()


#####################################################################################################################################################
### 3. Spreadsheet
#####################################################################################################################################################

class FormulaInterpreter:
    """
    class to analyse formulas typed in the formula field of the Spreadsheet header
    written by Christopher Tao
    source: https://levelup.gitconnected.com/how-to-write-a-formula-string-parser-in-python-5362210afeab
    """
    def __init__(self, data):
        self.data = data
        self.ops = {
            "+": operator.add,
            "-": operator.sub,
            "*": operator.mul,
            "/": operator.truediv}

    def interprete_formula(self, f):
        if re.match(r'\ACol\([0-9]+\)\Z', f):
            col_formula = int(re.findall(r'\b\d+\b', f)[0])
            return self.data[col_formula]['data']
        elif re.match(r'\A\(.+\)\Z', f) and self.parentheses_enclosed(f):  # e.g. '(Col(1)-Col(2))'
            return self.interprete_formula(f[1:-1])
        elif f.replace('.', '', 1).isdigit():                               # constant numbers: e.g. '2+3*Col(0)'
            return float(f)
        elif '+' in f or '-' in f or '*' in f or '/' in f:
            rest_f = self.remove_matched_parentheses(f)
            # not combine it with '+' and '-' because  multiplication and division first, then addition and subtraction
            if '+' in rest_f or '-' in rest_f:
                split_f = re.compile(r'[\+\-]').split(f)
            else:
                split_f = re.compile(r'[\*\/]').split(f)

            if split_f[0].count('(') != split_f[0].count(')'):
                nested_level = split_f[0].count('(') - split_f[0].count(')')
                pos = len(split_f[0])
                for sf in split_f[1:]:
                    if '(' in sf:
                        nested_level += sf.count('(')
                    if ')' in sf:
                        nested_level -= sf.count(')')
                    pos += len(sf) + 1  # +1 because of the operator inside parenthesis
                    if nested_level == 0:
                        break
            else:
                pos = len(split_f[0])

            left = f[:pos]          # left component
            right = f[pos + 1:]     # right component
            op = f[pos]             # the operator
            return self.ops[op](self.interprete_formula(left), self.interprete_formula(right))
        else:
            print('There is something wrong with the formula')
            return np.full(len(self.data[0]['data']), 0)

    def parentheses_enclosed(self, s):
        paren_order = re.findall(r'[\(\)]', s)

        if paren_order.count('(') != paren_order.count(')'):
            return False

        curr_levels = []
        nest_lv = 0
        for p in paren_order:
            if p == '(':
                nest_lv += 1
            else:
                nest_lv -= 1
            curr_levels.append(nest_lv)
        if 0 in curr_levels[:-1]:
            return False
        else:
            return True

    def remove_matched_parentheses(self, formula):
        if re.search(r'(?<!Col)\(', formula):
            match_end_par = re.search(r'(?<!Col\(\d)\)', formula)
            end_par = match_end_par.start()  # index of first ')'
            start_par = [m.start() for m in re.finditer(r'(?<!Col)\(', formula[:end_par])][-1] # index of last '('
            return self.remove_matched_parentheses(formula[:start_par] + formula[end_par + 1:])
        else:
            return formula


class RamanSpreadSheet(QTableWidget):
    """ A reimplementation of the QTableWidget"""

    def __init__(self, *args, **kwargs):
        super(RamanSpreadSheet, self).__init__(*args, **kwargs)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.horizontalHeader().hide()
        self.p = self.parent()
        self.setFrameStyle(0)
        self.setViewportMargins(0, 0, 0, 0)

    def resizeEvent(self, event):
        width = self.p.header_table.verticalHeader().width()
        self.verticalHeader().setFixedWidth(width)
        # keep the default behaviour
        super(RamanSpreadSheet, self).resizeEvent(event)


class Header(QTableWidget):
    """ A reimplementation of the QTableWidget to use it as multi-row header"""

    def __init__(self, *args, **kwargs):
        super(Header, self).__init__(*args, **kwargs)
        self.p = self.parent()
        row_height = self.rowHeight(0)
        row_count = self.rowCount()
        header_height = self.horizontalHeader().height()
        self.setFixedHeight(row_height * row_count + header_height)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setFrameStyle(0)

        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum))
        self.setVerticalHeaderLabels(['Name', 'Axis', 'Unit', 'Comments', 'F(x)='])
        hh = self.horizontalHeader()
        hh.sectionResized.connect(self.section_resized)
        hh.selectionModel().selectionChanged.connect(self.section_selected)

    def section_resized(self, idx, old_size, new_size):
        self.p.data_table.setColumnWidth(idx, new_size)

    def section_selected(self):
        idx = sorted(set(i.column() for i in self.selectedIndexes()))
        for i in idx:
            self.p.data_table.selectColumn(i)


class SpreadSheetWindow(QMainWindow):
    """
    creating QMainWindow containing the spreadsheet
    """
    new_pw_signal = QtCore.pyqtSignal()
    add_pw_signal = QtCore.pyqtSignal(str)
    closeWindowSignal = QtCore.pyqtSignal(str, str)

    def __init__(self, data, parent):
        super(SpreadSheetWindow, self).__init__(parent)
        # structure of self.data (dictionary):
        # {'dataX with X = (0,1,2,..)' : data,'short name', 'X, Y or Yerr', if loaded: 'filename', 'Long Name',
        # 'Axis Label', 'Unit', 'Comments')

        if data is None:
            self.data = [self.create_data(np.full(9, np.nan), shortname="A", type="X"),
                         self.create_data(np.full(9, np.nan), shortname="B", type="Y")]
        else:
            self.data = data
        self.mw = parent
        self.cols = len(self.data)  # number of columns
        if not self.data:
            self.rows = 0
        else:
            self.rows = max([len(d["data"]) for d in self.data])  # number of rows
        self.pHomeTxt = None  # path of Txt-File

        self.central_widget = QWidget()
        self.header_table = Header(5, self.cols, parent=self)  # table header
        self.data_table = RamanSpreadSheet(self.rows, self.cols, parent=self)  # table widget

        # Layout of tables
        self.main_layout = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.TopToBottom, self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addWidget(self.header_table)
        header_layout.addSpacing(21)  # to level with vertical scrollbar from data table
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.main_layout.addLayout(header_layout)
        self.main_layout.addWidget(self.data_table)

        self.setCentralWidget(self.central_widget)

        # connect scrollbar from data table with header table
        self.data_table.horizontalScrollBar().valueChanged.connect(self.header_table.horizontalScrollBar().setValue)

        self.create_table_items()
        self.create_header_items(start=0, end=self.cols)
        self.create_menubar()
        self.create_col_header()
        self.create_row_header()

    def create_data(self, data_content, shortname="A", type="Y", filename=None):
        data_dict = {"data": data_content,
                     "shortname": shortname,
                     "type": type,
                     "filename": filename,
                     "longname": None,
                     "axis label": None,
                     "unit": None,
                     "comments": None,
                     "formula": None}
        return data_dict

    def create_table_items(self):
        """ fill the table items with data """
        # self.data_table.setItemDelegate(SpreadSheetDelegate(self))
        for c in range(self.cols):
            for r in range(len(self.data[c]["data"])):
                cell = QTableWidgetItem(str(self.data[c]["data"][r]))
                self.data_table.setItem(r, c, cell)
        self.data_table.itemChanged.connect(self.update_data)

    def create_header_items(self, start, end):
        for c in range(start, end):
            for r, key in enumerate(["longname", "axis label", "unit", "comments", "formula"]):
                try:
                    item_text = self.data[c][key]
                except KeyError:
                    print(self.data[c]["shortname"], key, ": ERROOOORRR")
                    item_text = None
                    self.data[c][key] = None
                header_item = QTableWidgetItem(item_text)
                header_item.setBackground(QtGui.QColor(255, 255, 200))  # color: light yellow
                self.header_table.setItem(r, c, header_item)
        self.header_table.itemChanged.connect(self.update_header)

    def create_menubar(self):
        """ create the menubar """
        self.menubar = self.menuBar()

        # 1. menu item: File
        fileMenu = self.menubar.addMenu('&File')
        fileMenu.addAction('Save Data', self.file_save)
        fileMenu.addAction('Load Data', self.load_file)

        # 2. menu item: Edit
        editMenu = self.menubar.addMenu('&Edit')
        editMenu.addAction('New Column', self.new_col)

        # 3. menu item: Plot
        plotMenu = self.menubar.addMenu('&Plot')
        plotNew = plotMenu.addMenu('&New')
        plotNew.addAction('Line Plot', self.get_plot_data)
        plotNew.addAction('Dot Plot', self.get_plot_data)
        plotAdd = plotMenu.addMenu('&Add to')
        for j in self.mw.window['Plotwindow'].keys():
            plotAdd.addAction(j, self.get_plot_data)
        plotMenu.addAction('Plot all', lambda: self.get_plot_data(plot_all=True))

        self.show()

    def update_menubar(self):
        self.menubar.clear()
        self.create_menubar()

    def create_col_header(self):
        headers = ['{} ({})'.format(d['shortname'], d['type']) for d in self.data]

        self.header_table.setHorizontalHeaderLabels(headers)

        # open header_menu with right mouse click
        self.headers = self.header_table.horizontalHeader()
        self.headers.setContextMenuPolicy(Qt.CustomContextMenu)
        self.headers.customContextMenuRequested.connect(self.show_header_context_menu)
        self.headers.setSelectionMode(QAbstractItemView.SingleSelection)

        # opens rename_header with double mouse click
        self.headerline = QtWidgets.QLineEdit()  # Create
        self.headerline.setWindowFlags(QtCore.Qt.FramelessWindowHint)  # Hide title bar
        self.headerline.setAlignment(QtCore.Qt.AlignLeft)  # Set the Alignmnet
        self.headerline.setHidden(True)  # Hide it till its needed
        self.sectionedit = 0
        self.header_table.horizontalHeader().sectionDoubleClicked.connect(self.rename_header)

    def rename_header(self, logical_column):
        # This block sets up the geometry for the line edit
        header_position = self.headers.mapToGlobal(QtCore.QPoint(0, 0))
        edit_geometry = self.headerline.geometry()
        edit_geometry.setWidth(self.headers.sectionSize(logical_column))
        edit_geometry.setHeight(self.header_table.rowHeight(0))
        edit_geometry.moveLeft(header_position.x() + self.headers.sectionViewportPosition(logical_column))
        edit_geometry.moveTop(header_position.y())
        self.headerline.setGeometry(edit_geometry)
        visual_column = self.data_table.visualColumn(logical_column)
        self.headerline.editingFinished.connect(lambda: self.header_editing_finished(logical_column, visual_column))

        self.headerline.setText(self.data[visual_column]['shortname'])
        self.headerline.setHidden(False)  # Make it visible
        self.headerline.setFocus()

    def header_editing_finished(self, log_col, vis_col):
        self.headerline.setHidden(True)
        newHeader = str(self.headerline.text())
        self.data[vis_col]["shortname"] = newHeader
        self.header_table.horizontalHeaderItem(log_col).setText(
            '{} ({})'.format(self.data[vis_col]["shortname"], self.data[vis_col]["type"]))

    def show_header_context_menu(self, position):
        selected_column = self.headers.logicalIndexAt(position)
        header_menu = QMenu()
        delete_column = header_menu.addAction('Delete this column')
        set_xy = header_menu.addMenu('Set as:')
        set_xy.addAction('X')
        set_xy.addAction('Y')
        set_xy.addAction('Yerr')
        set_xy.addAction('Opacity')
        set_xy.triggered[QAction].connect(lambda QAction: self.set_column_type(QAction, selected_column))
        convert_unit = header_menu.addMenu("convert unit")
        convert_unit.addAction("cm^-1 to nm")
        convert_unit.addAction("nm to cm^-1")
        convert_unit.triggered[QAction].connect(lambda QAction: self.convert_column_unit(QAction, selected_column))
        mov_col = header_menu.addMenu("Move column")
        mov_col.addAction('Move left')
        mov_col.addAction('Move right')
        mov_col.addAction('Move to first')
        mov_col.addAction('Move to last')
        mov_col.triggered[QAction].connect(lambda QAction: self.move_column(QAction, selected_column))
        ac = header_menu.exec_(self.header_table.mapToGlobal(position))
        # Delete selected colums
        if ac == delete_column:
            # Get the index of all selected columns in reverse order, so that last column is deleted first
            selCol = sorted(set(index.column() for index in self.header_table.selectedIndexes()), reverse=True)
            for j in selCol:
                del self.data[j]  # Delete data
                self.data_table.removeColumn(j)  # Delete column
                self.header_table.removeColumn(j)
                self.cols = self.cols - 1

    def convert_column_unit(self, action, selected_column):
        dialog_wavelength = QDialog()
        layout = QtWidgets.QGridLayout()
        cbox = QtWidgets.QComboBox()
        cbox.addItem("325")
        cbox.addItem("442")
        cbox.addItem("532")
        cbox.addItem("633")
        cbox.addItem("785")
        layout.addWidget(cbox)
        dialog_wavelength.setLayout(layout)
        dialog_wavelength.setWindowTitle("Select a Wavelength")
        dialog_wavelength.setWindowModality(Qt.ApplicationModal)
        dialog_wavelength.exec_()
        wl0 = cbox.currentText()
        if action.text() == "cm^-1 to nm":
            unit_text = "nm"
            formula = f"{wl0}/(1-Col({selected_column})*0.0000001*{wl0})"

        elif action.text() == "nm to cm^-1":
            unit_text = "cm^-1"
            formula = f"((1/{wl0})-(1/Col({selected_column})))*10000000"

        self.header_table.item(2, selected_column).setText(unit_text)
        self.header_table.item(4, selected_column).setText(formula.format(wl0=wl0, selected_column=selected_column))

    def set_column_type(self, qaction, log_col):
        """
        setting the column type to X, Y or Yerr
        @param qaction:
        @param log_col: logical index of selected column
        @return:
        """
        col_type = qaction.text()
        vis_col = self.header_table.visualColumn(log_col)
        self.data[vis_col]["type"] = col_type
        self.header_table.horizontalHeaderItem(log_col).setText(
            "{}({})".format(self.data[vis_col]["shortname"], col_type))

    def move_column(self, qaction, selected_column):
        old_idx = self.headers.visualIndex(selected_column)
        if qaction.text() == 'Move left':
            new_idx = old_idx - 1
        elif qaction.text() == 'Move right':
            new_idx = old_idx + 1
        elif qaction.text() == 'Move to first':
            new_idx = 0
        elif qaction.text() == 'Move to last':
            new_idx = self.data_table.columnCount() - 1
        self.headers.moveSection(old_idx, new_idx)
        self.data_table.horizontalHeader().moveSection(old_idx, new_idx)
        self.data.insert(new_idx, self.data.pop(old_idx))

    def create_row_header(self):
        """opens header_menu with right mouse click on header"""
        self.row_headers = self.data_table.verticalHeader()
        self.row_headers.setContextMenuPolicy(Qt.CustomContextMenu)
        self.row_headers.customContextMenuRequested.connect(self.row_options)
        self.row_headers.setSelectionMode(QAbstractItemView.SingleSelection)

    def row_options(self, position):
        selected_row = self.row_headers.logicalIndexAt(position)
        header_menu = QMenu()
        delete_row = header_menu.addAction('Delete this row')
        ac = header_menu.exec_(self.data_table.mapToGlobal(position))
        # Delete selected colums
        if ac == delete_row:
            # Get the index of all selected rows in reverse order, so that last row is deleted first
            selRow = sorted(set(index.row() for index in self.data_table.selectedIndexes()), reverse=True)
            for c in range(self.cols):
                for r in selRow:
                    try:
                        self.data[c]["data"] = np.delete(self.data[c]["data"], r)  # Delete data
                    except IndexError as e:
                        print(e)
            for k in selRow:
                self.data_table.removeRow(k)  # Delete row
                self.rows = self.rows - 1

    def keyPressEvent(self, event):
        # A few shortcuts
        # Enter or Return: go to the next row
        key = event.key()
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            # go to next row
            cr = self.data_table.currentRow()
            cc = self.data_table.currentColumn()
            if cr == (self.rows - 1):
                self.data_table.insertRow(self.rows)
                for i in range(self.cols):
                    self.data_table.setItem(self.rows, i, QTableWidgetItem(''))
                self.rows = self.rows + 1
            else:
                pass
            ti = self.data_table.item(cr + 1, cc)
            self.data_table.setCurrentItem(ti)
        # if key == Qt.Key_Delete:
        #    selItem = [[index.row(), index.column()] for index in self.data_table.selectedIndexes()]
        #    for j in selItem:
        #        self.data_table.takeItem(j[0], j[1])
        #        self.data[j[1]]["data"][j[0]] = np.nan
        else:
            super(SpreadSheetWindow, self).keyPressEvent(event)

    def file_save(self):
        """
        save data from spreadsheet in txt-file
        """
        SaveFileName = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', self.pHomeTxt)

        if SaveFileName[0] != '':
            SaveFileName = SaveFileName[0]
        else:
            return

        save_data = [self.data[0]["data"]]
        header = self.data[0]["shortname"]
        for c in range(1, self.cols):
            save_data.append(self.data[c]["data"])
            header = '{}%{}'.format(header, self.data[c]["shortname"])
        header = '{} '.format(header)

        n = len(self.data[0]["data"])
        if all(len(x) == n for x in save_data):
            pass
        else:
            self.mw.show_statusbar_message('The columns have different lengths!', 4000)
            return

        save_data = np.transpose(save_data)

        if SaveFileName[-4:] != '.txt':
            SaveFileName = '{}.txt'.format(SaveFileName)

        self.pHomeTxt = SaveFileName

        np.savetxt(SaveFileName, save_data, fmt='%.5f', header=header)

    def load_file(self):
        """
        function to load data from a txt file into the spreadsheet
        """

        # In case there already is data in the spreadsheet, ask if replace or added
        if any(d['filename'] is not None for d in self.data):
            FrageErsetzen = QtWidgets.QMessageBox()
            FrageErsetzen.setIcon(QMessageBox.Question)
            FrageErsetzen.setWindowTitle('Replace or Add?')
            FrageErsetzen.setText('There is already loaded data. Shall it be replaced?')
            buttonY = FrageErsetzen.addButton(QMessageBox.Yes)
            buttonY.setText('Replace')
            buttonN = FrageErsetzen.addButton(QMessageBox.No)
            buttonN.setText('Add')
            buttonC = FrageErsetzen.addButton(QMessageBox.Cancel)
            buttonC.setText('Cancel')
            returnValue = FrageErsetzen.exec_()
            if returnValue == QMessageBox.Yes:  # Replace
                self.data = []
                self.cols = 0
                self.rows = 0
            elif returnValue == QMessageBox.No:  # Add
                pass
            else:  # Cancel
                return
        else:
            self.data = []
            self.cols = 0
            self.rows = 0

        cols_before = self.cols
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setNameFilter("Data Files (*.txt *.asc *.dat)")
        dialog.setViewMode(QFileDialog.List)
        dialog.setDirectory(self.pHomeTxt)
        if dialog.exec_():
            newFiles = dialog.selectedFiles()
        else:
            return

        n_newFiles = len(newFiles)
        load_data = []
        lines = []
        FileName = []
        header = []
        for j in range(n_newFiles):
            # read first line to get header
            with open(newFiles[j]) as f:
                try:
                    firstline = f.readline()
                except UnicodeDecodeError as e:
                    print(e, newFiles[j])
                    n_newFiles -= 1
                    continue
            # check if file has a header (starts with #)
            if firstline[0] == '#':
                firstline = firstline[1:-2]  # remove '#' at beginning and '\n' at end
                firstline = firstline.split('%')  # headers of different columns are seperated by '%'
                header.append(firstline)
            else:
                header.append(None)

            try:
                load_data.append(np.loadtxt(newFiles[j]))
                # load_data.append(np.genfromtxt(newFiles[j], missing_values='', filling_values=''))
            except Exception as e:
                self.mw.show_statusbar_message("The file couldn't be imported", 4000)
                print('{} \nThe file could not be imported, maybe the columns have different lengths'.format(e))
                return

            try:
                load_data[j] = np.transpose(load_data[j])
            except IndexError as e:
                print("The data format is not readabel for PyRaman\n", e)
                return

            if isinstance(load_data[j][0], float):
                load_data[j] = [load_data[j], np.ones(len(load_data[j])) * np.nan]

            lines.append(len(load_data[j]))
            FileName.append(os.path.splitext(os.path.basename(newFiles[j]))[0])
        for k in range(n_newFiles):
            for j in range(lines[k]):
                if j == 0:
                    col_type = 'X'
                else:
                    col_type = 'Y'

                if header[k] is None or len(header[k]) <= j:  # if header is None, use Filename as header
                    shortname = str(FileName[k])
                else:
                    shortname = header[k][j]
                self.data.append(self.create_data(load_data[k][j], shortname=shortname,
                                                  type=col_type, filename=newFiles[k]))
            self.cols = self.cols + lines[k]

        self.rows = max([len(d["data"]) for d in self.data])

        self.data_table.setColumnCount(self.cols)
        self.data_table.setRowCount(self.rows)
        self.header_table.setColumnCount(self.cols)
        self.header_table.setRowCount(5)

        # set header
        headers = ['{} ({})'.format(d["shortname"], d["type"]) for d in self.data]
        self.header_table.setHorizontalHeaderLabels(headers)
        self.create_header_items(cols_before, self.cols)

        for c in range(cols_before, self.cols):
            for r in range(len(self.data[c]["data"])):
                newcell = QTableWidgetItem(str(self.data[c]["data"][r]))
                self.data_table.setItem(r, c, newcell)

        self.pHomeTxt = FileName[0]

    def update_data(self, item):
        """ if content of spreadsheet cell is changed, data stored in variable self.data is also changed """
        new_cell_content = item.text()
        col = self.data_table.visualColumn(item.column())
        row = item.row()
        if new_cell_content == '':
            self.data_table.takeItem(row, col)
            new_cell_content = np.nan
        try:
            self.data[col]["data"][row] = new_cell_content
        except IndexError:  # occurs if index is out of bounds
            self.data[col]["data"] = np.append(self.data[col]["data"], new_cell_content)

    def update_header(self, item):
        """if header is changed, self.data is changed too"""
        content = item.text()
        col = item.column()
        row = item.row()

        if row == 0:    # Long Name
            self.data[col]["longname"] = content
        elif row == 1:
            self.data[col]["axis label"] = content
        elif row == 2:  # Unit
            self.data[col]["unit"] = content
        elif row == 3:  # Comments
            self.data[col]["comments"] = content
        elif row == 4:  # F(x) =
            self.data[col]["formula"] = content
            if content is None or content == '':
                return
            else:
                Interpreter = FormulaInterpreter(self.data)
                new_data = Interpreter.interprete_formula(content)
                if new_data is not None:
                    self.data[col]["data"] = new_data
                    for r in range(len(self.data[col]["data"])):
                        newcell = QTableWidgetItem(str(self.data[col]["data"][r]))
                        self.data_table.setItem(r, col, newcell)

    def new_col(self):
        # adds a new column at end of table
        self.cols = self.cols + 1
        self.data_table.setColumnCount(self.cols)
        self.header_table.setColumnCount(self.cols)
        self.data.append(self.create_data(np.zeros(self.rows), shortname=str(chr(ord('A') + self.cols - 1))))
        headers = [d["shortname"] + '(' + d["type"] + ')' for d in self.data]
        self.header_table.setHorizontalHeaderLabels(headers)
        for i in range(self.rows):
            cell = QTableWidgetItem('')
            self.data_table.setItem(i, self.cols - 1, cell)

        # Color header cells in yellow
        for r in range(5):
            self.header_table.setItem(r, self.cols - 1, QTableWidgetItem())
            self.header_table.item(r, self.cols - 1).setBackground(QtGui.QColor(255, 255, 200))

    def get_plot_data(self, plot_all=False):
        """ get data from selected columns and prepares data for plot """
        self.plot_data = [] # [X-data, Y-data, label, filename, plottype, yerr, spreadsheet-title]
        plot_content = {"x": None,
                        "y": None,
                        "yerr": None,
                        "plot type": None,
                        "label": None,
                        "xaxis": None,
                        "yaxis": None,
                        "filename": None,
                        "spreadsheet title": None
                        }

        if plot_all is True:
            selCol = [idx for idx, d in enumerate(self.data) if d["type"] == "Y"]
        else:
            # get visual index of selected columns in sorted order
            selCol = sorted(set(self.headers.visualIndex(idx.column()) for idx in self.header_table.selectedIndexes()))

        # Decides if line or dot plot
        action = self.sender()
        if action.text() == 'Line Plot':
            plot_type = '-'
        elif action.text() == 'Dot Plot':
            plot_type = 'o'
        elif action.text() == 'Plot all':
            plot_type = '-'
        else:
            plot_type = None

        # iterate over all selected columns
        for c in selCol:
            if self.data[c]["type"] != 'Y':
                self.mw.show_statusbar_message('Please only select Y-columns!', 4000)
                return
            else:
                k = c - 1
                while k >= 0:
                    if self.data[k]["type"] == 'X':
                        # label for plot legende
                        if self.data[c]["longname"] is None or self.data[c]["longname"] == '':
                            label = self.data[c]["shortname"]
                        else:
                            label = self.data[c]["longname"]

                        m = c + 1
                        yerr = None
                        while m <= self.cols:
                            if m == self.cols:
                                yerr = None
                                m = self.cols + 1
                            elif self.data[m]["type"] == 'Yerr':
                                yerr = self.data[m]["data"]
                                m = self.cols + 1
                            else:
                                m = m + 1
                        self.plot_data.append(plot_content.copy())
                        self.plot_data[-1]["x"] = self.data[k]["data"]
                        self.plot_data[-1]["y"] = self.data[c]["data"]
                        self.plot_data[-1]["filename"] = self.data[c]["filename"]
                        self.plot_data[-1]["label"] = label
                        self.plot_data[-1]["plot type"] = plot_type
                        self.plot_data[-1]["yerr"] = yerr
                        if self.data[k]["axis label"] is not None or self.data[k]["axis label"] == '':
                            self.plot_data[-1]["xaxis"] = self.data[k]["axis label"]
                            if self.data[k]["unit"] is not None or self.data[k]["unit"] == '':
                                self.plot_data[-1]["xaxis"] += " / {}".format(self.data[k]["unit"])
                        if self.data[c]["axis label"] is not None or self.data[c]["axis label"] == '':
                            self.plot_data[-1]["yaxis"] = self.data[c]["axis label"]
                            if self.data[c]["unit"] is not None or self.data[c]["unit"] == "":
                                self.plot_data[-1]["yaxis"] += " / {}".format(self.data[c]["unit"])
                        k = -2
                    else:
                        k = k - 1

                if k == -1:
                    self.mw.show_statusbar_message('At least one dataset Y has no assigned X dataset.', 4000)
                    return

        # check that x and y have same length to avoid problems later:
        # append Spreadsheet instance
        for pd in self.plot_data:
            # delete all values, which are nan
            if len(pd["x"]) == len(pd["y"]):
                x_bool = np.logical_not(np.isnan(pd["x"]))
                if all(x_bool) is False:
                    pd["x"] = pd["x"][x_bool]
                    pd["y"] = pd["y"][x_bool]
                    # Error
                    if pd["yerr"] is not None:
                        pd["yerr"] = pd["yerr"][x_bool]

                y_bool = np.logical_not(np.isnan(pd["y"]))
                if all(y_bool) is False:
                    pd["x"] = pd["x"][y_bool]
                    pd["y"] = pd["y"][y_bool]
                    # Error
                    if pd["yerr"] is not None:
                        pd["yerr"] = pd["yerr"][y_bool]

                pd["spreadsheet title"] = self.windowTitle()
            else:
                print(pd)
                self.mw.show_statusbar_message('X and Y have different lengths', 4000)
                return
        # emit signal to MainWindow to create new Plotwindow or add lines to existing plotwindow
        if plot_type is not None:
            self.new_pw_signal.emit()
        else:
            self.add_pw_signal.emit(action.text())

    def closeEvent(self, event):
        close = QMessageBox()
        close.setWindowTitle('Quit')
        close.setText("You sure?")
        close.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        close = close.exec_()

        if close == QMessageBox.Yes:
            self.closeWindowSignal.emit('Spreadsheet', self.windowTitle())
            event.accept()
        else:
            event.ignore()


#####################################################################################################################################################
### 4. Plot
#####################################################################################################################################################
class LineBuilder:
    """
    Plotting a vertical line in plot, e.g. to define area for fit
    """

    def __init__(self, line):
        self.line = line
        self.xs = line.get_xdata()[0]
        self.line.set_visible(True)
        self.canvas = self.line.figure.canvas
        self.cid_key = self.canvas.mpl_connect('key_press_event', self)
        self.cid_button = self.canvas.mpl_connect('button_press_event', self)
        self.canvas.start_event_loop(timeout=10000)

    def __call__(self, event):
        if event.inaxes != self.line.axes:
            return
        elif event.name == 'button_press_event':
            if event.button == 1:
                self.xs = event.xdata
                self.line.set_xdata([self.xs, self.xs])
                self.canvas.draw()
            elif event.button == 3 or event.key == QtCore.Qt.Key_Return:
                self.canvas.mpl_disconnect(self.cid_button)
                self.canvas.mpl_disconnect(self.cid_key)
                self.canvas.stop_event_loop(self)
        elif event.name == 'key_press_event':
            print(event.key)


class MoveSpectra:
    def __init__(self, line, scaling=False):
        """
        Class to move spectra
        Parameters
        ----------
        line: Line2D
        """

        self.line = line
        self.scaling = scaling
        self.x = line.get_xdata()
        self.y = line.get_ydata()
        self.fig = self.line.figure
        self.canvas = self.fig.canvas
        self.move_line = False  # True if right line is selected, otherwise False
        self.cid1 = self.canvas.mpl_connect('pick_event', self.onpick)
        self.cid2 = self.canvas.mpl_connect('motion_notify_event', self.onmove)
        self.cid3 = self.canvas.mpl_connect('button_release_event', self.onrelease)
        self.canvas.start_event_loop(timeout=10000)

    def onpick(self, event):
        if event.artist != self.line:
            return
        self.move_line = True

    def onmove(self, event):
        if not self.move_line:
            return
        # the click locations
        x_click = event.xdata
        y_click = event.ydata

        if x_click is None or y_click is None:
            return

        # get index of nearest point
        ind = min(range(len(self.x)), key=lambda i: abs(self.x[i] - x_click))

        if not self.scaling:
            shift_factor = y_click - self.y[ind]
            self.y = self.y + shift_factor
        else:
            scale_factor = y_click / self.y[ind]
            self.y = self.y * scale_factor

        self.line.set_ydata(self.y)
        self.canvas.draw()

    def onrelease(self, event):
        if self.move_line:
            self.canvas.mpl_disconnect(self.cid1)
            self.canvas.mpl_disconnect(self.cid2)
            self.canvas.mpl_disconnect(self.cid3)
            self.move_line = False
            self.canvas.stop_event_loop(self)


class LineDrawer:
    def __init__(self, arrow):
        """
        Class to draw lines and arrows
        idea: https://github.com/yuma-m/matplotlib-draggable-plot

        Parameters
        ----------
        arrow: FancyArrowPatch
        """
        self.arrow = arrow
        self.fig = self.arrow.figure
        self.ax = self.fig.axes[0]
        self.c = self.fig.canvas
        posA, *_, posB = self.arrow.get_path()._vertices
        self.posA = list(posA)
        self.posB = list(posB)
        self.pickedPoint = None
        self.arrow.set_picker(5)

        self.c.mpl_connect('pick_event', self.pickpoint)
        self.c.mpl_connect('motion_notify_event', self.movepoint)
        self.c.mpl_connect('button_release_event', self.unpickpoint)

    def pickpoint(self, event):
        if event.artist == self.arrow and event.mouseevent.button == 1:
            min_distance = 25
            distance_to_A = math.hypot(event.mouseevent.xdata - self.posA[0], event.mouseevent.ydata - self.posA[1])
            distance_to_B = math.hypot(event.mouseevent.xdata - self.posB[0], event.mouseevent.ydata - self.posB[1])
            if distance_to_A < min_distance:
                self.pickedPoint = self.posA
            elif distance_to_B < min_distance:
                self.pickedPoint = self.posB
            else:
                self.pickedPoint = None
                return
            self.selectedPoint, = self.ax.plot(self.pickedPoint[0], self.pickedPoint[1], 'o', ms=12, alpha=0.4,
                                               color='yellow')
            self.c.draw()
        elif event.artist == self.arrow and event.mouseevent.button == 3:
            self.options()
        else:
            pass

    def movepoint(self, event):
        if not self.pickedPoint:
            return
        elif event.xdata is None or event.ydata is None:
            return
        else:
            if self.pickedPoint == self.posA:
                self.posA = [event.xdata, event.ydata]
            elif self.pickedPoint == self.posB:
                self.posB = [event.xdata, event.ydata]
            else:
                return
            self.pickedPoint = [event.xdata, event.ydata]
            self.arrow.set_positions(self.posA, self.posB)
            self.selectedPoint.set_data(self.pickedPoint)
            self.c.draw()

    def unpickpoint(self, event):
        if self.pickedPoint and event.button == 1:
            self.pickedPoint = None
            self.selectedPoint.remove()
            self.c.draw()
        else:
            return

    def options(self):
        color = mcolors.to_hex(mcolors.to_rgba(self.arrow.get_edgecolor(),  # get color of arrow
                                               self.arrow.get_alpha()), keep_alpha=True)
        arrowstyle = self.arrow.get_arrowstyle()  # get arrow_style of arrow, returns object
        arrowstyle_start = str(arrowstyle).split(' ', 1)[0]  # get object name without adress x0....
        list_of_styles = mpatches.ArrowStyle.get_styles()  # get all possible arrowstyles, returns dictionnary
        current_style = 0
        for key, val in list_of_styles.items():  # compare arrowstyle with arrowstyle list to
            if str(mpatches.ArrowStyle(key)).split(' ', 1)[0] == arrowstyle_start:
                # in order to get arrowstyle name (e.g. '->')
                current_style = key

        lineOptions = [
            ('Width', self.arrow.get_linewidth()),
            ('Line style', [self.arrow.get_linestyle(),
                            ('-', 'solid'),
                            ('--', 'dashed'),
                            ('-.', 'dashDot'),
                            (':', 'dotted'),
                            ('None', 'None')]),
            ('Color', color),
            ('Remove Line', False)
        ]
        arrowOptions = [
            ('Arrow Style', [current_style, '-', '<-', '->', '<->', '-|>']),
            ('Head Length', arrowstyle.head_length),
            ('Head Wdith', arrowstyle.head_width),
        ]

        positionOptions = [
            ('x Start', self.posA[0]),
            ('y Start', self.posA[1]),
            ('x End', self.posB[0]),
            ('y End', self.posB[1]),
        ]

        optionsList = [(lineOptions, "Line", ""), (arrowOptions, "Arrow", ""), (positionOptions, 'Postion', '')]

        selectedOptions = formlayout.fedit(optionsList, title="Line options", apply=self.apply_options)
        if selectedOptions is not None:
            self.apply_options(selectedOptions)

    def apply_options(self, selectedOptions):
        lineOptions = selectedOptions[0]
        arrowOptions = selectedOptions[1]
        positionOptions = selectedOptions[2]

        (width, linestyle, color, remove_line) = lineOptions
        (arrowstyle, headlength, headwidth) = arrowOptions
        (xStart, yStart, xEnd, yEnd) = positionOptions

        self.arrow.set_linewidth(width)
        self.arrow.set_linestyle(linestyle)
        self.arrow.set_color(color)
        if arrowstyle != '-':
            self.arrow.set_arrowstyle(arrowstyle, head_length=headlength, head_width=headwidth)
        else:
            self.arrow.set_arrowstyle(arrowstyle)

        self.posA[0] = xStart
        self.posA[1] = yStart
        self.posB[0] = xEnd
        self.posB[1] = yEnd
        self.arrow.set_positions(self.posA, self.posB)

        if remove_line is True:
            self.arrow.remove()

        self.c.draw()


class InsertText:
    def __init__(self, text, main_window):
        self.text_annotation = text
        self.mw = main_window
        self.fig = self.text_annotation.figure
        if self.fig is None or self.text_annotation is None:
            return
        self.fig.canvas.mpl_connect('pick_event', self.on_pick)

    def on_pick(self, event):
        if event.artist == self.text_annotation and event.mouseevent.button == 1 and event.mouseevent.dblclick is True:
            self.edit()
        elif event.artist == self.text_annotation and event.mouseevent.button == 1:
            self.cid2 = self.fig.canvas.mpl_connect('button_release_event', self.on_release)
            self.cid3 = self.fig.canvas.mpl_connect('motion_notify_event', self.on_motion)
        elif event.artist == self.text_annotation and event.mouseevent.button == 3:
            self.text_options()
        else:
            pass

    def edit(self):
        self.textbox = QtWidgets.QLineEdit()
        self.textbox.setWindowFlags(Qt.FramelessWindowHint)  # Hide title bar
        self.textbox.setHidden(False)  # Make it visible
        self.textbox.setText(self.text_annotation.get_text())
        bb = self.text_annotation.get_window_extent()
        # width, height = int(bb.width), int(bb.height)
        x, y = bb.get_points()[0]
        mw_height = self.mw.geometry().height()
        global_point = self.fig.canvas.mapFromGlobal(self.fig.canvas.pos())
        x_canvas, y_canvas = int(global_point.x()), int(global_point.y())
        self.textbox.move(int(x - x_canvas), int(mw_height - y + y_canvas / 2))
        self.textbox.returnPressed.connect(self.finish_edit)
        self.textbox.setFocus()

    def finish_edit(self):
        self.text_annotation.set_text(self.textbox.text())
        self.textbox.setHidden(True)
        self.fig.canvas.draw()

    def on_motion(self, event):
        pos = (event.xdata, event.ydata)
        self.text_annotation.set_position(pos)
        self.fig.canvas.draw()

    def on_release(self, event):
        self.fig.canvas.mpl_disconnect(self.cid2)
        self.fig.canvas.mpl_disconnect(self.cid3)

    def text_options(self):
        color = mcolors.to_hex(mcolors.to_rgba(self.text_annotation.get_color(),
                                               self.text_annotation.get_alpha()), keep_alpha=True)
        text_options_list = [
            ('Fontsize', self.text_annotation.get_fontsize()),
            ('Color', color),
            ('Remove Text', False)
        ]

        text_option_menu = formlayout.fedit(text_options_list, title="Text options")
        if text_option_menu is not None:
            self.apply_callback(text_option_menu)

    def apply_callback(self, options):
        (fontsize, color, remove_text) = options

        self.text_annotation.set_fontsize(fontsize)
        self.text_annotation.set_color(color)
        if remove_text is True:
            self.text_annotation.remove()
        self.fig.canvas.draw()


class DataPointPicker:
    """
    Class to select a datapoint within the spectrum
    """

    def __init__(self, line, a):
        """
        Creates a yellow dot around a selected data point
        """
        self.xs = line.get_xdata()
        self.ys = line.get_ydata()
        self.line = line
        self.fig = self.line.figure
        self.idx = a
        self.selected, = self.fig.axes[0].plot(self.xs[a], self.ys[a], 'o',
                                               ms=12, alpha=0.4,
                                               color='yellow')  # Yellow point to mark selected Data points
        self.fig.canvas.draw()
        self.fig.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.fig.canvas.setFocus()

        self.cid1 = self.fig.canvas.mpl_connect('pick_event', self.onpick)
        self.cid2 = self.fig.canvas.mpl_connect('key_press_event', self.onpress)

        self.fig.canvas.start_event_loop(timeout=10000)

    def onpick(self, event):
        N = len(event.ind)
        if not N:
            return True

        # the click locations
        x = event.mouseevent.xdata
        y = event.mouseevent.ydata
        distances = np.hypot(x - self.xs[event.ind], y - self.ys[event.ind])
        indmin = distances.argmin()
        self.idx = int(event.ind[indmin])

        self.selected.set_data(self.xs[self.idx], self.ys[self.idx])
        self.selected.set_visible(True)
        self.fig.canvas.draw()

    def onpress(self, event):
        if event.key == 'enter':
            self.fig.canvas.mpl_disconnect(self.cid1)
            self.fig.canvas.mpl_disconnect(self.cid2)
            self.fig.canvas.stop_event_loop(self)
            self.selected.remove()
            self.fig.canvas.draw()
            return
        elif event.key == 'right':
            inc = 1
        elif event.key == 'left':
            inc = -1
        else:
            return
        self.idx += inc
        self.selected.set_data(self.xs[self.idx], self.ys[self.idx])
        self.fig.canvas.draw()


class DataSetSelecter(QtWidgets.QDialog):
    """
    Select one or several datasets

    Parameters
    ----------
    data_set_names           # names of all datasets
    select_only_one          # if True only on Dataset can be selected
    """

    def __init__(self, data_set_names, select_only_one=True):
        super(DataSetSelecter, self).__init__(parent=None)
        self.data_set_names = data_set_names
        self.select_only_one = select_only_one
        self.selectedDatasetNumber = []
        self.CheckDataset = []
        self.create_dialog()

    def create_dialog(self):
        layout = QtWidgets.QGridLayout()
        if self.select_only_one is False:
            check_all = QCheckBox("Select all", self)
            myFont = QtGui.QFont()
            myFont.setBold(True)
            check_all.setFont(myFont)
            check_all.stateChanged.connect(self.select_all)
            layout.addWidget(check_all, 0, 0)

        for idx, name in enumerate(self.data_set_names):
            self.CheckDataset.append(QCheckBox(name, self))
            layout.addWidget(self.CheckDataset[idx], idx + 1, 0)
            if self.select_only_one is True:
                self.CheckDataset[idx].stateChanged.connect(self.onStateChange)

        ok_button = QPushButton("OK", self)
        layout.addWidget(ok_button, len(self.data_set_names) + 1, 0)
        ok_button.clicked.connect(self.Ok_button)
        self.setLayout(layout)
        self.setWindowTitle("Select Dataset")
        self.exec_()

    @pyqtSlot(int)
    def onStateChange(self, state):
        if state == Qt.Checked:
            for j in self.CheckDataset:
                if self.sender() != j:
                    j.setChecked(False)

    @pyqtSlot(int)
    def select_all(self, state):
        if state == Qt.Checked:
            for cd in self.CheckDataset:
                cd.setCheckState(Qt.Checked)
        elif state == Qt.Unchecked:
            for cd in self.CheckDataset:
                cd.setCheckState(Qt.Unchecked)

    def Ok_button(self):
        """ OK Button for function SecetedDataset """
        for idx, d in enumerate(self.CheckDataset):
            if d.isChecked():
                self.selectedDatasetNumber.append(idx)
            else:
                pass
        self.close()


class BaselineCorrectionMethods:
    """Class containing all implemented methods of base line correction"""
    def __init__(self):
        # all implemented baseline correction methods
        self.methods = {'Rubberband':
                            {'function': self.rubberband, 'parameter': {}},
                        'Polynomial':
                            {'function': self.polynomial, 'parameter': {'order': 1, 'roi': [[150, 160], [3800, 4000]]}},
                        'Univariate Spline':
                            {'function': self.unispline, 'parameter': {'s': 1e0, 'roi': [[150, 160], [3800, 4000]]}},
                        'GCV Spline':
                            {'function': self.gcvspline, 'parameter': {'s': 0.1, 'roi': [[150, 160], [3800, 4000]]}},
                        'Asymmetric Least Square':
                            {'function': self.ALS, 'parameter': {'p': 0.001, 'lambda': 10000000}},
                        'Adaptive Iteratively Reweighted Penalized Least Squares':
                            {'function': self.airPLS, 'parameter': {'lambda': 10000000}},
                        'Asymmetrically Reweighted Penalized Least Squares':
                            {'function': self.arPLS, 'parameter': {'lambda': 10000000}},
                        'Doubly Reweighted Penalized Least Squares':
                            {'function': self.drPLS, 'parameter': {'lambda': 1000000}}
                        }
        # contains current method, for baseline dialog
        # start method is ASL
        self.current_method = 'Asymmetric Least Square'

    def rubberband(self, x, y):
        """
        Rubberband Baseline Correction
        source: https://dsp.stackexchange.com/questions/2725/how-to-perform-a-rubberband-correction-on-spectroscopic-data
        """
        # Find the convex hull
        v = scipy.spatial.ConvexHull(np.array(list(zip(x, y)))).vertices
        # Rotate convex hull vertices until they start from the lowest one
        v = np.roll(v, -v.argmin())
        # Leave only the ascending part
        v = v[:v.argmax()]

        # Create baseline using linear interpolation between vertices
        z = np.interp(x, x[v], y[v])
        y = y - z
        # y - background-corrected Intensity-values, z - background
        return y, z

    def polynomial(self, x, y, p_order, roi):
        y, z = rp.baseline(x, y, np.array(roi), 'poly', polynomial_order=p_order)
        y = y.flatten()
        z = z.flatten()
        return y, z

    def unispline(self, x, y, s, roi):
        """
        @param x: x data
        @param y: y data
        @param s: Positive smoothing factor used to choose the number of knots.
        Number of knots will be increased until the smoothing condition is satisfied:
        @param roi: region of interest
        @return: baseline corrected y data and baseline z
        """
        try:
            y, z = rp.baseline(x, y, np.array(roi), 'unispline', s=s)
        except ValueError as e:
            print(e)
            return None
        y = y.flatten()
        z = z.flatten()
        return y, z

    def gcvspline(self, x, y, s, roi):
        """
        @param x: x data
        @param y: y data
        @param s: Positive smoothing factor used to choose the number of knots.
        Number of knots will be increased until the smoothing condition is satisfied:
        @param roi: region of interest
        @return: baseline corrected y data and baseline z
        """
        try:
            y, z = rp.baseline(x, y, np.array(roi), 'gcvspline', s=s)
        except UnboundLocalError:
            print('ERROR: Install gcvspline to use this mode (needs a working FORTRAN compiler).')
            return None
        y = y.flatten()
        z = z.flatten()
        return y, z

    def ALS(self, x, y, p, lam):
        """
        baseline correction with Asymmetric Least Squares smoothing
        based on: P. H. C. Eilers and H. F. M. Boelens. Baseline correction with asymmetric least squares smoothing.
        Leiden University Medical Centre Report , 1(1):5, 2005. from Eilers and Boelens
        also look at: https://stackoverflow.com/questions/29156532/python-baseline-correction-library
        """
        niter = 10
        # p = 0.001   			#asymmetry 0.001 <= p <= 0.1 is a good choice
        # recommended from Eilers and Boelens for Raman: 0.001    recommended from Simon: 0.0001
        # lam = 10000000			#smoothness 10^2 <= lambda <= 10^9
        # recommended from Eilers and Boelens for Raman: 10^7      recommended from Simon: 10^7
        L = len(x)
        D = sparse.csc_matrix(np.diff(np.eye(L), 2))
        w = np.ones(L)
        for i in range(niter):
            W = sparse.spdiags(w, 0, L, L)
            Z = W + lam * D.dot(D.transpose())
            z = spsolve(Z, w * y)
            w = p * (y > z) + (1 - p) * (y < z)
        y = y - z
        return y, z  # y - background-corrected Intensity-values, baseline - baseline

    def airPLS(self, x, y, lam, ratio=0.001):
        """
        adaptive  iteratively  reweighted  penalized  least  squares
        based on: Zhi-Min  Zhang,  Shan  Chen,  and  Yi-Zeng Liang.
        Baseline correction using adaptive iteratively reweighted penalized least squares.
        Analyst, 135(5):1138–1146, 2010.
        code from https://github.com/charlesll/rampy/blob/master/rampy/baseline.py
        """

        N = len(y)
        D = sparse.csc_matrix(np.diff(np.eye(N), 2))
        w = np.ones(N)
        iter = 0
        while True:
            iter += 1
            W = sparse.spdiags(w, 0, N, N)
            Z = W + lam * D.dot(D.transpose())
            z = sparse.linalg.spsolve(Z, w * y)
            d = y - z
            # make d- and get w^t with m and s
            dn = d[d < 0]
            wt = 0 * (y >= z) + np.exp(iter * (y - z) / np.linalg.norm(dn)) * (y < z)
            # check exit condition and backup
            if np.linalg.norm(dn) < ratio * np.linalg.norm(y):
                break
            w = wt
        y = y - z
        return y, z

    def arPLS(self, x, y, lam, ratio=0.001):
        """(automatic) Baseline correction using asymmetrically reweighted penalized least squares smoothing.
        Baek et al. 2015, Analyst 140: 250-257;"""

        N = len(y)
        D = sparse.csc_matrix(np.diff(np.eye(N), 2))
        w = np.ones(N)

        while True:
            W = sparse.spdiags(w, 0, N, N)
            Z = W + lam * D.dot(D.transpose())
            z = sparse.linalg.spsolve(Z, w * y)
            d = y - z
            # make d- and get w^t with m and s
            dn = d[d < 0]
            m = np.mean(dn)
            s = np.std(dn)
            wt = 1.0 / (1 + np.exp(2 * (d - (2 * s - m)) / s))
            # check exit condition and backup
            if np.linalg.norm(w - wt) / np.linalg.norm(w) < ratio:
                break
            w = wt
        y = y - z
        return y, z

    def drPLS(self, x, y, lam, ratio=0.0001):
        """(automatic) Baseline correction method based on doubly reweighted penalized least squares.
        Xu et al., Applied Optics 58(14):3913-3920."""
        # roi is not needed for this baseline, but still is a requirement when calling the function.
        roi = np.array([[0, 100], [200, 220], [280, 290], [420, 430], [480, 500]])
        y, z = rp.baseline(x, y, roi, 'drPLS', ratio=ratio, lam=lam)
        y = y.flatten()
        z = z.flatten()
        return y, z


class BaselineCorrectionsDialog(QMainWindow):
    def __init__(self, parent, blc_methods):
        super(BaselineCorrectionsDialog, self).__init__(parent=parent)
        # contains parent: class PlotWindow
        self.pw = parent

        # get axis and figure of PlotWindow
        self.ax = self.pw.ax
        self.fig = self.pw.fig

        self.blcm = blc_methods
        self.methods = self.blcm.methods

        self.spectrum = None
        self.x = None
        self.y = None
        # list containing vertical spans (matplotlib.patches.Polygon) to color regions of interests
        self.roi_spans = []

        self.parameter_editor = {}
        self.parameter_label = {}

    def get_baseline(self, x, y, spectrum):
        self.x = x
        self.y = y
        self.spectrum = spectrum

        self.plot_baseline()
        self.create_dialog()
        self.apply_call()

    def create_dialog(self):
        # layouts
        main_layout = QtWidgets.QVBoxLayout()
        mthd_prmtr_layout = QtWidgets.QHBoxLayout()
        self.parameter_layout = QtWidgets.QGridLayout()

        method_group = self.create_method_group()
        self.fill_parameter_layout()
        parameter_group = QtWidgets.QGroupBox('Parameter')
        button_layout = self.create_buttons()

        # set layouts
        parameter_group.setLayout(self.parameter_layout)
        mthd_prmtr_layout.addWidget(method_group)
        mthd_prmtr_layout.addWidget(parameter_group)
        main_layout.addLayout(mthd_prmtr_layout)
        main_layout.addLayout(button_layout)
        widget = QtWidgets.QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)
        self.setWindowTitle("Baseline")
        self.setWindowModality(Qt.ApplicationModal)
        self.show()

    def create_method_group(self):
        method_layout = QtWidgets.QVBoxLayout()
        method_group = QtWidgets.QGroupBox('Methods')
        # method checkboxes
        method_check_group = QtWidgets.QButtonGroup(self)
        method_check_group.setExclusive(True)
        for meth in self.methods.keys():
            cb = QCheckBox(meth)
            method_layout.addWidget(cb)
            method_check_group.addButton(cb)
            method_check_group.addButton(cb)
            if meth == self.blcm.current_method:
                cb.setChecked(True)
        method_check_group.buttonClicked.connect(self.method_change)
        method_group.setLayout(method_layout)
        return method_group

    def fill_parameter_layout(self):
        idx = 0
        for key, val in self.methods[self.blcm.current_method]['parameter'].items():
            if key == "roi":
                self.add_roi_editors(val, idx)
                continue
            self.parameter_label[key] = QtWidgets.QLabel(key)
            self.parameter_editor[key] = QtWidgets.QLineEdit()
            self.parameter_layout.addWidget(self.parameter_editor[key], idx, 0)
            self.parameter_layout.addWidget(self.parameter_label[key], idx, 1)
            self.parameter_editor[key].setText(str(val))
            self.methods[self.blcm.current_method]['parameter'][key] = float(self.parameter_editor[key].text())
            idx += 1

    def add_roi_editors(self, roi, idx):
        roi_editors = []
        roi_layout_v = QtWidgets.QVBoxLayout()
        button_layout_v = QtWidgets.QVBoxLayout()
        button_layout_h = QtWidgets.QHBoxLayout()
        self.parameter_label['roi'] = QtWidgets.QLabel('regions of interest')
        button_add = QtWidgets.QPushButton('+')
        button_remove = QtWidgets.QPushButton('-')
        button_layout_h.addWidget(button_add)
        button_layout_h.addWidget(button_remove)
        button_layout_v.addWidget(self.parameter_label['roi'])
        button_layout_v.addLayout(button_layout_h)
        button_add.clicked.connect(self.add_roi)
        button_remove.clicked.connect(self.del_roi)
        self.parameter_layout.addLayout(button_layout_v, idx, 1)
        for i, r in enumerate(roi):
            roi_layout_h = QtWidgets.QHBoxLayout()
            editor1 = QtWidgets.QLineEdit()
            editor1.setText(str(r[0]))
            roi_layout_h.addWidget(editor1)
            editor2 = QtWidgets.QLineEdit()
            editor2.setText(str(r[1]))
            roi_layout_h.addWidget(editor2)
            roi_layout_v.addLayout(roi_layout_h)
            roi_editors.append([editor1, editor2])
            self.methods[self.blcm.current_method]['parameter']['roi'][i] = [float(editor1.text()),
                                                                             float(editor2.text())]
        self.parameter_layout.addLayout(roi_layout_v, idx, 0)
        self.parameter_editor['roi'] = roi_editors

    def add_roi(self):
        try:
            last_roi = self.methods[self.blcm.current_method]['parameter']['roi'][-1][1]
        except IndexError:
            last_roi = 140
        self.methods[self.blcm.current_method]['parameter']['roi'].append([last_roi+10, last_roi+40])
        self.method_change()

    def del_roi(self):
        try:
            del self.methods[self.blcm.current_method]['parameter']['roi'][-1]
        except IndexError:
            pass
        self.method_change()

    def sort_roi(self, roi_list):
        return (sorted(roi_list, key=lambda x: x[0]))

    def create_buttons(self):
        # buttons for ok, close and apply
        button_layout = QtWidgets.QHBoxLayout()

        self.finishbutton = QPushButton('Ok')
        self.finishbutton.setCheckable(True)
        self.finishbutton.setToolTip('Are you happy with the start parameters? '
                                     '\n Close the dialog window and save the baseline!')
        self.finishbutton.clicked.connect(self.finish_call)
        button_layout.addWidget(self.finishbutton)

        self.closebutton = QPushButton('Close')
        self.closebutton.setCheckable(True)
        self.closebutton.setToolTip('Closes the dialog window and baseline is not saved.')
        self.closebutton.clicked.connect(self.close)
        button_layout.addWidget(self.closebutton)

        applybutton = QPushButton('Apply')
        applybutton.setToolTip('Do you want to try the fit parameters? \n Lets do it!')
        applybutton.clicked.connect(self.apply_call)
        button_layout.addWidget(applybutton)

        return button_layout

    def plot_baseline(self):
        params = self.methods[self.blcm.current_method]["parameter"].values()
        return_value = self.methods[self.blcm.current_method]['function'](self.x, self.y, *params)
        if return_value is None:
            return
        else:
            yb, zb = return_value
        self.base_line, = self.ax.plot(self.x, zb, 'c--', label='baseline ({})'.format(self.spectrum.get_label()))
        self.blcSpektrum, = self.ax.plot(self.x, yb, 'c-', label='baseline-corrected ({})'.format(self.spectrum.get_label()))
        self.fig.canvas.draw()

    def method_change(self, button=None):
        if button is not None:
            self.blcm.current_method = button.text()

        # clear layout
        self.clear_layout(self.parameter_layout)

        self.parameter_editor = {}
        self.parameter_label = {}

        # create new layout
        self.fill_parameter_layout()
        self.update()

    def clear_layout(self, layout):
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget is None:
                self.clear_layout(layout.itemAt(i))
            else:
                widget.setParent(None)

    def clear_plot(self):
        try:
            self.blcSpektrum.remove()
        except ValueError:
            return
        self.base_line.remove()
        for rs in self.roi_spans:
            rs.remove()
        self.roi_spans = []
        self.fig.canvas.draw()

    def finish_call(self):
        params = self.methods[self.blcm.current_method]["parameter"].values()
        name = self.spectrum.get_label()
        for key, val in self.parameter_editor.items():
            if key == 'roi':
                for i, roi_pe in enumerate(val):
                    roi_start = float(roi_pe[0].text())
                    roi_end = float(roi_pe[1].text())
                    self.methods[self.blcm.current_method]["parameter"]['roi'][i] = [roi_start, roi_end]
                self.methods[self.blcm.current_method]["parameter"]['roi'] = self.sort_roi(
                    self.methods[self.blcm.current_method]["parameter"]['roi'])
                continue
            self.methods[self.blcm.current_method]["parameter"][key] = float(val.text())
        return_value = self.methods[self.blcm.current_method]['function'](self.x, self.y, *params)
        if return_value is None:
            self.close()
            return
        else:
            yb, zb = return_value

        # Plot
        self.pw.spectrum.append(self.ax.plot(self.x, yb, 'c-', label='{} (baseline-corrected)'.format(name))[0])
        self.ax.plot(self.x, zb, 'c--', label='baseline ({})'.format(name))

        self.close()

        # Save baseline corrected data
        (fileBaseName, fileExtension) = os.path.splitext(name)
        startFileDirName = os.path.dirname(self.pw.selectedData[0][3])
        startFileBaseName = startFileDirName + '/' + fileBaseName
        startFileName = startFileBaseName + '_bgc.txt'
        save_data = [self.x, yb]
        save_data = np.transpose(save_data)
        self.pw.save_to_file('Save background-corrected data in file', startFileName, save_data)

        # Append data
        self.pw.data.append([self.x, yb, '{}_bgc'.format(fileBaseName), startFileName, '-', 0])
        self.fig.canvas.draw()

    def apply_call(self):
        params = self.methods[self.blcm.current_method]["parameter"].values()
        name = self.spectrum.get_label()
        self.clear_plot()
        for key, val in self.parameter_editor.items():
            if key == 'roi':
                for i, roi_pe in enumerate(val):
                    roi_start = float(roi_pe[0].text())
                    roi_end = float(roi_pe[1].text())
                    self.methods[self.blcm.current_method]["parameter"]['roi'][i] = [roi_start, roi_end]
                    self.roi_spans.append(self.ax.axvspan(roi_start, roi_end, alpha=0.5, color='yellow'))
                self.methods[self.blcm.current_method]["parameter"]['roi'] = self.sort_roi(
                    self.methods[self.blcm.current_method]["parameter"]['roi'])
                continue
            self.methods[self.blcm.current_method]["parameter"][key] = float(val.text())
        return_value = self.methods[self.blcm.current_method]['function'](self.x, self.y, *params)
        if return_value is None:
            self.close()
            return
        else:
            yb, zb = return_value
        self.base_line, = self.ax.plot(self.x, zb, 'c--', label='baseline ({})'.format(name))
        self.blcSpektrum, = self.ax.plot(self.x, yb, 'c-', label='baseline-corrected ({})'.format(name))
        self.fig.canvas.draw()

    def closeEvent(self, event):
        self.clear_plot()
        event.accept()

class FitFunctions:
    """
    Fit functions
    """

    def __init__(self, pw):
        self.pw = pw

    def LinearFct(self, x, a, b):
        """ linear Function """
        return a * x + b

    def LorentzFct(self, x, xc, h, b):
        """ definition of Lorentzian for fit process """
        return h / (1 + (2 * (x - xc) / b) ** 2)

    def GaussianFct(self, x, xc, h, b):
        """ definition of Gaussian for fit process """
        return h * np.exp(-4 * math.log(2) * ((x - xc) / b) * ((x - xc) / b))

    def BreitWignerFct(self, x, xc, h, b, Q):
        """definition of Breit-Wigner-Fano fucntion for fit process

        (look e.g. "Interpretation of Raman spectra of disordered and amorphous carbon" von Ferrari und Robertson)
        Q is BWF coupling coefficient
        For Q^-1->0: the Lorentzian line is recovered
        """
        return h * (1 + 2 * (x - xc) / (Q * b)) ** 2 / (1 + (2 * (x - xc) / b) ** 2)

    def FctSumme(self, x, *p):
        """
        Summing up the fit functions
        @param x: x data
        @param p: fitparameter
        @return: fitted y data
        """
        a = self.pw.n_fit_fct['Lorentz']  # number of Lorentzians
        b = self.pw.n_fit_fct['Gauss']  # number of Gaussians
        c = self.pw.n_fit_fct['Breit-Wigner-Fano']  # number of Breit-Wigner-Fano functions
        pL = 1
        pG = 1 + a * 3
        pB = 1 + a * 3 + b * 3
        return p[0] + (
                np.sum([self.LorentzFct(x, p[i * 3 + 1], p[i * 3 + 2], p[i * 3 + 3]) for i in range(a)], axis=0) +
                np.sum([self.GaussianFct(x, p[i * 3 + pG], p[i * 3 + 1 + pG], p[i * 3 + 2 + pG]) for i in range(b)],
                       axis=0) +
                np.sum(
                    [self.BreitWignerFct(x, p[i * 4 + pB], p[i * 4 + 1 + pB], p[i * 4 + 2 + pB], p[i * 4 + 3 + pB])
                     for i in range(c)], axis=0))

class FitOptionsDialog(QMainWindow):
    closeSignal = QtCore.pyqtSignal()  # Signal in case Fit-parameter window is closed

    def __init__(self, parent):
        """
        Options Dialog for Fitprocess

        Parameters
        ----------
        parent: PlotWindow
        """
        super(FitOptionsDialog, self).__init__(parent=parent)
        self.parent = parent
        self.n_fit_fct = {  # number of fit functions (Lorentzian, Gaussian and Breit-Wigner-Fano)
            'Lorentz': 0,
            'Gauss': 0,
            'Breit-Wigner-Fano': 0
        }
        self.fit_fcts = {}
        self.continue_fit = False

        self.create_dialog()
        self.create_menubar()

    def create_dialog(self):
        self.layout = QtWidgets.QVBoxLayout()

        # Button to add Fit function
        addbutton = QPushButton("Add Function")
        addbutton.clicked.connect(lambda: self.add_function(
            'Lorentz', [[520, 0, np.inf], [100, 0, np.inf], [25, 0, np.inf]]))
        self.layout.addWidget(addbutton)

        # Button to remove fit funtion
        removebutton = QPushButton('Remove Funtion')
        removebutton.clicked.connect(self.remove_function)
        self.layout.addWidget(removebutton)

        # OK Button => accept start values for fit
        okbutton = QPushButton("OK")
        okbutton.clicked.connect(self.ok_press)
        self.layout.addWidget(okbutton)

        # create table
        self.table = QtWidgets.QTableWidget(1, 5)
        self.table.itemChanged.connect(self.value_changed)

        # set items in each cell
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                cell = QtWidgets.QTableWidgetItem('')
                self.table.setItem(r, c, cell)

        # set headers
        self.hheaders = ['Fit Function', 'Parameter', 'Value', 'Lower Bound', 'Upper Bound']
        self.table.setHorizontalHeaderLabels(self.hheaders)
        self.vheaders = ['0']
        self.table.setVerticalHeaderLabels(self.vheaders)

        # background
        self.table.item(0, 0).setFlags(Qt.NoItemFlags)  # no interaction with this cell
        self.table.item(0, 1).setText('Background')
        self.table.item(0, 1).setFlags(Qt.NoItemFlags)
        self.background = self.table.item(0, 2)
        self.background.setText(str(0.0))

        # bounds
        self.table.item(0, 3).setText(str(-np.inf))
        self.table.item(0, 4).setText(str(np.inf))

        self.layout.addWidget(self.table)

        widget = QtWidgets.QWidget()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)
        self.setWindowTitle("Fit Functions")
        self.setWindowModality(Qt.ApplicationModal)

    def create_menubar(self):
        self.menubar = self.menuBar()
        fileMenu = self.menubar.addMenu('File')
        fileMenu.addAction('Save Start Parameter', self.save_start_parameter)
        fileMenu.addAction('Load Start Parameter', self.load_start_parameter)

    def add_function(self, fct_name, fct_values):
        """
        add fit function to table
        """

        n = len(self.fit_fcts) + 1  # Number of functions
        self.fit_fcts.update({n: {}})

        if fct_name == 'Breit-Wigner-Fano':
            add_rows = 4
        else:
            add_rows = 3

        self.table.setRowCount(self.table.rowCount() + add_rows)
        self.vheaders.extend([str(n), str(n), str(n)])
        self.table.setVerticalHeaderLabels(self.vheaders)

        rows = self.table.rowCount()

        # set items in new cell
        for r in range(rows - add_rows, rows):
            for c in range(self.table.columnCount()):
                cell = QtWidgets.QTableWidgetItem('')
                self.table.setItem(r, c, cell)

        # add Combobox to select fit function
        cbox = QtWidgets.QComboBox(self)
        cbox.addItem("Lorentz")
        cbox.addItem("Gauss")
        cbox.addItem("Breit-Wigner-Fano")
        cbox.setCurrentText(fct_name)
        cbox.currentTextChanged.connect(lambda: self.fct_change(cbox.currentText(), n))
        self.table.setCellWidget(rows - add_rows, 0, cbox)
        self.fit_fcts[n].update({'fct': cbox})

        # configurate cells
        self.table.item(rows - 2, 0).setFlags(Qt.NoItemFlags)  # no interaction with these cells
        self.table.item(rows - 1, 0).setFlags(Qt.NoItemFlags)
        # postion
        self.table.item(rows - add_rows, 1).setText('Position')
        self.table.item(rows - add_rows, 1).setFlags(Qt.NoItemFlags)
        self.table.item(rows - add_rows, 2).setText(str(fct_values[0][0]))  # starting value
        self.table.item(rows - add_rows, 3).setText(str(fct_values[0][1]))  # lower bound
        self.table.item(rows - add_rows, 4).setText(str(fct_values[0][2]))  # upper bound
        self.fit_fcts[n].update({'position': self.table.item(rows - add_rows, 2)})

        # intensity
        self.table.item(rows - add_rows + 1, 1).setText('Intensity')
        self.table.item(rows - add_rows + 1, 1).setFlags(Qt.NoItemFlags)
        self.table.item(rows - add_rows + 1, 2).setText(str(fct_values[1][0]))  # starting value
        self.table.item(rows - add_rows + 1, 3).setText(str(fct_values[1][1]))  # lower bound
        self.table.item(rows - add_rows + 1, 4).setText(str(fct_values[1][2]))  # upper bound
        self.fit_fcts[n].update({'intensity': self.table.item(rows - add_rows + 1, 2)})
        # FWHM
        self.table.item(rows - add_rows + 2, 1).setText('FWHM')
        self.table.item(rows - add_rows + 2, 1).setFlags(Qt.NoItemFlags)
        self.table.item(rows - add_rows + 2, 2).setText(str(fct_values[2][0]))  # starting value
        self.table.item(rows - add_rows + 2, 3).setText(str(fct_values[2][1]))  # lower bound
        self.table.item(rows - add_rows + 2, 4).setText(str(fct_values[2][2]))  # upper bound
        self.fit_fcts[n].update({'FWHM': self.table.item(rows - add_rows + 2, 2)})

        if fct_name == 'Breit-Wigner-Fano':
            # additional parameter
            self.table.item(rows - add_rows + 3, 1).setText('Additional Parameter')
            self.table.item(rows - add_rows + 3, 1).setFlags(Qt.NoItemFlags)
            self.table.item(rows - add_rows + 3, 2).setText(str(fct_values[3][0]))  # starting value
            self.table.item(rows - add_rows + 3, 3).setText(str(fct_values[3][1]))  # lower bound
            self.table.item(rows - add_rows + 3, 4).setText(str(fct_values[3][2]))  # upper bound
            self.fit_fcts[n].update({'additional': self.table.item(rows - add_rows + 3, 2)})

        # boundaries
        low_bounds = []
        up_bounds = []
        for j in range(rows - add_rows, rows):
            low_bounds.append(self.table.item(j, 3))
            up_bounds.append(self.table.item(j, 4))
        self.fit_fcts[n].update({'lower boundaries': low_bounds})
        self.fit_fcts[n].update({'upper boundaries': up_bounds})

    def remove_function(self):
        try:
            last_key = list(self.fit_fcts.keys())[-1]
        except IndexError:
            return

        row_indices = [i for i, x in enumerate(self.vheaders) if x == str(last_key)]
        for j in reversed(row_indices):
            del self.vheaders[j]
            self.table.removeRow(j)
        del self.fit_fcts[last_key]

    def fct_change(self, fct_name, n):
        if fct_name == 'Breit-Wigner-Fano' and all(k != 'additional' for k in self.fit_fcts[n].keys()):
            row_index = self.vheaders.index(str(n)) + 3
            self.table.insertRow(row_index)
            self.vheaders.insert(row_index, str(n))
            self.table.setVerticalHeaderLabels(self.vheaders)
            # set items in new cell
            for c in range(self.table.columnCount()):
                cell = QTableWidgetItem('')
                self.table.setItem(row_index, c, cell)
            self.table.item(row_index, 1).setText('Additional Parameter')
            self.table.item(row_index, 1).setFlags(Qt.NoItemFlags)
            self.table.item(row_index, 2).setText(str(-10))
            # boundaries
            self.table.item(row_index, 3).setText(str(-np.inf))
            self.table.item(row_index, 4).setText(str(np.inf))
            # update dictionary
            self.fit_fcts[n]['lower boundaries'].append(self.table.item(row_index, 3))
            self.fit_fcts[n]['upper boundaries'].append(self.table.item(row_index, 4))
            self.fit_fcts[n].update({'additional': self.table.item(row_index, 2)})
        elif fct_name != 'Breit-Wigner-Fano' and any(k == 'additional' for k in self.fit_fcts[n].keys()):
            row_index = self.vheaders.index(str(n)) + 3
            del self.vheaders[row_index]
            self.table.removeRow(row_index)
            del self.fit_fcts[n]['additional']
        else:
            pass

    def value_changed(self, item):
        if item is None or self.table.item(item.row(), 3) is None or self.table.item(item.row(), 4) is None:
            return
        elif item.text() == '' or self.table.item(item.row(), 3).text() == '' or \
                self.table.item(item.row(), 4).text() == '':
            return
        else:
            pass
        # check that lower bound is strictly less than upper bound
        if item.column() == 3:
            if float(item.text()) > float(self.table.item(item.row(), 4).text()):
                self.parent.mw.show_statusbar_message('Lower bounds have to be strictly less than upper bounds', 4000,
                                                      error_sound=True)
                # add: replace item with old previous item
        elif item.column() == 4:  # check that upper bound is strictly higher than lower bound
            if float(item.text()) < float(self.table.item(item.row(), 3).text()):
                self.parent.mw.show_statusbar_message('Upper bounds have to be strictly higher than lower bounds', 4000,
                                                      error_sound=True)
                # add: replace item with old previous item

    def save_start_parameter(self):
        SaveFileName = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File')
        if SaveFileName[0] != '':
            filename = SaveFileName[0]
        else:
            return

        param = []
        for col in range(self.table.columnCount()):
            colparam = []
            for row in range(self.table.rowCount()):
                item = self.table.item(row, col)
                widget = self.table.cellWidget(row, col)
                if widget != None and isinstance(widget, QtWidgets.QComboBox):
                    colparam.append(widget.currentText())
                elif item != None:
                    colparam.append(item.text())
                else:
                    colparam.append(np.nan)
            param.append(colparam)

        param = np.array(param)

        np.savetxt(filename, param.T, fmt='%s', delimiter=', ')

    def load_start_parameter(self):
        load_filename = QtWidgets.QFileDialog.getOpenFileName(self, 'Load starting parameter')
        if load_filename[0] != '':
            filename = load_filename[0]
        else:
            return

        tablecontent = np.genfromtxt(filename, dtype='str', delimiter=', ')

        # set Background
        self.table.item(0, 2).setText(str(tablecontent[0][2]))  # starting parameter
        self.table.item(0, 3).setText(str(tablecontent[0][3]))  # lower bound
        self.table.item(0, 4).setText(str(tablecontent[0][4]))  # upper bound

        # delete background from tablecontent
        tablecontent = np.delete(tablecontent, 0, axis=0)

        fct_value = []
        for j in tablecontent:
            if j[0] != '' and fct_value != []:
                self.add_function(fct_name, fct_value)
                fct_value = []
                fct_name = j[0]
            elif j[0] != '':
                fct_name = j[0]
            else:
                pass
            fct_value.append([j[2], j[3], j[4]])
        self.add_function(fct_name, fct_value)

    def ok_press(self):
        self.p_start = [float(self.background.text())]  # Background
        parameter = {'Lorentz': [],
                     'Gauss': [],
                     'Breit-Wigner-Fano': []}

        bg_low = self.table.item(0, 3).text()
        bg_up = self.table.item(0, 4).text()
        if bg_low == '':
            bg_low = -np.inf
        else:
            bg_low = float(bg_low)
        if bg_up == '':
            bg_up = np.inf
        else:
            bg_up = float(bg_up)
        self.boundaries = [[bg_low], [bg_up]]
        lower_boundaries = {'Lorentz': [],
                            'Gauss': [],
                            'Breit-Wigner-Fano': []}
        upper_boundaries = {'Lorentz': [],
                            'Gauss': [],
                            'Breit-Wigner-Fano': []}

        for key in self.fit_fcts.keys():
            name_fct = self.fit_fcts[key]['fct'].currentText()
            parameter[name_fct].append(float(self.fit_fcts[key]['position'].text()))  # Peak position in cm^-1
            parameter[name_fct].append(float(self.fit_fcts[key]['intensity'].text()))  # Intensity
            parameter[name_fct].append(float(self.fit_fcts[key]['FWHM'].text()))  # FWHM
            if name_fct == 'Breit-Wigner-Fano':
                parameter[name_fct].append(
                    float(self.fit_fcts[key]['additional'].text()))  # additional BWF parameter for asymmetry
            for lb, ub in zip(self.fit_fcts[key]['lower boundaries'], self.fit_fcts[key]['upper boundaries']):
                if lb.text() == '':
                    lower_boundaries[name_fct].append(-np.inf)
                else:
                    lower_boundaries[name_fct].append(float(lb.text()))

                if ub.text() == '':
                    upper_boundaries[name_fct].append(np.inf)
                else:
                    upper_boundaries[name_fct].append(float(ub.text()))
            self.n_fit_fct[name_fct] += 1

        for p in parameter.values():
            self.p_start.extend(p)

        for lb, ub in zip(lower_boundaries.values(), upper_boundaries.values()):
            self.boundaries[0].extend(lb)
            self.boundaries[1].extend(ub)

        self.continue_fit = True
        self.close()

    def closeEvent(self, event):
        self.closeSignal.emit()
        event.accept


class MyCustomToolbar(NavigationToolbar2QT):
    signal_remove_line = QtCore.pyqtSignal(object)
    toolitems = [t for t in NavigationToolbar2QT.toolitems]
    # Add new toolitem at last position

    toolitems.append(
        ('Layers', "manage layers and layer contents",
         'Layer', "layer_content"))

    def __init__(self, plotCanvas):
        NavigationToolbar2QT.__init__(self, plotCanvas, parent=None)
        self.setWindowTitle("Top Toolbar")

    def layer_content(self):
        Layer_Legend = QDialog()
        layout = QtWidgets.QGridLayout()
        Layer_Legend.setLayout(layout)
        Layer_Legend.setWindowTitle("Layer Content")
        Layer_Legend.setWindowModality(Qt.ApplicationModal)
        Layer_Legend.exec_()

    def edit_parameters(self):
        axes = self.canvas.figure.get_axes()
        if not axes:
            QtWidgets.QMessageBox.warning(self.canvas.parent(), "Error", "There are no axes to edit.")
            return
        figureoptions.figure_edit(axes, self)

    def save_figure(self, *args):
        # keep the default behaviour
        super(MyCustomToolbar, self).save_figure(*args)

    def _icon(self, name, color=None):
        if name == 'Layer.png':
            icon = QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/Layer_content.png")
        else:
            name = name.replace('.png', '_large.png')
            pm = QtGui.QPixmap(str(cbook._get_data_path('images', name)))
            _setDevicePixelRatio(pm, _devicePixelRatioF(self))
            if color is not None:
                mask = pm.createMaskFromColor(QtGui.QColor('black'),
                                              QtCore.Qt.MaskOutColor)
                pm.fill(color)
                pm.setMask(mask)
            icon = QIcon(pm)
        return icon


class PlotWindow(QMainWindow):
    """
    Parameters
    ----------
    plot_data: array containing dict
    """

    closeWindowSignal = QtCore.pyqtSignal(str, str)  # Signal in case plotwindow is closed

    def __init__(self, plot_data, fig, parent):
        super(PlotWindow, self).__init__(parent)
        self.fig = fig
        self.data = plot_data
        self.mw = parent
        self.spectrum = []
        self.vert_line = None
        self.functions = FitFunctions(self)
        self.blc = BaselineCorrectionMethods()       # class for everything related to Baseline corrections
        self.inserted_text = []  # Storage for text inserted in the plot
        self.drawn_line = []  # Storage for lines and arrows drawn in the plot
        self.n_fit_fct = {  # number of fit functions (Lorentzian, Gaussian and Breit-Wigner-Fano)
            'Lorentz': 0,
            'Gauss': 0,
            'Breit-Wigner-Fano': 0
        }

        self.plot()
        self.create_statusbar()
        self.create_menubar()
        self.create_sidetoolbar()

        # self.cid1 = self.fig.canvas.mpl_connect('button_press_event', self.mousePressEvent)
        self.cid2 = self.fig.canvas.mpl_connect('key_press_event', self.keyPressEvent)
        self.cid3 = self.fig.canvas.mpl_connect('pick_event', self.pickEvent)

    def plot(self):
        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)
        layout = QtWidgets.QVBoxLayout(self.main_widget)
        legendfontsize = 24
        labelfontsize = 24
        tickfontsize = 18

        if self.fig is None:  # new Plot
            self.fig = Figure(figsize=(15, 9))
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvasQTAgg(self.fig)
            layout.addWidget(self.canvas)

            for d in self.data:
                if d["yerr"] is not None:  # errors
                    (spect, capline, barlinecol) = self.ax.errorbar(d["x"], d["y"], yerr=d["yerr"], fmt=d["plot type"],
                                                                    picker=True, pickradius=5, capsize=3,
                                                                    label='_Hidden errorbar {}'.format(d["label"]))
                    self.spectrum.append(spect)
                    spect.set_label(d["label"])
                else:
                    self.spectrum.append(self.ax.plot(d["x"], d["y"], d["plot type"], label=d["label"],
                                                      picker=True, pickradius=5)[0])
            self.ax.legend(fontsize=legendfontsize)
            if self.data[0]["xaxis"] is None:
                self.data[0]["xaxis"] = r'Raman shift / cm$^{-1}$'

            if self.data[0]["yaxis"] is None:
                self.data[0]["yaxis"] = r'Intensity / cts/s'

            self.ax.set_xlabel(self.data[0]["xaxis"], fontsize=labelfontsize)
            self.ax.set_ylabel(self.data[0]["yaxis"], fontsize=labelfontsize)
            self.ax.xaxis.set_tick_params(labelsize=tickfontsize)
            self.ax.yaxis.set_tick_params(labelsize=tickfontsize)
        else:  # loaded Plot
            # self.fig._remove_ax = lambda: None
            self.ax = self.fig.axes[0]
            self.canvas = FigureCanvasQTAgg(self.fig)
            layout.addWidget(self.canvas)
            for j in self.ax.lines:
                self.spectrum.append(j)
            it = []
            for j in self.ax.get_children():
                if type(j) == mpatches.FancyArrowPatch:  # all drawn lines and arrows
                    self.drawn_line.append(LineDrawer(j))
                elif type(j) == matplotlib.text.Annotation and j not in it:  # all inserted texts
                    it.append(j)
                    self.inserted_text.append(InsertText(j, self.mw))
                else:
                    pass
            self.ax.get_legend()
        toolbar = MyCustomToolbar(self.canvas)
        toolbar.signal_remove_line.connect(self.remove_line)
        self.addToolBar(toolbar)
        self.ax.get_legend().set_picker(5)

    def add_plot(self, new_data):
        ls = self.spectrum[0].get_linestyle()
        ma = self.spectrum[0].get_marker()
        for d in new_data:
            self.data.append(d)
            if d["yerr"] is not None:
                (spect, capline, barlinecol) = self.ax.errorbar(d["x"], d["y"], yerr=d["yerr"], picker=True,
                                                                pickradius=5, capsize=3,
                                                                label='_Hidden errorbar {}'.format(d["label"]))
                self.spectrum.append(spect)
                spect.set_label(d["label"])
            else:
                spect = self.ax.plot(d["x"], d["y"], label=d["label"], picker=True, pickradius=5)[0]
                self.spectrum.append(spect)
            spect.set_linestyle(ls)
            spect.set_marker(ma)
        handles, labels = self.ax.get_legend_handles_labels()
        self.update_legend(handles, labels)
        self.canvas.draw()

    def remove_line(self, line):
        """
        remove data from self.spectrum and self.data after line was removed
        in figureoptions
        """
        i = self.spectrum.index(line)
        self.data.pop(i)
        self.spectrum.pop(i)

    def pickEvent(self, event):
        if event.mouseevent.dblclick == True and event.artist == self.ax.get_legend():
            Dialog_Legend = QDialog()
            layout = QtWidgets.QGridLayout()
            handles, labels = self.ax.get_legend_handles_labels()

            LabelList = QtWidgets.QListWidget()
            LabelList.setAcceptDrops(True)
            LabelList.setDragEnabled(True)
            LabelList.setDragDropMode(LabelList.InternalMove)

            for j in labels:
                LabelList.insertItem(1, j)

            layout.addWidget(LabelList)

            Dialog_Legend.setLayout(layout)
            Dialog_Legend.setWindowTitle("Legend order")
            Dialog_Legend.setWindowModality(Qt.ApplicationModal)
            Dialog_Legend.exec_()

            LabelListItems = [LabelList.item(i).text() for i in range(LabelList.count())]
            new_handles = []
            new_labels = []
            for j in LabelListItems:
                for i in range(len(labels)):
                    if j == labels[i]:
                        new_handles.append(handles[i])
                        new_labels.append(labels[i])

            self.update_legend(new_handles, new_labels)
            self.canvas.draw()
        elif event.artist in self.spectrum and event.mouseevent.button == 3:
            line_dialog = QMenu()
            line_dialog.addAction("Go to Spreadsheet", lambda: self.go_to_spreadsheet(event.artist))
            point = self.mapToGlobal(
                QtCore.QPoint(event.mouseevent.x, self.frameGeometry().height() - event.mouseevent.y))
            line_dialog.exec_(point)
        else:
            pass

    def update_legend(self, leg_handles, leg_labels):
        if self.ax.get_legend() is not None:
            old_legend = self.ax.get_legend()
            leg_draggable = old_legend._draggable is not None
            leg_ncol = old_legend._ncol
            leg_fontsize = int(old_legend._fontsize)
            leg_frameon = old_legend.get_frame_on()
            leg_shadow = old_legend.shadow
            leg_fancybox = type(old_legend.legendPatch.get_boxstyle())
            leg_framealpha = old_legend.get_frame().get_alpha()
            leg_picker = old_legend.get_picker()
        else:
            leg_draggable = False
            leg_ncol = 1
            leg_fontsize = 15
            leg_frameon = True
            leg_shadow = True
            leg_fancybox = True
            leg_framealpha = 0.5
            leg_picker = 5

        new_legend = self.ax.legend(leg_handles, leg_labels,
                                    ncol=leg_ncol,
                                    fontsize=float(leg_fontsize),
                                    frameon=leg_frameon,
                                    shadow=leg_shadow,
                                    framealpha=leg_framealpha,
                                    fancybox=leg_fancybox)

        new_legend.set_picker(leg_picker)
        new_legend.set_draggable(leg_draggable)

    # Bars (menubar, toolbar, statusbar)
    def create_menubar(self):
        menubar = self.menuBar()
        # 1. menu item: File
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction('Save to File', self.menu_save_to_file)

        # 2. menu item: Edit
        editMenu = menubar.addMenu('&Edit')

        editDelete = editMenu.addMenu('Delete broken pixel - LabRam')
        editDelete.addAction("532nm")
        editDelete.addAction("633nm")
        editDelete.triggered[QAction].connect(self.del_broken_pixel)

        editDeletePixel = editMenu.addAction('Delete single datapoint', self.del_datapoint)
        editDeletePixel.setStatusTip(
            'Delete selected data point with Enter, Move with arrow keys, Press c to leave Delete-Mode')

        editSelectArea = editMenu.addAction('Define data area', self.DefineArea)
        editSelectArea.setStatusTip('Move area limit with left mouse click, set it fix with right mouse click')

        editNorm = editMenu.addMenu('Normalize spectrum regarding ...')
        editNorm.setStatusTip('Normalizes highest peak to 1')
        editNorm.addAction('... highest peak', self.normalize)
        editNorm.addAction('... selected peak', lambda: self.normalize(select_peak=True))

        editAddSubAct = editMenu.addAction('Add up or subtract two spectra', self.add_subtract_spectra)

        # 3. menu: Analysis
        analysisMenu = menubar.addMenu('&Analysis')

        # 3.1 Analysis Fit
        analysisFit = analysisMenu.addMenu('&Fit')

        analysisFitSingleFct = analysisFit.addMenu('&Single function')
        analysisFitSingleFct.addAction('Lorentz')
        analysisFitSingleFct.addAction('Gauss')
        analysisFitSingleFct.addAction('Breit-Wigner-Fano')
        analysisFitSingleFct.triggered[QAction].connect(self.fit_single_peak)

        analysisFit.addAction('Fit several Peaks', self.fit_peaks)

        analysisRoutine = analysisMenu.addMenu('&Analysis routines')
        analysisRoutine.addAction('D und G Bande', self.fit_D_G)
        analysisRoutine.addAction('Fit Sulfur oxyanion spectrum', self.fit_sulfuroxyanion)
        analysisRoutine.addAction('Get m/I(G) (Hydrogen content)', self.hydrogen_estimation)
        analysisRoutine.addAction('Norm to water peak', self.norm_to_water)

        # 3.2 Linear regression
        analysisMenu.addAction('Linear regression', self.linear_regression)

        # 3.3 Analysis base line correction
        analysisMenu.addAction('Baseline Corrections', self.baseline)

        # 3.3 Smoothing
        analysisSmoothing = analysisMenu.addMenu('&Smoothing')
        analysisSmoothing.addAction('Savitsky-Golay')
        analysisSmoothing.addAction('Whittaker')
        analysisSmoothing.triggered[QAction].connect(self.smoothing)

        # 3.5 Analysis find peaks
        analysisMenu.addAction('Find Peak', self.find_peaks)

        # 3.6 Get Area below curve
        analysisMenu.addAction('Get Area below Curve', self.detemine_area)

        self.show()

    def create_statusbar(self):
        self.statusBar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusBar)
        self.show()

    def create_sidetoolbar(self):
        toolbar = QtWidgets.QToolBar("Vertical Sidebar", self)
        self.addToolBar(QtCore.Qt.LeftToolBarArea, toolbar)

        # Vertical line for comparison of peak positions
        VertLineAct = QAction(QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/Tool_Line.png"), 'Vertical Line', self)
        VertLineAct.setStatusTip('Vertical line for comparison of peak position')
        VertLineAct.triggered.connect(self.vertical_line)
        toolbar.addAction(VertLineAct)

        # Tool to scale intensity of selected spectrum
        ScaleAct = QAction(QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/Tool_Scale.png"), 'Scale', self)
        ScaleAct.setStatusTip('Tool to scale intensity of selected spectrum')
        ScaleAct.triggered.connect(self.scale_spectrum)
        toolbar.addAction(ScaleAct)

        # Tool to shift selected spectrum in y-direction
        ShiftAct = QAction(QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/Tool_Shift.png"), 'Shift', self)
        ShiftAct.setStatusTip('Tool to shift selected spectrum in y-direction')
        ShiftAct.triggered.connect(self.shift_spectrum)
        toolbar.addAction(ShiftAct)

        # Tool to draw line
        DrawAct = QAction(QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/Arrow.png"), 'Draw', self)
        DrawAct.setStatusTip('Tool to draw lines and arrows')
        DrawAct.triggered.connect(self.draw_line)
        toolbar.addAction(DrawAct)

        # Tool to insert Text
        TextAct = QAction(QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/Tool_Text.png"), 'Text', self)
        TextAct.setStatusTip('Insert Text')
        TextAct.triggered.connect(self.insert_text)
        toolbar.addAction(TextAct)

        self.show()

    #### Functions and other stuff ####
    def go_to_spreadsheet(self, line):
        line_index = self.spectrum.index(line)
        if self.data[line_index]["spreadsheet title"]:
            spreadsheet_name = self.data[line_index]["spreadsheet title"]
            item = self.mw.treeWidget.findItems(spreadsheet_name, Qt.MatchFixedString | Qt.MatchRecursive)
            for j in item:  # select spreadsheet if there are several items with same name
                if j.type() == 1:
                    spreadsheet_item = j
                    break
                else:
                    continue
            self.mw.activate_window(spreadsheet_item)
            spreadsheet = self.mw.window['Spreadsheet'][spreadsheet_name]
            header_name = self.data[line_index]["label"]
            for j in range(spreadsheet.data_table.columnCount()):
                if spreadsheet.header_table.horizontalHeaderItem(j).text() == header_name + ' (Y)':
                    self.mw.show_statusbar_message(header_name, 4000)
                    spreadsheet.header_table.setCurrentCell(0, j)
                    break
                else:
                    continue

        else:
            self.mw.show_statusbar_message('OOPS! Something went wrong!', 3000)

    def SelectDataset(self, select_only_one=False):
        data_sets_name = []
        self.selectedData = []
        for j in self.spectrum:
            data_sets_name.append(j.get_label())
        if len(data_sets_name) == 0:
            self.selectedDatasetNumber = []
        elif len(data_sets_name) == 1:
            self.selectedDatasetNumber = [0]
        else:
            DSS = DataSetSelecter(data_sets_name, select_only_one)
            self.selectedDatasetNumber = DSS.selectedDatasetNumber

        for j in self.selectedDatasetNumber:
            self.selectedData.append(self.data[j])

    def menu_save_to_file(self):
        self.SelectDataset()
        for d in self.selectedData:
            if d["filename"] is not None:
                startFileDirName = os.path.dirname(d["filename"])
                startFileName = '{}/{}'.format(startFileDirName, d["label"])
            else:
                startFileName = None
            save_data = [d["x"], d["y"]]
            save_data = np.transpose(save_data)
            self.save_to_file('Save data selected data in file', startFileName, save_data)

    def save_to_file(self, WindowName, startFileName, data):
        SaveFileName = QFileDialog.getSaveFileName(self, WindowName, startFileName, "All Files (*);;Text Files (*.txt)")
        if SaveFileName[0] != '':
            SaveFileName = SaveFileName[0]
            if SaveFileName[-4:] == '.txt':
                pass
            else:
                SaveFileName = str(SaveFileName) + '.txt'
        else:
            return

        if isinstance(data, (np.ndarray, np.generic)):
            np.savetxt(SaveFileName, data, fmt='%.5f')
            np.savetxt(SaveFileName, data, fmt='%.5f')
        else:
            file = open(SaveFileName, 'w+')
            file.write(data)
            file.close()

    def del_datapoint(self):
        self.SelectDataset()
        for j in self.selectedDatasetNumber:
            pickDP = DataPointPicker(self.spectrum[j], 0)
            idx = pickDP.idx
            self.data[j]["x"] = np.delete(self.data[j]["x"], idx)
            self.data[j]["y"] = np.delete(self.data[j]["y"], idx)
            self.spectrum[j].set_data(self.data[j]["y"], self.data[j]["y"])
            self.setFocus()

    def del_broken_pixel(self, action):
        """
        Deletes data point with number 630+n*957, because this pixel is broken in CCD detector of LabRam
        """
        data_idx_diff = {'532nm': 957, '633nm': 924}
        self.SelectDataset()
        for j in self.selectedDatasetNumber:
            data_idx = 629         # index of first broken data point
            border = 6
            print('Following data points of {} were deleted'.format(self.data[j]["label"]))
            while data_idx <= len(self.data[j]["x"]):
                data_min_idx = np.argmin(self.data[j]["y"][data_idx - border:data_idx + border])
                if data_min_idx == 0 or data_min_idx == 2*border:
                    QMessageBox.about(self, "Title",
                                      "Please select this data point manually (around {} in the data set {})".format(
                                          self.data[j]["x"][data_idx], self.data[j]["y"]))
                    pickDP = DataPointPicker(self.spectrum[j], data_idx)
                    data_idx = pickDP.idx
                else:
                    data_idx += data_min_idx - border

                print(self.data[j]["x"][data_idx], self.data[j]["y"][data_idx])
                self.data[j]["x"] = np.round(np.delete(self.data[j]["x"], data_idx), 5)
                self.data[j]["y"] = np.delete(self.data[j]["y"], data_idx)
                data_idx += data_idx_diff[action.text()]

            self.spectrum[j].set_data(self.data[j]["x"], self.data[j]["y"])
            self.setFocus()
            self.canvas.draw()

            # Save data without defective data points
            startFileDirName = os.path.dirname(self.data[j]["filename"])
            startFileName = startFileDirName + '/' + self.data[j]["label"]
            save_data = [self.data[j]["x"], self.data[j]["y"]]
            save_data = np.transpose(save_data)
            self.save_to_file('Save data without deleted data points in file', startFileName, save_data)

    def normalize(self, select_peak=False):
        """
        normalize spectrum regarding to highest peak or regarding selected peak
        """
        self.SelectDataset()
        for n in self.selectedDatasetNumber:
            norm_factor = numpy.amax(self.data[n]["y"])
            if select_peak:
                dpp = DataPointPicker(self.spectrum[n], np.where(self.data[n]["y"] == norm_factor))
                idx = dpp.idx
                norm_factor = self.data[n]["y"][idx]

            self.data[n]["y"] = self.data[n]["y"] / norm_factor
            self.spectrum[n].set_data(self.data[n]["x"], self.data[n]["y"])
            self.canvas.draw()
            # Save normalized data
            if self.data[n]["filename"] is not None:
                (fileBaseName, fileExtension) = os.path.splitext(self.data[n]["label"])
                startFileDirName = os.path.dirname(self.data[n]["filename"])
                startFileBaseName = startFileDirName + '/' + fileBaseName
                startFileName = startFileBaseName + '_norm.txt'
            else:
                startFileName = None
            save_data = [self.data[n]["x"], self.data[n]["y"]]
            save_data = np.transpose(save_data)
            self.save_to_file('Save normalized data in file', startFileName, save_data)

    def add_subtract_spectra(self):
        """
        function to add or subtract a spectrum from an other spectrum
        """
        self.dialog_add_sub = QDialog()
        vlayout = QtWidgets.QVBoxLayout()
        hlayout = QtWidgets.QHBoxLayout()

        cbox_spectrum1 = QtWidgets.QComboBox(self.dialog_add_sub)
        for s in self.spectrum:
            cbox_spectrum1.addItem(s.get_label())
        hlayout.addWidget(cbox_spectrum1)

        cbox_operation = QtWidgets.QComboBox(self.dialog_add_sub)
        cbox_operation.addItem('+')
        cbox_operation.addItem('-')
        hlayout.addWidget(cbox_operation)

        cbox_spectrum2 = QtWidgets.QComboBox(self.dialog_add_sub)
        for s in self.spectrum:
            cbox_spectrum2.addItem(s.get_label())
        hlayout.addWidget(cbox_spectrum2)

        vlayout.addLayout(hlayout)

        ok_button = QtWidgets.QPushButton('Ok')
        ok_button.setFixedWidth(100)
        vlayout.addWidget(ok_button)

        ok_button.clicked.connect(self.dialog_add_sub.close)

        self.dialog_add_sub.setLayout(vlayout)
        self.dialog_add_sub.exec_()

        sp1 = cbox_spectrum1.currentText()
        i1 = cbox_spectrum1.currentIndex()
        sp2 = cbox_spectrum2.currentText()
        i2 = cbox_spectrum2.currentIndex()
        op = cbox_operation.currentText()

        x1 = self.spectrum[i1].get_xdata()
        x2 = self.spectrum[i2].get_xdata()

        # check that x data is the same
        if (x1 == x2).all():
            pass
        else:
            self.mw.show_statusbar_message('Not the same x data', 4000)
            return

        y1 = self.spectrum[i1].get_ydata()
        y2 = self.spectrum[i2].get_ydata()

        if op == '+':
            y = y1 + y2
        elif op == '-':
            y = y1 - y2
        else:
            return

        line = self.ax.plot(x1, y, label='subtracted Spectrum')
        self.spectrum.append(line)

        self.canvas.draw()

    def get_start_values(self, s_pos=3250, s_height=150, s_FWHM=300):
        self.Dialog_FitParameter = QDialog()
        layout_hor = QtWidgets.QHBoxLayout()
        layout1 = QtWidgets.QVBoxLayout()
        layout2 = QtWidgets.QVBoxLayout()

        background = QtWidgets.QLineEdit()
        layout1.addWidget(background)
        background.setText('0.0')
        layout2.addWidget(QtWidgets.QLabel('Background'))

        position = []
        intensity = []
        FWHM = []
        BWF_parmeter = []

        ni = 0
        for key, val in self.n_fit_fct.items():
            for j in range(ni, ni + int(val)):
                ni += 1
                layout1.addWidget(QtWidgets.QLabel('{}. {}'.format(j + 1, key)))
                layout2.addWidget(QtWidgets.QLabel(''))

                position.append(QtWidgets.QLineEdit())
                layout1.addWidget(position[j])
                position[j].setText(str(s_pos))
                layout2.addWidget(QtWidgets.QLabel(r'Position in cm^-1'))

                intensity.append(QtWidgets.QLineEdit())
                layout1.addWidget(intensity[j])
                intensity[j].setText(str(s_height))
                layout2.addWidget(QtWidgets.QLabel('Intensity'))

                FWHM.append(QtWidgets.QLineEdit())
                layout1.addWidget(FWHM[j])
                FWHM[j].setText(str(s_FWHM))
                layout2.addWidget(QtWidgets.QLabel('FWHM'))

                BWF_parmeter.append(QtWidgets.QLineEdit())
                BWF_parmeter[j].setText('-10')
                if key == 'Breit-Wigner-Fano':
                    layout1.addWidget(BWF_parmeter[j])
                    layout2.addWidget(QtWidgets.QLabel('Additional parameter'))

        okbutton = QPushButton('Ok', self)
        okbutton.setToolTip('Start the fit')
        okbutton.clicked.connect(self.Dialog_FitParameter.close)
        layout1.addWidget(okbutton)
        layout2.addWidget(QtWidgets.QLabel(''))

        layout_hor.addLayout(layout1)
        layout_hor.addLayout(layout2)
        self.Dialog_FitParameter.setLayout(layout_hor)
        self.Dialog_FitParameter.setWindowTitle("Fit Parameter")
        self.Dialog_FitParameter.setWindowModality(Qt.ApplicationModal)

        self.Dialog_FitParameter.exec_()
        parameter = [float(background.text())]  # Background
        for key in self.n_fit_fct.keys():
            for j in range(self.n_fit_fct[key]):
                parameter.append(float(position[j].text()))  # Peak position in cm^-1
                parameter.append(float(intensity[j].text()))  # Intensity
                parameter.append(float(FWHM[j].text()))  # FWHM
                if key == 'Breit-Wigner-Fano':
                    parameter.append(float(BWF_parmeter[j].text()))
        return parameter

    def fit_single_peak(self, q):
        self.SelectDataset()
        if self.selectedDatasetNumber:
            x_min, x_max = self.SelectArea()
            self.n_fit_fct[q.text()] = 1
        else:
            return

        for j in self.selectedDatasetNumber:
            xs = self.spectrum[j].get_xdata()
            ys = self.spectrum[j].get_ydata()
            x = xs[np.where((xs > x_min) & (xs < x_max))]
            y = ys[np.where((xs > x_min) & (xs < x_max))]
            idx_peaks, properties = signal.find_peaks(y, height=0.3 * max(y), width=5, distance=50)
            print(idx_peaks, properties)
            if idx_peaks.size > 0:
                p = round(x[idx_peaks[0]], 2)
                h = round(properties['peak_heights'][0], 2)
                w = round(properties['widths'][0], 2)
            else:
                # set start parameters arbitrary to silicon peak
                p = 520
                h = 100
                w = 20
            p_start = self.get_start_values(s_pos=p, s_height=h, s_FWHM=w)

            try:
                popt, pcov = curve_fit(self.functions.FctSumme, x, y, p0=p_start)
            except RuntimeError or ValueError as e:
                self.mw.show_statusbar_message(str(e), 4000)
                self.n_fit_fct = dict.fromkeys(self.n_fit_fct, 0)
                return
            x1 = np.linspace(min(x), max(x), 1000)
            self.ax.plot(x1, self.functions.FctSumme(x1, *popt), '-r')
            self.canvas.draw()

            print('\n {} {}'.format(self.spectrum[j].get_label(), q.text()))
            parmeter_name = ['Background', r'Raman Shift in cm^-1', 'Intensity', 'FWHM', 'additional Parameter']
            print_param = []
            for idx, po in enumerate(popt):
                print_param.append([parmeter_name[idx], po])
            print(tabulate(print_param, headers=['Parameters', 'Values']))

        self.n_fit_fct = dict.fromkeys(self.n_fit_fct, 0)

    def fit_peaks(self):
        self.SelectDataset()
        if self.selectedDatasetNumber:
            x_min, x_max = self.SelectArea()
            fitdialog = FitOptionsDialog(self)
            fitdialog.show()
            loop = QtCore.QEventLoop()
            fitdialog.closeSignal.connect(loop.quit)
            loop.exec_()
            continue_fit = fitdialog.continue_fit
            if continue_fit:
                pass
            else:
                return
            p_start = fitdialog.p_start
            boundaries = fitdialog.boundaries
            self.n_fit_fct = fitdialog.n_fit_fct
        else:
            return

        for n in self.selectedDatasetNumber:
            xs = self.spectrum[n].get_xdata()
            ys = self.spectrum[n].get_ydata()
            x = xs[np.where((xs > x_min) & (xs < x_max))]
            y = ys[np.where((xs > x_min) & (xs < x_max))]

            try:
                popt, pcov = curve_fit(self.functions.FctSumme, x, y, p0=p_start, bounds=boundaries)
            except RuntimeError as e:
                self.mw.show_statusbar_message(str(e), 4000)
                self.n_fit_fct = dict.fromkeys(self.n_fit_fct, 0)
                return
            except ValueError as e:
                self.mw.show_statusbar_message(str(e), 4000)
                self.n_fit_fct = dict.fromkeys(self.n_fit_fct, 0)
                return

            # Plot the Fit Data
            x1 = np.linspace(min(x), max(x), 1000)
            self.ax.plot(x1, self.functions.FctSumme(x1, *popt), '-r')

            aL = self.n_fit_fct['Lorentz']
            aG = self.n_fit_fct['Gauss']
            for key in self.n_fit_fct.keys():
                for i in range(self.n_fit_fct[key]):
                    if key == 'Lorentz':
                        y_fit = popt[0] + self.functions.LorentzFct(x1, popt[3 * i + 1], popt[3 * i + 2],
                                                                    popt[3 * i + 3])
                    elif key == 'Gauss':
                        y_fit = popt[0] + self.functions.GaussianFct(x1, popt[3 * (i + aL) + 1], popt[3 * (i + aL) + 2],
                                                                     popt[3 * (i + aL) + 3])
                    elif key == 'Breit-Wigner-Fano':
                        y_fit = popt[0] + self.functions.BreitWignerFct(x1, popt[4 * i + 3 * (aL + aG) + 1],
                                                                        popt[4 * i + 3 * (aL + aG) + 2],
                                                                        popt[4 * i + 3 * (aL + aG) + 3],
                                                                        popt[4 * i + 3 * (aL + aG) + 4])
                    self.ax.plot(x1, y_fit, '--g')

            self.canvas.draw()

            # Calculate Errors and R square
            perr = np.sqrt(np.diag(pcov))
            residuals = y - self.functions.FctSumme(x, *popt)
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)

            # bring data into printable form
            print_table = [['Background', popt[0], perr[0]], ['', '', '']]
            a = 1

            for key in self.n_fit_fct.keys():  # iterate over Lorentz, Gauss, BWF
                for j in range(self.n_fit_fct[key]):  # iterate over used fit functions per L, G or BWF
                    print_table.append(['{} {}'.format(key, j + 1)])
                    print_table.append(['Raman Shift in cm-1', popt[a], perr[a]])
                    print_table.append(['Peak height in cps', popt[a + 1], perr[a + 1]])
                    print_table.append(['FWHM in cm-1', popt[a + 2], perr[a + 2]])
                    if key == 'Lorentz':
                        area = np.trapz(self.functions.LorentzFct(x, popt[a], popt[a + 1], popt[a + 2]), x)
                        a += 3
                    elif key == 'Gauss':
                        area = np.trapz(self.functions.GaussianFct(x, popt[a], popt[a + 1], popt[a + 2]), x)
                        a += 3
                    elif key == 'Breit-Wigner-Fano':
                        area = np.trapz(
                            self.functions.BreitWignerFct(x, popt[a], popt[a + 1], popt[a + 2], popt[a + 3]), x)
                        print_table.append(
                            ['BWF Coupling Coefficient', popt[a + 3], perr[a + 3]])
                        a += 4
                    else:
                        print('This is weird!')
                    print_table.append(["Area under curve", area])
                    print_table.append(['', '', ''])
            print('\n {}'.format(self.spectrum[n].get_label()))
            print(r'R^2={:.4f}'.format(r_squared))
            save_data = tabulate(print_table, headers=['Parameters', 'Values', 'Errors'])
            print(save_data)

            # Save fit parameter in file
            filename = self.spectrum[n].get_label()
            startFileDirName = os.path.dirname(self.data[n]["filename"])
            filename = '{}/{}_fitparameter.txt'.format(startFileDirName, filename)

            self.save_to_file('Save fit parameter in file', filename, save_data)

        self.n_fit_fct = dict.fromkeys(self.n_fit_fct, 0)

    def DefineArea(self):
        self.SelectDataset()
        x_min, x_max = self.SelectArea()
        for n in self.selectedDatasetNumber:
            spct = self.spectrum[n]
            xs = spct.get_xdata()
            ys = spct.get_ydata()
            x = xs[np.where((xs > x_min) & (xs < x_max))]
            y = ys[np.where((xs > x_min) & (xs < x_max))]

            data_dict = {"x": x,
                         "y": y,
                         "label": '{}_cut'.format(spct.get_label()),
                         "filename": self.selectedData[0]["filename"]}

            self.data.append(data_dict)
            self.spectrum.append(self.ax.plot(x, y, label='{}_cut'.format(spct.get_label()), picker=True,
                                              pickradius=5)[0])

    def SelectArea(self):
        self.ax.autoscale(False)
        y_min, y_max = self.ax.get_ylim()
        x_min, x_max = self.ax.get_xlim()
        x_range = x_max-x_min
        line1, = self.ax.plot([x_min+0.01*x_range, x_min+0.01*x_range], [y_min, y_max], 'r-', lw=1)
        line2, = self.ax.plot([x_max-0.01*x_range, x_max-0.01*x_range], [y_min, y_max], 'r-', lw=1)
        self.canvas.draw()
        self.mw.show_statusbar_message('Left click shifts limits, Right click  them', 4000)
        linebuilder1 = LineBuilder(line1)
        x_min = linebuilder1.xs  # lower limit
        linebuilder2 = LineBuilder(line2)
        x_max = linebuilder2.xs  # upper limit
        line1.remove()
        line2.remove()
        self.canvas.draw()
        #self.ax.autoscale(True)
        return x_min, x_max

    def detemine_area(self):
        self.SelectDataset()
        area = {}
        for n in self.selectedDatasetNumber:
            x = self.data[n]["x"]
            y = self.data[n]["y"]
            area[self.data[n]["label"]] = np.trapz(y, x)

        print(area)
        return area

    def find_peaks(self):
        self.SelectDataset()
        for n in self.selectedDatasetNumber:
            x = self.data[n]["x"]
            y = self.data[n]["y"]
            y_max = max(y)

            idx_peaks, properties = signal.find_peaks(y, height=0.3 * y_max, width=5, distance=50)

            print(x[idx_peaks])

    def baseline(self):
        self.SelectDataset()
        x_min, x_max = self.SelectArea()
        baseline_methods = BaselineCorrectionMethods()
        for n in self.selectedDatasetNumber:
            spct = self.spectrum[n]
            xs = spct.get_xdata()
            ys = spct.get_ydata()

            x = xs[np.where((xs > x_min) & (xs < x_max))]
            y = ys[np.where((xs > x_min) & (xs < x_max))]

            baseline_dialog = BaselineCorrectionsDialog(self, baseline_methods)
            baseline_dialog.get_baseline(x, y, spct)

            # wait until QMainWindow is closes
            loop = QtCore.QEventLoop()
            baseline_dialog.closebutton.clicked.connect(loop.quit)
            baseline_dialog.finishbutton.clicked.connect(loop.quit)
            loop.exec_()
            if baseline_dialog.closebutton.isChecked():
                break

    def smoothing(self, action):
        self.SelectDataset()
        method = action.text()
        for n in self.selectedDatasetNumber:
            spct = self.spectrum[n]
            x = spct.get_xdata()
            y = spct.get_ydata()
            if method == "Savitsky-Golay":
                y_smooth = rp.smooth(x, y, method="savgol", window_length=15, polyorder=3)
            elif method == "Whittaker":
                y_smooth = rp.smooth(x, y, method="whittaker",Lambda=10**0.5)
            spct.set_ydata(y_smooth)
            self.canvas.draw()

    def linear_regression(self):
        self.SelectDataset()
        for n in self.selectedDatasetNumber:
            spct = self.spectrum[n]
            xs = spct.get_xdata()
            ys = spct.get_ydata()

            # delete all values, which are nan
            x = xs[np.logical_not(np.isnan(ys))]
            y = ys[np.logical_not(np.isnan(ys))]

            # Fit
            popt, pcov = curve_fit(self.functions.LinearFct, x, y)

            # Errors and R**2
            perr = np.sqrt(np.diag(pcov))
            residuals = y - self.functions.LinearFct(x, *popt)
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)

            # Plot determined linear function
            x1 = np.linspace(min(x), max(x), 1000)
            self.ax.plot(x1, self.functions.LinearFct(x1, *popt), '-r')
            self.canvas.draw()

            # Print results
            print('\n {}'.format(spct.get_label()))
            print(r'R^2={:.4f}'.format(r_squared))
            parmeter_name = ['Slope', 'y-Intercept']
            print_param = []
            for i in range(len(popt)):
                print_param.append([parmeter_name[i], popt[i], perr[i]])
            print(tabulate(print_param, headers=['Parameters', 'Values', 'Errors']))

    def hydrogen_estimation(self):
        """
        determine the slope of PL background in carbon spectra in order to estimate the hydrogen content compare with:
        C. Casiraghi, A. C. Ferrari, J. Robertson, Physical Review B 2005, 72, 8 085401.
        """

        self.SelectDataset()
        x_min_1 = 600
        x_max_1 = 900
        x_min_2 = 1900
        x_max_2 = 2300
        for n in self.selectedDatasetNumber:
            x = self.spectrum[n].get_xdata()
            y = self.spectrum[n].get_ydata()

            x1 = x[np.where((x > x_min_1) & (x < x_max_1))]
            y1 = y[np.where((x > x_min_1) & (x < x_max_1))]
            x2 = x[np.where((x > x_min_2) & (x < x_max_2))]
            y2 = y[np.where((x > x_min_2) & (x < x_max_2))]
            x = np.concatenate((x1, x2))
            y = np.concatenate((y1, y2))

            popt, pcov = curve_fit(self.functions.LinearFct, x, y)

            # Plot determined linear function
            x_plot = np.linspace(min(x), max(x), 1000)
            self.ax.plot(x_plot, self.functions.LinearFct(x_plot, *popt), '-r')
            self.canvas.draw()

            # get index of G peak
            idx_G = np.argmax(y)

            # calculate m/I(G):
            mIG = popt[0] / y[idx_G]
            if mIG > 0:
                H_content = 21.7 + 16.6 * math.log(mIG * 10 ** 4)
                print(mIG, H_content)
            else:
                print('negative slope')

    def fit_D_G(self):
        """
        Partially based on Christian's Mathematica Notebook
        Fitroutine for D and G bands in spectra of carbon compounds
        """
        # Select which data set will be fitted
        self.SelectDataset()
        # if self.selectedData == []:
        #    return

        # Limits for Backgroundcorrection
        x_min = 200
        x_max = 4000

        # parameter for background-correction
        p = 0.0005  # asymmetry 0.001 <= p <= 0.1 is a good choice  recommended from Eilers and Boelens for Raman: 0.001
        # recommended from Simon: 0.0005
        lam = 10000000  # smoothness 10^2 <= lambda <= 10^9         recommended from Eilers and Boelens for Raman: 10^7
        # recommended from Simon: 10^7

        # Limits for FitProcess
        # define fitarea
        x_min_fit = 945
        x_max_fit = 1830

        # Fitprocess
        # D-Band: Lorentz
        # G-Band: BreitWignerFano
        self.n_fit_fct['Lorentz'] = 1  # number of Lorentzian
        self.n_fit_fct['Gauss'] = 3  # number of Gaussian
        self.n_fit_fct['Breit-Wigner-Fano'] = 1  # number of Breit-Wigner-Fano
        aL = self.n_fit_fct['Lorentz']
        aG = self.n_fit_fct['Gauss']
        aB = self.n_fit_fct['Breit-Wigner-Fano']
        aLG = self.n_fit_fct['Lorentz'] + self.n_fit_fct['Gauss']

        # Fit parameter: initial guess and boundaries

        pStart = []
        pBoundsLow = []
        pBoundsUp = []
        inf = np.inf

        pStart.append((1350, 150, 30))  # D-Bande
        pBoundsLow.append((1335, 0, 0))
        pBoundsUp.append((1385, inf, 150))

        pStart.append((1160, 1, 5))  # additional Peak (PA)
        pBoundsLow.append((1150, 0, 0))
        pBoundsUp.append((1180, inf, 70))
        pStart.append((1240, 0.1, 5))  # additional Peak (PA)
        pBoundsLow.append((1225, 0, 0))
        pBoundsUp.append((1255, inf, 100))
        pStart.append((1430, 0.1, 5))  # additional Peak (PA)
        pBoundsLow.append((1420, 0, 0))
        pBoundsUp.append((1440, inf, 100))

        pStart.append((1590, 200, 30, -10))  # G-Peak (BWF)
        pBoundsLow.append((1575, 0, 0, -inf))
        pBoundsUp.append((1630, inf, inf, inf))

        p_start = []
        p_bounds_low = []
        p_bounds_up = []
        p_start.extend([0])
        p_bounds_low.extend([-10])
        p_bounds_up.extend([inf])
        for i in range(len(pStart)):
            p_start.extend(pStart[i])
            p_bounds_low.extend(pBoundsLow[i])
            p_bounds_up.extend(pBoundsUp[i])

        # Limits Fit parameter
        p_bounds = ((p_bounds_low, p_bounds_up))

        # iterate through all selected data sets
        for n in self.selectedDatasetNumber:
            x = self.spectrum[n].get_xdata()
            y = self.spectrum[n].get_ydata()

            # Limit data to fit range
            working_x = x[np.where((x > x_min) & (x < x_max))]
            working_y = y[np.where((x > x_min) & (x < x_max))]

            yb, zb = self.blc.ALS(working_x, working_y, p, lam)
            baseline, = self.ax.plot(working_x, zb, 'c--', label='baseline ({})'.format(self.spectrum[n].get_label()))
            blcSpektrum, = self.ax.plot(working_x, yb, 'c-',
                                             label='baseline-corrected ({})'.format(self.spectrum[n].get_label()))
            self.canvas.draw()

            # limit data to fitarea
            working_y = yb[np.where((working_x > x_min_fit) & (working_x < x_max_fit))]
            working_x = working_x[np.where((working_x > x_min_fit) & (working_x < x_max_fit))]

            try:
                popt, pcov = curve_fit(self.functions.FctSumme, working_x, working_y, p0=p_start, bounds=p_bounds,
                                       absolute_sigma=False)
            except RuntimeError as e:
                self.mw.show_statusbar_message(str(e), 4000)
                continue

            # Plot the Fit Data
            x1 = np.linspace(min(working_x), max(working_x), 3000)
            y_L = []
            for j in range(aL):
                y_L.append(np.array(
                    popt[0] + self.functions.LorentzFct(x1, popt[1 + 3 * j], popt[2 + 3 * j], popt[3 + 3 * j])))
            y_G = []
            for j in range(aG):
                y_G.append(np.array(
                    popt[0] + self.functions.GaussianFct(x1, popt[1 + 3 * aL + 3 * j], popt[2 + 3 * aL + 3 * j],
                                                         popt[3 + 3 * aL + 3 * j])))
            y_BWF = []
            for j in range(aB):
                y_BWF.append(np.array(
                    popt[0] + self.functions.BreitWignerFct(x1, popt[4 * j + 3 * aLG + 1], popt[4 * j + 3 * aLG + 2],
                                                            popt[4 * j + 3 * aLG + 3], popt[4 * j + 3 * aLG + 4])))
            y_Ges = np.array(self.functions.FctSumme(x1, *popt))
            self.ax.plot(x1, y_Ges, '-r')
            for j in y_G:
                self.ax.plot(x1, j, '--g')
            for j in y_L:
                self.ax.plot(x1, j, '--g')
            for j in y_BWF:
                self.ax.plot(x1, j, '--g')

            self.canvas.draw()

            # Calculate Errors and R square
            perr = np.sqrt(np.diag(pcov))

            residuals = working_y - self.functions.FctSumme(working_x, *popt)
            ss_res = numpy.sum(residuals ** 2)
            ss_tot = numpy.sum((working_y - numpy.mean(working_y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)

            # Calculate Peak-Areas and there Errors
            r, a0, h, xc, b, Q = sp.symbols('r a0 h xc b Q', real=True)

            # Anti-Derivative of Lorentzian Function
            F_L = (x_max_fit - x_min_fit) * a0 - b * h * sp.atan(2 * (xc - x_max_fit) / b) / 2 + b * h * sp.atan(
                2 * (xc - x_min_fit) / b) / 2
            Flam_L = lambdify([a0, xc, h, b], F_L)

            # Anti-Derivative of Gaussian Function
            F_G = (4 * a0 * (x_max_fit - x_min_fit) * sp.sqrt(sp.log(2)) - sp.sqrt(sp.pi) * b * h * sp.erf(
                2 * (xc - x_max_fit) * sp.sqrt(sp.log(2)) / b) +
                   sp.sqrt(sp.pi) * b * h * sp.erf(2 * (xc - x_min_fit) * sp.sqrt(sp.log(2)) / b)) / (
                          4 * sp.sqrt(sp.log(2)))
            Flam_G = lambdify([a0, xc, h, b], F_G)

            # Anti-Derivative of Breit-Wigner-Fano Function
            F_B = (Q * b * h * (sp.log(b ** 2 / 4 + xc ** 2 - 2 * xc * x_max_fit + x_max_fit ** 2) - sp.log(
                b ** 2 / 4 + xc ** 2 - 2 * xc * x_min_fit + x_min_fit ** 2)) -
                   b * h * (Q - 1) * (Q + 1) * sp.atan(2 * (xc - x_max_fit) / b) + b * h * (Q - 1) * (Q + 1) * sp.atan(
                        2 * (xc - x_min_fit) / b) + 2 * x_max_fit * (Q ** 2 * a0 + h) - 2 * x_min_fit * (
                           Q ** 2 * a0 + h)) / (2 * Q ** 2)
            Flam_B = lambdify([a0, xc, h, b, Q], F_B)

            # Calculate partial derivates
            dF_La0 = sp.diff(F_L, a0)
            dF_Lh = sp.diff(F_L, h)
            dF_Lxc = sp.diff(F_L, xc)
            dF_Lb = sp.diff(F_L, b)

            dF_Ga0 = sp.diff(F_G, a0)
            dF_Gh = sp.diff(F_G, h)
            dF_Gxc = sp.diff(F_G, xc)
            dF_Gb = sp.diff(F_G, b)

            dF_Ba0 = sp.diff(F_B, a0)
            dF_Bh = sp.diff(F_B, h)
            dF_Bxc = sp.diff(F_B, xc)
            dF_Bb = sp.diff(F_B, b)
            dF_BQ = sp.diff(F_B, Q)

            # Calculate Error of Peak Area with law of error propagation
            da0, dh, dxc, db, dQ = sp.symbols('da0 dh dxc db dQ', real=True)

            DeltaF_L = sp.Abs(dF_La0) * da0 + sp.Abs(dF_Lh) * dh + sp.Abs(dF_Lxc) * dxc + sp.Abs(dF_Lb) * db
            DeltaFlam_L = lambdify([a0, da0, xc, dxc, h, dh, b, db], DeltaF_L)
            DeltaF_G = sp.Abs(dF_Ga0) * da0 + sp.Abs(dF_Gh) * dh + sp.Abs(dF_Gxc) * dxc + sp.Abs(dF_Gb) * db
            DeltaFlam_G = lambdify([a0, da0, xc, dxc, h, dh, b, db], DeltaF_G)
            DeltaF_B = sp.Abs(dF_Ba0) * da0 + sp.Abs(dF_Bh) * dh + sp.Abs(dF_Bxc) * dxc + sp.Abs(dF_Bb) * db + sp.Abs(
                dF_BQ) * dQ
            DeltaFlam_B = lambdify([a0, da0, xc, dxc, h, dh, b, db, Q, dQ], DeltaF_B)

            # Peak Area
            area_D = 0
            area_G = 0
            area_D_err = 0
            area_G_err = 0
            pos_G = 1600
            pos_G_err = 0
            b_G = 0
            q_G = 0

            I_D = 0
            I_G = 0

            xD = 1350
            xG = 1600
            absxD = 1350
            absxG = 1600

            area_Lorentz = []
            area_Lorentz_err = []
            for j in range(aL):
                area_Lorentz.append(Flam_L(popt[0], popt[1 + 3 * j], popt[2 + 3 * j], popt[3 + 3 * j]))
                area_Lorentz_err.append(
                    DeltaFlam_L(popt[0], perr[0], popt[3 * j + 1], perr[3 * j + 1], popt[3 * j + 2], perr[3 * j + 2],
                                popt[3 * j + 3], perr[3 * j + 3]))
                if np.abs(popt[1 + 3 * j] - xD) < absxD:
                    area_D = area_Lorentz[j]
                    area_D_err = area_Lorentz_err[j]
                    absxD = np.abs(popt[1 + 3 * j] - xD)
                    I_D = popt[2 + 3 * j]
                elif np.abs(popt[1 + 3 * j] - xG) < absxG:
                    area_G = area_Lorentz[j]
                    area_G_err = area_Lorentz_err[j]
                    absxG = np.abs(popt[1 + 3 * j] - xD)
                    I_G = popt[2 + 3 * j]
                    pos_G = popt[1 + 3 * j]
                    pos_G_err = perr[1 + 3 * j]
                    b_G = popt[3 + 3 * j]
                    q_G = popt[4 + 3 * j]
                else:
                    pass

            area_Gauss = []
            area_Gauss_err = []
            for j in range(aG):
                area_Gauss.append(
                    Flam_G(popt[0], popt[1 + 3 * aL + 3 * j], popt[2 + 3 * aL + 3 * j], popt[3 + 3 * aL + 3 * j]))
                area_Gauss_err.append(DeltaFlam_G(popt[0], perr[0], popt[3 * j + 3 * aL + 1], perr[3 * j + 3 * aL + 1],
                                                  popt[3 * j + 3 * aL + 2], perr[3 * j + 3 * aL + 2],
                                                  popt[3 * j + 3 * aL + 3],
                                                  perr[3 * j + 3 * aL + 3]))
                if np.abs(popt[1 + 3 * aL + 3 * j] - xD) < absxD:
                    area_D = area_Gauss[j]
                    area_D_err = area_Gauss_err[j]
                    absxD = np.abs(popt[1 + 3 * aL + 3 * j] - xD)
                    I_D = popt[2 + 3 * aL + 3 * j]
                elif np.abs(popt[1 + 3 * aL + 3 * j] - xG) < absxG:
                    area_G = area_Gauss[j]
                    area_G_err = area_Gauss_err[j]
                    absxG = np.abs(popt[1 + 3 * aL + 3 * j] - xD)
                    I_G = popt[2 + 3 * aL + 3 * j]
                    pos_G = popt[1 + 3 * aL + 3 * j]
                    pos_G_err = perr[1 + 3 * aL + 3 * j]
                else:
                    pass

            area_BWF = []
            area_BWF_err = []
            for j in range(aB):
                area_BWF.append(
                    Flam_B(popt[0], popt[4 * j + 3 * aLG + 1], popt[4 * j + 3 * aLG + 2], popt[4 * j + 3 * aLG + 3],
                           popt[4 * j + 3 * aLG + 4]))
                area_BWF_err.append(DeltaFlam_B(popt[0], perr[0], popt[4 * j + 3 * aLG + 1], perr[4 * j + 3 * aLG + 1],
                                                popt[4 * j + 3 * aLG + 2], perr[4 * j + 3 * aLG + 2],
                                                popt[4 * j + 3 * aLG + 3], perr[4 * j + 3 * aLG + 3],
                                                popt[4 * j + 3 * aLG + 4], perr[4 * j + 3 * aLG + 4]))
                if np.abs(popt[4 * j + 3 * aLG + 1] - xD) < absxD:
                    area_D = area_BWF[j]
                    area_D_err = area_BWF_err[j]
                    absxD = np.abs(popt[4 * j + 3 * aLG + 1] - xD)
                    I_D = popt[4 * j + 3 * aLG + 2]
                elif np.abs(popt[4 * j + 3 * aLG + 1] - xG) < absxG:
                    area_G = area_BWF[j]
                    area_G_err = area_BWF_err[j]
                    absxG = np.abs(popt[4 * j + 3 * aLG + 1] - xD)
                    I_G = popt[4 * j + 3 * aLG + 2]
                    pos_G = popt[4 * j + 3 * aLG + 1]
                    pos_G_err = perr[4 * j + 3 * aLG + 1]
                    b_G = popt[4 * j + 3 * aLG + 3]
                    q_G = popt[4 * j + 3 * aLG + 4]
                else:
                    pass

            # Estimate Cluster size
            # ID/IG = C(lambda)/L_a
            # mit C(514.5 nm) = 44 Angstrom

            L_a = 4.4 * area_G / area_D
            L_a_err = L_a * (area_D_err / area_D + area_G_err / area_G)
            area_ratio = area_D / area_G
            area_ratio_err = area_ratio * (area_D_err / area_D + area_G_err / area_G)
            ratio = I_D / I_G
            ratio_err = 0

            # get data into printable form
            print_table = [['Background', popt[0], perr[0]]]
            print_table.append(['', '', ''])
            for j in range(aL):
                print_table.append(['Lorentz %i' % (j + 1)])
                print_table.append(['Raman Shift in cm-1', popt[j * 3 + 1], perr[j * 3 + 1]])
                print_table.append(['Peak height in cps', popt[j * 3 + 2], perr[j * 3 + 2]])
                print_table.append(['FWHM in cm-1', popt[j * 3 + 3], perr[j * 3 + 3]])
                print_table.append(['Peak area in cps*cm-1', area_Lorentz[j], area_Lorentz_err[j]])
                print_table.append(['', '', ''])
            for j in range(aG):
                print_table.append(['Gauss %i' % (j + 1)])
                print_table.append(['Raman Shift in cm-1', popt[j * 3 + 3 * aL + 1], perr[j * 3 + 3 * aL + 1]])
                print_table.append(['Peak height in cps', popt[j * 3 + 3 * aL + 2], perr[j * 3 + 3 * aL + 2]])
                print_table.append(['FWHM in cm-1', popt[j * 3 + 3 * aL + 3], perr[j * 3 + 3 * aL + 3]])
                print_table.append(['Peak area in cps*cm-1', area_Gauss[j], area_Gauss_err[j]])
                print_table.append(['', '', ''])
            for j in range(aB):
                print_table.append(['BWF %i' % (j + 1)])
                print_table.append(['Raman Shift in cm-1', popt[j * 3 + 3 * aLG + 1], perr[j * 3 + 3 * aLG + 1]])
                print_table.append(['Peak height in cps', popt[j * 3 + 3 * aLG + 2], perr[j * 3 + 3 * aLG + 2]])
                print_table.append(['FWHM in cm-1', popt[j * 3 + 3 * aLG + 3], perr[j * 3 + 3 * aLG + 3]])
                print_table.append(['BWF Coupling Coefficient', popt[j * 3 + 3 * aLG + 4], perr[j * 3 + 3 * aLG + 4]])
                print_table.append(['Peak area in cps*cm-1', area_BWF[j], area_BWF_err[j]])
                print_table.append(['', '', ''])

            print_table.append(['Cluster Size in nm', L_a, L_a_err])
            print_table.append(['I_D/I_G', ratio, ratio_err])

            save_data = r'R^2=%.6f \n' % r_squared + 'Lorentz 1 = D-Bande, BWF (Breit-Wigner-Fano) 1 = G-Bande \n' + tabulate(
                print_table, headers=['Parameters', 'Values', 'Errors'])
            print('\n')
            print(self.spectrum[n].get_label())
            print(save_data)

            (fileBaseName, fileExtension) = os.path.splitext(self.spectrum[n].get_label())
            startFileDirName = os.path.dirname(self.selectedData[0][3])
            with open(startFileDirName + "/ID-IG.txt", "a") as file_cluster:
                file_cluster.write('\n' + str(fileBaseName) + '   %.4f' % ratio + '   %.4f' % ratio_err)

            pos_G_max = pos_G + b_G / (2 * q_G)
            with open(startFileDirName + "/G-Position.txt", "a") as file_GPosition:
                file_GPosition.write('\n{} {:.4f}  {:.4f}'.format(fileBaseName, pos_G_max, 0.0))

            # Save the fit parameter
            startFileBaseName = startFileDirName + '/' + fileBaseName
            startFileName = startFileBaseName + '_fitpara.txt'
            # self.save_to_file('Save fit parameter in file', startFileName, save_data)

            # Save the Fit data
            startFileName = startFileBaseName + '_fitdata.txt'
            save_data = [x1]
            for j in y_L:
                save_data.append(j)
            for j in y_G:
                save_data.append(j)
            for j in y_BWF:
                save_data.append(j)
            save_data.append(y_Ges)
            save_data = np.transpose(save_data)
            # self.save_to_file('Save fit data in file', startFileName, save_data)

    def norm_to_water(self):
        """
        performs baseline correction on data with Doubly Reweighted Penalized Least Squares and lambda=9000000
        and than normalizes the spectra to the water peak
        """
        self.SelectDataset()
        for n in self.selectedDatasetNumber:
            # get data
            xs = self.data[n]["x"]
            ys = self.data[n]["y"]

            # background correction
            yb, baseline = self.blc.drPLS(xs, ys, lam=9000000)

            # norm spectrum regarding water peak
            norm_factor = np.max(yb[np.argwhere((xs>3000) & (xs<3700))])
            yb = yb / norm_factor
            self.data[n]["y"] = yb
            self.spectrum[n].set_data(xs, yb)
            self.canvas.draw()
            # Save normalized data
            if self.data[n]["filename"] is not None:
                (fileBaseName, fileExtension) = os.path.splitext(self.data[n]["label"])
                startFileDirName = os.path.dirname(self.data[n]["filename"])
                startFileBaseName = startFileDirName + '/' + fileBaseName
                startFileName = startFileBaseName + '_norm.txt'
            else:
                startFileName = None
            save_data = [self.data[n]["x"], self.data[n]["y"]]
            save_data = np.transpose(save_data)
            self.save_to_file('Save normalized data in file', startFileName, save_data)

    def fit_sulfuroxyanion(self):
        """function to fit region between 700 and 1400cm-1 in spectra with sulfuroxyanions with Lorentzians"""
        # select spectra, which should be fitted
        self.SelectDataset()

        # limit for fit region
        x_min, x_max = [700, 1400]

        # lists with positions and FWHM of all peaks in the fit region
        # positions and FWHM of Persulfate (S_2O_8^2-) peaks
        pos_PS = [802, 835, 1075]
        fwhm_PS = [25, 15, 7]
        # positions and FWHM of Caros acid (HSO_5^-)peaks
        pos_Caros = [767, 884, 1057]
        fwhm_Caros = [15, 15, 10]
        # other peaks
        peak_positions = [900, 982, 1030, 1045, 1190, 1256, 1291]
        peak_fwhm = [25, 30, 15, 15, 55, 55, 35]
        peak_positions.extend(pos_PS+pos_Caros)
        peak_fwhm.extend(fwhm_PS+fwhm_Caros)

        # sort list according to peak positions
        peak_positions = sorted(peak_positions)
        peak_fwhm = [f for _, f in sorted(zip(peak_positions, peak_fwhm))]

        # number of fit functions
        self.n_fit_fct['Lorentz'] = len(peak_positions)

        for n in self.selectedDatasetNumber:
            peak_areas = []

            # get data
            spct = self.spectrum[n]
            xs = spct.get_xdata()
            ys = spct.get_ydata()

            # limit data
            y = ys[np.where((xs > x_min) & (xs < x_max))]
            x = xs[np.where((xs > x_min) & (xs < x_max))]

            # Fit parameter: initial guess and boundaries
            p_start = [0]
            p_bounds_low = [-0.001]
            p_bounds_up = [np.inf]
            for (start_pos, start_width) in zip(peak_positions, peak_fwhm):
                start_height = max(y[np.where((x > (start_pos-3)) & (x < (start_pos+3)))])*0.9
                if start_height < 0:
                    start_height = 0
                start_width = 15
                p_start.extend([start_pos, start_height, start_width])
                p_bounds_low.extend([start_pos-10, 0, 0])
                p_bounds_up.extend([start_pos+10, np.inf, np.inf])
            p_bounds = [p_bounds_low, p_bounds_up]

            try:
                popt, pcov = curve_fit(self.functions.FctSumme, x, y, p0=p_start, bounds=p_bounds, absolute_sigma=False)
            except RuntimeError as e:
                self.mw.show_statusbar_message(str(e), 4000)
                continue

            # Plot the Fit Data
            x_fit = np.linspace(x_min, x_max, 3000)
            for j in range(self.n_fit_fct['Lorentz']):
                y_Lorentz = self.functions.LorentzFct(x_fit, popt[1 + 3 * j], popt[2 + 3 * j], popt[3 + 3 * j])
                peak_areas.append(np.trapz(y_Lorentz))
                self.ax.plot(x_fit, popt[0] + y_Lorentz, '--g')
            self.ax.plot(x_fit, self.functions.FctSumme(x_fit, *popt), '-r')
            self.canvas.draw()

            # Calculate Errors and R square
            perr = np.sqrt(np.diag(pcov))

            residuals = y - self.functions.FctSumme(x, *popt)
            ss_res = numpy.sum(residuals ** 2)
            ss_tot = numpy.sum((y - numpy.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)

            # store fitparameter in table
            print_table = [['Background', popt[0], perr[0]], ['', '', '']]
            for j in range(self.n_fit_fct['Lorentz']):
                print_table.append(['Lorentz %i' % (j + 1)])
                print_table.append(['Raman Shift in cm-1', popt[j * 3 + 1], perr[j * 3 + 1]])
                print_table.append(['Peak height in cps', popt[j * 3 + 2], perr[j * 3 + 2]])
                print_table.append(['FWHM in cm-1', popt[j * 3 + 3], perr[j * 3 + 3]])
                print_table.append(['Peak area in cps*cm-1', peak_areas[j], ''])
                print_table.append(['', '', ''])
            fit_parameter_table = tabulate(print_table, headers=['Parameters', 'Values', 'Errors'])

            # print fitparameter
            print('\n')
            print(self.spectrum[n].get_label(), "R^2={}".format(r_squared))
            print(fit_parameter_table)

            # save the fit parameter
            directory_name, file_name_spectrum = os.path.split(self.selectedData[n][3])
            (fileBaseName, fileExtension) = os.path.splitext(file_name_spectrum)
            file_name_parameter = '{}/{}_fitparameter.txt'.format(directory_name, fileBaseName)
            self.save_to_file('Save fit parameter in file', file_name_parameter, fit_parameter_table)

            # get peak heights of persulfate and CarosAcid peaks
            name = self.spectrum[n].get_label()
            idx_PS = [peak_positions.index(p) for p in pos_PS]
            idx_Caros = [peak_positions.index(p) for p in pos_Caros]
            for j in idx_PS:
                with open("{}/PS_intensity_PS{}cm-1.txt".format(directory_name, peak_positions[j]), "a") as f:
                    f.write('\n{} {:.4f}  {:.4f}'.format(name, popt[3*j+2], perr[3*j+2]))

            for j in idx_Caros:
                with open("{}/PS_intensity_Caros{}cm-1.txt".format(directory_name, peak_positions[j]), "a") as f:
                    f.write('\n{} {:.4f}  {:.4f}'.format(name, popt[3 * j + 2], perr[3 * j + 2]))

        self.n_fit_fct['Lorentz'] = 0

    ### Functions of toolbar ###
    def vertical_line(self):
        if self.vert_line is not None:
            return
        else:
            self.ax.autoscale(False)
            y_min, y_max = self.ax.get_ylim()
            x_min, x_max = self.ax.get_xlim()
            self.vert_line, = self.ax.plot([(x_min+x_max)/2, (x_min+x_max)/2], [y_min, y_max], 'r-', lw=1)
            self.canvas.draw()
            LineBuilder(self.vert_line)
            self.vert_line.remove()
            self.canvas.draw()
            self.ax.autoscale(True)
            self.vert_line = None

    def scale_spectrum(self):
        self.SelectDataset(True)
        for n in self.selectedDatasetNumber:
            try:
                ms = MoveSpectra(self.spectrum[n], scaling=True)
            except RuntimeError as e:
                print(e)
                continue
            self.spectrum[n] = ms.line
            self.data[n]["y"] = ms.y

    def shift_spectrum(self):
        self.SelectDataset(True)
        for n in self.selectedDatasetNumber:
            try:
                ms = MoveSpectra(self.spectrum[n])
            except RuntimeError as e:
                print(e)
                continue
            self.spectrum[n] = ms.line
            self.data[n]["y"] = ms.y

    def draw_line(self):
        self.selected_points = []
        self.pick_arrow_points_connection = self.canvas.mpl_connect('button_press_event', self.pick_points_for_arrow)

    def pick_points_for_arrow(self, event):
        self.selected_points.append([event.xdata, event.ydata])
        if len(self.selected_points) == 2:
            self.canvas.mpl_disconnect(self.pick_arrow_points_connection)
            posA = self.selected_points[0]
            posB = self.selected_points[1]

            arrow = mpatches.FancyArrowPatch(posA, posB, mutation_scale=10, arrowstyle='-', picker=50)
            arrow.set_figure(self.fig)
            self.ax.add_patch(arrow)
            self.drawn_line.append(LineDrawer(arrow))
            self.canvas.draw()

    def insert_text(self):
        self.pick_text_point_connection = self.canvas.mpl_connect('button_press_event', self.pick_point_for_text)

    def pick_point_for_text(self, event):
        pos = [event.xdata, event.ydata]
        text = self.ax.annotate(r'''*''', pos, picker=True, fontsize=24)
        self.inserted_text.append(InsertText(text, self.mw))
        self.canvas.mpl_disconnect(self.pick_text_point_connection)
        self.canvas.draw()

    def closeEvent(self, event):
        close = QMessageBox()
        close.setWindowTitle('Quit')
        close.setText("You sure?")
        close.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        close = close.exec_()

        if close == QMessageBox.Yes:
            self.closeWindowSignal.emit('Plotwindow', self.windowTitle())
            event.accept()
        else:
            event.ignore()


def new_MainWindow():
    MW = MainWindow()
    MW.showMaximized()
    MW.load()


def main():
    app = QApplication(sys.argv)
    MW = MainWindow()
    MW.showMaximized()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
