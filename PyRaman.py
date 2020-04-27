# Autor: Simon Brehm
import math
import matplotlib.pyplot as plt
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
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
#from matplotlib.backends.backend_qt5agg import (FigureCanvas)
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

# This file essentially consists of three parts:
# Main Window
# Spreadsheet
# Plot

#####################################################################################################################################################
### Main window
#####################################################################################################################################################
class MainWindow(QMainWindow):
    updata_menu_signal = QtCore.pyqtSignal()

    def __init__(self, parent = None):
        super(MainWindow, self).__init__(parent)
        self.create_mainwindow()

        self.spreadsheet = []                        # list of spreadsheets
        self.plotwindow = []                         # list of plotwindows
        self.pwtitle = []                            # list of plotwindow-titles
        self.count_ss = 0                            # number of spreadsheet windows (closed ones are included)
        self.count_p  = 0                            # number of plot windows (closed ones are included)
        self.nop_ss  = []                            # list of numbers of open spreadsheet windows
        self.nop_pw   = []                           # list of numbers of open plot windows
        self.FileName = os.path.dirname(__file__)    # path of this python file

    def create_mainwindow(self):
        self.setWindowTitle('Raman')
        self.mdi = QtWidgets.QMdiArea()
        self.setCentralWidget(self.mdi)
        self.create_menubar()

    def create_menubar(self):
        menu = self.menuBar()
        File = menu.addMenu('File')
        
        FileSave = File.addAction('Save', self.filesave)
        FileLoad = File.addAction('Load', self.fileload)
        newS = File.addAction('New spreadsheet', lambda: self.newSpreadsheet(None))     # Argument is 'None', because no data

        medit = menu.addMenu('Edit')
        medit.addAction('Cascade')
        medit.addAction('Tiled')
        medit.triggered[QAction].connect(self.edit)

    def filesave(self):
        p_home = 'C:/Users/Simon/Desktop/ITP_Computer/Python-Files/Raman/Spreadsheet'
        fileName = QtWidgets.QFileDialog.getSaveFileName(self, 'Save as', p_home, 'All Files (*);;Raman Files (*.sbd)')

        if fileName[0] != '':
            fileName = fileName[0]
        else:
            return

        saveFileContent = {}
        ss = [len(self.nop_ss)]
        p  = [len(self.nop_pw)]

        for j in self.nop_ss:
            ss.append(self.spreadsheet[j].d)

        for j in self.nop_pw:
            p.append([self.plotwindow[j].data, self.plotwindow[j].fig])

        saveFileContent.update({'Spreadsheet' : ss})
        saveFileContent.update({'Plot-Window' : p})

        file = open(fileName,'wb') 
        pickle.dump(saveFileContent, file)         
        file.close()  

    def fileload(self):
        # question = QMessageBox()
        # question.setWindowTitle('Load')
        # question.setText("The current windows will be closed. You sure?")
        # question.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        # answer = question.exec()

        # if answer == QMessageBox.Yes:
        #     pass
        # else:
        #     return

        p_home = 'C:/Users/Simon/Desktop/ITP_Computer/Daten/Raman-Files'
        fileName = QtWidgets.QFileDialog.getOpenFileName(self, 'Save as', p_home, 'All Files (*);;Raman Files (*.sbd)')

        if fileName[0] != '':
            fileName = fileName[0]
        else:
            return

        self.mdi.closeAllSubWindows()
        
        self.spreadsheet = []
        self.plotwindow  = []

        self.count_ss = 0
        self.count_p = 0
        file = open(fileName,'rb') 
        v = pickle.load(file)          
        file.close()  
        
        for j in range(v['Spreadsheet'][0]):
            self.newSpreadsheet(v['Spreadsheet'][j+1])

        for j in range(v['Plot-Window'][0]):
            fig = v['Plot-Window'][j+1][1]
            plot_data = v['Plot-Window'][j+1][0]
            self.newPlot(plot_data, fig)      
    
    def edit(self, q):
        if q.text() == "cascade":
            self.mdi.cascadeSubWindows()

        if q.text() == "Tiled":
            self.mdi.tileSubWindows()

    def newSpreadsheet(self, ssd):
        self.count_ss = self.count_ss+1
        a = self.count_ss -1
        self.nop_ss.append(a)

        if ssd == None:
            ssd = {'data0' : (np.zeros(1000),'A', 'X', None), 'data1' : (np.zeros(1000),'B', 'Y', None)}  #Spreadsheet- Data (for start only zeros)
        else:
            pass
        self.spreadsheet.append(SpreadSheet(self, ssd))
        self.spreadsheet[a].setObjectName('Spreadsheet'+str(a))
        self.spreadsheet[a].setWindowTitle('Spreadsheet-Window '+str(self.count_ss))
        self.mdi.addSubWindow(self.spreadsheet[a])
        self.spreadsheet[a].show()

        self.spreadsheet[a].new_pw_signal.connect(lambda: self.newPlot(self.spreadsheet[a].plot_data, None))
        self.spreadsheet[a].add_pw_signal.connect(lambda pw_name: self.addPlot(pw_name, self.spreadsheet[a].plot_data))
        self.spreadsheet[a].close_ss_signal.connect(lambda: self.closeSpreadsheetWindow(a))

    def newPlot(self, plot_data, fig):
        b = self.count_p
        self.count_p = self.count_p + 1
        self.nop_pw.append(b)

        self.plotwindow.append(PlotWindow(plot_data, fig, self))
        self.plotwindow[b].setObjectName('Plot'+str(b))
        self.pwtitle.append('Plot-Window '+str(self.count_p))
        self.plotwindow[b].setWindowTitle(self.pwtitle[b])
        self.mdi.addSubWindow(self.plotwindow[b])
        self.plotwindow[b].show()

        self.updata_menu_signal.emit()
        self.plotwindow[b].close_p_signal.connect(lambda: self.closePlotWindow(b))

    def addPlot(self, pw_name, plot_data):
        b = self.pwtitle.index(pw_name)
        for j in plot_data:
            j[4] = self.plotwindow[b].Spektrum[0].get_linestyle()
        self.plotwindow[b].add_plot(plot_data)

    def closeSpreadsheetWindow(self, a):
        self.nop_ss.remove(a)

    def closePlotWindow(self, b):
        self.nop_pw.remove(b)

    def closeEvent(self, event):
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
### Spreadsheet
#####################################################################################################################################################
cellre = re.compile(r'\b[A-Z][0-9]\b')


# teilweise (Class SpreadSheetDelegate and class SpreadSheetItem) geklaut von: 
# http://negfeedback.blogspot.com/2017/12/a-simple-gui-spreadsheet-in-less-than.html 
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
        self.value = eval(formula, {}, environment)

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
    close_ss_signal = QtCore.pyqtSignal()

    def __init__(self, mainwindow, data, parent = None):
        super(SpreadSheet, self).__init__(parent)
        self.cells = {}
        self.d = data              # structure of data (dictionary) {'dataX with X = (0,1,2,..)' : actual data,'name of data', 'X, Y or Yerr', 'if loaded: filename')}
        self.mw = mainwindow
        self.cols = len(self.d)	                                        # Anzahl Spalte
        self.rows = max([len(self.d[j][0]) for j in self.d.keys()])     # Anzahl Zeilen

        self.create_tablewidgets()
        self.create_menubar()
        self.create_header()
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

    ### Erstellen der Menu-Leiste ###
    def create_menubar(self):               
        self.menubar = self.menuBar()

        ### 1. Menüpunkt: File ###
        fileMenu = self.menubar.addMenu('&File')
        fileMenu.addAction('Save Data', self.file_save)
        fileMenu.addAction('Load Data', self.load_file)

        ### 2. Menüpunkt: Edit
        editMenu = self.menubar.addMenu('&Edit')
        editMenu.addAction('New Column', self.new_col)

        ### 3. Menüpunkt: Plot
        plotMenu = self.menubar.addMenu('&Plot')
        plotNew = plotMenu.addMenu('&New')
        plotNew.addAction('Line Plot', self.get_plot_data)
        plotNew.addAction('Dot Plot', self.get_plot_data)
        plotAdd = plotMenu.addMenu('&Add to')
        for j in self.mw.pwtitle:
            plotAdd.addAction(j, self.get_plot_data)

        self.show()

    def update_menubar(self):
        self.menubar.clear()
        self.create_menubar()

    def create_header(self):
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
        delete_column = header_menu.addAction('Diese Spalte löschen?')
        set_xy   = header_menu.addMenu('Setzen als:')
        set_x    = set_xy.addAction('X')
        set_y    = set_xy.addAction('Y')
        set_yerr = set_xy.addAction('Yerr')
        ac = header_menu.exec_(self.table.mapToGlobal(position))
        if ac == delete_column:
            selCol = sorted(set(index.column() for index in self.table.selectedIndexes()))
            cap = 0
            for j in selCol:
                del self.d['data%i'%(j-cap)]
                for k in range(j+1-cap, self.cols):
                    data_zs = self.d['data%i'%k]
                    self.d.update({'data%i'%(k-1) :(self.d['data%i'%k])})
                del self.d['data%i'%(self.cols-1)]
                self.table.removeColumn(j-cap)
                self.cols = self.cols - 1
                headers = [self.d['data%i'%k][1] + '(' + self.d['data%i'%k][2] + ')' for k in range(self.cols)]
                self.table.setHorizontalHeaderLabels(headers)
                cap +=1
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
            
    # A few shortcuts
    # Enter: go to the next row
    def keyPressEvent(self, event):
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
        p_home = '/home/simon/Daten'
        SaveFileName = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', p_home)
        if SaveFileName:
            SaveFileName = SaveFileName[0]
        else:
            return
        
        if SaveFileName[-4:] == '.txt':
            pass
        else:
            SaveFileName = str(SaveFileName) + '.txt'

        np.savetxt(SaveFileName, data, fmt = formattyp)	

    def load_file(self):
        #In case there already is data in the spreadsheet, ask if replace or added
        if any(self.d[j][3] != None for j in self.d.keys()):
            FrageErsetzen = QtWidgets.QMessageBox()
            FrageErsetzen.setIcon(QMessageBox.Question)
            FrageErsetzen.setWindowTitle('Eine kurze Frage')
            FrageErsetzen.setText('Es sind schon Daten geladen. Sollen diese Ersetzt werde?')
            buttonY = FrageErsetzen.addButton(QMessageBox.Yes)
            buttonY.setText('Ersetzen')
            buttonN = FrageErsetzen.addButton(QMessageBox.No)
            buttonN.setText('Hinzufügen')
            buttonC = FrageErsetzen.addButton(QMessageBox.Cancel)
            buttonC.setText('Abbrechen')
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
        p_home = '/home/simon/Daten/SFB920/19-11-18/Data_dbp_Var1'
        #dialog.setDirectory(p_home)
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
                        
    def get_plot_data(self):
        self.plot_data = []

        selCol = sorted(set(index.column() for index in self.table.selectedIndexes()))  #selected Columns

        # Decides if line of       
        action = self.sender()
        if action.text() == 'Line Plot':
            plot_type = '-'
        elif action.text() == 'Dot Plot':
            plot_type = 'o'
        else:
            plot_type = None        

        for j in selCol:
            if self.d['data%i'%j][2] != 'Y':
                print('Bitte nur y-Werte auswählen!')
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
                    print('Mindestens ein Datensatz Y hat keinen zugeordneten X Datensatz.')
                    return
                else:
                    pass

        if plot_type != None:
            self.new_pw_signal.emit()
        else:
            self.add_pw_signal.emit(action.text())

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

    def closeEvent(self, event):
        close = QMessageBox()
        close.setWindowTitle('Quit')
        close.setText("You sure?")
        close.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        close = close.exec()

        if close == QMessageBox.Yes:
            self.close_ss_signal.emit()
            event.accept()
        else:
            event.ignore()

#####################################################################################################################################################
### Plot
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

    ### Aufsummieren der FitFunktionen ###
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

#Creates a yellow dot around a selected data point
class DataPointPicker:
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

class MyCustomToolbar(NavigationToolbar): 
    def __init__(self, plotCanvas):
        NavigationToolbar.__init__(self, plotCanvas, parent=None)
        toolitems = [t for t in NavigationToolbar.toolitems]
        #figureoptions = toolitems[7]
	
class PlotWindow(QMainWindow):
    close_p_signal = QtCore.pyqtSignal()
    def __init__(self, plot_data, fig, parent):
        super(PlotWindow, self).__init__(parent)
        self.fig = fig
        self.data = plot_data
        self.backup_data = plot_data
        self.Spektrum = []
        self.functions = Functions(self)

        self.plot()
        self.create_statusbar()
        self.create_menubar()	
        self.create_toolbar()

        #self.cid1 = self.fig.canvas.mpl_connect('button_press_event', self.mousePressEvent)
        self.cid2 = self.fig.canvas.mpl_connect('key_press_event', self.keyPressEvent)
        self.cid3 = self.fig.canvas.mpl_connect('pick_event', self.pickEvent)

    def plot(self):
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        layout = QtWidgets.QVBoxLayout(self._main)
       
        if self.fig == None:
            self.fig = Figure(figsize=(15,9))
            self.ax = self.fig.add_subplot()
            self.Canvas = FigureCanvas(self.fig)
            layout.addWidget(self.Canvas)
            self.addToolBar(MyCustomToolbar(self.Canvas))
            for j in self.data:
                if isinstance(j[5], (np.ndarray, np.generic)):
                    self.Spektrum.append(self.ax.errorbar(j[0], j[1], label = j[2], fmt = j[4], yerr = j[5], picker = 5)[0])
                else:
                    self.Spektrum.append(self.ax.plot(j[0], j[1], j[4], label = j[2], picker = 5)[0])
            legend = self.ax.legend(fontsize = 17)
            self.ax.set_xlabel('Raman shift / cm⁻¹', fontsize = 17)
            self.ax.set_ylabel('Intensity / cts/s', fontsize = 17)
        else:
            self.ax = self.fig.axes[0]
            self.Canvas = FigureCanvas(self.fig)
            layout.addWidget(self.Canvas)
            self.addToolBar(NavigationToolbar(self.Canvas, self))
            for j in self.ax.lines:
                self.Spektrum.append(j)
            self.ax.get_legend()

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
        key = event.key()
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

        ### 2. Menüpunkt: Edit  ###
        editMenu = menubar.addMenu('&Edit')
        editMenu.addAction('Delete broken pixel - LabRam', self.delete_datapoint)
        editDeletePixel = editMenu.addAction('Delete single pixel', self.delete_pixel)
        editDeletePixel.setStatusTip('Delete selected data point with Enter, Move with arrow keys, Press c to leave Delete-Mode')
        editSelectArea = editMenu.addAction('Define data area', self.DefineArea)
        editSelectArea.setStatusTip('Move area limit with left mouse click, set it fix with right mouse click')        
        editNormAct = editMenu.addAction('Normalize Spectrum', self.normalize)
        editNormAct.setStatusTip('Normalizes highest peak to 1')

        ### 3. Menüpunkt: Analysis      ###
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

    def create_toolbar(self):
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
 
        self.show()

    ########## Functions and other stuff ##########

    def SelectDataset(self):
        self.Dialog_SelDataSet = QDialog()
        layout = QtWidgets.QGridLayout()
        self.CheckDataset = []
        for j in range(len(self.data)):
            self.CheckDataset.append(QCheckBox(self.data[j][2], self))
            layout.addWidget(self.CheckDataset[j], j, 0)
        ok_button = QPushButton("ok", self.Dialog_SelDataSet)
        layout.addWidget(ok_button, len(self.data), 0)
        ok_button.clicked.connect(self.Ok_button)
        self.Dialog_SelDataSet.setLayout(layout)
        self.Dialog_SelDataSet.setWindowTitle("Dialog")
        self.Dialog_SelDataSet.setWindowModality(Qt.ApplicationModal)
        self.Dialog_SelDataSet.exec_()

    def Ok_button(self):
        self.selectedDatasetNumber = []
        self.selectedData = []
        for j in range(len(self.CheckDataset)):
            if self.CheckDataset[j].isChecked():
                self.selectedDatasetNumber.append(j)
                self.selectedData.append(self.data[j])
            else:
                pass
        self.Dialog_SelDataSet.close()

    def menu_save_to_file(self):
        self.SelectDataset()
        
        for j in range(len(self.selectedData)):
            startFileDirName = os.path.dirname(self.selectedData[j][3])
            startFileName = startFileDirName + '/' + self.selectedData[j][2]
            save_data = [self.selectedData[j][0], self.selectedData[j][1]]
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

    ### Löscht die Datenpunkte Nr. 630+n*957, da dieser Pixel im CCD Detektor kaputt ist
    def delete_datapoint(self):
        self.SelectDataset()
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

        okbutton = QPushButton('Ok', self)
        okbutton.setToolTip('Do you want to try the fit parameters? \n Lets do it!')
        okbutton.clicked.connect(lambda: self.baseline_als_call(x, y, float(p_edit.text()), float(lam_edit.text())))
        layout.addWidget(okbutton, 2, 0)

        self.finishbutton = QPushButton('Finish', self)       
        self.finishbutton.setCheckable(True)
        self.finishbutton.setToolTip('Are you happy with the start parameters? \n Close the dialog window and save the baseline!')
        self.finishbutton.clicked.connect(lambda: self.baseline_als_call(x, y, float(p_edit.text()), float(lam_edit.text())))
        layout.addWidget(self.finishbutton, 2, 1)

        self.closebutton = QPushButton('Close', self)
        self.closebutton.setCheckable(True)
        self.closebutton.setToolTip('Closes the dialog window and baseline is not saved.')
        self.closebutton.clicked.connect(lambda: self.baseline_als_call(x, y, float(p_edit.text()), float(lam_edit.text())))
        layout.addWidget(self.closebutton, 2, 2)

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
	
    # Teilweise nachprogrammiert nach Mathematica Notebook von Christian
    # Fitroutine für D und G Bande in Kohlenstoffverbindungen
    def fitroutine1(self):
        # Auswählen an welchem Datensetz Fit-Routine durchgeführt werden soll (erstmal nur für einen Datensatz pro Durchgang möglich)
        self.SelectDataset()
        x = self.selectedData[0][0]
        y = self.selectedData[0][1]
      
        #Bereich für Untergrundkorrektur definineren
        x_min =  200
        x_max = 4000

        #Daten auf Fitbereich begrenzen 
        working_x = x[np.where((x > x_min)&(x < x_max))]
        working_y = y[np.where((x > x_min)&(x < x_max))]
 
        # parameter for background-correction 
        p   = 0.0001             #asymmetry 0.001 ≤ p ≤ 0.1 is a good choice     recommended from Eilers and Boelens for Raman: 0.001    recommended from Simon: 0.0001 
        lam = 10000000           #smoothness 10^2 ≤ λ ≤ 10^9                     recommended from Eilers and Boelens for Raman: 10⁷      recommended from Simon: 10⁷
       
        xb, yb, zb = self.baseline_als(working_x, working_y, p, lam)
        self.baseline,    = self.ax.plot(xb, zb, 'c--', label = 'baseline (' + self.selectedData[0][2] + ')')
        self.blcSpektrum, = self.ax.plot(xb, yb, 'c-', label = 'baseline-corrected '+ self.selectedData[0][2])
        self.ax.figure.canvas.draw()

        #Fitbereich definineren
        x_min =  850 
        x_max = 2000
        #Daten auf Fitbereich begrenzen 
        working_x = xb[np.where((xb > x_min)&(xb < x_max))]
        working_y = yb[np.where((xb > x_min)&(xb < x_max))]

        #Fit der D und G Bande
        #D-Bande: Lorentz
        #G-Bande: BreitWignerFano
        self.anzahl_Lorentz = 1   # Anzahl Lorentz
        self.anzahl_Gauss   = 0   # Anzahl Gauß
        self.anzahl_BWF     = 1   # Anzahl Breit-Wigner-Fano

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

        #Grenzen
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
    def scale_spectrum(self):
        self.SelectDataset()
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
        self.SelectDataset()
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
        pts = self.fig.ginput(2)
        drawLine = self.ax.plot([pts[0][0], pts[1][0]], [pts[0][1], pts[1][1]], 'r', lw=2)
        canvas = self.Canvas
        self.ax.figure.canvas.draw()    

    def closeEvent(self, event):
        close = QMessageBox()
        close.setWindowTitle('Quit')
        close.setText("You sure?")
        close.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        close = close.exec()

        if close == QMessageBox.Yes:
            self.close_p_signal.emit()
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    MW = MainWindow()
    MW.showMaximized()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
