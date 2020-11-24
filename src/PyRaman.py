# Autor: Simon Brehm
import beepy
import math
import matplotlib
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.backends.qt_editor._formlayout as formlayout
import numpy as np
import os
import pickle
import re
import scipy
import sympy as syp
import sys
import time
from datetime import datetime

#import collections
from collections import ChainMap
from matplotlib import *
from matplotlib.figure import Figure
from matplotlib.widgets import LassoSelector
from matplotlib.backend_bases import MouseEvent
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
import matplotlib.backends.qt_editor.figureoptions as figureoptions
from matplotlib.backends.qt_compat import _setDevicePixelRatioF, _devicePixelRatioF
from numpy import pi
from numpy.fft import fft, fftshift
from PyQt5 import QtGui, QtCore, QtWidgets, QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSlot, QObject
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QVBoxLayout, QSizePolicy, 
    QMessageBox, QPushButton, QCheckBox, QTreeWidgetItem, QTableWidgetItem, QItemDelegate, 
    QLineEdit, QPushButton, QWidget, QMenu, QAction, QDialog, QFileDialog, QInputDialog, QAbstractItemView)
from scipy import sparse
from scipy.optimize import curve_fit
from scipy.sparse.linalg import spsolve
from sympy.utilities.lambdify import lambdify
from tabulate import tabulate

import myfigureoptions  #see file 'myfigureoptions.py'
import Database_Measurements #see file Database_Measurements

# This file essentially consists of three parts:
# 1. Main Window
# 2. Text Window
# 3. Spreadsheet
# 4. Plot

#####################################################################################################################################################
### 1. Main window
#####################################################################################################################################################
class RamanTreeWidget(QtWidgets.QTreeWidget):
    """
    A reimplementation of the PyQt QTreeWidget.
    """
    itemDoubleClicked = QtCore.pyqtSignal(object)
    itemClicked = QtCore.pyqtSignal(object, object)
    itemDropped = QtCore.pyqtSignal(object, object)
 
    def __init__(self, parent=None):
        super(RamanTreeWidget, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def mouseDoubleClickEvent(self, event):
        '''
        Parameters
        ----------
        event : QMouseEvent            #The mouse event.
        '''
        item = self.itemAt(event.pos()) 
        if item != None:
            self.itemDoubleClicked.emit(item)
        else:
            return

    def mousePressEvent(self, event):
        '''
        Parameters
        ----------
        event : QMouseEvent           #The mouse event.
        '''
        item = self.itemAt(event.pos())
        if item != None:
            self.setCurrentItem(item)
        else:
            pass
        self.itemClicked.emit(event, item)

        # keep the default behaviour
        super(RamanTreeWidget, self).mousePressEvent(event)

    def startDrag(self, action):
        self.dragged_item = self.selectedItems()[0]

        # keep the default behaviour
        super(RamanTreeWidget, self).startDrag(action)

    def dropEvent(self, event):
        itemAtDropLocation = self.itemAt(event.pos())
        if itemAtDropLocation != None and itemAtDropLocation.type() == 0:
            self.itemDropped.emit(self.dragged_item, itemAtDropLocation)
        else:
            return

        # keep the default behaviour
        super(RamanTreeWidget, self).dropEvent(event)


class MainWindow(QMainWindow):
    '''
    Creating the main window
    '''
    def __init__(self, parent = None):
        super(MainWindow, self).__init__(parent)
        self.windowtypes = ['Folder', 'Spreadsheet', 'Plotwindow', 'Textwindow']
        self.window = {}                               # dictionary with windows
        self.windowNames = {}
        self.windowWidget = {}
        for j in self.windowtypes:
            self.window[j] = {}
            self.windowNames[j] = []
            self.windowWidget[j] = {}
        self.folder = {}                              # key = foldername, value = [Qtreewidgetitem, QmdiArea]
        self.FileName = os.path.dirname(__file__)     # path of this python file
        self.PyramanIcon = QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/PyRaman_logo.png")
        self.pHomeRmn = None                         # path of Raman File associated to the open project

        self.create_mainwindow()

    def create_mainwindow(self):
        """Create the main window"""
        self.setWindowIcon(self.PyramanIcon)
        self.setWindowTitle('PyRaman')                  # set window title

        self.mainWidget = QtWidgets.QSplitter(self)     # lets the user control the size of child widgets by dragging the boundary between them
        self.mainWidget.setHandleWidth(10)

        self.tabWidget = QtWidgets.QTabWidget()
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.setMovable(True)
        self.tabWidget.tabCloseRequested.connect(self.close_tab)
        self.treeWidget = RamanTreeWidget(self)                    # Qtreewidget, to controll open windows
        self.treeWidget.itemDoubleClicked.connect(self.activate_window)
        self.treeWidget.itemClicked.connect(self.tree_window_options)
        self.treeWidget.itemDropped.connect(self.change_folder)
        self.new_Folder(None)

        self.mainWidget.addWidget(self.treeWidget)
        self.mainWidget.addWidget(self.tabWidget)
        self.setCentralWidget(self.mainWidget)

        self.statusBar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusBar)
        self.show_statusbar_message('Welcome to PyRaman', 3000)

        self.create_menubar()

    def create_menubar(self):
        # create a menubar
        menu = self.menuBar()
        File = menu.addMenu('File')
        FileNew = File.addMenu('New')
        FileNew.addAction('Spreadsheet', lambda: self.newWindow(None, 'Spreadsheet', None, None))
        FileNew.addAction('Textwindow', lambda: self.newWindow(None, 'Textwindow','', None))
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
        # A few shortcuts
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
        # Load project from rmn file with pickle
        fileName = QtWidgets.QFileDialog.getOpenFileName(self, 'Load',       # get file name
                    self.pHomeRmn, 'All Files (*);;Raman Files (*.rmn)')

        if fileName[0] != '':                       # if fileName is not empty save in pHomeRmn
            self.pHomeRmn = fileName[0]
        else:
            self.close()
            return

        date_of_file = time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(self.pHomeRmn)))
        datetime_of_file = datetime.strptime(date_of_file, '%Y-%m-%d')

        file = open(self.pHomeRmn, 'rb')            # open file and save content in variable 'v' with pickle
        v = pickle.load(file)         
        file.close()

        datetime_of_save_change = datetime(2020, 10, 2)
        if datetime_of_file < datetime_of_save_change:
            for key, val in v['Spreadsheet'].items():   # open all saved spreadsheets
                self.newWindow(None, 'Spreadsheet', val, key)

            for key, val in v['Plot-Window'].items():   # open all saved plotwindows
                plot_data = val[0]
                fig = val[1]
                pwtitle = key
                self.newWindow(None, 'Plotwindow', [plot_data, fig], pwtitle)

            if 'Text-Window' in v.keys():
                for key, val in v['Text-Window'].items():
                    self.newWindow(None, 'Textwindow', val, key)
        else:
            self.treeWidget.clear()
            self.tabWidget.clear()
            self.folder = {}
            for foldername, foldercontent  in v.items():
                self.new_Folder(foldername)
                for key, val in foldercontent.items():
                    self.newWindow(foldername, val[0], val[1], key)

    def save(self, q):
        # function to save complete project in rmn-File with pickle

        # Ask for directory, if none is deposite or 'Save Project As' was pressed
        if self.pHomeRmn == None or q == 'Save As':
            fileName = QtWidgets.QFileDialog.getSaveFileName(self, 'Save as', self.pHomeRmn, 
                'All Files (*);;Raman Files (*.rmn)')
            if fileName[0] != '':
                self.pHomeRmn = fileName[0]
            else:
                return
        else:
            pass

        save_dict = {}
        for key, val in self.folder.items():
            save_dict[key] = {}
            for j in range(val[0].childCount()):
                win_name = val[0].child(j).text(0)
                win_type = self.windowtypes[val[0].child(j).type()]
                window = self.window[win_type][win_name]
                if win_type == 'Spreadsheet':
                    save_dict[key][win_name] = [win_type, window.d]
                elif win_type == 'Plotwindow':
                    save_dict[key][win_name] = [win_type, [window.data, window.fig]]
                elif win_type == 'Textwindow':
                    save_dict[key][win_name] = [win_type, window.text]
                else:
                    pass

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
            file = open(self.pHomeRmn,'wb')
            try: 
                pickle.dump(save_dict, file)
            except TypeError as e:
                self.show_statusbar_message('TypeError \n Someting went wrong. The file is not saved \n' + str(e), 4000)
            file.close()
            os.remove(os.path.splitext(self.pHomeRmn)[0] + '_test' + 
                                    os.path.splitext(self.pHomeRmn)[1]) 
        else:
            saveControllParam = 0
            pass

    def execute_database_measurements(self):
        title = 'Database'
        self.db_measurements = Database_Measurements.DatabaseMeasurements()
        DBM_tab = self.tabWidget.addTab(self.db_measurements, self.PyramanIcon, title)

    def close_tab(self, index):
        if self.tabWidget.widget(index) == self.db_measurements:
            self.tabWidget.removeTab(index)
        else:
            pass

    def create_sidetree_structure(self, structure):
        self.treeWidget.clear()
        for key, val in structure.items():
            self.new_Folder(key)

    def activate_window(self, item):
        text = item.text(0)
        winTypInt = item.type()     # 0 - Folder, 1 - Spreadsheet, 2 - Plotwindow, 3 - Textwindow

        if winTypInt == 0:          # 
            self.tabWidget.setCurrentWidget(self.folder[text][1])           
        else:
            windowtype = self.windowtypes[winTypInt]
            win = self.windowWidget[windowtype][text]
            currentFolder = item.parent().text(0)
            self.tabWidget.setCurrentWidget(self.folder[currentFolder][1])
            self.folder[currentFolder][1].setActiveSubWindow(win)
            win.showMaximized()

    def tree_window_options(self, event, item):
        if item != None:
            if event.button() == QtCore.Qt.RightButton:
                text = item.text(0)
                TreeItemMenu = QMenu()
                ActRename = TreeItemMenu.addAction('Rename')
                ac = TreeItemMenu.exec_(self.treeWidget.mapToGlobal(event.pos()))
                # Rename
                if ac == ActRename:
                    self.treeWidget.editItem(item)
                    self.treeWidget.itemChanged.connect(lambda item, column: self.rename_window(item, column, text))
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
                    self.newWindow(None, 'Spreadsheet', None, None)
                elif ac == ActNewText:
                    self.newWindow(None, 'Textwindow', '', None)
                else:
                    pass

    def change_folder(self, droppedItem, itemAtDropLocation):
        foldername = itemAtDropLocation.text(0)
        windowtyp = droppedItem.type()
        windowname = droppedItem.text(0)
        previous_folder = droppedItem.parent().text(0)
        if itemAtDropLocation.type() == 0:            # dropevent in folder
            self.tabWidget.setCurrentWidget(self.folder[previous_folder][1])
            wind = self.window[self.windowtypes[windowtyp]][windowname]
            mdi = self.folder[foldername][1]
            new_Window = mdi.addSubWindow(wind)
            previous_mdi = self.folder[previous_folder][1]
            previous_mdi.removeSubWindow(wind)
            self.windowWidget[self.windowtypes[windowtyp]][windowname] = new_Window
            self.delete_empty_subwindows(previous_mdi)
        else:
            return

    def delete_empty_subwindows(self, mdi):
        sub_win_list = mdi.subWindowList()
        for j in sub_win_list:
            if j.widget() == None:
                mdi.removeSubWindow(j)

    def rename_window(self, item, column, old_text):
        new_text = item.text(column)
        windowtype = self.windowtypes[item.type()]

        if new_text in self.windowNames[windowtype]:                # in case name is already assigned
            self.treeWidget.itemChanged.disconnect()
            item.setText(0, old_text)
            self.show_statusbar_message('Name is already assigned', 4000)
        else:
            if windowtype == 'Folder':
                self.folder[new_text] = self.folder.pop(old_text)
                index = self.tabWidget.indexOf(self.folder[new_text][1])
                self.tabWidget.setTabText(index, new_text)
            else:
                win = self.windowWidget[windowtype][old_text]
                win.setWindowTitle(new_text)
                self.window[windowtype][new_text] = self.window[windowtype].pop(old_text)
                self.windowWidget[windowtype][new_text] = self.windowWidget[windowtype].pop(old_text)
                index = self.windowNames[windowtype].index(old_text)
                self.update_spreadsheet_menubar()
            self.windowNames[windowtype][index] = new_text
            self.treeWidget.itemChanged.disconnect()

    def rearange(self, q):
        #rearange open windows
        if q.text() == "Cascade":
            self.tabWidget.currentWidget().cascadeSubWindows()

        if q.text() == "Tiled":
            self.tabWidget.currentWidget().tileSubWindows()

    def newWindow(self, foldername, windowtype, windowcontent, title):
        if foldername == None:
            foldername = self.tabWidget.tabText(self.tabWidget.currentIndex())
        else:
            foldername = foldername

        if title == None:
            i = 1
            while i <= 100:
                title = windowtype + ' ' + str(i)
                if title in self.windowNames[windowtype]:
                    i +=1
                else:
                    break
        else:
            pass

        if windowtype == 'Spreadsheet':
            ssd = windowcontent
            if ssd == None:
                ssd = {'data0' : (np.full(9, np.nan),'A', 'X', None), 'data1' : (np.full(9, np.nan),'B', 'Y', None)}  #Spreadsheet- Data (for start only zeros)
            else:
                pass
            windowtypeInt = 1
            self.window[windowtype][title] = SpreadSheet(self, ssd)
            newSS = self.window[windowtype][title]
            newSS.new_pw_signal.connect(lambda: self.newWindow(None, 'Plotwindow', [newSS.plot_data, None], None))
            newSS.add_pw_signal.connect(lambda pw_name: self.add_Plot(pw_name, newSS.plot_data))
            icon = QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/table.png")
        elif windowtype == 'Plotwindow':
            windowtypeInt = 2
            plotData, fig = windowcontent
            self.window[windowtype][title] = PlotWindow(plotData, fig, self)
            self.update_spreadsheet_menubar()
            icon = QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/PlotWindow.png")
        elif windowtype == 'Textwindow':
            windowtypeInt = 3
            txt = windowcontent
            self.window[windowtype][title] = TextWindow(self, txt)
            icon = QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/TextWindow.png")
        else:
            return

        self.windowWidget[windowtype][title] = self.folder[foldername][1].addSubWindow(self.window[windowtype][title])
        self.window[windowtype][title].setWindowTitle(title)
        self.window[windowtype][title].show()
        self.windowNames[windowtype].append(title)

        item = QTreeWidgetItem([title], type = windowtypeInt)
        item.setIcon(0, icon)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled |
                                         Qt.ItemIsUserCheckable | Qt.ItemNeverHasChildren)

        self.folder[foldername][0].addChild(item)
        self.window[windowtype][title].closeWindowSignal.connect(self.close_window)

    def new_Folder(self, title):
        if title == None:
            i = 1
            while i <= 100:
                title = 'Folder ' + str(i)
                if title in self.folder.keys():
                    i +=1
                else:
                    break
        else:
            pass

        self.folder[title] = []                    # first entry contains QTreeWidgetItem (Folder), second contains QMdiArea
        self.folder[title].append(QTreeWidgetItem([title]))
        self.folder[title][0].setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable |
                                     Qt.ItemIsDropEnabled)
        self.folder[title][0].setIcon(0, QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/folder.png"))
        self.treeWidget.addTopLevelItem(self.folder[title][0])
        self.treeWidget.expandItem(self.folder[title][0])
        self.windowNames['Folder'].append(title)
        self.folder[title].append(QtWidgets.QMdiArea(self))               # widget for multi document interface area
        self.tabWidget.addTab(self.folder[title][1], self.PyramanIcon, title)

    def add_Plot(self, pw_name, plotData):
        # add spectrum to existing plotwindow
        for j in plotData:
            j[4] = self.window['Plotwindow'][pw_name].Spektrum[0].get_linestyle()
        self.window['Plotwindow'][pw_name].add_plot(plotData)

    def close_window(self, windowtype, title):
        del self.window[windowtype][title]
        del self.windowWidget[windowtype][title] 
        self.windowNames[windowtype].remove(title)
        items = self.treeWidget.findItems(title, Qt.MatchFixedString | Qt.MatchRecursive)

        self.folder[items[0].parent().text(0)][0].removeChild(items[0])
        self.update_spreadsheet_menubar()

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
    def __init__(self, mainwindow, text, parent = None):
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
        fileName = QtWidgets.QFileDialog.getSaveFileName(self, 'Load', filter = 'All Files (*);; Txt Files (*.txt)')

        if fileName[0] != '':                       
            fileName = fileName[0]
        else:
            return

        file = open(fileName, 'w')            
        file.write(self.text)    
        file.close() 

    def load_file(self):
        fileName = QtWidgets.QFileDialog.getOpenFileName(self, 'Load', filter = 'All Files (*);; Txt Files (*.txt)')

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

# teilweise (Class SpreadSheetDelegate and class SpreadSheetItem) geklaut von: 
# http://negfeedback.blogspot.com/2017/12/a-simple-gui-spreadsheet-in-less-than.html 
cellre = re.compile(r'\b[A-Z][0-9]\b')

def cellname(i, j):
    return '{}{}'.format(chr(ord('A')+j), i+1)

class SpreadSheetDelegate(QItemDelegate):
	def __init__(self, parent=None):
		super(SpreadSheetDelegate, self).__init__(parent)

	def createEditor(self, parent, styleOption, index):
		editor = QLineEdit(parent)
		editor.editingFinished.connect(self.commitAndCloseEditor)
		return editor

	def commitAndCloseEditor(self):
		editor = self.sender()
		self.commitData.emit(editor)
		self.closeEditor.emit(editor, QItemDelegate.NoHint)

	def setEditorData(self, editor, index):
		editor.setText(index.model().data(index, Qt.EditRole))

	def setModelData(self, editor, model, index):
		model.setData(index, editor.text())


class SpreadSheetItem(QTableWidgetItem):
    def __init__(self, siblings, wert):
        super(SpreadSheetItem, self).__init__()
        self.siblings = siblings
        self.value = np.nan
        self.deps = set()
        self.reqs = set()
        self.wert = wert

    def formula(self):
        return super().data(Qt.DisplayRole)

    def data(self, role):
        if role == Qt.EditRole:
            return self.formula()
        if role == Qt.DisplayRole:
            return self.display()

        return super(SpreadSheetItem, self).data(role)

    def calculate(self):
        formula = self.formula()
        if formula is None:
            self.value = self.wert
            if math.isnan(self.value):
                self.value = ''
            return

        currentreqs = set(cellre.findall(formula))

        name = cellname(self.row(), self.column())

        if name == formula:
            print('You should not do this!')
            return

        # Add this cell to the new requirement's dependents
        for r in currentreqs - self.reqs:
            self.siblings[r].deps.add(name)
        # Add remove this cell from dependents no longer referenced
        for r in self.reqs - currentreqs:
            self.siblings[r].deps.remove(name)

        # Look up the values of our required cells
        reqvalues = {r: self.siblings[r].value for r in currentreqs}
        # Build an environment with these values and basic math functions
        environment = ChainMap(math.__dict__, reqvalues)
        # Note that eval is DANGEROUS and should not be used in production
        try:
            self.value = eval(formula, {}, environment)
        except NameError:                                   # occurs if letters were typed in
            print('Bitte keine Buchstaben eingeben')
            self.value = self.wert
        except SyntaxError:
            print('keine Ahnung was hier los ist')

        self.reqs = currentreqs

    def propagate(self):
        for i in self.deps:
            self.siblings[i].calculate()
            self.siblings[i].propagate()

    def display(self):
        self.calculate()
        self.propagate()
        return str(self.value)

class SpreadSheet(QMainWindow):

    new_pw_signal   = QtCore.pyqtSignal()
    add_pw_signal   = QtCore.pyqtSignal(str)
    closeWindowSignal = QtCore.pyqtSignal(str, str)

    def __init__(self, mainwindow, data, parent = None):
        super(SpreadSheet, self).__init__(parent)
        self.cells = {}
        self.d = data              # structure of data (dictionary) {'dataX with X = (0,1,2,..)' : actual data,'name of data', 'X, Y or Yerr', 'if loaded: filename')}
        self.mw = mainwindow
        self.cols = len(self.d)	                                        # number of columns
        self.rows = max([len(self.d[j][0]) for j in self.d.keys()])     # number of rows
        self.pHomeTxt = None                                            # path of Txt-File

        self.create_tablewidgets()
        self.create_menubar()
        self.create_col_header()
        self.create_row_header()

    def create_tablewidgets(self):        
        self.table = QTableWidget(self.rows, self.cols, self)
        ### fill the table items with data ###
        self.table.setItemDelegate(SpreadSheetDelegate(self))
        for j in range(self.cols):
            for k in range(len(self.d['data%i'%j][0])):
                cell = SpreadSheetItem(self.cells, self.d['data%i'%j][0][k])
                self.cells[cellname(k, j)] = cell
                self.table.setItem(k, j, cell)		

        self.setCentralWidget(self.table)
        self.table.itemChanged.connect(self.update_data)

    def create_menubar(self): 
    # create the menubar               
        self.menubar = self.menuBar()

        ### 1. menu item: File ###
        fileMenu = self.menubar.addMenu('&File')
        fileMenu.addAction('Save Data', self.file_save)
        fileMenu.addAction('Load Data', self.load_file)

        ### 2. menu item: Edit
        editMenu = self.menubar.addMenu('&Edit')
        editMenu.addAction('New Column', self.new_col)

        ### 3. menu item: Plot
        plotMenu = self.menubar.addMenu('&Plot')
        plotNew = plotMenu.addMenu('&New')
        plotNew.addAction('Line Plot', self.get_plot_data)
        plotNew.addAction('Dot Plot', self.get_plot_data)
        plotAdd = plotMenu.addMenu('&Add to')
        for j in self.mw.window['Plotwindow'].keys():
            plotAdd.addAction(j, self.get_plot_data)

        self.show()

    def update_menubar(self):
        self.menubar.clear()
        self.create_menubar()

    def create_col_header(self):
        headers = [self.d[j][1] + '(' + self.d[j][2] + ')' for j in self.d.keys()]
        self.table.setHorizontalHeaderLabels(headers)

        ### open header_menu with right mouse click ###
        self.headers = self.table.horizontalHeader()
        self.headers.setContextMenuPolicy(Qt.CustomContextMenu)
        self.headers.customContextMenuRequested.connect(self.show_header_context_menu)
        self.headers.setSelectionMode(QAbstractItemView.SingleSelection)

        ### opens rename_header with double mouse click ###
        self.headerline = QtWidgets.QLineEdit()                         # Create
        self.headerline.setWindowFlags(QtCore.Qt.FramelessWindowHint)   # Hide title bar
        self.headerline.setAlignment(QtCore.Qt.AlignLeft)               # Set the Alignmnet
        self.headerline.setHidden(True)                                 # Hide it till its needed
        self.sectionedit = 0
        self.table.horizontalHeader().sectionDoubleClicked.connect(self.rename_header)
        self.headerline.editingFinished.connect(self.doneEditing)

    def rename_header(self, column):
        # This block sets up the geometry for the line edit
        header_position = self.headers.mapToGlobal(QtCore.QPoint(0, 0))
        edit_geometry = self.headerline.geometry()
        edit_geometry.setWidth(self.headers.sectionSize(column))
        edit_geometry.setHeight(self.table.rowHeight(0))
        edit_geometry.moveLeft(header_position.x() + self.headers.sectionViewportPosition(column))
        edit_geometry.moveTop(header_position.y())
        self.headerline.setGeometry(edit_geometry)

        self.headerline.setText(self.d['data%i'%column][1])
        self.headerline.setHidden(False) # Make it visiable
        self.headerline.setFocus()
        self.sectionedit = column

    def doneEditing(self):
        self.headerline.setHidden(True)
        newHeader = str(self.headerline.text())
        data_zs = self.d['data%i'%self.sectionedit]
        self.d.update({'data%i'%self.sectionedit : (data_zs[0], newHeader, data_zs[2], data_zs[3])})
        self.table.horizontalHeaderItem(self.sectionedit).setText(self.d['data%i'%self.sectionedit][1] + '(' + self.d['data%i'%self.sectionedit][2] + ')')

    def show_header_context_menu(self, position):
        selected_column = self.headers.logicalIndexAt(position)
        header_menu = QMenu()
        delete_column = header_menu.addAction('Delete this column?')
        set_xy   = header_menu.addMenu('Set as:')
        set_x    = set_xy.addAction('X')
        set_y    = set_xy.addAction('Y')
        set_yerr = set_xy.addAction('Yerr')
        ac = header_menu.exec_(self.table.mapToGlobal(position))
        # Delete selected colums
        if ac == delete_column:
            # Get the index of all selected columns in reverse order, so that last column is deleted first
            selCol = sorted(set(index.column() for index in self.table.selectedIndexes()), reverse = True)      
            for j in selCol:
                del self.d['data%i'%j]                                                      # Delete data
                # Rename the remaining columns, so there is no gap in the numbering 
                for k in range(j+1, self.cols):
                    self.d['data%i'%(k-1)] = self.d.pop('data%i'%k)
                self.table.removeColumn(j)                                                  # Delete column
                self.cols = self.cols - 1
        if ac == set_x:
            data_zs = self.d['data%i'%selected_column]
            self.d.update({'data%i'%selected_column : (data_zs[0], data_zs[1], 'X', data_zs[3])})
            headers = [self.d[j][1] + '(' + self.d[j][2] + ')' for j in self.d.keys()]
            self.table.setHorizontalHeaderLabels(headers)
        if ac == set_y:
            data_zs = self.d['data%i'%selected_column]
            self.d.update({'data%i'%selected_column : (data_zs[0], data_zs[1], 'Y', data_zs[3])})
            headers = [self.d[j][1] + '(' + self.d[j][2] + ')' for j in self.d.keys()]
            self.table.setHorizontalHeaderLabels(headers)
        if ac == set_yerr:
            data_zs = self.d['data%i'%selected_column]
            self.d.update({'data%i'%selected_column : (data_zs[0], data_zs[1], 'Yerr', data_zs[3])})
            headers = [self.d[j][1] + '(' + self.d[j][2] + ')' for j in self.d.keys()]
            self.table.setHorizontalHeaderLabels(headers)

    def create_row_header(self):
         ### opens header_menu with right mouse click###
        self.row_headers = self.table.verticalHeader()
        self.row_headers.setContextMenuPolicy(Qt.CustomContextMenu)
        self.row_headers.customContextMenuRequested.connect(self.row_options)
        self.row_headers.setSelectionMode(QAbstractItemView.SingleSelection)

    def row_options(self, position):
        selected_row = self.row_headers.logicalIndexAt(position)
        header_menu = QMenu()
        delete_row = header_menu.addAction('Delete this row?')
        ac = header_menu.exec_(self.table.mapToGlobal(position))
        # Delete selected colums
        if ac == delete_row:
            # Get the index of all selected rows in reverse order, so that last row is deleted first
            selRow = sorted(set(index.row() for index in self.table.selectedIndexes()), reverse = True)      
            for j in range(self.cols):
                for k in selRow:
                    del self.d['data%i'%j][0][k]                                            # Delete data
              
            for k in selRow:
                self.table.removeRow(k)                                                  # Delete row
                self.rows = self.rows - 1
            
    def keyPressEvent(self, event):
    # A few shortcuts
    # Enter or Return: go to the next row
        key = event.key()
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            # go to next row
            cr = self.table.currentRow()
            cc = self.table.currentColumn()
            if cr == (self.rows-1):
                self.table.insertRow(self.rows)
                for i in range(self.cols):
                    self.table.setItem(self.rows, i, QTableWidgetItem())
                self.rows = self.rows + 1
            else:
                pass
            ti = self.table.item(cr+1, cc)
            self.table.setCurrentItem(ti)
        if key == Qt.Key_Delete:
            selItem = [[index.row(), index.column()] for index in self.table.selectedIndexes()]
            for j in selItem:
                self.table.takeItem(j[0], j[1])
                self.d['data%i' % j[1]][0][j[0]] = np.nan
        else:
            super(SpreadSheet, self).keyPressEvent(event)

    def file_save(self):
        SaveFileName = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', self.pHomeTxt)
        if SaveFileName[0] == '':
            SaveFileName = SaveFileName[0]
        else:
            return

        formattyp = '%.3f'
        data = [self.d['data0'][0]]
        for j in range(1, self.cols):
            data.append(self.d['data%i'%j][0])
            formattyp = formattyp + '	%.3f'
        
        n = len(self.d['data0'][0])
        if all(len(x) == n for x in data):
            pass
        else:
            self.mw.show_statusbar_message('The columns have different lengths!', 4000)
            return

        data = np.transpose(data)


        if SaveFileName[-4:] == '.txt':
            pass
        else:
            SaveFileName = str(SaveFileName) + '.txt'

        self.pHomeTxt = SaveFileName

        np.savetxt(SaveFileName, data, fmt = formattyp)	

    def load_file(self):
        #In case there already is data in the spreadsheet, ask if replace or added
        if any(self.d[j][3] != None for j in self.d.keys()):
            FrageErsetzen = QtWidgets.QMessageBox()
            FrageErsetzen.setIcon(QMessageBox.Question)
            FrageErsetzen.setWindowTitle('Replace or Add?')
            FrageErsetzen.setText('Data is already loaded. Shall these be replaced?')
            buttonY = FrageErsetzen.addButton(QMessageBox.Yes)
            buttonY.setText('Replace')
            buttonN = FrageErsetzen.addButton(QMessageBox.No)
            buttonN.setText('Add')
            buttonC = FrageErsetzen.addButton(QMessageBox.Cancel)
            buttonC.setText('Cancel')
            returnValue = FrageErsetzen.exec_()
            if returnValue == QMessageBox.Yes:      #Replace
                self.d    = {} 
                self.cols = 0	
                self.rows = 0
            elif returnValue == QMessageBox.No:     #Add
                self.cols = self.cols
            else:                                   #Cancel
                return
        else:
            self.cols = 0
            
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setNameFilter(("Data (*.txt)"))
        dialog.setViewMode(QFileDialog.List)
        dialog.setDirectory(self.pHomeTxt)
        if dialog.exec_():
            newFiles = dialog.selectedFiles()
        else:
            return
        
        n_newFiles = len(newFiles)
        data = []
        lines = []
        FileName = []
        header = []
        for j in range(n_newFiles):
            # read first line to get header
            with open(newFiles[j]) as f:
                firstline = f.readline()
            # check if file has a header (starts with #)
            if firstline[0] == '#':
                firstline = firstline[1:-2]                      # remove '#' at beginning and '\n' at end
                firstline = firstline.split('%')               # headers of different columns are seperated by '%'
                header.append(firstline)
            else:
                header.append(None)
                pass
            data.append(np.loadtxt(newFiles[j]))
            data[j] = np.transpose(data[j])
            lines.append(len(data[j]))
            FileName.append(os.path.splitext(os.path.basename(newFiles[j]))[0]) 
        for k in range(n_newFiles):
            for j in range(lines[k]):	
                data_name = 'data%i'%(j+self.cols)			
                if j == 0:
                    if header[k] == None:   # if header is None, use Filename as header
                        self.d.update({data_name : (data[k][j], str(FileName[k]), 'X', newFiles[k])})
                    else:
                        self.d.update({data_name: (data[k][j], header[k][j], 'X', newFiles[k])})
                else:
                    if header[k] == None:
                        self.d.update({data_name : (data[k][j], str(FileName[k]), 'Y', newFiles[k])})
                    else:
                        self.d.update({data_name: (data[k][j], header[k][j], 'Y', newFiles[k])})
            self.cols = self.cols + lines[k]

        self.rows = max([len(self.d[j][0]) for j in self.d.keys()])

        self.table.setColumnCount(self.cols)
        self.table.setRowCount(self.rows)
        
        headers = [self.d[j][1] + '(' + self.d[j][2] + ')' for j in self.d.keys()]
        self.table.setHorizontalHeaderLabels(headers)

        for j in range(self.cols):
            zwischenspeicher = self.d['data%i'%j][0]
            for k in range(len(zwischenspeicher)):
                newcell = SpreadSheetItem(self.cells, zwischenspeicher[k])
                self.cells[cellname(k, j)] = newcell
                self.table.setItem(k, j, newcell)

        self.pHomeTxt = FileName[0]

    def update_data(self, item):
        new_cell_content = item.text()
        col = item.column()
        row = item.row()
        if new_cell_content == '':
            self.table.takeItem(row, col)
            self.d['data{}'.format(col)][0][row]= np.nan
        else:
            self.d['data{}'.format(col)][0][row] = new_cell_content

    def new_col(self):
        self.cols = self.cols + 1
        self.table.setColumnCount(self.cols)
        self.d.update({'data%i'%(self.cols-1) : (np.zeros(self.rows), str(chr(ord('A') + self.cols - 1)), 'Y', '')})
        headers = [self.d[j][1] + '(' + self.d[j][2] + ')' for j in self.d.keys()]  
        self.table.setHorizontalHeaderLabels(headers)
        for i in range(self.rows):
            cell = SpreadSheetItem(self.cells, 0)
            self.cells[cellname(i, self.cols-1)] = cell
            self.table.setItem(i, self.cols-1, cell)
                        
    def get_plot_data(self):
        # get data from selected columns and prepares data for plot

        self.plot_data = []     # [X-data, Y-data, label, file, yerr, plottype]  # in newer projected additional entry: self


        selCol = sorted(set(index.column() for index in self.table.selectedIndexes()))  #selected Columns

        # Decides if line or dot plot       
        action = self.sender()
        if action.text() == 'Line Plot':
            plot_type = '-'
        elif action.text() == 'Dot Plot':
            plot_type = 'o'
        else:
            plot_type = None        

        for j in selCol:
            if self.d['data%i'%j][2] != 'Y':
                self.mw.show_statusbar_message('Please only select Y-columns!', 4000)
                return
            else:
                k = j-1
                while k >=0:
                    if self.d['data%i'%k][2] == 'X':
                        self.plot_data.append([self.d['data%i'%k][0], self.d['data%i'%j][0], self.d['data%i'%j][1], self.d['data%i'%k][3], plot_type])
                        m = j+1
                        while m <= self.cols:
                            if m == self.cols:
                                yerr = 0
                                m = self.cols+1
                            elif self.d['data%i'%m][2] == 'Yerr':
                                yerr = self.d['data%i'%m][0]
                                m = self.cols+1
                            else:
                                m = m+1
                        self.plot_data[-1].append(yerr)
                        k = -2
                    else:
                        k = k-1
                if k == -1:
                    self.mw.show_statusbar_message('At least one dataset Y has no assigned X dataset.', 4000)
                    return
                else:
                    pass

        # check that x and y have same length to avoid problems later:
        # append Spreadsheet instance
        for j in self.plot_data:
            if len(j[0]) == len(j[1]):
                j.append(self.windowTitle())
            else:
                self.mw.show_statusbar_message('X and Y have different lengths')
                return


        # emit signal to MainWindow to create new Plotwindow or add lines to existing plotwindow
        if plot_type != None:
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
class Functions:
    def __init__(self, pw):
        self.pw = pw

    ### definition of Lorentzian for fit process ###
    def LorentzFct(self, x, xc, h, b):
        return  h/(1 + (2*(x - xc)/b)**2)
        #return a2/pi*a1/((x-a0)*(x-a0)+a1*a1)

    ### definition of Gaussian for fit process ###
    def GaussianFct(self, x, xc, h, b):
        return h*np.exp(-4*math.log(2)*((x - xc)/b)*((x-xc)/b))
        #return a2*np.exp(-(x-a0)*(x-a0)/(2*a1*a1))

    ### definition of Breit-Wigner-Fano fucntion for fit process ###
    #(look e.g. "Interpretation of Raman spectra of disordered and amorphous carbon" von Ferrari und Robertson)
    #Q is BWF coupling coefficient
    #For Q^-1->0: the Lorentzian line is recovered
    def BreitWignerFct(self, x, xc, h, b, Q):
        return h*(1+2*(x-xc)/(Q*b))**2/(1+(2*(x-xc)/b)**2)

    ### Summing up the fit functions ###
    def FctSumme(self, x, *p):   
        a = self.pw.n_fit_fct['Lorentz']     #number of Lorentzians
        b = self.pw.n_fit_fct['Gauss']       #number of Gaussians
        c = self.pw.n_fit_fct['Breit-Wigner-Fano']        #number of Breit-Wigner-Fano functions
        pL = 1  
        pG = 1 + a*3
        pB = 1 + a*3 + b*3
        return p[0] + (np.sum([self.LorentzFct(x, p[i*3+1], p[i*3+2], p[i*3+3]) for i in range(a)], axis=0)+ 
                       np.sum([self.GaussianFct(x, p[i*3+pG], p[i*3+1+pG], p[i*3+2+pG]) for i in range(b)], axis=0) + 
                       np.sum([self.BreitWignerFct(x, p[i*4+pB], p[i*4+1+pB], p[i*4+2+pB], p[i*4+3+pB]) for i in range(c)], axis=0))

# Plotting a vertical line in plot, e.g. to define area for fit
class LineBuilder:
    def __init__(self, line):
        self.line = line
        self.xs = line.get_xdata()[0]
        self.line.set_visible(True)
        self.cid = line.figure.canvas.mpl_connect('button_press_event', self)
        line.figure.canvas.start_event_loop(timeout=10000)
    def __call__(self, event):
        if event.inaxes!=self.line.axes: return
        elif event.button == 1:
            self.xs = event.xdata
            self.line.set_xdata([self.xs, self.xs])
            self.line.figure.canvas.draw()
        elif event.button == 3:
            self.line.figure.canvas.mpl_disconnect(self.cid)
            self.line.figure.canvas.stop_event_loop(self)
        else:
            pass

#idea: https://github.com/yuma-m/matplotlib-draggable-plot
class LineDrawer:
    def __init__(self, arrow):
        '''
        Class to draw lines and arrows

        Parameters
        ----------
        arrow: FancyArrowPatch
        '''
        self.arrow = arrow
        self.fig = self.arrow.figure
        self.ax = self.fig.axes[0]
        self.c = self.fig.canvas
        posA, *_, posB = self.arrow.get_path()._vertices
        self.posA = list(posA)
        self.posB = list(posB)
        self.pickedPoint = None

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
            self.selectedPoint, = self.ax.plot(self.pickedPoint[0], self.pickedPoint[1], 'o', ms=12, alpha=0.4, color='yellow')
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
        arrowstyle = self.arrow.get_arrowstyle()                            # get arrow_style of arrow, returns object
        arrowstyle_start = str(arrowstyle).split(' ', 1)[0]                 # get object name without adress x0....
        list_of_styles = mpatches.ArrowStyle.get_styles()                   # get all possible arrowstyles, returns dictionnary
        current_style = 0
        for key, val in list_of_styles.items():                             # compare arrowstyle with arrowstyle list to 
            if str(mpatches.ArrowStyle(key)).split(' ', 1)[0] == arrowstyle_start:   #in order to get arrowstyle name (e.g. '->')
                current_style = key
                
        lineOptions = [
            ('Width', self.arrow.get_linewidth()),
            ('Line style', [self.arrow.get_linestyle(), 
                ('-', 'solid'),
                ('--', 'dashed'),
                ('-.', 'dashDot'),
                (':', 'dotted'),
                ('None', 'None')]),
            ('Color', color)
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

        selectedOptions = formlayout.fedit(optionsList, title="Line options")
        if selectedOptions is not None:
            self.apply_callback(selectedOptions)

    def apply_callback(self, selectedOptions):
        lineOptions = selectedOptions[0]
        arrowOptions = selectedOptions[1]
        positionOptions = selectedOptions[2]

        (width, linestyle, color) = lineOptions
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

        self.c.draw()

class InsertText:
    def __init__(self, text):
        self.text = text
        self.fig = self.text.figure
        if self.fig == None:
            return
        self.cid1 = self.fig.canvas.mpl_connect('pick_event', self.on_pick)
        self.newText = None     #text content

    def on_pick(self, event):
        if event.artist == self.text and event.mouseevent.button == 1 and event.mouseevent.dblclick == True:
            tbox=dict(boxstyle='Square', fc="w", ec="k")
            self.text.set_bbox(tbox)
            self.cid4 = self.fig.canvas.mpl_connect('key_press_event', self.text_input)
            self.fig.canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
            self.fig.canvas.setFocus()
            self.fig.canvas.draw()
        elif event.artist == self.text and event.mouseevent.button == 1:
            self.cid2 = self.fig.canvas.mpl_connect('button_release_event', self.on_release)
            self.cid3 = self.fig.canvas.mpl_connect('motion_notify_event', self.on_motion)
        elif event.artist == self.text and event.mouseevent.button == 3:
            self.text_options()
        elif 'cid4' in locals():
            self.fig.canvas.mpl_disconnect(self.cid4)
        else:
            return

    def on_motion(self, event):
        pos = (event.xdata, event.ydata)
        self.text.set_position(pos)
        self.fig.canvas.draw()

    def on_release(self, event):
        self.fig.canvas.mpl_disconnect(self.cid2)
        self.fig.canvas.mpl_disconnect(self.cid3)

    def text_input(self, event):
        insert = event.key
        old_text = self.newText
        if event.key == 'enter':
            self.text.figure.canvas.mpl_disconnect(self.cid4)
            self.text.set_text(self.newText)
            self.text.set_bbox(None)
            self.fig.canvas.draw()
            self.newText = None
            return
        elif insert == 'shift':
            pass
        elif insert == 'ctrl+alt' or insert == 'control':
            pass
        elif insert[:-2] == 'ctrl+alt':
            insert = insert[9]
            self.newText = self.newText + insert
        elif insert == 'backspace':
            self.newText = self.newText[:-1]
        elif self.newText == None:
            self.newText = insert
        else:
            self.newText = self.newText + insert

        try:
            self.text.set_text(self.newText)
            self.fig.canvas.draw()
        except ValueError as e:
            self.text.set_text(old_text)
            self.fig.canvas.draw()
            print(e)


    def text_options(self):
        color = mcolors.to_hex(mcolors.to_rgba(self.text.get_color(), self.text.get_alpha()), keep_alpha=True)
        text_options_list = [
            ('Fontsize', self.text.get_fontsize()),
            ('Color', color),
            ]

        text_option_menu = formlayout.fedit(text_options_list, title="Text options")
        if text_option_menu is not None:
            self.apply_callback(text_option_menu)

    def apply_callback(self, options):
        (fontsize, color) = options

        self.text.set_fontsize(fontsize)
        self.text.set_color(color)
        self.fig.canvas.draw()


class DataPointPicker:
    def __init__(self, line, selected, a):
        # Creates a yellow dot around a selected data point
        self.xs = line.get_xdata()
        self.ys = line.get_ydata()
        self.line = line
        self.selected = selected
        self.lastind = a
        self.controll_delete_parameter = True
        self.selected.set_visible(True)
        self.selected.figure.canvas.draw() 
        
        self.line.figure.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.line.figure.canvas.setFocus()
        
        self.cid1 = line.figure.canvas.mpl_connect('pick_event', self.onpick)
        self.cid2 = line.figure.canvas.mpl_connect('key_press_event', self.onpress)

        line.figure.canvas.start_event_loop(timeout=10000)

    def onpick(self, event):
        N = len(event.ind)
        if not N:
            return True

        # the click locations
        x = event.mouseevent.xdata
        y = event.mouseevent.ydata
        distances = np.hypot(x - self.xs[event.ind], y - self.ys[event.ind])
        indmin = distances.argmin()
        self.lastind = int(event.ind[indmin])

        self.selected.set_data(self.xs[self.lastind], self.ys[self.lastind])
        self.selected.set_visible(True)
        self.selected.figure.canvas.draw()

    def onpress(self, event):
        if event.key == 'enter':
            self.line.figure.canvas.mpl_disconnect(self.cid1)
            self.line.figure.canvas.mpl_disconnect(self.cid2)
            self.line.figure.canvas.stop_event_loop(self)
            return
        elif event.key == 'right':
            inc = 1
        elif event.key == 'left':
            inc = -1     
        elif event.key == 'c':
            self.controll_delete_parameter = False
            self.line.figure.canvas.mpl_disconnect(self.cid1)
            self.line.figure.canvas.mpl_disconnect(self.cid2)
            self.line.figure.canvas.stop_event_loop(self)
            return
        else:
            return
        self.lastind += inc
        self.selected.set_data(self.xs[self.lastind], self.ys[self.lastind])
        self.selected.figure.canvas.draw()


class DataSetSelecter(QtWidgets.QDialog):
    def __init__(self, data_set_names, select_only_one = True):
        super(DataSetSelecter, self).__init__(parent=None)
        '''
        Select one or several datasets

        Parameters
        ----------
        data_set_names           # names of all datasets
        select_only_one          # if True only on Dataset can be selected
        '''
        self.data_set_names = data_set_names
        self.select_only_one = select_only_one
        self.selectedDatasetNumber = []
        self.CheckDataset = []
        self.create_dialog()

    def create_dialog(self):
        layout = QtWidgets.QGridLayout()

        for idx, name in enumerate(self.data_set_names):
            self.CheckDataset.append(QCheckBox(name, self))
            layout.addWidget(self.CheckDataset[idx], idx, 0)
            if self.select_only_one is True:
                self.CheckDataset[idx].stateChanged.connect(self.onStateChange)

        ok_button = QPushButton("ok", self)
        layout.addWidget(ok_button, len(self.data_set_names), 0)
        ok_button.clicked.connect(self.Ok_button)
        self.setLayout(layout)
        self.setWindowTitle("Dialog")
        self.exec_()

    @pyqtSlot(int)
    def onStateChange(self, state):
        if state == Qt.Checked:
            for j in self.CheckDataset:
                if self.sender() != j:
                    j.setChecked(False)

    def Ok_button(self):
        # OK Button for function SecetedDataset
        for idx, d in enumerate(self.CheckDataset):
            if d.isChecked():
                self.selectedDatasetNumber.append(idx)
            else:
                pass
        self.close()



class FitOptionsDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super(FitOptionsDialog, self).__init__(parent=parent)
        '''
        Options Dialog for Fitprocess

        Parameters
        ----------
        parent: PlotWindow
        '''
        self.parent = parent
        self.n_fit_fct = {  # number of fit functions (Lorentzian, Gaussian and Breit-Wigner-Fano)
            'Lorentz': 0,
            'Gauss': 0,
            'Breit-Wigner-Fano': 0
        }
        self.fit_fcts = {}

        self.p_start, self.p_bound = self.create_dialog()

    def create_dialog(self):
        self.layout = QtWidgets.QVBoxLayout()

        # Button to add Fit function
        addbutton = QPushButton("Add Function")
        addbutton.clicked.connect(self.add_function)
        self.layout.addWidget(addbutton)

        # Button to remove fit funtion
        removebutton = QPushButton('Remove Funtion')
        removebutton.clicked.connect(self.remove_function)
        self.layout.addWidget(removebutton)

        # OK Button => accept start values for fit
        okbutton = QPushButton("OK")
        okbutton.clicked.connect(self.close)
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
        self.table.item(0, 0).setFlags(Qt.NoItemFlags)        # no interaction with this cell
        self.table.item(0, 1).setText('Background')
        self.table.item(0, 1).setFlags(Qt.NoItemFlags)
        background = self.table.item(0, 2)
        background.setText(str(0.0))

        # bounds
        self.table.item(0, 3).setText(str(-np.inf))
        self.table.item(0, 4).setText(str(np.inf))

        self.layout.addWidget(self.table)

        self.setLayout(self.layout)
        self.setWindowTitle("Fit Functions")
        self.setWindowModality(Qt.ApplicationModal)
        self.exec_()

        p_start = [float(background.text())]                                      # Background
        parameter = {'Lorentz': [],
                     'Gauss': [],
                     'Breit-Wigner-Fano': []}

        bg_low =  self.table.item(0, 3).text()
        bg_up = self.table.item(0, 4).text()
        if bg_low == '':
            bg_low = -np.inf
        else:
            bg_low = float(bg_low)
        if bg_up == '':
            bg_up = np.inf
        else:
            bg_up = float(bg_up)
        boundaries = [[bg_low], [bg_up]]
        lower_boundaries = {'Lorentz': [],
                     'Gauss': [],
                     'Breit-Wigner-Fano': []}
        upper_boundaries = {'Lorentz': [],
                     'Gauss': [],
                     'Breit-Wigner-Fano': []}

        for key in self.fit_fcts.keys():
            name_fct = self.fit_fcts[key]['fct'].currentText()
            parameter[name_fct].append(float(self.fit_fcts[key]['position'].text()))          # Peak position in cm^-1
            parameter[name_fct].append(float(self.fit_fcts[key]['intensity'].text()))         # Intensity
            parameter[name_fct].append(float(self.fit_fcts[key]['FWHM'].text()))              # FWHM
            if name_fct == 'Breit-Wigner-Fano':
                parameter[name_fct].append(float(self.fit_fcts[key]['additional'].text()))    # additional BWF parameter for asymmetry
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
            p_start.extend(p)

        for lb, ub in zip(lower_boundaries.values(), upper_boundaries.values()):
            boundaries[0].extend(lb)
            boundaries[1].extend(ub)

        return p_start, boundaries

    def add_function(self):
        # Add combobox to select fit function
        n = len(self.fit_fcts) + 1          #Number of functions
        self.fit_fcts.update({n: {}})

        self.table.setRowCount(self.table.rowCount()+3)
        self.vheaders.extend([str(n), str(n), str(n)])
        self.table.setVerticalHeaderLabels(self.vheaders)

        rows = self.table.rowCount()

        # set items in new cell
        for r in range(rows-3, rows):
            for c in range(self.table.columnCount()):
                cell = QtWidgets.QTableWidgetItem()
                self.table.setItem(r, c, cell)

        # configurate cells
        self.table.item(rows - 2, 0).setFlags(Qt.NoItemFlags)        # no interaction with this cell
        self.table.item(rows - 1, 0).setFlags(Qt.NoItemFlags)
        # postion
        self.table.item(rows - 3, 1).setText('Position')
        self.table.item(rows - 3, 1).setFlags(Qt.NoItemFlags)
        self.table.item(rows - 3, 2).setText(str(520))
        self.fit_fcts[n].update({'position': self.table.item(rows - 3, 2)})
        # intensity
        self.table.item(rows - 2, 1).setText('Intensity')
        self.table.item(rows - 2, 1).setFlags(Qt.NoItemFlags)
        self.table.item(rows - 2, 2).setText(str(100))
        self.fit_fcts[n].update({'intensity': self.table.item(rows - 2, 2)})
        # FWHM
        self.table.item(rows - 1, 1).setText('FWHM')
        self.table.item(rows - 1, 1).setFlags(Qt.NoItemFlags)
        self.table.item(rows - 1, 2).setText(str(25))
        self.fit_fcts[n].update({'FWHM': self.table.item(rows - 1, 2)})

        # boundaries
        # position
        self.table.item(rows - 3, 3).setText('0')
        self.table.item(rows - 3, 4).setText(str(np.inf))
        # intensity
        self.table.item(rows - 2, 3).setText('0')
        self.table.item(rows - 2, 4).setText(str(np.inf))
        # FWHM
        self.table.item(rows - 1, 3).setText('0')
        self.table.item(rows - 1, 4).setText(str(np.inf))
        self.fit_fcts[n].update({'lower boundaries': [self.table.item(rows-3,3), self.table.item(rows-2,3),
                                                      self.table.item(rows-1,3)]})
        self.fit_fcts[n].update({'upper boundaries': [self.table.item(rows - 3, 4), self.table.item(rows - 2, 4),
                                                      self.table.item(rows - 1, 4)]})

        # add Combobox to select fit function
        cbox = QtWidgets.QComboBox(self)
        cbox.addItem("Lorentz")
        cbox.addItem("Gauss")
        cbox.addItem("Breit-Wigner-Fano")
        cbox.currentTextChanged.connect(lambda: self.fct_change(cbox.currentText(), n))
        self.table.setCellWidget(rows - 3, 0, cbox)
        self.fit_fcts[n].update({'fct': cbox})

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
        if fct_name == 'Breit-Wigner-Fano' and all(k != 'additional' for k in self.fit_fcts[n].keys() ):
            row_index = self.vheaders.index(str(n)) + 3
            self.table.insertRow(row_index)
            self.vheaders.insert(row_index, str(n))
            self.table.setVerticalHeaderLabels(self.vheaders)
            # set items in new cell
            for c in range(self.table.columnCount()):
                cell = QtWidgets.QTableWidgetItem()
                self.table.setItem(row_index, c, cell)
            self.table.item(row_index, 1).setText('Additional Parameter')
            self.table.item(row_index, 1).setFlags(Qt.NoItemFlags)
            self.table.item(row_index, 2).setText(str(-10))
            # boundaries
            self.table.item(row_index, 3).setText('')
            self.table.item(row_index, 4).setText('')
            # update dictionary
            self.fit_fcts[n]['lower boundaries'].append(self.table.item(row_index, 3))
            self.fit_fcts[n]['upper boundaries'].append(self.table.item(row_index, 4))
            self.fit_fcts[n].update({'additional': self.table.item(row_index, 2)})
        elif fct_name != 'Breit-Wigner-Fano' and any(k == 'additional' for k in self.fit_fcts[n].keys() ):
            row_index = self.vheaders.index(str(n)) + 3
            del self.vheaders[row_index]
            self.table.removeRow(row_index)
            del self.fit_fcts[n]['additional']
        else:
            pass

    def value_changed(self, item):
        if item.text() == '' or self.table.item(item.row(), 3).text() == '' or self.table.item(item.row(), 4).text() == '':
            return
        # check that lower bound is strictly less than upper bound
        if item.column() == 3:
            if float(item.text()) > float(self.table.item(item.row(), 4).text()):
                self.parent.mw.show_statusbar_message('Lower bounds have to be strictly less than upper bounds', 4000, error_sound=True)
                # add: replace item with old previous item
        elif item.column() == 4:            # check that upper bound is strictly higher than lower bound
            if float(item.text()) < float(self.table.item(item.row(), 3).text()):
                self.parent.mw.show_statusbar_message('Upper bounds have to be strictly higher than lower bounds', 4000, error_sound=True)
                # add: replace item with old previous item


class MyCustomToolbar(NavigationToolbar2QT):
    toolitems = [t for t in NavigationToolbar2QT.toolitems]
    # Add new toolitem at last position

    toolitems.append(
        ('Layers', "manage layers and layer contents",
         'Layer', "layer_content"))

    def __init__(self, plotCanvas):
        NavigationToolbar2QT.__init__(self, plotCanvas, parent=None)

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
            QtWidgets.QMessageBox.warning(
                self.canvas.parent(), "Error", "There are no axes to edit.")
            return
        figureoptions.figure_edit(axes, self)

    def _icon(self, name, color=None):
        if name == 'Layer.png':
            icon = QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/Layer_content.png")
        else:
            name = name.replace('.png', '_large.png')
            pm = QtGui.QPixmap(str(cbook._get_data_path('images', name)))
            _setDevicePixelRatioF(pm, _devicePixelRatioF(self))
            if color is not None:
                mask = pm.createMaskFromColor(QtGui.QColor('black'),
                                              QtCore.Qt.MaskOutColor)
                pm.fill(color)
                pm.setMask(mask)
            icon = QIcon(pm)
        return icon


class PlotWindow(QMainWindow):
    '''
    Parameters
    ----------
    plot_data: array    # [X-Data, Y-Data, label, ...]
    '''

    closeWindowSignal = QtCore.pyqtSignal(str, str)                     # Signal in case plotwindow is closed
    def __init__(self, plot_data, fig, parent):
        super(PlotWindow, self).__init__(parent)
        self.fig = fig
        self.data = plot_data
        self.mw = parent
        self.backup_data = plot_data
        self.Spektrum = []
        self.ErrorBar = []
        self.functions = Functions(self)
        self.inserted_text = []                          # Storage for text inserted in the plot
        self.drawn_line = []                             # Storage for lines and arrows drawn in the plot
        self.n_fit_fct = {                               # number of fit functions (Lorentzian, Gaussian and Breit-Wigner-Fano)
            'Lorentz': 0,
            'Gauss': 0,
            'Breit-Wigner-Fano': 0
        }

        self.plot()
        self.create_statusbar()
        self.create_menubar()
        self.create_sidetoolbar()

        #self.cid1 = self.fig.canvas.mpl_connect('button_press_event', self.mousePressEvent)
        self.cid2 = self.fig.canvas.mpl_connect('key_press_event', self.keyPressEvent)
        self.cid3 = self.fig.canvas.mpl_connect('pick_event', self.pickEvent)

    def plot(self):
        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)
        layout = QtWidgets.QVBoxLayout(self.main_widget)
        legendfontsize = 24
        labelfontsize = 24
        tickfontsize = 18

        if self.fig == None:            #new Plot
            self.fig = Figure(figsize=(15,9))
            self.ax = self.fig.add_subplot(111)
            self.Canvas = FigureCanvasQTAgg(self.fig)
            layout.addWidget(self.Canvas)

            for j in self.data:
                if isinstance(j[5], (np.ndarray, np.generic)):
                    (spect, capline, barlinecol) = self.ax.errorbar(j[0], j[1], yerr=j[5], fmt=j[4],
                        picker=5, capsize=3)
                    self.Spektrum.append(spect)
                    spect.set_label(j[2])
                    capline[0].set_label('_Hidden capline bottom ' + j[2])
                    capline[1].set_label('_Hidden capline top ' + j[2])
                    barlinecol[0].set_label('_Hidden barlinecol ' + j[2])
                else:
                    self.Spektrum.append(self.ax.plot(j[0], j[1], j[4], label = j[2], picker = 5)[0])
            self.ax.legend(fontsize = legendfontsize)
            self.ax.set_xlabel(r'Raman shift / cm$^{-1}$', fontsize = labelfontsize)
            self.ax.set_ylabel(r'Intensity / cts/s', fontsize = labelfontsize)
            self.ax.xaxis.set_tick_params(labelsize=tickfontsize)
            self.ax.yaxis.set_tick_params(labelsize=tickfontsize)
        else:                       #loaded Plot
            self.ax = self.fig.axes[0]
            self.Canvas = FigureCanvasQTAgg(self.fig)
            layout.addWidget(self.Canvas)
            for j in self.ax.lines:
                self.Spektrum.append(j)
            for j in self.ax.get_children():
                if type(j) == mpatches.FancyArrowPatch:             # all drawn lines and arrows
                    self.drawn_line.append(LineDrawer(j))
                elif type(j)== matplotlib.text.Annotation:          # all inserted texts
                    self.inserted_text.append(InsertText(j))
                else:
                    pass
            self.ax.get_legend()
        self.addToolBar(MyCustomToolbar(self.Canvas))

        self.ax.get_legend().set_picker(5)

    def add_plot(self, new_data):
        ls = self.Spektrum[0].get_linestyle()
        ma = self.Spektrum[0].get_marker()
        for j in new_data:
            self.data.append(j)
            if isinstance(j[5], (np.ndarray, np.generic)):
                (spect, capline, barlinecol) = self.ax.errorbar(j[0], j[1], yerr=j[5], picker=5, capsize=3)
                self.Spektrum.append(spect)
                spect.set_label(j[2])
                capline[0].set_label('_Hidden capline bottom ' + j[2])
                capline[1].set_label('_Hidden capline top ' + j[2])
                barlinecol[0].set_label('_Hidden barlinecol ' + j[2])
            else:
                spect = self.ax.plot(j[0], j[1], label = j[2], picker = 5)[0]
                self.Spektrum.append(spect)
            spect.set_linestyle(ls)
            spect.set_marker(ma)
        handles, labels = self.ax.get_legend_handles_labels()
        self.update_legend(handles, labels)
        self.fig.canvas.draw()

    def keyPressEvent(self, event):
        key = event.key
        if key == (Qt.Key_Control and Qt.Key_Z):
            k = 0
            for j in self.backup_data:
                self.Spektrum[k].set_xdata(j[0])
                self.Spektrum[k].set_ydata(j[1])
                k = k+1
            self.fig.canvas.draw()
        else:
            pass

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
            self.ax.figure.canvas.draw()
        elif event.artist in self.Spektrum and event.mouseevent.button == 3:
            self.lineDialog = QMenu()
            self.lineDialog.addAction("Go to Spreadsheet",lambda: self.go_to_spreadsheet(event.artist))
            point = self.mapToGlobal(QtCore.QPoint(event.mouseevent.x, self.frameGeometry().height() - event.mouseevent.y))
            self.lineDialog.exec_(point)
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

    ########## Bars (menubar, toolbar, statusbar) ##########
    def create_menubar(self):
        menubar = self.menuBar()
        ### 1. menu item: File ###
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction('Save to File', self.menu_save_to_file)

        ### 2. menu item: Edit  ###
        editMenu = menubar.addMenu('&Edit')
        editMenu.addAction('Delete broken pixel - LabRam', self.delete_datapoint)
        editDeletePixel = editMenu.addAction('Delete single pixel', self.delete_pixel)
        editDeletePixel.setStatusTip('Delete selected data point with Enter, Move with arrow keys, Press c to leave Delete-Mode')
        editSelectArea = editMenu.addAction('Define data area', self.DefineArea)
        editSelectArea.setStatusTip('Move area limit with left mouse click, set it fix with right mouse click')        
        editNormAct = editMenu.addAction('Normalize Spectrum', self.normalize)
        editNormAct.setStatusTip('Normalizes highest peak to 1')

        ### 3. menu: Analysis  ###
        analysisMenu = menubar.addMenu('&Analysis')

        ### 3.1 Analysis Fit
        analysisFit = analysisMenu.addMenu('&Fit')

        analysisFitSingleFct = analysisFit.addMenu('&Single function')
        analysisFitSingleFct.addAction('Lorentz')
        analysisFitSingleFct.addAction('Gaussian')
        analysisFitSingleFct.addAction('Breit-Wigner-Fano')
        analysisFitSingleFct.triggered[QAction].connect(self.fit_single_peak)

        analysisFit.addAction('Fit several Peaks', self.fit_peaks)

        analysisRoutine = analysisMenu.addMenu('&Analysis routines')
        analysisRoutine.addAction('D und G Bande', self.fit_D_G)
        analysisRoutine.addAction('Sulfur oxyanion ratios', self.ratio_H2O_sulfuroxyanion)

        ### 3.2 Analysis base line correction
        analysisMenu.addAction('Baseline Correction', self.menu_baseline_als)

        self.show()

    def create_statusbar(self):
        self.statusBar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusBar)
        self.show()

    def create_sidetoolbar(self):
        toolbar = QtWidgets.QToolBar(self)
        self.addToolBar(QtCore.Qt.LeftToolBarArea, toolbar)
        
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


    ########## Functions and other stuff ##########
    def go_to_spreadsheet(self, line):
        line_index = self.Spektrum.index(line)
        if len(self.data[line_index]) == 7:
            spreadsheet_name = self.data[line_index][6]
            item = self.mw.treeWidget.findItems(spreadsheet_name, Qt.MatchFixedString | Qt.MatchRecursive)
            for j in item:              #select spreadsheet if there are several items with same name
                if j.type() == 1:
                    spreadsheet_item = j
                    break
                else:
                    continue
            self.mw.activate_window(spreadsheet_item)
            spreadsheet = self.mw.window['Spreadsheet'][spreadsheet_name]
            header_name = self.data[line_index][2]
            for j in range(spreadsheet.table.columnCount()):
                if spreadsheet.table.horizontalHeaderItem(j).text() == header_name+'(Y)':
                    self.mw.show_statusbar_message(header_name, 4000)
                    spreadsheet.table.setCurrentCell(0, j)
                else:
                    continue

        elif len(self.data[line]) == 6:
            self.mw.show_statusbar_message('This functions will be available, in future projects. This project is too old', 3000)
        else:
            self.mw.show_statusbar_message('This is weird!', 3000)

    def SelectDataset(self, select_only_one=False):
        data_sets_name = []
        for j in self.ax.get_lines():
            data_sets_name.append(j.get_label())
        DSS = DataSetSelecter(data_sets_name, select_only_one)
        self.selectedData = []
        self.selectedDatasetNumber = DSS.selectedDatasetNumber
        for j in self.selectedDatasetNumber:
            self.selectedData.append(self.data[j])

    def menu_save_to_file(self):
        self.SelectDataset(True)
        for j in self.selectedData:
            if j[3] != None:
                startFileDirName = os.path.dirname(j[3])
                startFileName = startFileDirName + '/' + j[2]
            else:
                startFileName = None
            save_data = [j[0], j[1]]
            save_data = np.transpose(save_data)
            self.save_to_file('Save data selected data in file', startFileName, save_data)

    def save_to_file(self, WindowName , startFileName, data):
        SaveFileName = QFileDialog.getSaveFileName(self, WindowName, startFileName, "All Files (*);;Text Files (*.txt)")

        if SaveFileName:
            SaveFileName = SaveFileName[0]
            if SaveFileName[-4:] == '.txt':
                pass
            else:
                SaveFileName = str(SaveFileName) + '.txt'
        else:
            return

        if isinstance(data, (np.ndarray, np.generic)):
            np.savetxt(SaveFileName, data)
        else:
            file = open(SaveFileName, 'w+')
            file.write(data)
            file.close()

    def delete_pixel(self):
        self.SelectDataset()
        for j in self.selectedDatasetNumber:
            controll_delete_parameter = True
            while controll_delete_parameter == True:
                self.selectedPoint, = self.ax.plot(self.data[j][0][0], self.data[j][1][0], 'o', ms=12, alpha=0.4, color='yellow', visible=True)  #Yellow point to mark selected Data points
                pickDP = DataPointPicker(self.Spektrum[j], self.selectedPoint, 0)
                a = pickDP.lastind
                controll_delete_parameter = pickDP.controll_delete_parameter
                self.selectedPoint.set_visible(False)
                self.ax.figure.canvas.draw()
                self.data[j][0] = np.delete(self.data[j][0], a)
                self.data[j][1] = np.delete(self.data[j][1], a)
                self.Spektrum[j].set_data(self.data[j][0], self.data[j][1])
                self.fig.canvas.draw()
                controll_delete_parameter = pickDP.controll_delete_parameter
            else:
                self.setFocus()
                return

    ### Deletes data point with number 630+n*957, because this pixel is broken in CCD detector of LabRam
    def delete_datapoint(self):
        self.SelectDataset()
        for j in self.selectedDatasetNumber:
            a = 629
            grenze = 6
            controll_delete_parameter = True        #Parameter to controll if data point should be deleted
            self.mw.show_statusbar_message('Following data points of {} were deleted'.format(self.data[j][2]), 3000)
            while a <= len(self.data[j][0]):
                b = np.argmin(self.data[j][1][a-grenze:a+grenze])
                if b == 0 or b == 12:
                    QMessageBox.about(self, "Title", 
                        "Please select this data point manually (around %d in the data set %s)"%(self.data[j][0][a], self.data[j][2]))
                    self.selectedPoint, = self.ax.plot(self.data[j][0][a], self.data[j][1][a], 'o', ms=12, alpha=0.4, color='yellow', visible=False)  #Yellow point to mark selected Data points
                    pickDP = DataPointPicker(self.Spektrum[j], self.selectedPoint, a) 
                    a = pickDP.lastind
                    controll_delete_parameter = pickDP.controll_delete_parameter
                    self.selectedPoint.set_visible(False)
                    self.ax.figure.canvas.draw()     
                else:
                    a = a + b - grenze
                
                if controll_delete_parameter == True:
                    print(self.data[j][0][a], self.data[j][1][a])
                    #self.table.removeRow(a)
                    self.data[j][0] = np.delete(self.data[j][0], a)
                    self.data[j][1] = np.delete(self.data[j][1], a)
                else:
                    pass
                a = a + 957
                  
            self.Spektrum[j].set_data(self.data[j][0], self.data[j][1])            
            self.setFocus() 
            self.fig.canvas.draw()

            ### Save data without defective data points ###
            startFileDirName = os.path.dirname(self.data[j][3])
            startFileName = startFileDirName + '/' + self.data[j][2]
            save_data = [self.data[j][0], self.data[j][1]]
            save_data = np.transpose(save_data)
            self.save_to_file('Save data without deleted data points in file', startFileName, save_data)

    def normalize(self):
        self.SelectDataset()
        for n in self.selectedDatasetNumber:
            self.data[n][1] = self.data[n][1]/numpy.amax(self.data[n][1])
            self.Spektrum[n].set_data(self.data[n][0], self.data[n][1])
            self.fig.canvas.draw()
            ### Save normalized data ###
            (fileBaseName, fileExtension) = os.path.splitext(self.data[n][2])
            startFileDirName = os.path.dirname(self.data[n][3])
            startFileBaseName = startFileDirName + '/' + fileBaseName
            startFileName = startFileBaseName + '_norm.txt'
            save_data = [self.data[n][0], self.data[n][1]]
            save_data = np.transpose(save_data)
            self.save_to_file('Save normalized data in file', startFileName, save_data)

    def get_start_values(self):
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
            for j in range(ni, ni+int(val)):
                ni += 1
                layout1.addWidget(QtWidgets.QLabel('{}. {}'.format(j+1, key)))
                layout2.addWidget(QtWidgets.QLabel(''))

                position.append(QtWidgets.QLineEdit())
                layout1.addWidget(position[j])
                position[j].setText('3250')
                layout2.addWidget(QtWidgets.QLabel(r'Position in cm^-1'))

                intensity.append(QtWidgets.QLineEdit())
                layout1.addWidget(intensity[j])
                intensity[j].setText('150')
                layout2.addWidget(QtWidgets.QLabel('Intensity'))

                FWHM.append(QtWidgets.QLineEdit())
                layout1.addWidget(FWHM[j])
                FWHM[j].setText('300')
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
        parameter = [float(background.text())]               #Background
        for key in self.n_fit_fct.keys():
            for j in range(self.n_fit_fct[key]):
                parameter.append(float(position[j].text()))      #Peak position in cm^-1
                parameter.append(float(intensity[j].text()))     #Intensity
                parameter.append(float(FWHM[j].text()))          #FWHM
                if key == 'Breit-Wigner-Fano':
                    parameter.append(float(BWF_parmeter[j].text()))
        return parameter

    def fit_single_peak(self, q):
        self.SelectDataset()
        if self.selectedDatasetNumber != []:
            x_min, x_max = self.SelectArea()
            self.n_fit_fct[q.text()] = 1
            p_start = self.get_start_values()
        else:
            return

        for j in self.selectedDatasetNumber:
            xs = self.Spektrum[j].get_xdata()
            ys = self.Spektrum[j].get_ydata()
            x = xs[np.where((xs > x_min) & (xs < x_max))]
            y = ys[np.where((xs > x_min) & (xs < x_max))]

            popt, pcov = curve_fit(self.functions.FctSumme, x, y, p0=p_start)  # , bounds=([0, 500], [200, 540]))
            x1 = np.linspace(min(x), max(x), 1000)
            self.ax.plot(x1, self.functions.FctSumme(x1, *popt), '-r')
            self.fig.canvas.draw()

            print('\n {} {}'.format(self.Spektrum[j].get_label(), q.text()))
            parmeter_name = ['Background', r'Raman Shift in cm^-1', 'Intensity', 'FWHM', 'additional Parameter']
            print_param = []
            for idx, p in enumerate(popt):
                print_param.append([parmeter_name[idx], p])
            print(tabulate(print_param, headers=['Parameters', 'Values']))

        self.n_fit_fct = dict.fromkeys(self.n_fit_fct, 0)

    def fit_peaks(self):
        self.SelectDataset()
        if self.selectedDatasetNumber != []:
            x_min, x_max = self.SelectArea()
            fitdialog = FitOptionsDialog(self)
            p_start = fitdialog.p_start
            boundaries = fitdialog.p_bound
            self.n_fit_fct = fitdialog.n_fit_fct

        for n in self.selectedDatasetNumber:
            xs = self.Spektrum[n].get_xdata()
            ys = self.Spektrum[n].get_ydata()
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

            ### Plot the Fit Data ###
            x1 = np.linspace(min(x), max(x), 1000)
            self.ax.plot(x1, self.functions.FctSumme(x1, *popt), '-r')

            aL = self.n_fit_fct['Lorentz']
            aG = self.n_fit_fct['Gauss']
            for key in self.n_fit_fct.keys():
                for i in range(self.n_fit_fct[key]):
                    if key == 'Lorentz':
                        y_fit = popt[0] + self.functions.LorentzFct(x1, popt[3*i+1], popt[3*i+2], popt[3*i+3])
                    elif key == 'Gauss':
                        y_fit = popt[0] + self.functions.GaussianFct(x1, popt[3*(i+aL)+1], popt[3*(i+aL)+2], popt[3*(i+aL)+3])
                    elif key == 'Breit-Wigner-Fano':
                        y_fit = popt[0] + self.functions.BreitWignerFct(x1, popt[4*i+3*(aL+aG)+1], popt[4*i+3*(aL+aG)+2], popt[4*i+3*(aL+aG)+3], popt[4*i+3*(aL+aG)+4])
                    self.ax.plot(x1, y_fit, '--g')

            self.fig.canvas.draw()

            #Calculate Errors and R square
            perr = np.sqrt(np.diag(pcov))
            residuals = y - self.functions.FctSumme(x, *popt)
            ss_res = numpy.sum(residuals**2)
            ss_tot = numpy.sum((y - numpy.mean(y))**2)
            r_squared = 1 - (ss_res / ss_tot)

            # bring data into printable form
            data_table = [['Background', popt[0], perr[0]]]
            data_table.append(['', '', ''])
            a = 1

            for key in self.n_fit_fct.keys():
                for j in range(self.n_fit_fct[key]):
                    data_table.append(['{} {}'.format(key, j+1)])
                    data_table.append(['Raman Shift in cm-1', popt[a], perr[a]])
                    data_table.append(['Peak height in cps', popt[a+1], perr[a+1]])
                    data_table.append(['FWHM in cm-1', popt[a+2], perr[a+2]])
                    if key != 'Breit-Wigner-Fano':
                        a += 3
                    else:
                        data_table.append(
                            ['BWF Coupling Coefficient', popt[a+3], perr[a+3]])
                        a += 4
                    data_table.append(['', '', ''])
            print('\n {}'.format(self.Spektrum[n].get_label()))
            print(r'R^2={:.4f}'.format(r_squared))
            print(tabulate(data_table, headers=['Parameters', 'Values', 'Errors']))

        self.n_fit_fct = dict.fromkeys(self.n_fit_fct, 0)

    def DefineArea(self):
        self.SelectDataset()
        for n in self.selectedDatasetNumber:
            spct = self.Spektrum[n]
            xs = spct.get_xdata()
            ys = spct.get_ydata()
            x_min, x_max = self.SelectArea()
            x = xs[np.where((xs > x_min)&(xs < x_max))]
            y = ys[np.where((xs > x_min)&(xs < x_max))]

            self.data.append([x, y, '{}_cut'.format(spct.get_label()), self.selectedData[0][3]])
            self.Spektrum.append(self.ax.plot(x, y, label='{}_cut'.format(spct.get_label()), picker=5))

    def SelectArea(self):
        self.ax.autoscale(False)
        y_min, y_max = self.ax.get_ylim()
        x_min, x_max = self.ax.get_xlim()
        line1, = self.ax.plot([x_min, x_min], [y_min, y_max], 'r-', lw=1)
        line2, = self.ax.plot([x_max, x_max], [y_min, y_max], 'r-', lw=1)
        self.fig.canvas.draw()
        self.mw.show_statusbar_message('Left click shifts limits, Right click  them', 4000)
        linebuilder1 = LineBuilder(line1)
        x_min = linebuilder1.xs  #lower limit
        linebuilder2 = LineBuilder(line2)
        x_max = linebuilder2.xs  #upper limit
        line1.remove()
        line2.remove()
        self.fig.canvas.draw()
        self.ax.autoscale(True)
        return x_min, x_max
	
    def menu_baseline_als(self):
        self.SelectDataset()
        x_min, x_max = self.SelectArea()
        p_start = '0.001'
        lam_start = '10000000'
        for n in self.selectedDatasetNumber:
            spct = self.Spektrum[n]
            xs = spct.get_xdata()
            ys = spct.get_ydata()

            x = xs[np.where((xs > x_min)&(xs < x_max))]
            y = ys[np.where((xs > x_min)&(xs < x_max))]

            self.Dialog_BaselineParameter = QDialog()
            layout = QtWidgets.QGridLayout()

            p_edit = QtWidgets.QLineEdit()
            layout.addWidget(p_edit, 0, 0)
            p_edit.setText(p_start)
            p_label = QtWidgets.QLabel('p')
            layout.addWidget(p_label, 0, 1)

            lam_edit = QtWidgets.QLineEdit()
            layout.addWidget(lam_edit, 1, 0)
            lam_edit.setText(lam_start)
            lam_label = QtWidgets.QLabel('lambda')
            layout.addWidget(lam_label, 1, 1)

            p = float(p_edit.text())
            lam = float(lam_edit.text())
            xb,yb,zb = self.baseline_als(x, y, p, lam)
            self.baseline,    = self.ax.plot(xb, zb, 'c--', label = 'baseline ({})'.format(spct.get_label()))
            self.blcSpektrum, = self.ax.plot(xb, yb, 'c-', label = 'baseline-corrected ({})'.format(spct.get_label()))
            self.fig.canvas.draw()

            self.finishbutton = QPushButton('Ok', self)
            self.finishbutton.setCheckable(True)
            self.finishbutton.setToolTip('Are you happy with the start parameters? \n Close the dialog window and save the baseline!')
            self.finishbutton.clicked.connect(lambda: self.baseline_als_call(x, y, float(p_edit.text()), float(lam_edit.text()), spct))
            layout.addWidget(self.finishbutton, 2, 0)

            self.closebutton = QPushButton('Close', self)
            self.closebutton.setCheckable(True)
            self.closebutton.setToolTip('Closes the dialog window and baseline is not saved.')
            self.closebutton.clicked.connect(lambda: self.baseline_als_call(x, y, float(p_edit.text()), float(lam_edit.text()), spct))
            layout.addWidget(self.closebutton, 2, 1)

            applybutton = QPushButton('Apply', self)
            applybutton.setToolTip('Do you want to try the fit parameters? \n Lets do it!')
            applybutton.clicked.connect(lambda: self.baseline_als_call(x, y, float(p_edit.text()), float(lam_edit.text()), spct))
            layout.addWidget(applybutton, 2, 2)

            self.Dialog_BaselineParameter.setLayout(layout)
            self.Dialog_BaselineParameter.setWindowTitle("Baseline Parameter")
            self.Dialog_BaselineParameter.setWindowModality(Qt.ApplicationModal)
            self.Dialog_BaselineParameter.exec_()
            p_start = p_edit.text()
            lam_start = lam_edit.text()
    
    def baseline_als_call(self, x, y, p, lam, spct):
        self.blcSpektrum.remove()
        self.baseline.remove()
        name = spct.get_label()
        if self.closebutton.isChecked():
            self.Dialog_BaselineParameter.close()
        elif self.finishbutton.isChecked():
            xb, yb, zb = self.baseline_als(x, y, p, lam)
            self.baseline,    = self.ax.plot(xb, zb, 'c--', label = 'baseline ({})'.format(name))
            self.Spektrum.append(self.ax.plot(xb, yb, 'c-', label = 'baseline-corrected ({})'.format(name)[0]))
            
            ### Save background-corrected data ###
            (fileBaseName, fileExtension) = os.path.splitext(name)
            startFileDirName = os.path.dirname(self.selectedData[0][3])
            startFileBaseName = startFileDirName + '/' + fileBaseName
            startFileName = startFileBaseName + '_backgroundCorr.txt'
            save_data = [xb, yb, zb, x, y]
            save_data = np.transpose(save_data)
            self.save_to_file('Save background-corrected data in file', startFileName, save_data)
            
            ### Append data ###        
            self.data.append([xb, yb, fileBaseName+'_backgroundCorr', startFileName, '-', 0])
            self.Dialog_BaselineParameter.close()
        else:
            xb, yb, zb = self.baseline_als(x, y, p, lam)
            self.baseline,    = self.ax.plot(xb, zb, 'c--', label='baseline ({})'.format(name))
            self.blcSpektrum, = self.ax.plot(xb, yb, 'c-', label='baseline-corrected ({})'.format(name))
        self.fig.canvas.draw()

    # Baseline correction 
    # based on: "Baseline Correction with Asymmetric Least SquaresSmoothing" from Eilers and Boelens
    # also look at: https://stackoverflow.com/questions/29156532/python-baseline-correction-library
    def baseline_als(self, x, y, p, lam):
        niter = 10
        #p = 0.001   			#asymmetry 0.001 <= p <= 0.1 is a good choice     recommended from Eilers and Boelens for Raman: 0.001    recommended from Simon: 0.0001
        #lam = 10000000			#smoothness 10^2 <= lambda <= 10^9                     recommended from Eilers and Boelens for Raman: 10^7      recommended from Simon: 10^7
        L = len(x)
        D = sparse.csc_matrix(np.diff(np.eye(L), 2))
        w = np.ones(L)
        for i in range(niter):
            W = sparse.spdiags(w, 0, L, L)
            Z = W + lam * D.dot(D.transpose())
            z = spsolve(Z, w*y)
            w = p * (y > z) + (1-p) * (y < z)
        y = y-z
        
#        self.baseline,    = self.ax.plot(x, z, 'c--', label = 'baseline (' + self.selectedData[0][2] + ')')
#        self.blcSpektrum, = self.ax.plot(x, y, 'c-', label = 'baseline-corrected '+ self.selectedData[0][2])
#        self.fig.canvas.draw()
        return x, y, z          #x - Raman Shift, y - background-corrected Intensity-values, z - background
	
    # Partially based on Christian's Mathematica Notebook
    # Fitroutine for D and G bands in spectra of carbon compounds
    def fit_D_G(self):
        # Select which data set will be fitted
        self.SelectDataset()
        #if self.selectedData == []:
        #    return

        #Limits for Backgroundcorrection
        x_min =  200
        x_max = 4000

        # parameter for background-correction
        p = 0.0001  # asymmetry 0.001 <= p <= 0.1 is a good choice     recommended from Eilers and Boelens for Raman: 0.001    recommended from Simon: 0.0001
        lam = 10000000  # smoothness 10^2 <= lambda <= 10^9            recommended from Eilers and Boelens for Raman: 10^7     recommended from Simon: 10^7

        # Limits for FitProcess
        # define fitarea
        x_min_fit = 850
        x_max_fit = 2000

        #Fitprocess
        #D-Band: Lorentz
        #G-Band: BreitWignerFano
        self.n_fit_fct['Lorentz'] = 1   # number of Lorentzian
        self.n_fit_fct['Gauss']   = 0   # number of Gaussian
        self.n_fit_fct['Breit-Wigner-Fano']     = 1   # number of Breit-Wigner-Fano
        aL  = self.n_fit_fct['Lorentz']
        aG  = self.n_fit_fct['Gauss']
        aB  = self.n_fit_fct['Breit-Wigner-Fano']
        aLG = self.n_fit_fct['Lorentz'] + self.n_fit_fct['Gauss']

        # Fit parameter: initial guess and boundaries

        pStart = []
        pBoundsLow = []
        pBoundsUp = []
        inf = np.inf

        pStart.append((1360, 80, 50))  # Lorentz (D-Bande)
        pBoundsLow.append((1335, 0, 0))
        pBoundsUp.append((1385, inf, inf))

        # pStart.append((1165,   2,   5))         #Gaussian 0
        # pBoundsLow.append((1150, 0, 0))
        # pBoundsUp.append((1180, inf, inf))
        # pStart.append((1238,   2,   5))         #Gaussian 1
        # pBoundsLow.append((1223, 0, 0))
        # pBoundsUp.append((1253, inf, inf))
        # pStart.append((1435, 20, 80))           #Gaussian 2
        # pBoundsLow.append((1420, 0, 0))
        # pBoundsUp.append((1455, inf, inf))
        pStart.append((1600, 200, 50, -10))  # Breit-Wigner-Fano
        pBoundsLow.append((0, 0, 0, -inf))
        pBoundsUp.append((inf, inf, inf, 0))

        p_start = []
        p_bounds_low = []
        p_bounds_up = []
        p_start.extend([0])
        p_bounds_low.extend([-10])
        p_bounds_up.extend([10])
        for i in range(len(pStart)):
            p_start.extend(pStart[i])
            p_bounds_low.extend(pBoundsLow[i])
            p_bounds_up.extend(pBoundsUp[i])

        # Limits Fit parameter
        p_bounds = ((p_bounds_low, p_bounds_up))

        # iterate through all selected data sets
        for n in self.selectedDatasetNumber:
            x = self.Spektrum[n].get_xdata()
            y = self.Spektrum[n].get_ydata()
      
            #Limit data to fit range
            working_x = x[np.where((x > x_min)&(x < x_max))]
            working_y = y[np.where((x > x_min)&(x < x_max))]

            xb, yb, zb = self.baseline_als(working_x, working_y, p, lam)
            self.baseline,    = self.ax.plot(xb, zb, 'c--', label = 'baseline ({})'.format(self.Spektrum[n].get_label()))
            self.blcSpektrum, = self.ax.plot(xb, yb, 'c-', label = 'baseline-corrected ({})'.format(self.Spektrum[n].get_label()))
            self.fig.canvas.draw()

            #limit data to fitarea
            working_x = xb[np.where((xb > x_min_fit)&(xb < x_max_fit))]
            working_y = yb[np.where((xb > x_min_fit)&(xb < x_max_fit))]

            popt, pcov = curve_fit(self.functions.FctSumme, working_x, working_y, p0 = p_start, bounds = p_bounds, absolute_sigma = False)

            ### Plot the Fit Data ###
            x1  = np.linspace(min(working_x), max(working_x), 3000)
            y_L = []
            for j in range(aL):
                y_L.append(np.array(popt[0] + self.functions.LorentzFct(x1, popt[1+3*j], popt[2+3*j], popt[3+3*j])))
            y_G = []
            for j in range(aG):
                y_G.append(np.array(popt[0] + self.functions.GaussianFct(x1, popt[1+3*aL+3*j], popt[2+3*aL+3*j], popt[3+3*aL+3*j])))
            y_BWF = []
            for j in range(aB):
                y_BWF.append(np.array(popt[0] + self.functions.BreitWignerFct(x1, popt[4*j+3*aLG+1], popt[4*j+3*aLG+2], popt[4*j+3*aLG+3], popt[4*j+3*aLG+4])))
            y_Ges = np.array(self.functions.FctSumme(x1, *popt))
            self.ax.plot(x1, y_Ges, '-r')
            for j in y_G:
                self.ax.plot(x1, j, '--g')
            for j in y_L:
                self.ax.plot(x1, j, '--g')
            for j in y_BWF:
                self.ax.plot(x1, j, '--g')

            self.fig.canvas.draw()
        
            #### Calculate Errors and R square ###
            perr = np.sqrt(np.diag(pcov))

            residuals = working_y - self.functions.FctSumme(working_x, *popt)
            ss_res = numpy.sum(residuals**2)
            ss_tot = numpy.sum((working_y - numpy.mean(working_y))**2)
            r_squared = 1 - (ss_res / ss_tot)
        
            #### Calculate Peak-Areas and there Errors ####
            r,a0,h,xc,b,Q = syp.symbols('r a0 h xc b Q', real=True)

            #Anti-Derivative of Lorentzian Function
            #F_L = syp.integrate(a0 + h/(1 + (2*(r - xc)/b)**2), (r, x_min, x_max))
            #F_L = syp.simplify(F_L)
            #F_L = syp.trigsimp(F_L)
            F_L = (x_max-x_min)*a0 - b*h*syp.atan(2*(xc - x_max)/b)/2 + b*h*syp.atan(2*(xc - x_min)/b)/2
            Flam_L = lambdify([a0, xc, h, b], F_L)

            #Anti-Derivative of Gaussian Function
            #f_G = (a0 + h*syp.exp(-4*syp.log(2)*((r-xc)/b)*((r-xc)/b)))
            #F_G = syp.integrate(f_G, (r, xmin, xmax))
            #F_G = syp.simplify(F_G)
            #F_G = syp.trigsimp(F_G)
            F_G = (4*a0*(x_max - x_min)*syp.sqrt(syp.log(2)) - syp.sqrt(syp.pi)*b*h*syp.erf(2*(xc - x_max)*syp.sqrt(syp.log(2))/b) +
                  syp.sqrt(syp.pi)*b*h*syp.erf(2*(xc - x_min)*syp.sqrt(syp.log(2))/b))/(4*syp.sqrt(syp.log(2)))
            Flam_G = lambdify([a0, xc, h, b], F_G)

            #Anti-Derivative of Breit-Wigner-Fano Function
            #f_B = (a0 + BreitWignerFct(r, xc, h, b, Q))
            #F_B = syp.integrate(f_B, (r, x_min, x_max))
            #F_B = syp.simplify(F_B)
            #F_B = syp.trigsimp(F_B)
            F_B = (Q*b*h*(syp.log(b**2/4 + xc**2 - 2*xc*x_max + x_max**2) - syp.log(b**2/4 + xc**2 - 2*xc*x_min + x_min**2)) -
                  b*h*(Q - 1)*(Q + 1)*syp.atan(2*(xc - x_max)/b) + b*h*(Q - 1)*(Q + 1)*syp.atan(2*(xc - x_min)/b) + 2*x_max*(Q**2*a0 + h) - 2*x_min*(Q**2*a0 + h))/(2*Q**2)
            Flam_B = lambdify([a0, xc, h, b, Q], F_B)

            #Peak Area
            I_L = []
            for j in range(aL):
                I_L.append(Flam_L(popt[0], popt[1+3*j], popt[2+3*j], popt[3+3*j]))

            I_G = []
            for j in range(aG):
                I_G.append(Flam_G(popt[0], popt[1+3*aL+3*j], popt[2+3*aL+3*j], popt[3+3*aL+3*j]))

            I_BWF = []
            for j in range(aB):
                I_BWF.append(Flam_B(popt[0], popt[4*j+3*aLG+1], popt[4*j+3*aLG+2], popt[4*j+3*aLG+3], popt[4*j+3*aLG+4]))

            #Calculate partial derivates
            dF_La0 = syp.diff(F_L, a0)
            dF_Lh  = syp.diff(F_L, h)
            dF_Lxc = syp.diff(F_L, xc)
            dF_Lb  = syp.diff(F_L, b)

            dF_Ga0 = syp.diff(F_G, a0)
            dF_Gh  = syp.diff(F_G, h)
            dF_Gxc = syp.diff(F_G, xc)
            dF_Gb  = syp.diff(F_G, b)

            dF_Ba0 = syp.diff(F_B, a0)
            dF_Bh  = syp.diff(F_B, h)
            dF_Bxc = syp.diff(F_B, xc)
            dF_Bb  = syp.diff(F_B, b)
            dF_BQ  = syp.diff(F_B, Q)

            #Calculate Error of Peak Area with law of error propagation
            da0,dh,dxc,db,dQ = syp.symbols('da0 dh dxc db dQ', real=True)

            DeltaF_L = syp.Abs(dF_La0)*da0 + syp.Abs(dF_Lh)*dh + syp.Abs(dF_Lxc)*dxc + syp.Abs(dF_Lb)*db
            DeltaFlam_L = lambdify([a0, da0, xc, dxc, h, dh, b, db], DeltaF_L)
            I_L_err = []
            for j in range(aL):
                I_L_err.append(DeltaFlam_L(popt[0], perr[0], popt[3*j+1], perr[3*j+1], popt[3*j+2], perr[3*j+2], popt[3*j+3], perr[3*j+3]))

            DeltaF_G = syp.Abs(dF_Ga0)*da0 + syp.Abs(dF_Gh)*dh + syp.Abs(dF_Gxc)*dxc + syp.Abs(dF_Gb)*db
            DeltaFlam_G = lambdify([a0, da0, xc, dxc, h, dh, b, db], DeltaF_G)
            I_G_err = []
            for j in range(aG):
                I_G_err.append(DeltaFlam_G(popt[0], perr[0], popt[3*j+3*aL+1], perr[3*j+3*aL+1], popt[3*j+3*aL+2], perr[3*j+3*aL+2], popt[3*j+3*aL+3], perr[3*j+3*aL+3]))

            DeltaF_B = syp.Abs(dF_Ba0)*da0 + syp.Abs(dF_Bh)*dh + syp.Abs(dF_Bxc)*dxc + syp.Abs(dF_Bb)*db + syp.Abs(dF_BQ)*dQ
            DeltaFlam_B = lambdify([a0, da0, xc, dxc, h, dh, b, db, Q, dQ], DeltaF_B)
            I_BWF_err = []
            for j in range(aB):
                I_BWF_err.append(DeltaFlam_B(popt[0], perr[0], popt[4*j+3*aLG+1], perr[4*j+3*aLG+1], popt[4*j+3*aLG+2], perr[4*j+3*aLG+2], popt[4*j+3*aLG+3], perr[4*j+3*aLG+3], popt[4*j+3*aLG+4], perr[4*j+3*aLG+4]))

            ### Estimate Cluster size ###
            #ID/IG = C(lambda)/L_a
            #mit C(514.5 nm) = 44 Angstrom
            ID = I_L[0]
            IG = I_BWF[0]
            ID_err = I_L_err[0]
            IG_err = I_BWF_err[0]
            L_a = 4.4 * IG/ID
            L_a_err = L_a*(ID_err/ID + IG_err/IG)
            ratio = ID/IG
            ratio_err = ratio*(ID_err/ID + IG_err/IG)

            # bring data into printable form
            data_table = [['Background', popt[0], perr[0]]]
            data_table.append(['','',''])
            for j in range(aL):
                data_table.append(['Lorentz %i'%(j+1)])
                data_table.append(['Raman Shift in cm-1', popt[j*3+1], perr[j*3+1]])
                data_table.append(['Peak height in cps', popt[j*3+2], perr[j*3+2]])
                data_table.append(['FWHM in cm-1', popt[j*3+3], perr[j*3+3]])
                data_table.append(['Peak area in cps*cm-1', I_L[j], I_L_err[j]])
                data_table.append(['','',''])
            for j in range(aG):
                data_table.append(['Gauss %i'%(j+1)])
                data_table.append(['Raman Shift in cm-1', popt[j*3+3*aL+1], perr[j*3+3*aL+1]])
                data_table.append(['Peak height in cps', popt[j*3+3*aL+2], perr[j*3+3*aL+2]])
                data_table.append(['FWHM in cm-1', popt[j*3+3*aL+3], perr[j*3+3*aL+3]])
                data_table.append(['Peak area in cps*cm-1', I_G[j], I_G_err[j]])
                data_table.append(['','',''])
            for j in range(aB):
                data_table.append(['BWF %i'%(j+1)])
                data_table.append(['Raman Shift in cm-1', popt[j*3+3*aLG+1], perr[j*3+3*aLG+1]])
                data_table.append(['Peak height in cps', popt[j*3+3*aLG+2], perr[j*3+3*aLG+2]])
                data_table.append(['FWHM in cm-1', popt[j*3+3*aLG+3], perr[j*3+3*aLG+3]])
                data_table.append(['BWF Coupling Coefficient', popt[j*3+3*aLG+4], perr[j*3+3*aLG+4]])
                data_table.append(['Peak area in cps*cm-1', I_BWF[j], I_BWF_err[j]])
                data_table.append(['','',''])

            data_table.append(['Cluster Size in nm', L_a, L_a_err])
            data_table.append(['I_D/I_G', ratio, ratio_err])

            save_data = r'R^2=%.6f \n'%r_squared + 'Lorentz 1 = D-Bande, BWF (Breit-Wigner-Fano) 1 = G-Bande \n' + tabulate(data_table, headers = ['Parameters', 'Values', 'Errors'])
            print('\n')
            print(self.Spektrum[n].get_label())
            print(save_data)

            (fileBaseName, fileExtension) = os.path.splitext(self.Spektrum[n].get_label())
            startFileDirName = os.path.dirname(self.selectedData[0][3])
            file_cluster = open(startFileDirName + "/Clustersize.txt", "a")
            file_cluster.write('\n'+str(fileBaseName) + '   %.4f'%L_a + '   %.4f'%L_a_err)
            file_cluster.close()

            ### Save the fit parameter ###
            startFileBaseName = startFileDirName + '/' + fileBaseName
            startFileName = startFileBaseName + '_fitpara.txt'
            self.save_to_file('Save fit parameter in file', startFileName, save_data)

            ### Save the Fit data ###
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
            self.save_to_file('Save fit data in file', startFileName, save_data)

            ### Save background-corrected data ###
            startFileName = startFileBaseName + '_backgroundCorr.txt'
            save_data = [xb, yb, zb]
            save_data = np.transpose(save_data)
            self.save_to_file('Save background-corrected data in file', startFileName, save_data)

    def ratio_H2O_sulfuroxyanion(self):
        # this function calculates the intensity ratio of different peaks
        # simply by getting the maximum of a peak

        self.SelectDataset()
        save_data = []
        for n in self.selectedDatasetNumber:
            spct = self.Spektrum[n]
            xs = spct.get_xdata()
            ys = spct.get_ydata()

            ### get height of water peak
            x_min, x_max = [3000, 3750]
            y = ys[np.where((xs > x_min) & (xs < x_max))]
            water_peak = max(y)

            ### get height of hydrogensulfate peak (at ca. 1050cm-1)
            x_min, x_max = [1040, 1060]
            y = ys[np.where((xs > x_min) & (xs < x_max))]
            hydrogensulfate_peak = max(y)

            ### get height of sulfate peak (at ca. 980cm-1)
            x_min, x_max = [970, 990]
            y = ys[np.where((xs > x_min) & (xs < x_max))]
            sulfate_peak = max(y)

            ### get height of peroxydisulfate peak (at ca. 835cm-1)
            x_min, x_max = [825, 835]
            y = ys[np.where((xs > x_min) & (xs < x_max))]
            peroxydisulfate_peak = max(y)

            ### get height of peroxydisulfate peak (at ca. 1075cm-1)
            x_min, x_max = [1060, 1085]
            y = ys[np.where((xs > x_min) & (xs < x_max))]
            peroxydisulfate_peak_2 = max(y)

            # calculate ratios

            r_sulfate_water = sulfate_peak/water_peak
            r_peroxydisulfate_water = peroxydisulfate_peak/water_peak
            r_peroxydisulfate_water_2 = peroxydisulfate_peak_2/water_peak
            r_hydrogensulfate_water = hydrogensulfate_peak/water_peak

            save_data.append([r_sulfate_water, r_peroxydisulfate_water, r_peroxydisulfate_water_2, r_hydrogensulfate_water])

            #print(sulfate_peak, hydrogensulfate_peak, peroxydisulfate_peak, peroxydisulfate_peak_2, water_peak)


        filename = 'ratios.txt'
        filepath = os.path.dirname(self.selectedData[0][3])
        save_data = np.array(save_data)
        print(save_data)

        ### Save the ratios ###
        filename = '{}/{}'.format(filepath, filename)
        self.save_to_file('Save calculated ratios in file', filename, save_data)



    ########## Functions of toolbar ##########
    def check_if_line_was_removed(self):
        lines = self.ax.get_lines()
        if len(lines) != len(self.data):
            line_ydata = []
            not_deleted = []
            for line in lines:
                line_ydata.append(line.get_ydata())
            for d in self.data:
                for lydata in line_ydata:
                    if (lydata == d[1]).all():
                        not_deleted.append(d[2])

            for j in range(len(self.data)):
                if self.data[j][2] in not_deleted:
                    pass
                else:
                    self.data.pop(j)
                    self.Spektrum.pop(j)
                    return
        else:
            return

    def scale_spectrum(self):
        self.check_if_line_was_removed()
        self.SelectDataset(True)
        for n in self.selectedDatasetNumber:
            ys = self.Spektrum[n].get_ydata()
            self.cid_scale = self.fig.canvas.mpl_connect('button_release_event', self.scale_click)
            self.ax.figure.canvas.start_event_loop(timeout=10000)
            ys = ys*self.scale_factor
            self.data[n][1] = ys
            self.Spektrum[n].set_ydata(ys)
            self.fig.canvas.draw()
            
    def scale_click(self, event):
        if event.button == 1:
            for n in self.selectedDatasetNumber:
                xs = self.Spektrum[n].get_xdata()
                ys = self.Spektrum[n].get_ydata()
                x = event.xdata
                y = event.ydata
                ind = min(range(len(xs)), key=lambda i: abs(xs[i]-x))
                self.scale_factor = y/ys[ind]
                self.fig.canvas.mpl_disconnect(self.cid_scale)
                self.fig.canvas.stop_event_loop(self)
        else:
            pass

    def shift_spectrum(self):
        self.check_if_line_was_removed()
        self.SelectDataset(True)
        for n in self.selectedDatasetNumber:
            ys = self.Spektrum[n].get_ydata()
            self.cid_shift = self.fig.canvas.mpl_connect('button_release_event', self.shift_click)
            self.ax.figure.canvas.start_event_loop(timeout=10000)
            ys = ys + self.shift_factor
            self.data[n][1] = ys
            self.Spektrum[n].set_ydata(ys)
            self.fig.canvas.draw()

    def shift_click(self, event):
        if event.button == 1:
            for n in self.selectedDatasetNumber:
                xs = self.Spektrum[n].get_xdata()
                ys = self.Spektrum[n].get_ydata()
                x = event.xdata
                y = event.ydata
                ind = min(range(len(xs)), key=lambda i: abs(xs[i]-x))
                self.shift_factor = y - ys[ind]
                self.fig.canvas.mpl_disconnect(self.cid_shift)
                self.fig.canvas.stop_event_loop(self)
        else:
            pass

    def pick_points_for_arrow(self, event):
        self.selected_points.append([event.xdata, event.ydata])
        if len(self.selected_points) == 2:
            self.fig.canvas.mpl_disconnect(self.pick_arrow_points_connection)
            posA = self.selected_points[0]
            posB = self.selected_points[1]

            arrow = mpatches.FancyArrowPatch(posA, posB, mutation_scale=10, arrowstyle='-', picker=10)
            arrow.set_figure(self.fig)
            self.ax.add_patch(arrow)
            self.drawn_line.append(LineDrawer(arrow))
            self.fig.canvas.draw()

    def draw_line(self):
        self.selected_points = []
        self.pick_arrow_points_connection = self.fig.canvas.mpl_connect('button_press_event', self.pick_points_for_arrow)

    def pick_point_for_text(self, event):
        pos = [event.xdata, event.ydata]
        text = self.ax.annotate(r'''*''', pos, picker=5)
        self.inserted_text.append(InsertText(text))
        self.ax.add_artist(text)
        self.fig.canvas.mpl_disconnect(self.pick_text_point_connection)
        self.fig.canvas.draw()

    def insert_text(self):
        self.pick_text_point_connection = self.fig.canvas.mpl_connect('button_press_event', self.pick_point_for_text)

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
