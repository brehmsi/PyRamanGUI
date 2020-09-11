# Autor: Simon Brehm
import math
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.widgets as mwidgets
import matplotlib.backends.qt_editor._formlayout as formlayout
import numpy as np
import os
import pandas as pd
import pickle
import pylab
import random
import re
import scipy
import sympy as syp
import sys
import time

from collections import ChainMap
from matplotlib import *
from matplotlib.widgets import Slider, Button, RadioButtons
from matplotlib.figure import Figure
from matplotlib.backend_bases import MouseEvent
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.backends.qt_compat import QtCore, QtWidgets
from numpy import pi
from numpy.fft import fft, fftshift
from os.path import join as pjoin
from PyQt5 import QtGui, QtCore 
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSlot, QObject
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QVBoxLayout, QSizePolicy, QMessageBox, QPushButton, QCheckBox,
	QTableWidgetItem, QItemDelegate, QLineEdit, QPushButton, QWidget, QMenu, QAction, QDialog, QFileDialog, QInputDialog, QAbstractItemView)
from scipy import sparse, fftpack
from scipy.optimize import curve_fit
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve
from scipy.integrate import quad
from scipy.signal import (find_peaks, savgol_filter, argrelextrema)
from sympy.utilities.lambdify import lambdify, implemented_function
from tabulate import tabulate

import myfigureoptions  #see file 'myfigureoptions.py'
import mytoolbar

# This file essentially consists of three parts:
# 1. Main Window
# 2. Text Window
# 3. Spreadsheet
# 4. Plot

#####################################################################################################################################################
### 1. Main window
#####################################################################################################################################################
class MainWindow(QMainWindow):
    ''' Creating the main window '''
    updata_menu_signal = QtCore.pyqtSignal()

    def __init__(self, parent = None):
        super(MainWindow, self).__init__(parent)
        self.create_mainwindow()

        self.spreadsheet = {}                        # dictionary with spreadsheets
        self.plotwindow = {}                         # dictionary with plotwindows
        self.textwindow = {}                         # dictionary with textwindows
        self.count_ss = 0                            # number of spreadsheet windows (closed ones are included)
        self.count_p  = 0                            # number of plot windows (closed ones are included)
        self.count_t  = 0                            # number of text windows (closed ones are included)
        self.FileName = os.path.dirname(__file__)    # path of this python file
        self.pHomeRmn = None                         # path of Raman File

    def create_mainwindow(self):
        #Create the main window
        self.setWindowTitle('PyRaman')          # set window title
        self.mdi = QtWidgets.QMdiArea()         # widget for multi document interface area
        self.setCentralWidget(self.mdi)         # set mdi-widget as central widget
        self.create_menubar()

    def create_menubar(self):
        # create a menubar
        menu = self.menuBar()

        File = menu.addMenu('File')
        FileNew = File.addMenu('New')
        newSpreadSheet = FileNew.addAction('Spreadsheet', lambda: self.newSpreadsheet(None, None))
        newText = FileNew.addAction('Text', lambda: self.newTextWindow('', None))
        FileLoad = File.addAction('Open Project', self.open)        
        FileSaveAs = File.addAction('Save Project As ...', lambda: self.save('Save As'))
        FileSave = File.addAction('Save Project', lambda: self.save('Save'))

        medit = menu.addMenu('Edit')
        medit.addAction('Cascade')
        medit.addAction('Tiled')
        medit.triggered[QAction].connect(self.rearange)

    def open(self):
        # Load project in new MainWindow or in existing MW, if empty
        if self.spreadsheet == {} and self.plotwindow == {}:
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

        file = open(self.pHomeRmn, 'rb')            # open file and save content in variable 'v' with pickle 
        v = pickle.load(file)         
        file.close()  

        for key, val in v['Spreadsheet'].items():   # open all saved spreadsheets
            self.newSpreadsheet(val, key)

        for key, val in v['Plot-Window'].items():   # open all saved plotwindows
            plot_data = val[0]
            fig = val[1]
            pwtitle = key
            self.newPlot(plot_data, fig, pwtitle)  

        if 'Text-Window' in v.keys():
            for key, val in v['Text-Window'].items():
                self.newTextWindow(val, key)
        else:
            pass

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

        ss = {}                                         # creating new dictionary for spreadsheet containing 
        for key, val in self.spreadsheet.items():       # only data and name from spreadsheet,
            ss.update({key : val.d})                    # because spreadsheet cannot saved with pickle

        p  = {}                                         # creating new dictionary for plotwindow
        for key, val in self.plotwindow.items():
            p.update({key : (val.data, val.fig)})

        t  = {}                                         # creating new dictionary for plotwindow
        for key, val in self.textwindow.items():
            t.update({key : (val.text)})

        saveFileContent = {}                            # dictionary containing ss and p 
        saveFileContent.update({'Spreadsheet' : ss})
        saveFileContent.update({'Plot-Window' : p})
        saveFileContent.update({'Text-Window' : t})

        # Test if file can be saved
        saveControllParam = 0
        file = open(os.path.splitext(self.pHomeRmn)[0] + '_test' + 
                                    os.path.splitext(self.pHomeRmn)[1], 'wb')
        try: 
            pickle.dump(saveFileContent, file)
        except TypeError as e:
            print('TypeError \n Someting went wrong. The file is not saved \n' + str(e)) 
            saveControllParam = 1      
        file.close() 

        if saveControllParam == 0:
            file = open(self.pHomeRmn,'wb')
            try: 
                pickle.dump(saveFileContent, file)
            except TypeError as e:
                print('TypeError \n Someting went wrong. The file is not saved \n' + str(e))       
            file.close()
            os.remove(os.path.splitext(self.pHomeRmn)[0] + '_test' + 
                                    os.path.splitext(self.pHomeRmn)[1]) 
        else:
            saveControllParam = 0
            pass
   
    def rearange(self, q):
        # rearange open windows
        if q.text() == "cascade":
            self.mdi.cascadeSubWindows()

        if q.text() == "Tiled":
            self.mdi.tileSubWindows()

    def newTextWindow(self, txt, title):
        self.count_t = self.count_t+1
        a = self.count_t -1
        txttitle = title
        if txttitle == None:
            txttitle = 'Text-Window ' + str(self.count_t)

        self.textwindow[txttitle] = TextWindow(self, txt)
        newTxt = self.textwindow[txttitle]
        newTxt.setWindowTitle(txttitle)
        self.mdi.addSubWindow(newTxt)
        newTxt.show()
        newTxt.close_txt_signal.connect(self.close_text_window)

    def newSpreadsheet(self, ssd, title):
        ''' open new spreadsheet window 
        parameterr:
        ssd : data opened in spreadsheet
        title: window-title'''

        self.count_ss = self.count_ss+1
        a = self.count_ss -1
        sstitle = title

        if sstitle == None:
            sstitle = 'Spreadsheet-Window ' + str(self.count_ss)
        else:
            pass

        if ssd == None:
            ssd = {'data0' : (np.zeros(1000),'A', 'X', None), 'data1' : (np.zeros(1000),'B', 'Y', None)}  #Spreadsheet- Data (for start only zeros)
        else:
            pass

        self.spreadsheet[sstitle] = SpreadSheet(self, ssd)
        newSS = self.spreadsheet[sstitle]
        newSS.setWindowTitle(sstitle)
        self.mdi.addSubWindow(newSS)
        newSS.show()

        newSS.new_pw_signal.connect(lambda: self.newPlot(newSS.plot_data, None, None))
        newSS.add_pw_signal.connect(lambda pw_name: self.addPlot(pw_name, newSS.plot_data))
        newSS.close_ss_signal.connect(self.close_spreadsheet_window)

    def newPlot(self, plotData, fig, title):
        ''' Open new Plotwindow
        parameter:
        plotData: data, plotted in the new window
        fig: matplotlib.figure if already existing, otherwise None
        title: title of plotwindow
        '''
        b = self.count_p
        self.count_p = self.count_p + 1

        pwtitle = title
        if pwtitle == None:
            pwtitle = 'Plot-Window '+ str(self.count_p)
        else:
            pass
        self.plotwindow[pwtitle] = PlotWindow(plotData, fig, self)
        self.plotwindow[pwtitle].setWindowTitle(pwtitle)
        self.mdi.addSubWindow(self.plotwindow[pwtitle])
        self.plotwindow[pwtitle].show()

        self.updata_menu_signal.emit()
        self.plotwindow[pwtitle].change_window_title_signal.connect(self.change_plotwindow_title)
        self.plotwindow[pwtitle].close_p_signal.connect(self.close_plot_window)

    def addPlot(self, pw_name, plotData):
        # add spectrum to existing plotwindow
        for j in plotData:
            j[4] = self.plotwindow[pw_name].Spektrum[0].get_linestyle()
        self.plotwindow[pw_name].add_plot(plotData)

    def close_plot_window(self, pwtitle):
        # delete plotwindow and update menubar from spreadsheets after closing a plotwindow
        del self.plotwindow[pwtitle]
        self.updata_menu_signal.emit()  

    def close_spreadsheet_window(self, sstitle):
        # delete spreadsheet window
        del self.spreadsheet[sstitle]

    def close_text_window(self, txttitle):
        # delete spreadsheet window
        del self.textwindow[txttitle]

    def change_plotwindow_title(self, oldtitle, newtitle):
        # update menubar from spreadsheets after changing name of a plotwindow
        self.plotwindow[newtitle] = self.plotwindow.pop(oldtitle)
        self.updata_menu_signal.emit()

    def closeEvent(self, event):
        # close mainwindow
        close = QMessageBox()
        close.setWindowTitle('Quit')
        close.setText("You sure?")
        close.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        close = close.exec()

        if close == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

#####################################################################################################################################################
### 2. Text - Window
#####################################################################################################################################################

class TextWindow(QMainWindow):
    close_txt_signal = QtCore.pyqtSignal(str)
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

        ### 1. Menüpunkt: File ###
        fileMenu = self.menubar.addMenu('&File')
        fileMenu.addAction('Save Text', self.file_save)
        fileMenu.addAction('Load Text', self.load_file)

        ### 2. Menüpunkt: Edit
        editMenu = self.menubar.addMenu('&Edit')
        editMenu.addAction('Change Window Title', self.change_window_title)        

        self.show()

    def text_change(self):
        self.text = self.textfield.toPlainText()        

    def change_window_title(self):
        # Change title of the text window
        oldTitle = self.windowTitle()
        newTitle, ok = QInputDialog.getText(self, 'Text Input Dialog', 'Enter the new Window Title:')
        if ok:
            self.setWindowTitle(newTitle)
            self.mw.textwindow[newTitle] = self.mw.textwindow.pop(oldTitle)
        else:
            return

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
        close = close.exec()

        if close == QMessageBox.Yes:
            self.close_txt_signal.emit(self.windowTitle())
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
    return f'{chr(ord("A")+j)}{i+1}'

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
        self.value = 0 
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

        if (formula is None or formula == ''):
            self.value = self.wert 
            return

        currentreqs = set(cellre.findall(formula))

        name = cellname(self.row(), self.column())

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
        except NameError:
            print('Bitte keine Buchstaben eingeben')
            self.value = str(0.0)

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
    close_ss_signal = QtCore.pyqtSignal(str)

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

        self.mw.updata_menu_signal.connect(self.update_menubar)

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

    
    def create_menubar(self): 
    # create the menubar               
        self.menubar = self.menuBar()

        ### 1. Menüpunkt: File ###
        fileMenu = self.menubar.addMenu('&File')
        fileMenu.addAction('Save Data', self.file_save)
        fileMenu.addAction('Load Data', self.load_file)

        ### 2. Menüpunkt: Edit
        editMenu = self.menubar.addMenu('&Edit')
        editMenu.addAction('Change Window Title', self.change_window_title)
        editMenu.addAction('New Column', self.new_col)

        ### 3. Menüpunkt: Plot
        plotMenu = self.menubar.addMenu('&Plot')
        plotNew = plotMenu.addMenu('&New')
        plotNew.addAction('Line Plot', self.get_plot_data)
        plotNew.addAction('Dot Plot', self.get_plot_data)
        plotAdd = plotMenu.addMenu('&Add to')
        for j in self.mw.plotwindow.keys():
            plotAdd.addAction(j, self.get_plot_data)

        self.show()

    def update_menubar(self):
        self.menubar.clear()
        self.create_menubar()

    def create_col_header(self):
        headers = [self.d[j][1] + '(' + self.d[j][2] + ')' for j in self.d.keys()]
        self.table.setHorizontalHeaderLabels(headers)

        ### bei Rechts-Klick auf Header wird header_menu geöffnet ###
        self.headers = self.table.horizontalHeader()
        self.headers.setContextMenuPolicy(Qt.CustomContextMenu)
        self.headers.customContextMenuRequested.connect(self.show_header_context_menu)
        self.headers.setSelectionMode(QAbstractItemView.SingleSelection)

        ### bei Doppelklick auf Tabellenkopf wird rename_header geöffnet ###
        self.headerline = QtWidgets.QLineEdit()                         # Create
        self.headerline.setWindowFlags(QtCore.Qt.FramelessWindowHint)   # Hide title bar
        self.headerline.setAlignment(QtCore.Qt.AlignLeft)               # Set the Alignmnet
        self.headerline.setHidden(True)                                 # Hide it till its needed
        self.sectionedit = 0
        self.table.horizontalHeader().sectionDoubleClicked.connect(self.rename_header)
        self.headerline.editingFinished.connect(self.doneEditing)

    def rename_header(self, column):
        window_position = self.pos()
        # This block sets up the geometry for the line edit
        edit_geometry = self.headerline.geometry()
        edit_geometry.setWidth(self.table.columnWidth(column))
        edit_geometry.setHeight(self.table.rowHeight(0))
        x_column_pos = self.table.columnWidth(column)*column
        edit_geometry.setX(window_position.x() + x_column_pos + 37)
        edit_geometry.setY(window_position.y() + 60) 
        #edit_geometry.moveLeft(self.sectionViewportPosition(section))
        self.headerline.setGeometry(edit_geometry)

        self.headerline.setText(self.d['data%i'%column][1])
        self.headerline.setHidden(False) # Make it visiable
        self.headerline.setFocus()
        self.sectionedit = column
        oldHeader = self.table.horizontalHeaderItem(column)

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
         ### bei Rechts-Klick auf Header wird header_menu geöffnet ###
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
            for j in range(self.cols):
                data_zs = []
                for k in range(self.rows):
                    ti = float(self.table.item(k, j).text())
                    data_zs.append(ti)
                zs = self.d['data%i'%j]
                self.d.update({'data%i'%j : (data_zs, zs[1], zs[2], zs[3])})
            
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
        else:
            super(SpreadSheet, self).keyPressEvent(event)   

    def file_save(self):
        formattyp = '%.3f' 
        data = [self.d['data0'][0]]
        for j in range(1, self.cols):
            data.append(self.d['data%i'%j][0])
            formattyp = formattyp + '	%.3f'
        
        n = len(self.d['data0'][0])
        if all(len(x) == n for x in data):
            pass
        else:
            print('Die Spalten haben nicht die gleiche Länge, soweit bin ich noch nicht mit programmieren!')
            return

        data = np.transpose(data)
        SaveFileName = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', self.pHomeTxt)
        if SaveFileName:
            SaveFileName = SaveFileName[0]
        else:
            return

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
        
        anz_newFiles = len(newFiles)
        data = []
        lines = []
        FileName = []
        for j in range(anz_newFiles):
            data.append(np.loadtxt(newFiles[j]))
            data[j] = np.transpose(data[j])
            lines.append(len(data[j]))
            FileName.append(os.path.splitext(os.path.basename(newFiles[j]))[0]) 
        for k in range(anz_newFiles): 
            for j in range(lines[k]):	
                data_name = 'data%i'%(j+self.cols)			
                if j == 0:
                    self.d.update({data_name : (data[k][j], str(FileName[k]), 'X', newFiles[k])})
                else:
                    self.d.update({data_name : (data[k][j], str(FileName[k]), 'Y', newFiles[k])})
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

    def change_window_title(self):
        # Change title of the spreadsheet window
        oldTitle = self.windowTitle()
        newTitle, ok = QInputDialog.getText(self, 'Text Input Dialog', 'Enter the new Window Title:')
        if ok:
            self.setWindowTitle(newTitle)
            self.mw.spreadsheet[newTitle] = self.mw.spreadsheet.pop(oldTitle)
        else:
            return

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

        self.plot_data = []    

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
                print('Please only select Y-columns!')
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
                    print('At least one dataset Y has no assigned X dataset.')
                    return
                else:
                    pass

        if plot_type != None:
            self.new_pw_signal.emit()
        else:
            self.add_pw_signal.emit(action.text())

    def closeEvent(self, event):
        close = QMessageBox()
        close.setWindowTitle('Quit')
        close.setText("You sure?")
        close.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        close = close.exec()

        if close == QMessageBox.Yes:
            self.close_ss_signal.emit(self.windowTitle())
            event.accept()
        else:
            event.ignore()

#####################################################################################################################################################
### 4. Plot
#####################################################################################################################################################
class Functions:
    def __init__(self, pw):
        self.pw = pw

    ### Definition der Lorentz Funktion für Fit ###
    def LorentzFct(self, x, xc, h, b):
        return  h/(1 + (2*(x - xc)/b)**2)
        #return a2/pi*a1/((x-a0)*(x-a0)+a1*a1)

    ### Definition der Gauß Funktion für Fit ###
    def GaussianFct(self, x, xc, h, b):
        return h*np.exp(-4*math.log(2)*((x - xc)/b)*((x-xc)/b))
        #return a2*np.exp(-(x-a0)*(x-a0)/(2*a1*a1))

    ### Definition der Breit-Wigner-Fano Funktion für Fit ###
    #(siehe z.B. "Interpretation of Raman spectra of disordered and amorphous carbon" von Ferrari und Robertson)
    #Q is BWF coupling coefficient
    #For Q⁻¹->0: the Lorentzian line is recovered
    def BreitWignerFct(self, x, xc, h, b, Q):
        return h*(1+2*(x-xc)/(Q*b))**2/(1+(2*(x-xc)/b)**2)

    ### Summing up the fit functions ###
    def FctSumme(self, x, *p):   
        a = self.pw.anzahl_Lorentz     #number of Lorentzians
        b = self.pw.anzahl_Gauss       #number of Gaussians
        c = self.pw.anzahl_BWF         #number of Breit-Wigner-Fano functions
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
    def __init__(self, line):
        self.line = line
        self.pickedPoint = None
        self.xs = self.line.get_xdata()
        self.ys = self.line.get_ydata()
        self.ax = self.line.axes

        self.startPlot()
         
    def startPlot(self):    
        self.selectedPoint, = self.ax.plot(self.xs[0], self.ys[0], 'o', ms=12, alpha=0.4, color='yellow', visible = False)
        self.arrow = mpatches.FancyArrowPatch((self.xs[1], self.ys[1]), (self.xs[0], self.ys[0]),
                                 mutation_scale=10, arrowstyle='-')
        self.ax.add_patch(self.arrow)
        #self.line.set_visible(True)
        self.line.figure.canvas.draw()
        self.cid1 = self.line.figure.canvas.mpl_connect('pick_event', self.pickpoint)
        self.cid2 = self.line.figure.canvas.mpl_connect('button_release_event', self.unpickpoint)
        self.cid3 = self.line.figure.canvas.mpl_connect('motion_notify_event', self.movepoint)

    def pickpoint(self, event):
        if event.artist == self.line and event.mouseevent.button == 1:
            distance_threshold = 10
            min_distance = math.sqrt(2 * (100 ** 2))
            for x, y in zip(self.xs, self.ys):
                distance = math.hypot(event.mouseevent.xdata - x, event.mouseevent.ydata - y)
                if distance < min_distance:
                    min_distance = distance
                    self.pickedPoint = (x, y)
            if min_distance < distance_threshold:
                pass
            else:
                self.pickedPoint = None
            self.selectedPoint.set_data(self.pickedPoint)
            self.selectedPoint.set_visible(True)
            self.selectedPoint.figure.canvas.draw()
        elif event.artist == self.line and event.mouseevent.button == 3:
            self.options()
        else:
            self.selectedPoint.set_visible(False)
            self.selectedPoint.figure.canvas.draw()

    def unpickpoint(self, event):
        if self.pickedPoint and event.button == 1:
            self.updatePlot()
            self.pickedPoint = None
            self.selectedPoint.set_visible(False)
            self.selectedPoint.figure.canvas.draw()
        else:
            return

    def movepoint(self, event):
        if not self.pickedPoint:
            return
        elif event.xdata is None or event.ydata is None:
            return
        else:
            self.xs = self.removePoint(self.xs, 0)
            self.ys = self.removePoint(self.ys, 1)
            self.addPoint(event)
            self.updatePlot()

    def addPoint(self, e):
        if isinstance(e, MouseEvent):
            x, y = float(e.xdata), float(e.ydata)
            self.xs = np.append(self.xs, x)
            self.ys = np.append(self.ys, y)
            self.pickedPoint = [x,y]
        else:
            return

    def removePoint(self, a, i):
        for index, item in enumerate(a):
            if item == self.pickedPoint[i]:
                a = np.delete(a, index)
                return a

    def updatePlot(self):
        if self.pickedPoint == None:
            return
        else:
            self.line.set_data(self.xs, self.ys)
            self.arrow.set_positions((self.xs[0], self.ys[0]), (self.xs[1], self.ys[1]))
            self.line.figure.canvas.draw()
            self.arrow.figure.canvas.draw()

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
            ('x Start', self.xs[0]),
            ('y Start', self.ys[0]),
            ('x End', self.xs[1]),
            ('y End', self.ys[1]),
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

        self.line.set_linewidth(width)
        self.line.set_linestyle(linestyle)
        self.line.set_color(color)

        self.arrow.set_linewidth(width)
        self.arrow.set_linestyle(linestyle)
        self.arrow.set_color(color)
        if arrowstyle != '-':
            self.arrow.set_arrowstyle(arrowstyle, head_length = headlength, head_width = headwidth)
        else:
            self.arrow.set_arrowstyle(arrowstyle)

        self.xs[0] = xStart
        self.ys[0] = yStart
        self.xs[1] = xEnd
        self.ys[1] = yEnd

        self.line.set_data(self.xs, self.ys)
        self.arrow.set_positions((self.xs[0], self.ys[0]), (self.xs[1], self.ys[1]))

        self.line.figure.canvas.draw()

    def addArrow(self):
        #self.arrow_style = mpatches.ArrowStyle("->", head_length=.6, head_width=.6)
        self.arrow = mpatches.FancyArrowPatch((self.xs[1], self.ys[1]), (self.xs[0], self.ys[0]),
                                 mutation_scale=10, arrowstyle='<-')
        self.ax.add_patch(self.arrow)


class InsertText:
    def __init__(self, spot): 
        self.fig = spot.figure
        self.ax = spot.axes
        self.textpt = spot.get_data()   #Point, where text is placed
        self.pickedText = None
        self.newText = None
        self.create_textbox()

    def create_textbox(self):
        self.texty = self.ax.annotate(r'''*''', self.textpt, picker = 5)
        self.ax.add_artist(self.texty)
        
        self.cid1 = self.texty.figure.canvas.mpl_connect('pick_event', self.on_pick)
        self.cid2 = self.texty.figure.canvas.mpl_connect('button_release_event', self.on_release)
        self.cid3 = self.texty.figure.canvas.mpl_connect('motion_notify_event', self.on_motion)

    def on_pick(self, event):
        if event.artist == self.texty and event.mouseevent.button == 1 and event.mouseevent.dblclick == True:
            tbox=dict(boxstyle='Square', fc="w", ec="k")
            self.texty.set_bbox(tbox) 
            self.cid4 = self.texty.figure.canvas.mpl_connect('key_press_event', self.text_input)
            self.fig.canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
            self.fig.canvas.setFocus()
            self.fig.canvas.draw()
        elif event.artist == self.texty and event.mouseevent.button == 1:
            self.pickedText = self.texty
        elif event.artist == self.texty and event.mouseevent.button == 3:
            self.text_options()
        elif 'cid4' in locals():
            self.texty.figure.canvas.mpl_disconnect(self.cid4)
        else:
            return

    def on_release(self, event):
        if self.pickedText == None:
            return
        elif event.button == 1:
            self.pickedText = None
        else:
            return

    def on_motion(self, event):
        if self.pickedText == None:
            return
        else:
            pos = (event.xdata, event.ydata)
            self.texty.set_position(pos)
            self.fig.canvas.draw()

    def text_input(self, event):
        insert = event.key
        if event.key == 'enter':
            self.texty.figure.canvas.mpl_disconnect(self.cid4)
            self.texty.set_text(self.newText)
            self.texty.set_bbox(None)
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
        self.texty.set_text(self.newText)
        self.fig.canvas.draw()

    def text_options(self):
        color = mcolors.to_hex(mcolors.to_rgba(self.texty.get_color(), self.texty.get_alpha()), keep_alpha=True)
        text_options_list = [
            ('Fontsize', self.texty.get_fontsize()),
            ('Color', color),
            ]

        texty_option = formlayout.fedit(text_options_list, title="Text options")
        if texty_option is not None:
            self.apply_callback(texty_option)

    def apply_callback(self, options):
        (fontsize, color) = options

        self.texty.set_fontsize(fontsize)
        self.texty.set_color(color)

        self.fig.canvas.draw()


class DataPointPicker:
#Creates a yellow dot around a selected data point
    def __init__(self, line, selected, a):
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

class MyCustomToolbar(NavigationToolbar2QT): 
    toolitems = [t for t in NavigationToolbar2QT.toolitems]
    # Add new toolitem at last position
    toolitems.append(
        ("Layers", "manage layers and layer contents",
        "", "layer_content"))

    def __init__(self, plotCanvas):
        NavigationToolbar2QT.__init__(self, plotCanvas, parent=None)

    def layer_content(self):
        Layer_Legend = QDialog()
        layout = QtWidgets.QGridLayout()
        Layer_Legend.setLayout(layout)
        Layer_Legend.setWindowTitle("Layer Content")
        Layer_Legend.setWindowModality(Qt.ApplicationModal)
        Layer_Legend.exec_()

class PlotWindow(QMainWindow):
    close_p_signal = QtCore.pyqtSignal(str)                     # Signal in case plotwindow is closed
    change_window_title_signal = QtCore.pyqtSignal(str, str)    # Signal in case plotwindow title is changed
    def __init__(self, plot_data, fig, parent):
        super(PlotWindow, self).__init__(parent)
        self.fig = fig
        self.data = plot_data
        self.backup_data = plot_data
        self.Spektrum = []
        self.ErrorBar = []
        self.functions = Functions(self)
        self.InsertedText = []                          # Storage for text inserted in the plot

        self.plot()
        self.create_statusbar()
        self.create_menubar()	
        self.create_sidetoolbar()

        #self.cid1 = self.fig.canvas.mpl_connect('button_press_event', self.mousePressEvent)
        self.cid2 = self.fig.canvas.mpl_connect('key_press_event', self.keyPressEvent)
        self.cid3 = self.fig.canvas.mpl_connect('pick_event', self.pickEvent)

    def plot(self):
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        layout = QtWidgets.QVBoxLayout(self._main)
        legendfontsize = 24
        labelfontsize = 24
        tickfontsize = 18
       
        if self.fig == None:
            self.fig = Figure(figsize=(15,9))
            self.ax = self.fig.add_subplot()
            self.Canvas = FigureCanvasQTAgg(self.fig)
            layout.addWidget(self.Canvas)

            for j in self.data:
                if isinstance(j[5], (np.ndarray, np.generic)):
                    (spect, capline, barlinecol) = self.ax.errorbar(j[0], j[1], fmt=j[4], yerr=j[5], 
                        picker=5, capsize=3)
                    self.Spektrum.append(spect)
                    spect.set_label(j[2])
                    capline[0].set_label('_Hidden capline bottom ' + j[2])
                    capline[1].set_label('_Hidden capline top ' + j[2])
                    barlinecol[0].set_label('_Hidden barlinecol ' + j[2])
                else:
                    self.Spektrum.append(self.ax.plot(j[0], j[1], j[4], label = j[2], picker = 5)[0])
            legend = self.ax.legend(fontsize = legendfontsize)
            self.ax.set_xlabel('Raman shift / cm⁻¹', fontsize = labelfontsize)
            self.ax.set_ylabel('Intensity / cts/s', fontsize = labelfontsize)
            self.ax.xaxis.set_tick_params(labelsize=tickfontsize)
            self.ax.yaxis.set_tick_params(labelsize=tickfontsize)
        else:
            self.ax = self.fig.axes[0]
            self.Canvas = FigureCanvasQTAgg(self.fig)
            layout.addWidget(self.Canvas)
            for j in self.ax.lines:
                self.Spektrum.append(j)
            self.ax.get_legend()
        self.addToolBar(MyCustomToolbar(self.Canvas))

        self.ax.get_legend().set_picker(5)

    def add_plot(self, new_data):
        for j in new_data:
            self.data.append(j)
            if isinstance(j[5], (np.ndarray, np.generic)):
                self.Spektrum.append(self.ax.errorbar(j[0], j[1], label = j[2], fmt = j[4], yerr = j[5], picker = 5)[0])
            else:
                self.Spektrum.append(self.ax.plot(j[0], j[1], j[4], label = j[2], picker = 5)[0])
        handles, labels = self.ax.get_legend_handles_labels()
        self.update_legend(handles, labels)
        self.ax.figure.canvas.draw()

    def keyPressEvent(self, event):
        key = event.key
        if key == (Qt.Key_Control and Qt.Key_Z):
            k = 0
            for j in self.backup_data:
                print(j[0])
                print(j[1])
                self.Spektrum[k].set_xdata(j[0])
                self.Spektrum[k].set_ydata(j[1])
                k = k+1
            canvas = self.Canvas
            self.ax.figure.canvas.draw()
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

    def update_legend(self, leg_handles, leg_labels):
        if self.ax.get_legend() is not None:
            old_legend = self.ax.get_legend()
            leg_draggable = old_legend._draggable is not None
            leg_ncol = old_legend._ncol
            leg_fontsize = int(old_legend._fontsize)
            leg_frameon = old_legend._drawFrame
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
        ### 1. Menüpunkt: File ###
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction('Save to File', self.menu_save_to_file)
        fileMenu.addAction('Change Name of Window', self.change_window_title)

        ### 2. Menüpunkt: Edit  ###
        editMenu = menubar.addMenu('&Edit')
        editMenu.addAction('Delete broken pixel - LabRam', self.delete_datapoint)
        editDeletePixel = editMenu.addAction('Delete single pixel', self.delete_pixel)
        editDeletePixel.setStatusTip('Delete selected data point with Enter, Move with arrow keys, Press c to leave Delete-Mode')
        editSelectArea = editMenu.addAction('Define data area', self.DefineArea)
        editSelectArea.setStatusTip('Move area limit with left mouse click, set it fix with right mouse click')        
        editNormAct = editMenu.addAction('Normalize Spectrum', self.normalize)
        editNormAct.setStatusTip('Normalizes highest peak to 1')

        ### 3. Menüpunkt: Analysis  ###
        analysisMenu = menubar.addMenu('&Analysis')

        ### 3.1 Analysis Fit
        analysisFit = analysisMenu.addMenu('&Fit')
        
        analysisFitEinzel = analysisFit.addMenu('&Einzelfunktionen')
        analysisFitEinzel.addAction('Lorentz', self.FitLorentz)
        analysisFitEinzel.addAction('Gaussian', self.FitGaussian)
        analysisFitEinzel.addAction('Breit-Wigner', self.FitBreitWigner)
        
        analysisFitRoutine = analysisFit.addMenu('&Fitroutine')
        analysisFitRoutine.addAction('D und G Bande', self.fitroutine1)

        ### 3.2 Analysis Basislinien-Korrektion
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
        ScaleAct = QAction(QIcon.fromTheme('go-up'), 'Scale', self)
        ScaleAct.setStatusTip('Tool to scale intensity of selected spectrum')
        ScaleAct.triggered.connect(self.scale_spectrum)
        toolbar.addAction(ScaleAct)

        # Tool to shift selected spectrum in y-direction       
        ShiftAct = QAction(QIcon.fromTheme('go-up'), 'Shift', self)
        ShiftAct.setStatusTip('Tool to shift selected spectrum in y-direction')
        ShiftAct.triggered.connect(self.shift_spectrum)
        toolbar.addAction(ShiftAct)

        # Tool to draw line       
        DrawAct = QAction(QIcon.fromTheme(''), 'Draw', self)
        DrawAct.setStatusTip('Tool to draw line')
        DrawAct.triggered.connect(self.draw_line)
        toolbar.addAction(DrawAct)

        # Tool to draw line       
        TextAct = QAction(QIcon.fromTheme(''), 'Text', self)
        TextAct.setStatusTip('Insert Text')
        TextAct.triggered.connect(self.insert_text)
        toolbar.addAction(TextAct) 
 
        self.show()

    ########## Functions and other stuff ##########

    def SelectDataset(self):
        # Select one or several datasets  
        self.selectedDatasetNumber = []
        self.selectedData = []
        self.Dialog_SelDataSet = QDialog()
        layout = QtWidgets.QGridLayout()
        self.CheckDataset = []
        # for j in range(len(self.data)):
        #     self.CheckDataset.append(QCheckBox(self.data[j][2], self))
        #     layout.addWidget(self.CheckDataset[j], j, 0)
        for idx, line in enumerate(self.ax.get_lines()):
            self.CheckDataset.append(QCheckBox(line.get_label(), self))
            layout.addWidget(self.CheckDataset[idx], idx, 0)

        ok_button = QPushButton("ok", self.Dialog_SelDataSet)
        layout.addWidget(ok_button, len(self.data), 0)
        ok_button.clicked.connect(self.Ok_button)
        self.Dialog_SelDataSet.setLayout(layout)
        self.Dialog_SelDataSet.setWindowTitle("Dialog")
        self.Dialog_SelDataSet.setWindowModality(Qt.ApplicationModal)
        self.Dialog_SelDataSet.exec_()

    def Ok_button(self):
        # OK Button for function SecetedDataset
        for idx, d in enumerate(self.CheckDataset):
            if d.isChecked():
                self.selectedDatasetNumber.append(idx)
                self.selectedData.append(self.data[idx])
            else:
                pass
        self.Dialog_SelDataSet.close()

    def menu_save_to_file(self):
        self.SelectDataset()
        if self.selectedData == []:
            return

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

    def change_window_title(self):
        # Change title of the plot window
        oldTitle = self.windowTitle()
        newTitle, ok = QInputDialog.getText(self, 'Text Input Dialog', 'Enter the new Window Title:')
        if ok:
            self.setWindowTitle(newTitle)
            self.change_window_title_signal.emit(oldTitle, newTitle)
        else:
            return

    def delete_pixel(self):
        self.SelectDataset()
        if self.selectedData == []:
            return

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

    ### Löscht die Datenpunkte Nr. 630+n*957, da dieser Pixel im CCD Detektor kaputt ist
    def delete_datapoint(self):
        self.SelectDataset()
        if self.selectedData == []:
            return

        for j in self.selectedDatasetNumber:
            a = 629
            grenze = 6
            controll_delete_parameter = True        #Parameter to controll if data point should be deleted
            print('Folgende Datenpunkte von ' + self.data[j][2]  + ' wurden gelöscht:')
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

            ### Speichern der Daten ohne fehlerhaften Datenpunkte ###
            startFileDirName = os.path.dirname(self.data[j][3])
            startFileName = startFileDirName + '/' + self.data[j][2]
            save_data = [self.data[j][0], self.data[j][1]]
            save_data = np.transpose(save_data)
            self.save_to_file('Save data without deleted data points in file', startFileName, save_data)

    def normalize(self):
        self.SelectDataset()
        if self.selectedData == []:
            return

        for j in self.selectedDatasetNumber:
            self.data[j][1] = self.data[j][1]/numpy.amax(self.data[j][1])
            self.Spektrum[j].set_data(self.data[j][0], self.data[j][1])
            self.fig.canvas.draw()
            ### Save normalized data ###
            (fileBaseName, fileExtension) = os.path.splitext(self.data[j][2])
            startFileDirName = os.path.dirname(self.data[j][3])
            startFileBaseName = startFileDirName + '/' + fileBaseName
            startFileName = startFileBaseName + '_norm.txt'
            save_data = [self.data[j][0], self.data[j][1]]
            save_data = np.transpose(save_data)
            self.save_to_file('Save normalized data in file', startFileName, save_data)

    def get_start_values(self):
        self.Dialog_FitParameter = QDialog()
        layout = QtWidgets.QGridLayout()

        d0_edit = QtWidgets.QLineEdit()
        layout.addWidget(d0_edit, 0, 0)
        d0_edit.setText('0.0')
        d0_name = QtWidgets.QLabel('Background')
        layout.addWidget(d0_name, 0, 1)

        d1_edit = QtWidgets.QLineEdit()
        layout.addWidget(d1_edit, 1, 0)
        d1_edit.setText('500')
        d1_name = QtWidgets.QLabel('Position in cm⁻¹')
        layout.addWidget(d1_name, 1, 1)

        d2_edit = QtWidgets.QLineEdit()
        layout.addWidget(d2_edit, 2, 0)
        d2_edit.setText('100')
        d2_name = QtWidgets.QLabel('Intensity')
        layout.addWidget(d2_name, 2, 1)

        d3_edit = QtWidgets.QLineEdit()
        layout.addWidget(d3_edit, 3, 0)
        d3_edit.setText('5')
        d3_name = QtWidgets.QLabel('FWHM')
        layout.addWidget(d3_name, 3, 1)

        okbutton = QPushButton('Ok', self)
        okbutton.setToolTip('Starts the fit')
        okbutton.clicked.connect(self.Dialog_FitParameter.close)
        layout.addWidget(okbutton, 4, 0)

        self.Dialog_FitParameter.setLayout(layout)
        self.Dialog_FitParameter.setWindowTitle("Fit Parameter")
        self.Dialog_FitParameter.setWindowModality(Qt.ApplicationModal)

        self.Dialog_FitParameter.exec_()
        d0 = float(d0_edit.text())      #Background
        d1 = float(d1_edit.text())      #Peak-Position in cm^-1
        d2 = float(d2_edit.text())      #Intensity
        d3 = float(d3_edit.text())      #FWHM
        return ([d0, d1, d2, d3])

    def FitLorentz(self):
        self.SelectDataset()
        if self.selectedData == []:
            return

        xs = self.selectedData[0][0]
        ys = self.selectedData[0][1]
        x,y = self.SelectArea(xs, ys)

        p_start = self.get_start_values()
        self.anzahl_Lorentz = 1                       
        self.anzahl_Gauss   = 0   
        self.anzahl_BWF     = 0
        popt, pcov = curve_fit(self.functions.FctSumme, x, y, p0 = p_start) #, bounds=([0, 500], [200, 540]))

        x1 = np.linspace(min(x), max(x), 1000)
        self.ax.plot(x1, self.functions.FctSumme(x1, *popt), '-r')
        canvas = self.Canvas
        self.ax.figure.canvas.draw()
        print('\n', 'Lorentz')
        print(tabulate([['Background', popt[0]], ['Raman Shift in cm⁻¹', popt[1]], ['Intensity', popt[2]], ['FWHM', popt[3]]], headers=['Parameters', 'Values']))
                
    def FitGaussian(self):
        self.SelectDataset()
        if self.selectedData == []:
            return

        xs = self.selectedData[0][0]
        ys = self.selectedData[0][1]
        x,y = self.SelectArea(xs, ys)

        p_start = self.get_start_values()

        self.anzahl_Lorentz = 0                       
        self.anzahl_Gauss   = 1   
        self.anzahl_BWF     = 0
        popt, pcov = curve_fit(self.functions.GaussianFct, x, y, p0 = p_start) #, bounds=([0, 500], [200, 540]))

        x1 = np.linspace(min(x), max(x), 10000)
        self.ax.plot(x1, self.functions.FctSumme(x1, *popt), '-r')
        canvas = self.Canvas
        self.ax.figure.canvas.draw()
        print('\n' + 'Gaussian')
        print(tabulate([['Background', popt[0]], ['Raman Shift in cm⁻¹', popt[1]], ['Intensity', popt[2]], ['FWHM', popt[3]]], headers=['Parameters', 'Values']))

    def FitBreitWigner(self):
        self.SelectDataset()
        if self.selectedData == []:
            return

        xs = self.selectedData[0][0]
        ys = self.selectedData[0][1]
        x,y = self.SelectArea(xs, ys)
        
        p_start = self.get_start_values()
        p_start.append(-10)

        self.anzahl_Lorentz = 0                       
        self.anzahl_Gauss   = 0   
        self.anzahl_BWF     = 1

        popt, pcov = curve_fit(self.functions.FctSumme, x, y, p0 = p_start) #, bounds=([0, 500], [200, 540]))
        x1 = np.linspace(min(x), max(x), 10000)
        self.ax.plot(x1, self.functions.FctSumme(x1, *popt), '-r')
        canvas = self.Canvas
        self.ax.figure.canvas.draw()
        print('\n Breit-Wigner')
        print(tabulate([['Background', popt[0]], ['Raman Shift in cm⁻¹', popt[1]], ['Intensity', popt[2]], ['FWHM', popt[3]], ['Zusätzlicher Parameter', popt[4]]], headers=['Parameters', 'Values']))

    def DefineArea(self):
        self.SelectDataset()
        if self.selectedData == []:
            return

        xs = self.selectedData[0][0]
        ys = self.selectedData[0][1]
        x,y = self.SelectArea(xs, ys)
        self.data.append([x, y, self.selectedData[0][2]+'_cut', self.selectedData[0][3]])
        self.Spektrum.append(self.ax.plot(x, y, label = self.selectedData[0][2]+'_cut', picker=5))

    def SelectArea(self, x, y):
        line1, = self.ax.plot([min(x), min(x)], [min(y), max(y)], 'r-', lw=1)
        line2, = self.ax.plot([max(x), max(x)], [min(y), max(y)], 'r-', lw=1)
        canvas = self.Canvas
        self.ax.figure.canvas.draw()
        linebuilder1 = LineBuilder(line1)
        x_min = linebuilder1.xs  #untere Grenze Fitbereich

        linebuilder2 = LineBuilder(line2)
        x_max = linebuilder2.xs  #oberer Grenze Fitbereich
               
 
        working_x = x[np.where((x > x_min)&(x < x_max))]
        working_y = y[np.where((x > x_min)&(x < x_max))]
        
        line1.remove()
        line2.remove()
        self.ax.figure.canvas.draw()
        return working_x, working_y
	
    def menu_baseline_als(self):
        self.SelectDataset()
        if self.selectedData == []:
            return

        xs = self.selectedData[0][0]
        ys = self.selectedData[0][1]
        x,y = self.SelectArea(xs, ys)
        
        self.Dialog_BaselineParameter = QDialog()
        layout = QtWidgets.QGridLayout()
        
        p_edit = QtWidgets.QLineEdit()  
        layout.addWidget(p_edit, 0, 0)
        p_edit.setText('0.001')
        p_label = QtWidgets.QLabel('p')
        layout.addWidget(p_label, 0, 1)

        lam_edit = QtWidgets.QLineEdit() 
        layout.addWidget(lam_edit, 1, 0)
        lam_edit.setText('10000000')
        lam_label = QtWidgets.QLabel('lambda')
        layout.addWidget(lam_label, 1, 1)

        p = float(p_edit.text())
        lam = float(lam_edit.text())
        xb,yb,zb = self.baseline_als(x, y, p, lam)    
        self.baseline,    = self.ax.plot(xb, zb, 'c--', label = 'baseline (' + self.selectedData[0][2] + ')')
        self.blcSpektrum, = self.ax.plot(xb, yb, 'c-', label = 'baseline-corrected '+ self.selectedData[0][2])
        self.ax.figure.canvas.draw()



        self.finishbutton = QPushButton('Ok', self)       
        self.finishbutton.setCheckable(True)
        self.finishbutton.setToolTip('Are you happy with the start parameters? \n Close the dialog window and save the baseline!')
        self.finishbutton.clicked.connect(lambda: self.baseline_als_call(x, y, float(p_edit.text()), float(lam_edit.text())))
        layout.addWidget(self.finishbutton, 2, 0)

        self.closebutton = QPushButton('Close', self)
        self.closebutton.setCheckable(True)
        self.closebutton.setToolTip('Closes the dialog window and baseline is not saved.')
        self.closebutton.clicked.connect(lambda: self.baseline_als_call(x, y, float(p_edit.text()), float(lam_edit.text())))
        layout.addWidget(self.closebutton, 2, 1)

        applybutton = QPushButton('Apply', self)
        applybutton.setToolTip('Do you want to try the fit parameters? \n Lets do it!')
        applybutton.clicked.connect(lambda: self.baseline_als_call(x, y, float(p_edit.text()), float(lam_edit.text())))
        layout.addWidget(applybutton, 2, 2)

        self.Dialog_BaselineParameter.setLayout(layout)
        self.Dialog_BaselineParameter.setWindowTitle("Baseline Parameter")
        self.Dialog_BaselineParameter.setWindowModality(Qt.ApplicationModal)
        self.Dialog_BaselineParameter.exec_()
    
    def baseline_als_call(self, x, y, p, lam):
        self.blcSpektrum.remove()
        self.baseline.remove()
        if self.closebutton.isChecked():
            self.Dialog_BaselineParameter.close()
            self.ax.figure.canvas.draw()
        elif self.finishbutton.isChecked():
            xb, yb, zb = self.baseline_als(x, y, p, lam)
            self.baseline,    = self.ax.plot(xb, zb, 'c--', label = 'baseline (' + self.selectedData[0][2] + ')')
            self.Spektrum.append(self.ax.plot(xb, yb, 'c-', label = 'baseline-corrected '+ self.selectedData[0][2])[0])
            self.ax.figure.canvas.draw()
            
            ### Save background-corrected data ###
            (fileBaseName, fileExtension) = os.path.splitext(self.selectedData[0][2])
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
            self.baseline,    = self.ax.plot(xb, zb, 'c--', label = 'baseline (' + self.selectedData[0][2] + ')')
            self.blcSpektrum, = self.ax.plot(xb, yb, 'c-', label = 'baseline-corrected '+ self.selectedData[0][2])
            self.ax.figure.canvas.draw()

    # Baseline correction 
    # based on: "Baseline Correction with Asymmetric Least SquaresSmoothing" from Eilers and Boelens
    # also look at: https://stackoverflow.com/questions/29156532/python-baseline-correction-library
    def baseline_als(self, x, y, p, lam):
        niter = 10
        #p = 0.001   			#asymmetry 0.001 ≤ p ≤ 0.1 is a good choice     recommended from Eilers and Boelens for Raman: 0.001    recommended from Simon: 0.0001 
        #lam = 10000000			#smoothness 10^2 ≤ λ ≤ 10^9                     recommended from Eilers and Boelens for Raman: 10⁷      recommended from Simon: 10⁷
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
#        self.ax.figure.canvas.draw()
        return x, y, z          #x - ist klar, y - background-corrected Intensity-values, z - background
	
    # Partially based on Christian's Mathematica Notebook
    # Fitroutine for D and G bands in spectra of carbon compounds
    def fitroutine1(self):
        # Select which data set will be fitted  (at moment only for one at the same time)
        self.SelectDataset()
        if self.selectedData == []:
            return
            
        x = self.selectedData[0][0]
        y = self.selectedData[0][1]
      
        #Limits for Backgroundcorrection
        x_min =  200
        x_max = 4000

        #Limit data to fit range 
        working_x = x[np.where((x > x_min)&(x < x_max))]
        working_y = y[np.where((x > x_min)&(x < x_max))]
 
        # parameter for background-correction 
        p   = 0.0001             #asymmetry 0.001 ≤ p ≤ 0.1 is a good choice     recommended from Eilers and Boelens for Raman: 0.001    recommended from Simon: 0.0001 
        lam = 10000000           #smoothness 10^2 ≤ λ ≤ 10^9                     recommended from Eilers and Boelens for Raman: 10⁷      recommended from Simon: 10⁷
       
        xb, yb, zb = self.baseline_als(working_x, working_y, p, lam)
        self.baseline,    = self.ax.plot(xb, zb, 'c--', label = 'baseline (' + self.selectedData[0][2] + ')')
        self.blcSpektrum, = self.ax.plot(xb, yb, 'c-', label = 'baseline-corrected '+ self.selectedData[0][2])
        self.ax.figure.canvas.draw()

        #define fitarea 
        x_min =  850 
        x_max = 2000
        #limit data to fitarea 
        working_x = xb[np.where((xb > x_min)&(xb < x_max))]
        working_y = yb[np.where((xb > x_min)&(xb < x_max))]

        #Fitprocess
        #D-Band: Lorentz
        #G-Band: BreitWignerFano
        self.anzahl_Lorentz = 1   # number of Lorentzian
        self.anzahl_Gauss   = 0   # number of Gaussian
        self.anzahl_BWF     = 1   # number of Breit-Wigner-Fano

        aL  = self.anzahl_Lorentz
        aG  = self.anzahl_Gauss
        aB  = self.anzahl_BWF
        aLG = self.anzahl_Lorentz + self.anzahl_Gauss

        pStart = []
        pBoundsLow = []
        pBoundsUp  = []
        inf = np.inf

        pStart.append((1360,  80,  50))         #Lorentz (D-Bande)
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
        pStart.append((1600, 200,  50, -10))    #Breit-Wigner-Fano
        pBoundsLow.append((0, 0, 0, -inf))
        pBoundsUp.append((inf, inf, inf, 0))

        p_start = []
        p_bounds_low = []
        p_bounds_up  = []
        p_start.extend([0])
        p_bounds_low.extend([-10])
        p_bounds_up.extend([10])
        for i in range(len(pStart)):
            p_start.extend(pStart[i])
            p_bounds_low.extend(pBoundsLow[i])
            p_bounds_up.extend(pBoundsUp[i])

        #Limits
        p_bounds = ((p_bounds_low, p_bounds_up))
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

        canvas = self.Canvas
        self.ax.figure.canvas.draw()
        
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

        save_data = 'R²=%.6f \n'%r_squared + 'Lorentz 1 = D-Bande, BWF (Breit-Wigner-Fano) 1 = G-Bande \n' + tabulate(data_table, headers = ['Parameters', 'Values', 'Errors'])
        print('\n')
        print(self.selectedData[0][2])
        print(save_data)

        (fileBaseName, fileExtension) = os.path.splitext(self.selectedData[0][2])
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
        self.SelectDataset()
        if self.selectedData == []:
            return
        xs = self.selectedData[0][0]
        ys = self.selectedData[0][1]
        ns = self.selectedDatasetNumber[0]
        canvas = self.Canvas
        self.cid_scale = self.ax.figure.canvas.mpl_connect('button_release_event', self.scale_click)
        self.ax.figure.canvas.start_event_loop(timeout=10000) 
        ys = ys*self.scale_factor
        self.data[ns][1] = ys
        self.Spektrum[ns].set_ydata(ys)
        canvas = self.Canvas
        self.ax.figure.canvas.draw()
            
    def scale_click(self, event):
        xs = self.selectedData[0][0]
        ys = self.selectedData[0][1]
        ns = self.selectedDatasetNumber[0]
        if event.button == 1:
            x = event.xdata
            y = event.ydata
            ind = min(range(len(xs)), key=lambda i: abs(xs[i]-x))
            self.scale_factor = y/ys[ind]
            self.ax.figure.canvas.mpl_disconnect(self.cid_scale)
            self.ax.figure.canvas.stop_event_loop(self)
        else:
            pass

    def shift_spectrum(self):
        self.check_if_line_was_removed()
        self.SelectDataset()
        if self.selectedData == []:
            return
        xs = self.selectedData[0][0]
        ys = self.selectedData[0][1]
        ns = self.selectedDatasetNumber[0]
        canvas = self.Canvas
        self.cid_shift = self.ax.figure.canvas.mpl_connect('button_release_event', self.shift_click)
        self.ax.figure.canvas.start_event_loop(timeout=10000)
        ys = ys + self.shift_factor
        self.data[ns][1] = ys
        self.Spektrum[ns].set_ydata(ys)
        canvas = self.Canvas
        self.ax.figure.canvas.draw()

    def shift_click(self, event):
        xs = self.selectedData[0][0]
        ys = self.selectedData[0][1]
        ns = self.selectedDatasetNumber[0]
        if event.button == 1:
            x = event.xdata
            y = event.ydata
            ind = min(range(len(xs)), key=lambda i: abs(xs[i]-x))
            self.shift_factor = y - ys[ind]
            self.ax.figure.canvas.mpl_disconnect(self.cid_shift)
            self.ax.figure.canvas.stop_event_loop(self)
        else:
            pass

    def draw_line(self):
        try:
            pts = self.fig.ginput(2)
        except RuntimeError:
            return

        line, = self.ax.plot([pts[0][0], pts[1][0]], [pts[0][1], pts[1][1]], 'black', lw=2, picker=5)
        line.set_visible(False)
        self.drawedLine = LineDrawer(line)
        canvas = self.Canvas
        self.ax.figure.canvas.draw()

    def insert_text(self):
        try:
            pt = self.fig.ginput(1)
        except RuntimeError:
            return

        textspot, = self.ax.plot([pt[0][0]], [pt[0][1]], 'black', lw=2, picker=5)
        textspot.set_visible(False)
        self.InsertedText.append(InsertText(textspot))
        self.fig.canvas.draw()

    def closeEvent(self, event):
        close = QMessageBox()
        close.setWindowTitle('Quit')
        close.setText("You sure?")
        close.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        close = close.exec()

        if close == QMessageBox.Yes:
            self.close_p_signal.emit(self.windowTitle())
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
