# author: Simon Brehm
import io
import json
import math
import matplotlib
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import numpy as np
import operator
import os
import pickle
import prettytable
import rampy as rp
import re
import scipy
import sys
import glob
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
import matplotlib.backends.qt_editor.figureoptions as figureoptions
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QMessageBox, QCheckBox,
                             QTreeWidgetItem, QTableWidgetItem, QPushButton, QWidget, QMenu,
                             QAction, QDialog, QFileDialog, QAbstractItemView)
from matplotlib.backends.qt_editor import _formlayout as formlayout
from scipy import signal, stats
from scipy.optimize import curve_fit
from sklearn import decomposition


# Import files
import myfigureoptions
import databaseMeasurements
import analysisRoutine
from BrokenAxes import brokenaxes
import databaseSpectra
import analysisMethods
import peakFitting

# This file essentially consists of four parts:
# 1. Main Window
# 2. Text Window
# 3. Spreadsheet
# 4. Plot

########################################################################################################################
# 1. Main window
########################################################################################################################


class RamanTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    """
        A reimplementation of the PyQt QTreeWidgetItem.
    """
    def __init__(self, parent=None):
        """
        Parameters
        ----------
        parent : class, optional
            (default is None)
        """
        super(RamanTreeWidgetItem, self).__init__(parent)

    def mouseMoveEvent(self, event):
        """mouse move event with implemented drag functionality (https://doc.qt.io/qtforpython/overviews/dnd.html)"""
        if event.buttons() == QtCore.Qt.LeftButton:
            drag = QtGui.QDrag(self)
            mime = QtCore.QMimeData()
            drag.setMimeData(mime)

            pixmap = QtGui.QPixmap(self.size())
            self.render(pixmap)
            drag.setPixmap(pixmap)
            drag.exec_(QtCore.Qt.CopyAction)


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
        item, which was selected by a mouseclick

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

        self.dragged_item = None

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
        Parameters
        ---------
        event : QDropEvent
        """
        event.setDropAction(Qt.MoveAction)
        item_at_drop_location = self.itemAt(event.pos())

        if item_at_drop_location is None:
            # no drops outside of folders
            return
        elif item_at_drop_location != self.dragged_item.parent():
            # send signal if parents (folder) of item changes during drag-drop-event
            self.itemDropped.emit(self.dragged_item, item_at_drop_location)

        # keep the default behaviour
        super(RamanTreeWidget, self).dropEvent(event)

        if self.dragged_item.parent() is None:
            print("The item was dropped outside a folder. This will cause some issues")
            item_at_drop_location.addChild(self.dragged_item)
            item_at_drop_location.setExpanded(True)


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
        self.treeWidget = RamanTreeWidget(self)  # Qtreewidget, to control open windows
        self.tabWidget = QtWidgets.QTabWidget()
        self.statusBar = QtWidgets.QStatusBar()

        self.create_mainwindow()

    def create_mainwindow(self):
        """
        Create the main window
        """
        self.setWindowIcon(self.PyramanIcon)
        self.setWindowTitle("PyRamanGui")  # set window title

        # the user can control the size of child widgets by dragging the boundary between them
        self.mainWidget.setHandleWidth(10)

        self.tabWidget.setTabsClosable(True)
        self.tabWidget.setMovable(True)
        self.tabWidget.tabCloseRequested.connect(self.close_tab)
        self.treeWidget.itemDoubleClicked.connect(self.activate_window)
        self.treeWidget.itemClicked.connect(self.tree_window_options)
        self.treeWidget.itemDropped.connect(self.change_folder)
        self.create_new_folder(None)

        self.mainWidget.addWidget(self.treeWidget)
        self.mainWidget.addWidget(self.tabWidget)
        self.setCentralWidget(self.mainWidget)

        self.setStatusBar(self.statusBar)
        self.show_statusbar_message("Welcome to PyRamanGui", 3000)

        self.create_menubar()

    def create_menubar(self):
        """
        create a menu bar
        """
        menu = self.menuBar()
        File = menu.addMenu("File")
        File.addAction("Open Project", self.open)
        File.addAction("Save Project As ...", lambda: self.save("Save As"))
        File.addAction("Save Project", lambda: self.save("Save"))
        FileNew = File.addMenu("New")
        FileNew.addAction("Spreadsheet", lambda: self.new_window(None, "Spreadsheet", None, None))
        FileNew.addAction("Textwindow", lambda: self.new_window(None, "Textwindow", "", None))
        FileNew.addAction("Folder", lambda: self.create_new_folder(None))

        medit = menu.addMenu("Edit")
        medit.addAction("Cascade")
        medit.addAction("Tiled")
        medit.triggered[QAction].connect(self.rearrange)

        menu_tools = menu.addMenu("Tools")
        menu_tools.addAction("Database for measurements", self.execute_database_measurements)

    def show_statusbar_message(self, message, time, error_sound=False):
        self.statusBar.showMessage(message, time)

    def keyPressEvent(self, event):
        """
        A few shortcuts
        """
        key = event.key()
        if key == (Qt.Key_Control and Qt.Key_S):
            self.save("Save")
        else:
            super(MainWindow, self).keyPressEvent(event)

    def open(self):
        # Load project in new MainWindow or in existing MW, if empty
        if self.window["Spreadsheet"] == {} and self.window["Plotwindow"] == {}:
            self.load()
        else:
            new_MainWindow()

    def load(self):
        """
        Load project from rmn file with json
        @return: None
        """
        # get file name
        file_name = QtWidgets.QFileDialog.getOpenFileName(self, "Load",
                                                          self.pHomeRmn, "All Files (*);;Raman Files (*.rmn)")

        if file_name[0] != "":  # if fileName is not empty save in pHomeRmn
            self.pHomeRmn = file_name[0]
        else:
            self.close()
            return

        # open file and save content in variable 'v' with json
        with open(self.pHomeRmn, "rb") as file:
            v = json.load(file)

        self.treeWidget.clear()
        self.tabWidget.clear()
        self.folder = {}
        for folder_name, folder_content in v.items():
            self.create_new_folder(folder_name)
            for key, val in folder_content.items():
                self.new_window(folder_name, val[0], val[1], key)

    def save(self, q):
        """
        function to save complete project in json-File

        Parameters:
        -----------
        q: str

        """

        # Ask for directory, if none is deposit or 'Save Project As' was pressed
        if self.pHomeRmn is None or q == "Save As":
            file_name = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save as", self.pHomeRmn, "All Files (*);;Raman Files (*.rmn)")

            if file_name[0] != "":
                self.pHomeRmn = file_name[0]
            else:
                return

        # get data, which should be saved
        save_dict_json = {}
        save_dict = {}
        for key, val in self.folder.items():
            save_dict[key] = {}
            save_dict_json[key] = {}
            for j in range(val[0].childCount()):
                win_name = val[0].child(j).text(0)
                win_type = self.window_types[val[0].child(j).type()]
                window = self.window[win_type][win_name]
                window_content = None
                window_content_json = None
                if win_type == "Spreadsheet":
                    window_content = window.data
                    window_content_json = window.data.copy()
                    for i in range(len(window_content)):
                        window_content_json[i]["data"] = list(window_content_json[i]["data"])
                elif win_type == "Plotwindow":
                    window_content_json = self.get_save_data_plotwindow(window)
                    window_content = [window.data, window.fig]
                elif win_type == "Textwindow":
                    window_content_json = window.text
                    window_content = window.text
                save_dict[key][win_name] = [win_type, window_content]
                save_dict_json[key][win_name] = [win_type, window_content_json]

        # save with json
        with open(os.path.splitext(self.pHomeRmn)[0] + ".jrmn", "w", encoding="utf-8") as f:
            json.dump(save_dict_json, f, ensure_ascii=False)

        self.show_statusbar_message("The project was saved", 2000)

    def get_save_data_plotwindow(self, window):
        """Get all data and parameter from plot window and store it in dictionary, which will be saved with json"""

        # get data from plotwindow
        data_keys = ["plot type", "label", "xaxis", "yaxis", "filename", "spreadsheet title"]

        # change all numpy arrays to lists, since "Object of type ndarray is not JSON serializable" (TypeError)
        window_data = []
        for i in range(len(window.data)):
            window_data.append({})
            window_data[i]["x"] = list(window.data[i]["x"])
            window_data[i]["y"] = list(window.data[i]["y"])
            window_data[i]["yerr"] = None
            if isinstance(window.data[i]["yerr"], int):
                window.data[i]["yerr"] = None
            if window.data[i]["yerr"] is not None:
                window_data[i]["yerr"] = list(window.data[i]["yerr"])
            for dk in data_keys:
                window_data[i][dk] = window.data[i][dk]

        # necessary for some y data, can be removed later
        for wd in window_data:
            if isinstance(wd["y"][0], np.ndarray):
                wd["y"] = [y[0] for y in wd["y"]]

        # get all arrows and texts in plot window
        annotations = {"arrows": [], "text": []}
        for dl in window.drawn_line:
            annotations["arrows"].append({"posA": list(dl.posA),
                                          "posB": list(dl.posB),
                                          "style": dl.arrow_style,
                                          "head width": dl.head_width,
                                          "head length": dl.head_length,
                                          "line width": dl.line_width,
                                          "line style": dl.line_style,
                                          "color": dl.color})

        for t in window.inserted_text:
            annotations["text"].append({"text": t.text,
                                        "position": t.position,
                                        "font size": t.font_size,
                                        "color": t.color})

        # get all figure settings
        fig = window.fig
        axes = fig.get_axes()

        # check if axis is broken
        axis_break = False
        if len(axes) == 1:
            ax, = axes
            ax1 = ax
            axl = ax
        else:
            ax = axes[0]  # main axis
            ax1 = axes[1]  # axis of first segment
            axl = axes[-1]  # axis of last segment
            axis_break = True

        # get general figure settings
        xticks = ax1.get_xticks()
        yticks = ax1.get_yticks()

        if xticks.size > 1:
            xtickspace = xticks[1] - xticks[0]
        else:
            xtickspace = None
        if yticks.size > 1:
            ytickspace = yticks[1] - yticks[0]
        else:
            ytickspace = None

        if 'labelsize' in ax1.xaxis._major_tick_kw:
            _ticksize = int(ax1.xaxis._major_tick_kw['labelsize'])
        else:
            _ticksize = 15

        axis_options = {
            'axis break': axis_break,
            'x scale': ax1.get_xscale(),
            'x lower limit': ax1.get_xlim()[0],
            'x upper limit': ax1.get_xlim()[1],
            'x tick step size': xtickspace,
            'y scale': ax1.get_yscale(),
            'y lower limit': ax1.get_ylim()[0],
            'y upper limit': ax1.get_ylim()[1],
            'y tick step size': ytickspace
        }

        if axis_break:
            axis_options["x lower limit 2"] = axl.get_xlim()[0]
            axis_options["x upper limit 2"] = axl.get_xlim()[1]

        general = {
            'title': ax.get_title(),
            'title font size': int(ax.title.get_fontsize()),
            'label font size': int(ax.xaxis.label.get_fontsize()),
            'tick size': _ticksize,
            'grid': ax.xaxis._major_tick_kw['gridOn'],
            'x label': ax.get_xlabel(),
            'x label pad': ax.xaxis.labelpad,
            'y label': ax.get_ylabel(),
            'y label pad': ax.yaxis.labelpad
        }

        if ax.legend_ is not None:
            old_legend = ax.get_legend()
            _visible = old_legend._visible
            _draggable = old_legend._draggable is not None
            try:
                # dependent on matplotlib version (>= 3.6.0 _ncols else _ncol)
                _ncol = old_legend._ncol
            except AttributeError:
                _ncol = old_legend._ncols
            _fontsize = int(old_legend._fontsize)
            _frameon = old_legend.get_frame_on()
            _shadow = old_legend.shadow
            _fancybox = type(old_legend.legendPatch.get_boxstyle()) == matplotlib.patches.BoxStyle.Round
            _framealpha = old_legend.get_frame().get_alpha()
            _picker = 5
        else:
            _visible = True
            _draggable = False
            _ncol = 1
            _fontsize = 15
            _frameon = True
            _shadow = True
            _fancybox = True
            _framealpha = 0.5
            _picker = 5

        legend = {
            'visible': _visible,
            'draggable': _draggable,
            'columns': _ncol,
            'font size': _fontsize,
            'frame': _frameon,
            'shadow': _shadow,
            'fancy box': _fancybox,
            'alpha': _framealpha,
            'picker': _picker
        }

        # get all style elements of curves
        for i, wd in enumerate(window.data):
            if "line" in window.data[i].keys():
                if isinstance(window.data[i]["line"], dict):
                    wd["line options"] = window.data[i]["line"]
                else:
                    line = window.data[i]["line"]
                    window.data[i]["label"] = line.get_label()
                    window_data[i]["label"] = line.get_label()
                    alpha = line.get_alpha()
                    color = mcolors.to_hex(mcolors.to_rgba(line.get_color(), alpha), keep_alpha=True)
                    ec = mcolors.to_hex(mcolors.to_rgba(line.get_markeredgecolor(), alpha), keep_alpha=True)
                    fc = mcolors.to_hex(mcolors.to_rgba(line.get_markerfacecolor(), alpha), keep_alpha=True)
                    curvedata = {
                        "line style": line.get_linestyle(),
                        "draw style": line.get_drawstyle(),
                        "line width": line.get_linewidth(),
                        "color": color,
                        "marker style": line.get_marker(),
                        "marker size": line.get_markersize(),
                        "marker face color": fc,
                        "marker edge color": ec}
                    window_data[i]["line options"] = curvedata

        # get styles for error bars
        for container in ax1.containers:
            if type(container) == matplotlib.container.ErrorbarContainer:
                plotline, caplines, barlinecols = container
                try:
                    idx = 0
                    for i, wd in enumerate(window.data):
                        if plotline == wd["line"]:
                            idx = i
                            break
                    # idx = [window.data.index(wd) for wd in window.data if plotline == wd["line"]][0]
                except KeyError as e:
                    print(e)
                    print(window.data)
                    continue
                error_color = mcolors.to_hex(
                    mcolors.to_rgba(caplines[0].get_markerfacecolor(), barlinecols[0].get_alpha()), keep_alpha=True)
                window_data[idx]["line options"]["error bar cap size"] = caplines[0].get_markersize()
                window_data[idx]["line options"]["error bar line width"] = caplines[0].get_markeredgewidth()
                window_data[idx]["line options"]["error bar color"] = error_color

        figure_settings = {"general": general, "axis options": axis_options, "legend": legend}
        save_data = [window_data, {"figure settings": figure_settings, "annotations": annotations}]

        return save_data

    def execute_database_measurements(self):
        title = 'Database'
        self.db_measurements = databaseMeasurements.DatabaseMeasurements()
        DBM_tab = self.tabWidget.addTab(self.db_measurements, self.PyramanIcon, title)

    def create_sidetree_structure(self, structure):
        self.treeWidget.clear()
        for key, val in structure.items():
            self.create_new_folder(key)

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
                tree_item_menu = QMenu()
                act_rename = tree_item_menu.addAction('Rename')
                act_delete = tree_item_menu.addAction('Delete')
                act_copy = tree_item_menu.addAction('Copy')
                ac = tree_item_menu.exec_(self.treeWidget.mapToGlobal(event.pos()))
                window_type = self.window_types[tree_item.type()]

                if ac == act_rename:
                    self.treeWidget.editItem(tree_item)
                    self.treeWidget.itemChanged.connect(lambda item, column:
                                                        self.rename_window(item, column, item_text))
                elif ac == act_delete:
                    if tree_item.type() == 0:  # if item is folder:
                        self.close_folder(foldername=tree_item.text(0))
                    else:
                        title = tree_item.text(0)
                        self.windowWidget[window_type][title].close()
                elif ac == act_copy:
                    window_name = tree_item.text(0)
                    window = self.window[window_type][window_name]
                    if window_type == "Spreadsheet":
                        data = [window_type, window.data.copy()]
                    elif window_type == "Plotwindow":
                        # no deepcopy of figure possible => create new figure with pickle
                        buf = io.BytesIO()
                        try:
                            pickle.dump(window.fig, buf)
                        except TypeError as e:
                            print(e)
                            print("Try to set the legend not-draggable")
                            return
                        buf.seek(0)
                        fig_copy = pickle.load(buf)
                        data = [window_type, [window.data.copy(), fig_copy]]
                    elif window_type == "Textwindow":
                        data = [window_type, window.text]
                    else:
                        return
                    folder_name = self.tabWidget.tabText(self.tabWidget.currentIndex())
                    self.new_window(folder_name, data[0], data[1], window_name + "_Copy")
        else:
            if event.button() == QtCore.Qt.RightButton:
                tree_item_menu = QMenu()
                MenuNew = tree_item_menu.addMenu('&New')
                ActNewFolder = MenuNew.addAction('Folder')
                ActNewSpreadsheet = MenuNew.addAction('Spreadsheet')
                ActNewText = MenuNew.addAction('Text window')
                ac = tree_item_menu.exec_(self.treeWidget.mapToGlobal(event.pos()))
                # Rename
                if ac == ActNewFolder:
                    self.create_new_folder(None)
                elif ac == ActNewSpreadsheet:
                    self.new_window(None, 'Spreadsheet', None, None)
                elif ac == ActNewText:
                    self.new_window(None, 'Textwindow', '', None)

    def change_folder(self, dropped_item, item_at_drop_location):
        """function is called every time a qtreewidgetitem is dropped"""
        if item_at_drop_location.parent() is None:
            new_folder = item_at_drop_location
        else:
            new_folder = item_at_drop_location.parent()
        foldername = new_folder.text(0)
        windowtyp = dropped_item.type()
        windowname = dropped_item.text(0)
        if new_folder.type() == 0 and dropped_item.type() != 0:  # drop event in folder
            try:
                previous_folder = dropped_item.parent().text(0)
            except AttributeError as e:
                print("This shouldn't happen \n", e)
                return
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

    def rearrange(self, q):
        # rearrange open windows
        if q.text() == "Cascade":
            self.tabWidget.currentWidget().cascadeSubWindows()

        if q.text() == "Tiled":
            self.tabWidget.currentWidget().tileSubWindows()

    def create_figure(self, settings_dictionary, data):
        fig = Figure(figsize=(15, 9))
        ax = fig.add_subplot(111)

        figure_settings = settings_dictionary["figure settings"]

        # Set general figure settings
        general = figure_settings["general"]

        ax.set_title(general["title"])
        ax.title.set_fontsize(general["title font size"])

        ax.set_xlabel(general["x label"])
        ax.xaxis.labelpad = general["x label pad"]
        ax.set_ylabel(general["y label"])
        ax.yaxis.labelpad = general["y label pad"]
        ax.xaxis.label.set_size(general["label font size"])
        ax.yaxis.label.set_size(general["label font size"])

        axis_option = figure_settings["axis options"]

        if ax.get_xscale() != axis_option["x scale"]:
            ax.set_xscale(axis_option["x scale"])
        if ax.get_yscale() != axis_option["y scale"]:
            ax.set_yscale(axis_option["y scale"])

        if axis_option["x tick step size"] is not None:
            x_tick = axis_option["x tick step size"]
            xtick_space_start = math.ceil(axis_option["x lower limit"] / x_tick) * x_tick
            ax.xaxis.set_ticks(np.arange(xtick_space_start, axis_option["x upper limit"], x_tick))
            ax.xaxis.set_ticks(np.arange(xtick_space_start, axis_option["x upper limit"], x_tick))
        ax.set_xlim(axis_option["x lower limit"], axis_option["x upper limit"])
        ax.xaxis.set_tick_params(labelsize=general["tick size"])

        if axis_option["y tick step size"] is not None:
            y_tick = axis_option["y tick step size"]
            ytick_space_start = math.ceil(axis_option["y lower limit"] / y_tick) * y_tick
            ax.yaxis.set_ticks(np.arange(ytick_space_start, axis_option["y upper limit"], y_tick))
        ax.set_ylim(axis_option["y lower limit"], axis_option["y upper limit"])
        ax.yaxis.set_tick_params(labelsize=general["tick size"])

        ax.grid(general["grid"])

        # plot data in figure
        for d in data:
            if d["yerr"] is not None:  # errorbars
                if d["plot type"] is None:
                    d["plot type"] = "o"
                (spect, caplines, barlinecol) = ax.errorbar(d["x"], d["y"], yerr=d["yerr"], fmt=d["plot type"],
                                                            picker=True, pickradius=5, capsize=3,
                                                            label="_Hidden errorbar {}".format(d["label"]))
                spect.set_label(d["label"])
                if "line options" in d.keys():
                    if "error bar line width" in d["line options"].keys():
                        dlo = d["line options"]
                        for capline in caplines:
                            capline.set_markersize(dlo["error bar cap size"])
                            capline.set_markeredgewidth(dlo["error bar line width"])
                            capline.set_markerfacecolor(dlo["error bar color"])
                            capline.set_markeredgecolor(dlo["error bar color"])
                        barlinecol[0].set_linewidth(dlo["error bar line width"])
                        barlinecol[0].set_color(dlo["error bar color"])
                else:
                    print("no line options")

            else:
                try:
                    spect, = ax.plot(d["x"], d["y"], d["plot type"], label=d["label"], picker=True, pickradius=5)
                except ValueError as e:
                    print(e)
                    print(d["label"])
                    if d["plot type"] is None:
                        d["plot type"] = "-"
                        spect, = ax.plot(d["x"], d["y"], d["plot type"], label=d["label"], picker=True, pickradius=5)
            if "line options" in d.keys():
                line_options = d["line options"]
                spect.set_linestyle(line_options["line style"])
                spect.set_drawstyle(line_options["draw style"])
                spect.set_linewidth(line_options["line width"])
                rgba = mcolors.to_rgba(line_options["color"])
                spect.set_alpha(None)
                spect.set_color(rgba)
                if line_options["marker style"] != "none":
                    spect.set_marker(line_options["marker style"])
                    spect.set_markersize(line_options["marker size"])
                    spect.set_markerfacecolor(line_options["marker face color"])
                    spect.set_markeredgecolor(line_options["marker edge color"])
            else:
                print("no line options in dict")
            d["line"] = spect

        if axis_option["axis break"]:
            baxes = brokenaxes(xlims=((axis_option["x lower limit"], axis_option["x upper limit"]),
                              (axis_option["x lower limit 2"], axis_option["x upper limit 2"])), fig=fig)
            for d in data:
                for ol, nl in zip(baxes.old_lines, baxes.new_lines[0]):
                    if ol == d["line"]:
                        d["line"] = nl

            handles, labels = fig.axes[2].get_legend_handles_labels()
        else:
            handles, labels = ax.get_legend_handles_labels()

        # Set legend
        legend = figure_settings["legend"]

        new_legend = ax.legend(handles, labels,
                               ncol=legend["columns"],
                               fontsize=float(legend["font size"]),
                               frameon=legend["frame"],
                               shadow=legend["shadow"],
                               framealpha=legend["alpha"],
                               fancybox=legend["fancy box"])

        new_legend.set_visible(legend["visible"])
        new_legend.set_picker(legend["picker"])
        new_legend.set_draggable(legend["draggable"])

        # insert text and arrows
        for a in settings_dictionary["annotations"]["arrows"]:
            arrow = mpatches.FancyArrowPatch(a["posA"], a["posB"], mutation_scale=10, picker=50)
            arrow.set_linewidth(a["line width"])
            arrow.set_linestyle(a["line style"])
            arrow.set_color(a["color"])
            if a["style"] != '-':
                arrow.set_arrowstyle(a["style"], head_length=a["head length"], head_width=a["head width"])
            else:
                arrow.set_arrowstyle(a["style"])
            arrow.set_figure(fig)
            ax.add_patch(arrow)
        for t in settings_dictionary["annotations"]["text"]:
            ax.annotate(t["text"], t["position"], picker=True, fontsize=t["font size"], color=t["color"])
        return fig

    def new_window(self, folder_name, window_type, window_content, title):
        if folder_name is None:
            folder_name = self.tabWidget.tabText(self.tabWidget.currentIndex())
            if folder_name == "Database":
                self.show_statusbar_message("Please open window in other folder", 4000)
                return

        # if new window has no title, create one
        if title is None:
            i = 1
            while i <= 100:
                title = window_type + " " + str(i)
                if title in self.window[window_type].keys():
                    i += 1
                else:
                    break

        if window_type == "Spreadsheet":
            if window_content is not None:
                for i in range(len(window_content)):
                    window_content[i]["data"] = np.array(window_content[i]["data"])

            windowtypeInt = 1
            self.window[window_type][title] = SpreadSheetWindow(window_content, parent=self)
            new_spreadsheet = self.window[window_type][title]
            new_spreadsheet.new_pw_signal.connect(lambda: self.new_window(
                None, "Plotwindow", [new_spreadsheet.plot_data, None], None))
            new_spreadsheet.add_pw_signal.connect(lambda pw_name: self.add_Plot(pw_name, new_spreadsheet.plot_data))
            icon = QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/Icon_spreadsheet.png")
        elif window_type == "Plotwindow":
            windowtypeInt = 2
            plot_data, fig = window_content

            if isinstance(fig, dict):
                fig = self.create_figure(fig, plot_data)
            if not plot_data:
                self.show_statusbar_message("Please select the columns you want to plot!", 4000)
                return

            if fig is not None:
                # necessary to avoid weird error:
                fig.set_size_inches(10, 10)

            # make plotData list to numpy array, since its easier to work with
            for pd in plot_data:
                pd["x"] = np.array(pd["x"])
                pd["y"] = np.array(pd["y"])

            self.window[window_type][title] = PlotWindow(plot_data, fig, self)

            self.update_spreadsheet_menubar()
            icon = QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/Icon_plotwindow.png")
        elif window_type == "Textwindow":
            windowtypeInt = 3
            txt = window_content
            self.window[window_type][title] = TextWindow(self, txt)
            icon = QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/Icon_textwindow.png")
        else:
            return

        self.windowWidget[window_type][title] = self.folder[folder_name][1].addSubWindow(
            self.window[window_type][title])
        self.window[window_type][title].setWindowTitle(title)
        self.window[window_type][title].show()

        item = QTreeWidgetItem([title], type=windowtypeInt)
        item.setIcon(0, icon)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled |
                      Qt.ItemIsUserCheckable)

        self.folder[folder_name][0].addChild(item)
        self.window[window_type][title].closeWindowSignal.connect(self.close_window)

    def create_new_folder(self, title):
        if title is None:
            i = 1
            while i <= 100:
                title = "Folder " + str(i)
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
            j[4] = self.window['Plotwindow'][pw_name].data[0]["line"].get_linestyle()
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


########################################################################################################################
# 2. Text - Window
########################################################################################################################

class TextWindow(QMainWindow):
    closeWindowSignal = QtCore.pyqtSignal(str, str)

    def __init__(self, mainwindow, text, parent=None):
        super(TextWindow, self).__init__(parent)
        self.text = text
        self.mw = mainwindow

        self.menubar = None
        self.textfield = None

        self.create_textwidget()
        self.create_menubar()
        self.show()

    def create_textwidget(self):
        self.textfield = QtWidgets.QPlainTextEdit()
        self.textfield.setPlainText(self.text)
        self.textfield.createStandardContextMenu()
        # set tab size to 4 spaces
        self.textfield.setTabStopDistance(QtGui.QFontMetricsF(self.textfield.font()).horizontalAdvance(' ') * 4)
        self.textfield.setUndoRedoEnabled(True)
        self.textfield.setShortcutEnabled(True)
        self.setCentralWidget(self.textfield)
        self.textfield.textChanged.connect(self.text_change)

    def create_menubar(self):
        # create the menubar
        self.menubar = self.menuBar()

        # 1. Menu item: File
        fileMenu = self.menubar.addMenu("&File")
        fileMenu.addAction("Save Text", self.file_save)
        fileMenu.addAction("Load Text", self.load_file)

    def text_change(self):
        self.text = self.textfield.toPlainText()

    def file_save(self):
        fileName = QtWidgets.QFileDialog.getSaveFileName(self, "Save", filter="All Files (*);; Txt Files (*.txt)")

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
        fileName = QtWidgets.QFileDialog.getOpenFileName(self, "Load", filter="All Files (*);; Txt Files (*.txt)")

        if fileName[0] != "":
            fileName = fileName[0]
        else:
            return

        file = open(fileName, "rb")
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


########################################################################################################################
# 3. Spreadsheet
########################################################################################################################

class DataImportDialog(QMainWindow):
    closeSignal = QtCore.pyqtSignal()

    def __init__(self, parent, data):
        """
        options dialog for spreadsheet data import

        Parameters
        ----------
        parent: spreadsheet window object
        """
        super(DataImportDialog, self).__init__(parent=parent)
        self.parent = parent
        self.data = data
        self.cols = len(self.data)
        self.cols_before = self.cols
        self.rows = max([len(d["data"]) for d in self.data])
        self.file_names = None
        self.delimiters = {
            "Tab/Space": None,      # default is any whitespace
            "Space": " ",
            "Tab": "    ",
            "Comma": ",",
            "Semicolon": ";"
        }

        self.comments = [
            "#",
            "%",
            "&",
            None
        ]

        self.main_layout = None
        self.box_add_or_replace = None
        self.box_delimiter = None
        self.box_skip_lines = None
        self.box_header = None
        self.box_comments = None
        self.label_filename = None
        self.ok_button = None
        self.cancel_button = None

        # create actual window
        self.create_dialog()

    def create_dialog(self):
        dialog_layout = QtWidgets.QGridLayout()

        n_rows = 0

        # In case there already is data in the spreadsheet, ask if replace or added
        if any(d["filename"] is not None for d in self.data):
            label_add_or_replace = QtWidgets.QLabel("Add data to existing data? Or replace existing data")
            dialog_layout.addWidget(label_add_or_replace, n_rows, 0)
            self.box_add_or_replace = QtWidgets.QComboBox()
            self.box_add_or_replace.addItem("Add")
            self.box_add_or_replace.addItem("Replace")
            dialog_layout.addWidget(self.box_add_or_replace, n_rows, 1)
            n_rows += 1

        # get file name(s)
        self.label_filename = QtWidgets.QLabel("File name(s)")
        self.label_filename.setToolTip("One or several filenames")
        dialog_layout.addWidget(self.label_filename, n_rows, 0)
        button_filename = QtWidgets.QPushButton()
        icon = button_filename.style().standardIcon(getattr(QtWidgets.QStyle, "SP_FileDialogStart"))
        button_filename.setIcon(icon)
        button_filename.clicked.connect(self.get_file_name)
        dialog_layout.addWidget(button_filename, n_rows, 1)
        n_rows += 1

        # skip lines
        label_skip_lines = QtWidgets.QLabel("Skip lines at beginning")
        label_skip_lines.setToolTip("The number of lines to skip at the beginning of the file.")
        dialog_layout.addWidget(label_skip_lines, n_rows, 0)
        self.box_skip_lines = QtWidgets.QSpinBox()
        dialog_layout.addWidget(self.box_skip_lines, n_rows, 1)
        n_rows += 1

        # header
        label_header = QtWidgets.QLabel("Header")
        label_header.setToolTip("If checked, the first line after the first skipped lines is used as header.")
        dialog_layout.addWidget(label_header, n_rows, 0)
        self.box_header = QtWidgets.QCheckBox()
        dialog_layout.addWidget(self.box_header, n_rows, 1)
        n_rows += 1

        # comments
        label_comments = QtWidgets.QLabel("Comments")
        label_comments.setToolTip("The character used to indicate the start of a comment. "
                                  "All the characters occurring on a line after a comment are discarded.")
        dialog_layout.addWidget(label_comments, n_rows, 0)
        self.box_comments = QtWidgets.QComboBox()
        for d in self.comments:
            self.box_comments.addItem(d)
        # make only the last item editable
        self.box_comments.currentIndexChanged.connect(self.comment_editable)
        dialog_layout.addWidget(self.box_comments, n_rows, 1)
        n_rows += 1

        # get delimiter
        label_delimiter = QtWidgets.QLabel("Delimiter")
        label_delimiter.setToolTip("The character used to separate values.")
        dialog_layout.addWidget(label_delimiter, n_rows, 0)
        self.box_delimiter = QtWidgets.QComboBox()
        for d in self.delimiters.keys():
            self.box_delimiter.addItem(d)
        dialog_layout.addWidget(self.box_delimiter, n_rows, 1)
        n_rows += 1

        # cancel and ok button
        button_layout = QtWidgets.QHBoxLayout()

        self.ok_button = QtWidgets.QPushButton("Ok")
        self.ok_button.clicked.connect(self.apply_ok)
        button_layout.addWidget(self.ok_button)

        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.apply_cancel)
        button_layout.addWidget(self.cancel_button)

        # put main layout together
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.addLayout(dialog_layout)
        self.main_layout.addLayout(button_layout)

        # create placeholder widget
        widget = QtWidgets.QWidget()
        widget.setLayout(self.main_layout)
        self.setCentralWidget(widget)

        self.setWindowTitle("Data import")
        self.setWindowModality(QtCore.Qt.ApplicationModal)

    def comment_editable(self, index):
        if index == (self.box_comments.count()-1):
            self.box_comments.setEditable(True)
        else:
            self.box_comments.setEditable(False)

    def add_or_replace(self):
        if self.box_add_or_replace is None or self.box_add_or_replace.currentText() == "Replace":
            self.data = []
            self.cols = 0
            self.rows = 0

    def get_file_name(self):
        # file dialog to get file name
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setNameFilter("Data Files (*.txt *.asc *.csv)")
        dialog.setViewMode(QFileDialog.List)
        dialog.setDirectory(self.parent.pHomeTxt)
        if dialog.exec_():
            self.file_names = dialog.selectedFiles()
            text = ""
            for f in self.file_names:
                text += "{}\n".format(f)
            self.label_filename.setText(text)

    def get_comments(self):
        return self.box_comments.currentText()

    def get_delimiter(self):
        return self.delimiters.get(self.box_delimiter.currentText(), " ")

    def get_skip_header(self):
        return self.box_skip_lines.value()

    def get_names(self):
        if self.box_header.isChecked():
            return True
        else:
            return None

    def load_data(self):
        # load new data
        loaded_data = []
        n_lines = []
        delimiter = self.get_delimiter()
        skip_header = self.get_skip_header()
        names = self.get_names()
        comments = self.get_comments()
        header = []
        for j in range(len(self.file_names)):
            try:
                if comments is not None and comments != "":
                    dat = np.genfromtxt(self.file_names[j], delimiter=delimiter, skip_header=skip_header, names=names,
                                        dtype=float, comments=comments)
                else:
                    dat = np.genfromtxt(self.file_names[j], delimiter=delimiter, skip_header=skip_header, names=names,
                                        dtype=float)
                header.append(dat.dtype.names)
            except Exception as e:
                self.parent.mw.show_statusbar_message("The file couldn't be imported", 4000)
                print('{} \nThe file could not be imported, maybe the columns have different lengths'.format(e))
                return

            # transpose data (change rows and columns
            if names:
                data_transpose = []
                for dat_name in dat.dtype.names:
                    data_transpose.append(dat[dat_name])

            else:
                try:
                    data_transpose = np.transpose(dat)
                except IndexError as e:
                    print("The data format is not readable for PyRamanGui\n", e)
                    return

            if isinstance(data_transpose[0], float):
                data_transpose = [data_transpose, np.ones(len(data_transpose)) * np.nan]

            n_lines.append(len(data_transpose))
            loaded_data.append(data_transpose)

        # set header
        for k in range(len(self.file_names)):
            for j in range(n_lines[k]):
                if j == 0:
                    col_type = "X"
                else:
                    col_type = "Y"
                short_name = str(os.path.splitext(os.path.basename(self.file_names[k]))[0])
                self.data.append(self.parent.create_data(loaded_data[k][j], shortname=short_name,
                                                         column_type=col_type, filename=self.file_names[k]))
                if header[k] is not None:
                    self.data[-1]["longname"] = header[k][j]
            self.cols = self.cols + n_lines[k]

    def apply_cancel(self):
        self.closeSignal.emit()
        self.close()

    def apply_ok(self):
        """ ok was clicked"""
        # check if file was selected
        if self.file_names is None:
            self.parent.mw.show_statusbar_message("You have to select a file for import", 4000)
            return

        self.add_or_replace()
        self.cols_before = self.cols
        self.load_data()
        self.closeSignal.emit()
        self.close()


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
            if col_formula >= len(self.data):
                # in case there are not enough columns
                print('There is something wrong with the formula')
                return np.full(len(self.data[0]['data']), 0)
            return self.data[col_formula]['data']
        elif re.match(r'\A\(.+\)\Z', f) and self.parentheses_enclosed(f):  # e.g. '(Col(1)-Col(2))'
            return self.interprete_formula(f[1:-1])
        elif f.replace('.', '', 1).isdigit():  # constant numbers: e.g. '2+3*Col(0)'
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

            left = f[:pos]  # left component
            right = f[pos + 1:]  # right component
            op = f[pos]  # the operator
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
        if re.search(r"(?<!Col)\(", formula):
            match_end_par = re.search(r"(?<!Col\(\d)\)", formula)
            end_par = match_end_par.start()  # index of first ')'
            start_par = [m.start() for m in re.finditer(r"(?<!Col)\(", formula[:end_par])][-1]  # index of last '('
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
    creates QMainWindow containing the spreadsheet
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
            self.data = [self.create_data(np.full(9, np.nan), shortname="A", column_type="X"),
                         self.create_data(np.full(9, np.nan), shortname="B", column_type="Y")]
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

        self.show()

    def create_data(self, data_content, shortname="A", column_type="Y", filename=None, long_name=None, axis_label=None,
                    unit=None, comments=None, formula=None):
        data_dict = {"data": data_content,
                     "shortname": shortname,
                     "type": column_type,
                     "filename": filename,
                     "longname": long_name,
                     "axis label": axis_label,
                     "unit": unit,
                     "comments": comments,
                     "formula": formula}
        return data_dict

    def create_table_items(self):
        """ fill the table items with data """
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
        editMenu.addAction("Select all X columns", lambda: self.select_all_("X"))
        editMenu.addAction("Select all Y columns", lambda: self.select_all_("Y"))
        editMenu.addAction("Resample", self.resample_x_axis)

        # 3. menu item: Plot
        plotMenu = self.menubar.addMenu('&Plot')
        plotNew = plotMenu.addMenu('&New')
        plotNew.addAction('Line Plot', self.get_plot_data)
        plotNew.addAction('Dot Plot', self.get_plot_data)
        plotAdd = plotMenu.addMenu('&Add to')
        for j in self.mw.window['Plotwindow'].keys():
            plotAdd.addAction(j, self.get_plot_data)
        plotMenu.addAction('Plot all', lambda: self.get_plot_data(plot_all=True))

        # 4. menu item: Analysis
        analysis_menu = self.menubar.addMenu("&Analysis")
        analysis_menu.addAction("Principal component analysis", self.pca_nmf)
        analysis_menu.addAction("Non-negative matrix factorization", self.pca_nmf)

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
        handler = self.headerline.editingFinished.connect(lambda: self.header_editing_finished(logical_column,
                                                                                               visual_column, handler))

        self.headerline.setText(self.data[visual_column]['shortname'])
        self.headerline.setHidden(False)  # Make it visible
        self.headerline.setFocus()

    def header_editing_finished(self, log_col, vis_col, handler):
        try:
            self.headerline.editingFinished.disconnect(handler)
        except Exception:
            return
        self.headerline.setHidden(True)
        newHeader = str(self.headerline.text())
        self.data[vis_col]["shortname"] = newHeader
        self.header_table.horizontalHeaderItem(log_col).setText(
            '{} ({})'.format(self.data[vis_col]["shortname"], self.data[vis_col]["type"]))

    def show_header_context_menu(self, position):
        selected_column = self.headers.logicalIndexAt(position)
        header_menu = QMenu()
        plot_data = header_menu.addMenu("Plot data")
        plot_data.addAction("Line Plot", self.get_plot_data)
        plot_data.addAction("Dot Plot", self.get_plot_data)
        delete_column = header_menu.addAction("Delete this column")
        set_xy = header_menu.addMenu("Set as:")
        set_xy.addAction("X")
        set_xy.addAction("Y")
        set_xy.addAction("Yerr")
        set_xy.triggered[QAction].connect(lambda QAction: self.set_column_type(QAction, selected_column))
        convert_unit = header_menu.addMenu("convert unit")
        convert_unit.addAction("cm^-1 to nm")
        convert_unit.addAction("nm to cm^-1")
        convert_unit.triggered[QAction].connect(lambda QAction: self.convert_column_unit(QAction, selected_column))
        header_menu.addAction("Flip column", lambda: self.flip_column(selected_column))
        mov_col = header_menu.addMenu("Move column")
        mov_col.addAction("Move left")
        mov_col.addAction("Move right")
        mov_col.addAction("Move to first")
        mov_col.addAction("Move to last")
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

    def flip_column(self, selected_column):
        """
        flip the selected column
        @param selected_column: logical index of selected column
        @return:
        """
        selected_column = self.header_table.visualColumn(selected_column)
        self.data[selected_column]["data"] = np.flip(self.data[selected_column]["data"])
        self.create_table_items()

    def resample_x_axis(self):
        idx_y = sorted(set(self.headers.visualIndex(idx.column()) for idx in self.header_table.selectedIndexes()))
        # get indices of corresponding x columns
        idx_x = [self.get_assigned_x_column(i) for i in idx_y]

        # create new array for x data
        x_min = min(self.data[idx_x[0]]["data"])
        x_max = max(self.data[idx_x[0]]["data"])
        for ix in idx_x:
            x_min = max(x_min, min(self.data[ix]["data"]))
            x_max = min(x_max, max(self.data[ix]["data"]))

        # create new arrays for y data with shared x-axis
        x_new = np.arange(x_min, x_max, 1.0)
        data_new = [self.create_data(x_new,
                                     shortname=self.data[idx_x[0]]["shortname"],
                                     column_type=self.data[idx_x[0]]["type"],
                                     filename=self.data[idx_x[0]]["filename"],
                                     long_name=self.data[idx_x[0]]["longname"],
                                     axis_label=self.data[idx_x[0]]["axis label"],
                                     unit=self.data[idx_x[0]]["unit"],
                                     comments=self.data[idx_x[0]]["comments"],
                                     formula=self.data[idx_x[0]]["formula"])]
        for ix, iy in zip(idx_x, idx_y):
            y_new = rp.resample(self.data[ix]["data"], self.data[iy]["data"], x_new)
            data_new.append(self.create_data(y_new,
                                             shortname=self.data[iy]["shortname"],
                                             column_type=self.data[iy]["type"],
                                             filename=self.data[iy]["filename"],
                                             long_name=self.data[iy]["longname"],
                                             axis_label=self.data[iy]["axis label"],
                                             unit=self.data[iy]["unit"],
                                             comments=self.data[iy]["comments"],
                                             formula=self.data[iy]["formula"]))
        self.mw.new_window(None, "Spreadsheet", data_new, None)

    def select_all_(self, column_type):
        for c in range(self.cols):
            if self.data[c]["type"] == column_type:
                self.header_table.item(0, c).setSelected(True)

    def pca_nmf(self):
        """principal component analysis with all selected y values"""
        selected_columns = sorted(set(self.headers.visualIndex(idx.column()) for idx in
                                      self.header_table.selectedIndexes()))

        if not selected_columns:
            self.mw.show_statusbar_message('Please select the columns, which should be used!', 4000)
            return

        y_all = []
        # get all data
        for n in selected_columns:
            if self.data[n]["type"] != 'Y':
                self.mw.show_statusbar_message('Please only select Y-columns!', 4000)
                return

            ys = self.data[n]["data"]
            y_all.append(ys)

        # check if all have same length
        y_it = iter(y_all)
        len_y = len(next(y_it))
        if not all(len(l) == len_y for l in y_it):
            self.mw.show_statusbar_message("Data has to have same length!", 4000)
            return

        n_comp, ok = QtWidgets.QInputDialog().getInt(self, "Number of components", "Number of components", value=2,
                                                     min=2, max=len(y_all), step=1)
        # stack all y data
        all_samples = np.stack(y_all, axis=0)

        action_text = self.sender().text()
        if action_text == "Principal component analysis":
            # do the PCA analysis
            pca = decomposition.PCA(n_components=n_comp)
            y_transformed = pca.fit_transform(all_samples.T).T
            analysis_name = "PCA"
        elif action_text == "Non-negative matrix factorization":
            # do the NMF analysis
            nmf = decomposition.NMF(n_components=n_comp)
            y_transformed = nmf.fit_transform(all_samples.T).T
            analysis_name = "NMF"

        # insert data in table
        for idx, y_i in enumerate(y_transformed):
            self.new_col(data_content=y_i, short_name="{} {}".format(analysis_name, idx + 1))

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
        header_menu = QMenu()
        delete_row = header_menu.addAction("Delete this row")
        ac = header_menu.exec_(self.data_table.mapToGlobal(position))
        # Delete selected columns
        if ac == delete_row:
            # Get the index of all selected rows in reverse order, so that last row is deleted first
            selected_row = sorted(set(index.row() for index in self.data_table.selectedIndexes()), reverse=True)
            for c in range(self.cols):
                for r in selected_row:
                    try:
                        self.data[c]["data"] = np.delete(self.data[c]["data"], r)  # Delete data
                    except IndexError as e:
                        print(e)
            for k in selected_row:
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

        # get file name
        file_name = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', self.pHomeTxt)
        if file_name[0] != '':
            file_name = file_name[0]
        else:
            return

        # get data
        save_data = [self.data[0]["data"]]
        for c in range(1, self.cols):
            save_data.append(self.data[c]["data"])

        # check if all columns have same length to avoid problems with numpy savetxt
        n = len(self.data[0]["data"])
        if all(len(x) == n for x in save_data):
            pass
        else:
            self.mw.show_statusbar_message('The columns have different lengths!', 4000)
            return

        # save data
        if file_name[-4:] != '.txt':
            file_name = '{}.txt'.format(file_name)

        self.pHomeTxt = file_name

        np.savetxt(file_name, np.transpose(save_data), fmt='%.5f')

    def load_file(self):
        """
        function to load data from a file into the spreadsheet
        """

        di = DataImportDialog(self, self.data)
        di.show()

        loop = QtCore.QEventLoop()
        di.closeSignal.connect(loop.quit)
        loop.exec_()

        if not di.data:
            self.mw.show_statusbar_message("The file could not be imported! Please check the error messages!", 6000)
            return

        self.data = di.data
        cols_before = di.cols_before

        self.cols = len(self.data)
        self.rows = max([len(d["data"]) for d in self.data])
        self.data_table.setColumnCount(self.cols)
        self.data_table.setRowCount(self.rows)
        self.header_table.setColumnCount(self.cols)

        # set header
        headers = ['{} ({})'.format(d["shortname"], d["type"]) for d in self.data]
        self.header_table.setHorizontalHeaderLabels(headers)
        self.create_header_items(cols_before, self.cols)

        # set data
        for c in range(cols_before, self.cols):
            for r in range(len(self.data[c]["data"])):
                new_cell = QTableWidgetItem(str(self.data[c]["data"][r]))
                self.data_table.setItem(r, c, new_cell)

        # self.pHomeTxt = FileName[0]

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
        except ValueError:
            self.mw.show_statusbar_message("Only numbers please", 5000)
            item.setText("")

    def update_header(self, item):
        """if header is changed, self.data is changed too"""
        content = item.text()
        col = item.column()
        row = item.row()

        if row == 0:  # Long Name
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
                try:
                    new_data = Interpreter.interprete_formula(content)
                except Exception as e:
                    print(e)
                    new_data = None
                if new_data is None:
                    return
                elif isinstance(new_data, float):
                    self.data[col]["data"] = np.full(len(self.data[col]), new_data)
                else:
                    self.data[col]["data"] = new_data

                for r in range(len(self.data[col]["data"])):
                    new_cell = QTableWidgetItem(str(self.data[col]["data"][r]))
                    self.data_table.setItem(r, col, new_cell)

    def new_col(self, data_content=None, short_name=None):
        # adds a new column at end of table
        if data_content is None:
            data_content = np.zeros(self.rows)
        elif len(data_content) != self.rows:
            self.mw.show_statusbar_message("data has different length than table rows", 5000)
            return

        if short_name is None:
            short_name = str(chr(ord('A') + self.cols - 1))
        self.cols = self.cols + 1
        self.data_table.setColumnCount(self.cols)
        self.header_table.setColumnCount(self.cols)
        self.data.append(self.create_data(data_content=data_content, shortname=short_name))
        headers = [d["shortname"] + '(' + d["type"] + ')' for d in self.data]
        self.header_table.setHorizontalHeaderLabels(headers)
        for i in range(self.rows):
            cell = QTableWidgetItem(str(data_content[i]))
            self.data_table.setItem(i, self.cols - 1, cell)

        # Color header cells in yellow
        for r in range(5):
            self.header_table.setItem(r, self.cols - 1, QTableWidgetItem())
            self.header_table.item(r, self.cols - 1).setBackground(QtGui.QColor(255, 255, 200))

    def get_assigned_x_column(self, idx_y):
        # idx_y = index of selected y column
        # idx_x = index of corresponding x column
        if self.data[idx_y]["type"] != 'Y':
            self.mw.show_statusbar_message('Please only select Y-columns!', 4000)
            return
        else:
            idx_x = idx_y - 1
            while idx_x >= 0:
                if self.data[idx_x]["type"] == 'X':
                    return idx_x
                else:
                    idx_x -= 1

            if idx_x == -1:
                self.mw.show_statusbar_message("At least one dataset Y has no assigned X dataset.", 4000)
                return

    def get_plot_data(self, plot_all=False):
        """ get data from selected columns and prepares data for plot """
        self.plot_data = []
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
        if action.text() == 'Line Plot' or action.text() == 'Plot all':
            plot_type = '-'
        elif action.text() == 'Dot Plot':
            plot_type = 'o'
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
                        if self.data[k]["axis label"] is not None and self.data[k]["axis label"] != '':
                            self.plot_data[-1]["xaxis"] = self.data[k]["axis label"]
                            if self.data[k]["unit"] is not None and self.data[k]["unit"] != '':
                                self.plot_data[-1]["xaxis"] += " / {}".format(self.data[k]["unit"])
                        if self.data[c]["axis label"] is not None and self.data[c]["axis label"] != '':
                            self.plot_data[-1]["yaxis"] = self.data[c]["axis label"]
                            if self.data[c]["unit"] is not None and self.data[c]["unit"] != "":
                                self.plot_data[-1]["yaxis"] += " / {}".format(self.data[c]["unit"])
                        k = -2
                    else:
                        k = k - 1

                if k == -1:
                    self.mw.show_statusbar_message("At least one dataset Y has no assigned X dataset.", 4000)
                    return

        # check that x and y have same length to avoid problems later:
        # append Spreadsheet instance
        for pd in self.plot_data:

            if len(pd["x"]) == len(pd["y"]):
                # delete all nan values and make sure all values are floats

                pd["x"], pd["y"] = np.array(pd["x"]), np.array(pd["y"])
                if pd["yerr"] is not None:
                    pd["yerr"] = np.array(pd["yerr"])

                try:
                    x_bool = np.logical_not(np.isnan(pd["x"]))
                except TypeError as e:
                    print(e)
                    self.mw.show_statusbar_message('It seems there is a strange data typ in one X column.', 4000)
                    return

                if all(x_bool) is False:
                    try:
                        pd["x"] = pd["x"][x_bool]
                        pd["y"] = pd["y"][x_bool]
                    except TypeError as e:
                        self.mw.show_statusbar_message('Something is wrong! Check for error messages!', 4000)
                        print(e, "line 2101")
                        return
                    # Error
                    if pd["yerr"] is not None:
                        pd["yerr"] = pd["yerr"][x_bool]

                try:
                    y_bool = np.logical_not(np.isnan(pd["y"]))
                except TypeError as e:
                    print(e)
                    self.mw.show_statusbar_message('It seems there is a strange data typ in one Y column.', 4000)
                    return

                if all(y_bool) is False:
                    try:
                        pd["x"] = pd["x"][y_bool]
                        pd["y"] = pd["y"][y_bool]
                    except TypeError as e:
                        self.mw.show_statusbar_message('Something is wrong! Check for error messages!', 4000)
                        print(e, "line 2122")
                        return
                    # Error
                    if pd["yerr"] is not None:
                        pd["yerr"] = pd["yerr"][y_bool]

                pd["spreadsheet title"] = self.windowTitle()
            else:
                self.mw.show_statusbar_message('X and Y have different lengths', 4000)
                return
        # emit signal to MainWindow to create new plot window or add lines to existing plot window
        if plot_type is not None:
            self.new_pw_signal.emit()
        else:
            self.add_pw_signal.emit(action.text())

    def closeEvent(self, event):
        close = QMessageBox()
        close.setWindowTitle("Quit")
        close.setText("You sure?")
        close.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        close = close.exec_()

        if close == QMessageBox.Yes:
            self.closeWindowSignal.emit('Spreadsheet', self.windowTitle())
            event.accept()
        else:
            event.ignore()


########################################################################################################################
# 4. Plot
########################################################################################################################
class LineBuilder(matplotlib.lines.Line2D):
    """
    Plotting a vertical line in plot, e.g. to define area for fit
    """

    def __init__(self, x, y, canvas, linewidth=1, linestyle="-", color='r', loop=False, parent=None):
        super(LineBuilder, self).__init__(x, y, linewidth=linewidth, linestyle=linestyle, color=color)
        self.canvas = canvas
        self.canvas.figure.gca().add_artist(self)
        self.set_picker(5)
        self.set_pickradius(5)
        self.loop = loop
        self.move_line = False
        self.parent = parent

        # set event connections
        self.cid_pick = self.canvas.mpl_connect("pick_event", self)
        self.cid_move = self.canvas.mpl_connect("motion_notify_event", self.on_move)
        self.cid_release = self.canvas.mpl_connect("button_release_event", self.on_release)
        self.cid_press = self.canvas.mpl_connect("button_press_event", self)
        self.cid_key = self.canvas.mpl_connect("key_press_event", self.on_key)
        self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.canvas.setFocus()

        self.canvas.draw()

        if self.loop:
            self.canvas.start_event_loop(10000)

    def __call__(self, event):
        if event.name == "pick_event":
            if event.artist == self:
                self.move_line = True
        elif event.name == "button_press_event":
            if event.button == 3:
                self.remove_line()

    def on_key(self, event):
        if event.key == "enter":
            self.remove_line()

    def on_move(self, event):
        if not self.move_line:
            return
        xs = event.xdata
        if xs is None:
            return

        self.set_xdata(xs)
        self.canvas.draw()

    def on_release(self, event):
        self.move_line = False

    def remove_line(self):
        c = self.canvas
        c.mpl_disconnect(self.cid_pick)
        c.mpl_disconnect(self.cid_move)
        c.mpl_disconnect(self.cid_release)
        c.mpl_disconnect(self.cid_press)
        c.mpl_disconnect(self.cid_key)

        self.remove()
        c.draw()

        if self.loop:
            c.stop_event_loop()

        if self.parent:
            self.parent.remove_vertical_line()


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

        # get arrow style, head length, head width
        arrowstyle = self.arrow.get_arrowstyle()  # get arrow_style of arrow, returns object
        self.head_length = arrowstyle.head_length
        self.head_width = arrowstyle.head_width
        arrowstyle_start = str(arrowstyle).split(' ', 1)[0]  # get object name without address x0....
        list_of_styles = mpatches.ArrowStyle.get_styles()  # get all possible arrow styles, returns dictionary
        self.arrow_style = "-"
        for key, val in list_of_styles.items():  # compare arrow style with arrowstyle list to
            if str(mpatches.ArrowStyle(key)).split(' ', 1)[0] == arrowstyle_start:
                # in order to get arrow style name (e.g. '->')
                self.arrow_style = key

        # get color
        self.color = mcolors.to_hex(mcolors.to_rgba(self.arrow.get_edgecolor(), self.arrow.get_alpha()),
                                    keep_alpha=True)

        # get line width
        self.line_width = self.arrow.get_linewidth()

        # get line style
        self.line_style = self.arrow.get_linestyle()

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
        """Options dialog"""
        lineOptions = [
            ('Width', self.line_width),
            ('Line style', [self.line_style,
                            ('-', 'solid'),
                            ('--', 'dashed'),
                            ('-.', 'dashDot'),
                            (':', 'dotted'),
                            ('None', 'None')]),
            ('Color', self.color),
            ('Remove Line', False)
        ]

        arrowOptions = [
            ('Arrow Style', [self.arrow_style, '-', '<-', '->', '<->', '-|>', '<|-|>']),
            ('Head Length', self.head_length),
            ('Head Wdith', self.head_width),
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

        (self.line_width, self.line_style, self.color, remove_line) = lineOptions
        (self.arrow_style, self.head_length, self.head_width) = arrowOptions
        (xStart, yStart, xEnd, yEnd) = positionOptions

        self.arrow.set_linewidth(self.line_width)
        self.arrow.set_linestyle(self.line_style)
        self.arrow.set_color(self.color)
        if self.arrow_style != '-':
            self.arrow.set_arrowstyle(self.arrow_style, head_length=self.head_length, head_width=self.head_width)
        else:
            self.arrow.set_arrowstyle(self.arrow_style)

        self.posA[0] = xStart
        self.posA[1] = yStart
        self.posB[0] = xEnd
        self.posB[1] = yEnd
        self.arrow.set_positions(self.posA, self.posB)

        if remove_line is True:
            self.arrow.remove()

        self.c.draw()


class InsertText:
    def __init__(self, text_annotation, main_window):
        self.text_annotation = text_annotation
        self.mw = main_window
        self.fig = self.text_annotation.figure
        if self.fig is None or self.text_annotation is None:
            return
        self.fig.canvas.mpl_connect("pick_event", self.on_pick)

        # get text
        self.text = self.text_annotation.get_text()
        # get position in plot coordinates
        self.position = self.text_annotation.xyann
        # get font size
        self.font_size = self.text_annotation.get_fontsize()
        # get color of text
        self.color = mcolors.to_hex(mcolors.to_rgba(self.text_annotation.get_color(),
                                                    self.text_annotation.get_alpha()), keep_alpha=True)

    def on_pick(self, event):
        if event.artist == self.text_annotation and event.mouseevent.button == 1 and event.mouseevent.dblclick is True:
            self.edit()
        elif event.artist == self.text_annotation and event.mouseevent.button == 1:
            self.cid2 = self.fig.canvas.mpl_connect("button_release_event", self.on_release)
            self.cid3 = self.fig.canvas.mpl_connect("motion_notify_event", self.on_motion)
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
        self.text = self.textbox.text()
        self.text_annotation.set_text(self.text)
        self.textbox.setHidden(True)
        self.fig.canvas.draw()

    def on_motion(self, event):
        self.position = (event.xdata, event.ydata)
        self.text_annotation.set_position(self.position)
        self.fig.canvas.draw()

    def on_release(self, event):
        self.fig.canvas.mpl_disconnect(self.cid2)
        self.fig.canvas.mpl_disconnect(self.cid3)

    def text_options(self):
        """Option dialog"""
        text_options_list = [
            ("Text", self.text),
            ("Font size", self.font_size),
            ("Color", self.color),
            ("Remove Text", False)
        ]

        text_option_menu = formlayout.fedit(text_options_list, title="Text options", apply=self.apply_options)
        if text_option_menu is not None:
            self.apply_options(text_option_menu)

    def apply_options(self, options):
        (self.text, self.font_size, self.color, remove_text) = options

        self.text_annotation.set_text(self.text)
        self.text_annotation.set_fontsize(self.font_size)
        self.text_annotation.set_color(self.color)
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


class DataSetSelecter(QtWidgets.QMainWindow):
    """
    Select one or several datasets

    Parameters
    ----------
    data_set_names           # names of all data sets
    select_only_one          # if True only one Dataset can be selected
    """

    def __init__(self, data_set_names, select_only_one=True):
        super(DataSetSelecter, self).__init__(parent=None)
        self.data_set_names = data_set_names
        self.select_only_one = select_only_one
        self.selectedDatasetNumber = []
        self.CheckDataset = []
        self.create_dialog()
        self.show()

    def create_dialog(self):
        scroll_area = QtWidgets.QScrollArea()
        layout = QtWidgets.QVBoxLayout()
        content_widget = QtWidgets.QWidget()

        if self.select_only_one is False:
            check_all = QCheckBox("Select all", content_widget)
            font = QtGui.QFont()
            font.setBold(True)
            check_all.setFont(font)
            check_all.stateChanged.connect(self.select_all)
            layout.addWidget(check_all)

        for idx, name in enumerate(self.data_set_names):
            self.CheckDataset.append(QCheckBox(name, content_widget))
            layout.addWidget(self.CheckDataset[idx])
            if self.select_only_one is True:
                self.CheckDataset[idx].stateChanged.connect(self.onStateChange)

        # ok button
        self.ok_button = QPushButton("OK", self)
        self.ok_button.clicked.connect(self.apply_ok)
        layout.addWidget(self.ok_button)

        content_widget.setLayout(layout)

        # scroll area properties
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)

        self.setCentralWidget(scroll_area)

        self.setWindowTitle("Select Dataset")

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

    def apply_ok(self):
        """ ok button was clicked """
        for idx, d in enumerate(self.CheckDataset):
            if d.isChecked():
                self.selectedDatasetNumber.append(idx)
            else:
                pass
        self.close()


class MyCustomToolbar(NavigationToolbar2QT):
    signal_remove_line = QtCore.pyqtSignal(object)
    signal_axis_break = QtCore.pyqtSignal(list, list)

    toolitems = [t for t in NavigationToolbar2QT.toolitems]
    # Add new toolitem at last position
    toolitems.append(("Layers", "manage layers and layer contents", "Layer", "layer_content"))

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

    def _icon(self, name, *args):
        if name == 'Layer.png':
            return QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/Layer_content.png")
        else:
            return super(MyCustomToolbar, self)._icon(name, *args)


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
        self.vertical_line = None
        self.fit_functions = peakFitting.FitFunctions()
        self.blc = analysisMethods.BaselineCorrectionMethods()  # class for everything related to Baseline corrections
        self.inserted_text = []  # Storage for text inserted in the plot
        self.drawn_line = []  # Storage for lines and arrows drawn in the plot
        self.peak_positions = {}  # dict to store Line2D object marking peak positions
        self.selectedData = []

        self.plot()
        self.create_statusbar()
        self.create_menubar()
        self.create_sidetoolbar()
        self.show()
        # self.cid1 = self.fig.canvas.mpl_connect('button_press_event', self.mousePressEvent)
        # self.cid2 = self.fig.canvas.mpl_connect('key_press_event', self.keyPressEvent)
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
                    d["line"] = spect
                    spect.set_label(d["label"])
                else:
                    d["line"], = self.ax.plot(d["x"], d["y"], d["plot type"], label=d["label"],
                                              picker=True, pickradius=5)
            self.ax.legend(fontsize=legendfontsize)
            if self.data[0]["xaxis"] is None:
                self.data[0]["xaxis"] = r'Raman Shift / cm$^{-1}$'

            if self.data[0]["yaxis"] is None:
                self.data[0]["yaxis"] = r'Raman Intensity / Arbitr. Units'

            self.ax.set_xlabel(self.data[0]["xaxis"], fontsize=labelfontsize)
            self.ax.set_ylabel(self.data[0]["yaxis"], fontsize=labelfontsize)
            self.ax.xaxis.set_tick_params(labelsize=tickfontsize)
            self.ax.yaxis.set_tick_params(labelsize=tickfontsize)
        else:  # loaded Plot
            self.ax = self.fig.axes[0]
            self.canvas = FigureCanvasQTAgg(self.fig)
            layout.addWidget(self.canvas)

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
        toolbar.signal_axis_break.connect(self.axis_break)
        self.addToolBar(toolbar)
        self.ax.get_legend().set_picker(5)

    def add_plot(self, new_data):
        ls = self.data[0]["line"].get_linestyle()
        ma = self.data[0]["line"].get_marker()

        for d in new_data:
            self.data.append(d)
            if d["yerr"] is not None:
                (spect, capline, barlinecol) = self.ax.errorbar(d["x"], d["y"], yerr=d["yerr"], picker=True,
                                                                pickradius=5, capsize=3,
                                                                label='_Hidden errorbar {}'.format(d["label"]))
                d["line"] = spect
                spect.set_label(d["label"])
            else:
                spect, = self.ax.plot(d["x"], d["y"], label=d["label"], picker=True, pickradius=5)
                d["line"] = spect
            spect.set_linestyle(ls)
            spect.set_marker(ma)
            if ls is not None:
                d["plot type"] = ls
            else:
                d["plot type"] = ma
        handles, labels = self.ax.get_legend_handles_labels()
        self.update_legend(handles, labels)
        self.canvas.draw()

    def remove_line(self, line):
        """
        remove data from self.data after line was removed in figure options
        """
        idx = 0
        for d in self.data:
            if d["line"] == line:
                break
            idx += 1
        try:
            self.data.pop(idx)
        except IndexError:
            pass

    def axis_break(self, old_lines, new_lines):
        """in case of axis breaks, new line objects (Line2D) are created, this function replaces old line objects in
        self.data with new one"""
        for d in self.data:
            for ol, nl in zip(old_lines, new_lines[0]):
                if ol == d["line"]:
                    d["line"] = nl

    def pickEvent(self, event):
        if event.mouseevent.dblclick is True and event.artist == self.ax.get_legend():
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
        elif event.artist in [d["line"] for d in self.data] and event.mouseevent.button == 3:
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
            try:
                # dependent on matplotlib version (>= 3.6.0 _ncols else _ncol)
                leg_ncol = old_legend._ncol
            except AttributeError:
                leg_ncol = old_legend._ncols
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

        # editDelete = editMenu.addMenu('Delete broken pixel - LabRam')
        # editDelete.addAction("532nm")
        # editDelete.addAction("633nm")
        # editDelete.triggered[QAction].connect(self.del_broken_pixel)

        editDeletePixel = editMenu.addAction('Delete single datapoint', self.del_datapoint)
        editDeletePixel.setStatusTip(
            'Delete selected data point with Enter, Move with arrow keys, Press c to leave Delete-Mode')

        edit_remove_spikes = editMenu.addAction("Remove cosmic spikes", self.remove_cosmic_spikes)

        editSelectArea = editMenu.addAction('Define data area', self.DefineArea)
        editSelectArea.setStatusTip('Move area limit with left mouse click, set it fix with right mouse click')

        edit_shift = editMenu.addAction("Shift spectrum to zero line", self.shift_spectrum_to_zero)

        editNorm = editMenu.addMenu('Normalize spectrum regarding ...')
        editNorm.setStatusTip('Normalizes highest peak to 1')
        editNorm.addAction('... highest peak', self.normalize)
        editNorm.addAction('... selected peak', lambda: self.normalize(select_peak=True))

        editAddSubAct = editMenu.addAction('Add up or subtract two spectra', self.add_subtract_spectra)

        # 3. menu: Analysis
        analysisMenu = menubar.addMenu('&Analysis')

        # 3.1 Analysis Fit
        analysisFit = analysisMenu.addMenu('&Fit')

        analysisFitSingleFct = analysisFit.addMenu('&Quick Fit')
        analysisFitSingleFct.addAction('Lorentz')
        analysisFitSingleFct.addAction('Gauss')
        analysisFitSingleFct.addAction('Breit-Wigner-Fano')
        analysisFitSingleFct.triggered[QAction].connect(self.quick_fit)

        analysisFit.addAction("Fit Dialog", self.open_fit_dialog)

        analysis_routine_menu = analysisMenu.addMenu("&Analysis routines")
        analysis_routine_menu.addAction("D und G band", self.fit_D_G)
        analysis_routine_menu.addAction("Fit Sulfur oxyanion spectrum", self.fit_sulfuroxyanion)
        analysis_routine_menu.addAction("Get m/I(G) (Hydrogen content)", self.hydrogen_estimation)
        analysis_routine_menu.addAction("Norm to water peak", self.norm_to_water)
        analysis_routine_menu.addAction("Create own routine", self.create_analysis_routine)
        own_routine_menu = analysis_routine_menu.addMenu("&Apply own routine")
        files = glob.glob("analysis_routines/*.txt")
        for f in files:
            own_routine_menu.addAction(f)
        own_routine_menu.triggered[QAction].connect(self.get_own_routine)

        # 3.2 Linear regression
        analysisMenu.addAction("Linear regression", self.linear_regression)

        # 3.3 Analysis baseline correction
        analysisMenu.addAction('Baseline Corrections', self.baseline)

        # 3.3 Smoothing
        analysisMenu.addAction("Smooth spectrum", self.smoothing)

        # 3.4 Analysis find peaks
        analysisMenu.addAction('Find Peak', self.find_peaks)

        # 3.5 Get Area below curve
        analysisMenu.addAction('Get Area below Curve', self.determine_area)

        # 4. menu: spectra data base
        menubar.addAction('&Data base peak positions', self.open_peakdatabase)

    def create_statusbar(self):
        self.statusBar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusBar)

    def create_sidetoolbar(self):
        toolbar = QtWidgets.QToolBar("Vertical Sidebar", self)
        self.addToolBar(QtCore.Qt.LeftToolBarArea, toolbar)

        # Vertical line for comparison of peak positions
        self.VertLineAct = QAction(QIcon(os.path.dirname(os.path.realpath(__file__)) + "/Icons/Tool_Line.png"),
                                   'Vertical Line', self)
        self.VertLineAct.setStatusTip('Vertical line for comparison of peak position')
        self.VertLineAct.triggered.connect(self.create_vertical_line)
        self.VertLineAct.setCheckable(True)
        toolbar.addAction(self.VertLineAct)

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

    def create_data(self, x, y, yerr=None, line=None, style="-", label="_newline", filename=None, sstitle=None):
        data_dict = {"x": x,
                     "y": y,
                     "yerr": yerr,
                     "line": line,
                     "plot type": style,
                     "label": label,
                     "xaxis": None,
                     "yaxis": None,
                     "filename": filename,
                     "spreadsheet title": sstitle
                     }
        return data_dict

    def go_to_spreadsheet(self, line):
        line_index = [d["line"] for d in self.data].index(line)
        if self.data[line_index]["spreadsheet title"]:
            spreadsheet_name = self.data[line_index]["spreadsheet title"]
            item = self.mw.treeWidget.findItems(spreadsheet_name, Qt.MatchFixedString | Qt.MatchRecursive)
            for j in item:  # select spreadsheet if there are several items with same name
                if j.type() == 1:
                    spreadsheet_item = j
                    break
                else:
                    continue
            try:
                self.mw.activate_window(spreadsheet_item)
            except UnboundLocalError:
                return
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

    def select_data_set(self, select_only_one=False):
        data_sets_name = []
        self.selectedData = []
        for d in self.data:
            data_sets_name.append(d["line"].get_label())
        if len(data_sets_name) == 0:
            self.selectedDatasetNumber = []
        elif len(data_sets_name) == 1:
            self.selectedDatasetNumber = [0]
        else:
            DSS = DataSetSelecter(data_sets_name, select_only_one)

            loop = QtCore.QEventLoop()
            DSS.ok_button.clicked.connect(loop.quit)
            loop.exec_()
            self.selectedDatasetNumber = DSS.selectedDatasetNumber

        for j in self.selectedDatasetNumber:
            self.selectedData.append(self.data[j])

    def menu_save_to_file(self):
        self.select_data_set()

        start_file_name = None

        if len(self.selectedDatasetNumber) > 1:
            msg = QtWidgets.QMessageBox()
            msg.setWindowTitle("Do you want to save the data in one file or every data set in a single file?")
            msg.setText("Yes - one file \nNo  - data set in several files")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            ret = msg.exec_()

            if ret == QMessageBox.Yes:
                save_data = []
                for d in self.selectedData:
                    if d["filename"] is not None:
                        startFileDirName = os.path.dirname(d["filename"])
                        start_file_name = '{}/{}'.format(startFileDirName, d["label"])
                    else:
                        start_file_name = None
                    save_data.append(d["x"])
                    save_data.append(d["y"])
                if save_data:
                    # check that every column has same length, otherwise fill up with np.nan
                    max_length = max([len(i) for i in save_data])
                    for sd in save_data:
                        np.append(sd, np.full(max_length-len(sd), np.nan))

                    # transpose data and save it
                    save_data = np.transpose(save_data)
                    self.save_to_file('Save data selected data in file', start_file_name, save_data)
            elif ret == QMessageBox.No:
                for d in self.selectedData:
                    if d["filename"] is not None:
                        startFileDirName = os.path.dirname(d["filename"])
                        start_file_name = '{}/{}'.format(startFileDirName, d["label"])
                    else:
                        start_file_name = None
                    save_data = [d["x"], d["y"]]
                    save_data = np.transpose(save_data)
                    self.save_to_file('Save data selected data in file', start_file_name, save_data)
            else:
                return
        elif len(self.selectedDatasetNumber) == 1:
            save_data = [self.selectedData[0]["x"], self.selectedData[0]["y"]]
            save_data = np.transpose(save_data)
            self.save_to_file('Save data selected data in file', start_file_name, save_data)

    def save_to_file(self, window_name, file_name, data, header=""):
        file_name = QFileDialog.getSaveFileName(self, window_name, file_name, "All Files (*);;Text Files (*.txt)")
        if file_name[0] != '':
            file_name = file_name[0]
            if file_name[-4:] == '.txt':
                pass
            else:
                file_name = str(file_name) + '.txt'
        else:
            return

        try:
            if isinstance(data, (np.ndarray, np.generic)):
                np.savetxt(file_name, data, fmt='%.5f', header=header)
            elif isinstance(data, list):
                np.savetxt(file_name, data, fmt="%s", header=header)
            else:
                file = open(file_name, 'w+')
                file.write(data)
                file.close()
        except Exception as e:
            self.mw.show_statusbar_message(str(e), 3000)
            print(e)

    def del_datapoint(self):
        self.select_data_set()
        for j in self.selectedDatasetNumber:
            pickDP = DataPointPicker(self.data[j]["line"], 0)
            idx = pickDP.idx
            self.data[j]["x"] = np.delete(self.data[j]["x"], idx)
            self.data[j]["y"] = np.delete(self.data[j]["y"], idx)
            self.data[j]["line"].set_data(self.data[j]["x"], self.data[j]["y"])
            self.setFocus()
            self.canvas.draw()

    def del_broken_pixel(self, action):
        """
        Deletes data point with number 630+n*957, because this pixel is broken in CCD detector of LabRam
        """
        data_idx_diff = {'532nm': 957, '633nm': 924}
        self.select_data_set()
        for j in self.selectedDatasetNumber:
            data_idx = 629  # index of first broken data point
            border = 6
            print('Following data points of {} were deleted'.format(self.data[j]["label"]))
            while data_idx <= len(self.data[j]["x"]):
                data_min_idx = np.argmin(self.data[j]["y"][data_idx - border:data_idx + border])
                if data_min_idx == 0 or data_min_idx == 2 * border:
                    QMessageBox.about(self, "Title",
                                      "Please select this data point manually (around {} in the data set {})".format(
                                          self.data[j]["x"][data_idx], self.data[j]["y"]))
                    pickDP = DataPointPicker(self.data[j]["line"], data_idx)
                    data_idx = pickDP.idx
                else:
                    data_idx += data_min_idx - border

                print(self.data[j]["x"][data_idx], self.data[j]["y"][data_idx])
                self.data[j]["x"] = np.round(np.delete(self.data[j]["x"], data_idx), 5)
                self.data[j]["y"] = np.delete(self.data[j]["y"], data_idx)
                data_idx += data_idx_diff[action.text()]

            self.data[j]["line"].set_data(self.data[j]["x"], self.data[j]["y"])
            self.setFocus()
            self.canvas.draw()

            # Save data without defective data points
            startFileDirName = os.path.dirname(self.data[j]["filename"])
            startFileName = startFileDirName + '/' + self.data[j]["label"]
            save_data = [self.data[j]["x"], self.data[j]["y"]]
            save_data = np.transpose(save_data)
            self.save_to_file('Save data without deleted data points in file', startFileName, save_data)

    def remove_cosmic_spikes(self):
        """
        Remove cosmic spikes from Raman spectra
        Whitaker, Darren A., and Kevin Hayes. "A simple algorithm for despiking Raman spectra."
        Chemometrics and Intelligent Laboratory Systems 179 (2018): 82-84.
        @return: spectrum without spikes
        """
        self.select_data_set()
        for n in self.selectedDatasetNumber:
            y = self.data[n]["y"]
            y_diff = np.diff(y)
            z = (y_diff - np.median(y_diff)) / scipy.stats.median_abs_deviation(y_diff)
            z = np.append(z, 0)

            threshold = 8
            z = (abs(z) > threshold) * 1
            spikes = np.where(z == 1)
            ma = 5

            if spikes[0].size > 1:
                print("{} contains cosmic spikes".format(self.data[n]["label"]))

            for i in spikes[0]:
                w = np.arange(start=max([1, i - ma]), stop=min([len(y), i + ma]), step=1)
                w = w[np.where(z[w] == 0)]
                y[i] = np.mean(np.array(y)[w])

            self.data[n]["line"].set_ydata(y)
            self.data[n]["y"] = y
        self.canvas.draw()

    def normalize(self, select_peak=False):
        """
        normalize spectrum regarding the highest peak or regarding the selected peak
        """
        self.select_data_set()
        for n in self.selectedDatasetNumber:
            norm_factor = np.amax(self.data[n]["y"])
            if select_peak:
                dpp = DataPointPicker(self.data[n]["line"], np.where(self.data[n]["y"] == norm_factor))
                idx = dpp.idx
                norm_factor = self.data[n]["y"][idx]

            self.data[n]["y"] = self.data[n]["y"] / norm_factor
            self.data[n]["line"].set_data(self.data[n]["x"], self.data[n]["y"])
            self.canvas.draw()
            # Save normalized data
            # if self.data[n]["filename"] is not None:
            #    (fileBaseName, fileExtension) = os.path.splitext(self.data[n]["label"])
            #     startFileDirName = os.path.dirname(self.data[n]["filename"])
            #     startFileBaseName = startFileDirName + '/' + fileBaseName
            #     startFileName = startFileBaseName + '_norm.txt'
            # else:
            #     startFileName = None
            # save_data = [self.data[n]["x"], self.data[n]["y"]]
            # save_data = np.transpose(save_data)
            # self.save_to_file('Save normalized data in file', startFileName, save_data)

    def add_subtract_spectra(self):
        """
        function to add or subtract a spectrum from an other spectrum
        """
        self.dialog_add_sub = QDialog()
        vlayout = QtWidgets.QVBoxLayout()
        hlayout = QtWidgets.QHBoxLayout()

        cbox_spectrum1 = QtWidgets.QComboBox(self.dialog_add_sub)
        for d in self.data:
            cbox_spectrum1.addItem(d["line"].get_label())
        hlayout.addWidget(cbox_spectrum1)

        cbox_operation = QtWidgets.QComboBox(self.dialog_add_sub)
        cbox_operation.addItem('+')
        cbox_operation.addItem('-')
        hlayout.addWidget(cbox_operation)

        cbox_spectrum2 = QtWidgets.QComboBox(self.dialog_add_sub)
        for d in self.data:
            cbox_spectrum2.addItem(d["line"].get_label())
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

        x1 = self.data[i1]["x"]
        x2 = self.data[i2]["x"]

        # check that x data is the same
        if (x1 == x2).all():
            pass
        else:
            self.mw.show_statusbar_message('Not the same x data', 4000)
            return

        y1 = self.data[i1]["y"]
        y2 = self.data[i2]["y"]

        if op == '+':
            y = y1 + y2
            line_label = "accumulated spectrum"
        elif op == '-':
            y = y1 - y2
            line_label = "subtracted spectrum"
        else:
            return

        line_style = self.data[i1]["line"].get_linestyle()
        line, = self.ax.plot(x1, y, label=line_label, linestyle=line_style)
        self.data.append(self.create_data(x1, y, label=line_label, style=line_style, line=line))

        self.canvas.draw()

    def quick_fit(self, q):
        """fit one peak without opening the fit dialog"""
        self.select_data_set()
        if self.selectedDatasetNumber:
            x_min, x_max = self.SelectArea()
            self.fit_functions.n_fit_fct[q.text()] = 1
        else:
            return

        for j in self.selectedDatasetNumber:
            xs = self.data[j]["line"].get_xdata()
            ys = self.data[j]["line"].get_ydata()
            x = xs[np.where((xs > x_min) & (xs < x_max))]
            y = ys[np.where((xs > x_min) & (xs < x_max))]
            idx_peaks, properties = signal.find_peaks(y, height=0.1 * max(y))
            if idx_peaks.size > 0:
                background = round(np.mean(np.concatenate([y[:3], y[-3:]])), 2)
                idx = np.argmax(properties["peak_heights"]) # get index of highest peak
                p = round(x[idx_peaks[idx]], 2)
                h = round(properties["peak_heights"][idx] - background, 2)
                w = signal.peak_widths(y, idx_peaks)[0][idx]
            else:
                self.mw.show_statusbar_message("Couldn't find good start parameters \n"
                                               "Use Fit Dialog please", 4000)
                return
            p_start = [background, p, h, w]

            try:
                popt, pcov = curve_fit(self.fit_functions.FctSumme, x, y, p0=p_start)
            except RuntimeError or ValueError as e:
                self.mw.show_statusbar_message(str(e), 4000)
                self.fit_functions.n_fit_fct = dict.fromkeys(self.fit_functions.n_fit_fct, 0)
                return
            x1 = np.linspace(min(x), max(x), 1000)
            y1 = self.fit_functions.FctSumme(x1, *popt)
            line, = self.ax.plot(x1, y1, '-r')
            label = line.get_label()
            self.data.append(self.create_data(x1, y1, label=label, style='-r', line=line))
            self.canvas.draw()

            # print parameter
            print_table = prettytable.PrettyTable()
            print_table.field_names = ["Parameters", "Values"]
            parameter_name = ["Background", "Raman Shift in cm^-1", "Intensity", "FWHM", "Additional Parameter"]
            for idx, po in enumerate(popt):
                print_table.add_row([parameter_name[idx], po])

            print("\n {} {}".format(self.data[j]["line"].get_label(), q.text()))
            print(print_table)

        # set number of fit functions to 0 again
        self.fit_functions.n_fit_fct = dict.fromkeys(self.fit_functions.n_fit_fct, 0)

    def open_fit_dialog(self):
        self.select_data_set()
        if self.selectedDatasetNumber:
            x_min, x_max = self.SelectArea()
        else:
            return

        for n in self.selectedDatasetNumber:
            xs = self.data[n]["line"].get_xdata()
            ys = self.data[n]["line"].get_ydata()
            x = xs[np.where((xs > x_min) & (xs < x_max))]
            y = ys[np.where((xs > x_min) & (xs < x_max))]

            fit_dialog = peakFitting.FitOptionsDialog(self, x, y, self.data[n]["line"])
            fit_dialog.setMinimumWidth(600)
            if os.path.isfile("fit_parameter_cache.txt"):
                fit_dialog.load_fit_parameter(file_name="fit_parameter_cache.txt")
            fit_dialog.show()

            loop = QtCore.QEventLoop()
            fit_dialog.closeSignal.connect(loop.quit)
            loop.exec_()

        os.remove("fit_parameter_cache.txt")

    def DefineArea(self):
        self.select_data_set()
        x_min, x_max = self.SelectArea()
        for n in self.selectedDatasetNumber:
            spct = self.data[n]["line"]
            xs = spct.get_xdata()
            ys = spct.get_ydata()
            x = xs[np.where((xs > x_min) & (xs < x_max))]
            y = ys[np.where((xs > x_min) & (xs < x_max))]

            label = "{}_cut".format(spct.get_label())
            line, = self.ax.plot(x, y, label=label, picker=True, pickradius=5)
            self.data.append(self.create_data(x, y, label=label, line=line, filename=self.selectedData[0]["filename"]))

    def SelectArea(self):
        self.ax.autoscale(False)
        y_min, y_max = self.ax.get_ylim()
        x_min, x_max = self.ax.get_xlim()
        x_range = x_max - x_min
        self.mw.show_statusbar_message('Left click shifts limits, Right click to finish', 4000)

        line_1 = LineBuilder([x_min + 0.01 * x_range], [y_min, y_max], self.canvas)
        line_2 = LineBuilder([x_max - 0.01 * x_range], [y_min, y_max], self.canvas, loop=True)

        x_min = line_1.get_xdata()  # lower limit
        x_max = line_2.get_xdata()  # upper limit

        self.canvas.draw()
        self.ax.autoscale(True)
        return x_min, x_max

    def determine_area(self):
        self.select_data_set()
        area = {}
        for n in self.selectedDatasetNumber:
            x = self.data[n]["x"]
            y = self.data[n]["y"]
            area[self.data[n]["label"]] = np.trapz(y, x)

        print(area)
        return area

    def find_peaks(self):
        self.select_data_set()
        for n in self.selectedDatasetNumber:
            x = self.data[n]["x"]
            y = self.data[n]["y"]
            y_max = max(y)

            idx_peaks, properties = signal.find_peaks(y, height=0.3 * y_max, width=5, distance=50)

            print(x[idx_peaks])

    def shift_spectrum_to_zero(self):
        self.select_data_set()
        for n in self.selectedDatasetNumber:
            spct = self.data[n]["line"]
            xs = spct.get_xdata()
            ys = spct.get_ydata()
            min_y = min(ys)
            y_shifted = ys - min_y
            spct.set_ydata(y_shifted)
            self.data[n]["y"] = y_shifted
            self.canvas.draw()

    def baseline(self):
        self.select_data_set()
        x_min, x_max = self.SelectArea()
        for n in self.selectedDatasetNumber:
            spct = self.data[n]["line"]
            xs = spct.get_xdata()
            ys = spct.get_ydata()

            x = xs[np.where((xs > x_min) & (xs < x_max))]
            y = ys[np.where((xs > x_min) & (xs < x_max))]

            baseline_dialog = analysisMethods.BaselineCorrectionDialog(self, x, y, spct, self.blc)
            baseline_dialog.show()

            # wait until QMainWindow is closes
            loop = QtCore.QEventLoop()
            baseline_dialog.close_button.clicked.connect(loop.quit)
            baseline_dialog.ok_button.clicked.connect(loop.quit)
            loop.exec_()
            if baseline_dialog.close_button.isChecked():
                break

    def smoothing(self):
        self.select_data_set()
        smoothing_methods = analysisMethods.SmoothingMethods()
        for n in self.selectedDatasetNumber:
            spct = self.data[n]["line"]
            x = spct.get_xdata()
            y = spct.get_ydata()

            smooth_dialog = analysisMethods.SmoothingDialog(self, x, y, spct, smoothing_methods)
            smooth_dialog.show()

            # wait until SmoothingDialog is closed
            loop = QtCore.QEventLoop()
            smooth_dialog.close_button.clicked.connect(loop.quit)
            smooth_dialog.ok_button.clicked.connect(loop.quit)
            loop.exec_()
            if smooth_dialog.close_button.isChecked():
                break

    def linear_regression(self):
        self.select_data_set()
        for n in self.selectedDatasetNumber:
            spct = self.data[n]["line"]
            xs = spct.get_xdata()
            ys = spct.get_ydata()

            # delete all values, which are nan
            x = xs[np.logical_not(np.isnan(ys))]
            y = ys[np.logical_not(np.isnan(ys))]

            # Fit
            popt, pcov = curve_fit(self.fit_functions.LinearFct, x, y)

            # Errors and R**2
            perr = np.sqrt(np.diag(pcov))
            residuals = y - self.fit_functions.LinearFct(x, *popt)
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)

            # Plot determined linear function
            x1 = np.linspace(min(x), max(x), 1000)
            y1 = self.fit_functions.LinearFct(x1, *popt)
            line, = self.ax.plot(x1, y1, '-r')
            label = line.get_label()
            self.data.append(self.create_data(x, y, label=label, line=line, style='-'))
            self.canvas.draw()

            # print results
            print_table = prettytable.PrettyTable()
            print_table.field_names = ["Parameters", "Values", "Errors"]
            parameter_name = ["Slope", "y-Intercept"]
            for i in range(len(popt)):
                print_table.add_row([parameter_name[i], popt[i], perr[i]])
            print('\n {}'.format(spct.get_label()))
            print(r'R^2={:.4f}'.format(r_squared))
            print(print_table)

    def create_analysis_routine(self):
        """create own analysis routine"""
        list_of_methods = {
            "Define data area":
                analysisMethods.DataLimit(self),
            "Cosmic spike removal":
                "Not yet implemented",
            "Smoothing":
                analysisMethods.AnalysisDialog(self, analysisMethods.SmoothingMethods(), add_apply_button=False),
            "Baseline correction":
                analysisMethods.AnalysisDialog(self, self.blc, add_apply_button=False),
            "Peak fitting":
                peakFitting.Dialog(self),
            "Other":
                "Not yet implemented",
        }

        ab = analysisRoutine.MainWindow(self, list_of_methods)
        ab.show()

    def get_own_routine(self, action):
        """execute own analysis routine"""
        self.select_data_set()
        result_text = "{}\n\n".format(action.text())
        output_list = []
        header = ["name"]

        # opens file and saves content in variable 'v' with json
        with open(action.text(), "rb") as file:
            analysis_routine = json.load(file)

        input_routine, output_routine = analysis_routine["input"], analysis_routine["output"]
        if len(input_routine) != len(output_routine):
            print("Something is wrong with the length of the input and output of the analysis routine")

        for n in self.selectedDatasetNumber:
            spectrum = self.data[n]["line"]
            x = spectrum.get_xdata()
            y = spectrum.get_ydata()
            label = spectrum.get_label()
            result_text += "\n{}\n".format(label)
            for i, o in zip(input_routine, output_routine):

                result_text += "{}\n".format(i["method"])
                x, y, result_text, output = self.apply_own_routine(i["method"], i["info"], x, y, label, result_text)
                if y is None:
                    break
                if output is None:
                    continue
                else:
                    if o["method"] == "Peak fitting":
                        buffer_list = [label]
                        idx_fct = 0
                        for op, iop in zip(output, o["info"]):
                            for opk in iop["parameter"]:
                                buffer_list.append(op[opk])
                                if len(header) < len(buffer_list):
                                    header.append("{} {} ({})".format(opk, idx_fct, iop["function"]))
                            idx_fct += 1
                        output_list.append(buffer_list)

        self.save_to_file("Save", "output.txt", output_list, header="".join(header))

        print(result_text)
        self.mw.new_window(None, "Textwindow", result_text, None)

    def apply_own_routine(self, method, parameter, x, y, label, result_text):
        if method == "Define data area":
            parameter = parameter[0]
            x_min = float(parameter["parameter"]["start"])
            x_max = float(parameter["parameter"]["end"])
            x_cut = x[np.where((x > x_min) & (x < x_max))]
            y_cut = y[np.where((x > x_min) & (x < x_max))]
            result_text += "{}\n".format(parameter["name"])
            result_text += "{}\n".format(parameter["parameter"])
            x = x_cut
            y = y_cut
            output = None
        elif method == "Baseline correction":

            # apply baseline correction
            parameter = parameter[0]
            function = self.blc.methods[parameter["name"]]["function"]
            params = list(parameter["parameter"].values())
            yb, zb = function(x, y, *params)

            # plot
            line, = self.ax.plot(x, yb, label="{} ({})".format(label, "baseline corrected"))
            self.canvas.draw()
            self.create_data(x, yb, line=line, label=line.get_label())

            # save results
            result_text += "{}\n".format(parameter["name"])
            result_text += "{}\n".format(parameter["parameter"])
            y = yb
            output = None
        elif method == "Smoothing":
            # apply smoothing
            parameter = parameter[0]
            function = analysisMethods.SmoothingMethods().methods[parameter["name"]]["function"]
            params = list(parameter["parameter"].values())
            y_smoothed = function(x, y, *params)

            # plot
            line, = self.ax.plot(x, y_smoothed, label="{} ({})".format(label, "smoothed"))
            self.canvas.draw()
            self.create_data(x, y_smoothed, line=line, label=line.get_label())

            # save results
            result_text += "{}\n".format(parameter["name"])
            result_text += "{}\n".format(parameter["parameter"])
            y = y_smoothed
            output = None
        elif method == "Peak fitting":
            for key in self.fit_functions.n_fit_fct.keys():
                self.fit_functions.n_fit_fct[key] = len([i["name"] for i in parameter if i["name"] == key])
            p_start = []
            output_parameter = []
            p_bounds = [[], []]
            for p in parameter:
                # fit starting parameter
                p_start.extend([i[0] for i in p["parameter"].values()])
                # lower bound
                p_bounds[0].extend([i[1] for i in p["parameter"].values()])
                # upper bound
                p_bounds[1].extend([i[2] for i in p["parameter"].values()])
            try:
                popt, pcov = curve_fit(self.fit_functions.FctSumme, x, y, p0=p_start, bounds=p_bounds)
            except RuntimeError as e:
                self.mw.show_statusbar_message(str(e), 4000)
                return x, None, result_text
            except ValueError as e:
                self.mw.show_statusbar_message(str(e), 4000)
                return x, None, result_text

            # plot
            y_fit_total = self.fit_functions.FctSumme(x, *popt)
            line, = self.ax.plot(x, y_fit_total, label="{} ({})".format(label, "total fit"))

            self.canvas.draw()
            self.create_data(x, y_fit_total, line=line, label=line.get_label())

            # Calculate Errors and R square
            perr = np.sqrt(np.diag(pcov))
            residuals = y - y_fit_total
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)

            # parameter in table
            print_table = prettytable.PrettyTable()
            print_table.field_names = ["Parameters", "Values", "Errors"]
            print_table.add_rows([["background", round(popt[0], 5), round(perr[0], 5)], ["", "", ""]])
            a = 1
            area = {}
            for key in self.fit_functions.n_fit_fct.keys():  # iterate over Lorentz, Gauss, BWF, ...
                area[key] = []
                for j in range(self.fit_functions.n_fit_fct[key]):  # iterate over used fit functions per L, G or BWF
                    print_table.add_row(["{} {}".format(key, j + 1), "", ""])
                    params = popt[a: a + len(self.fit_functions.function_parameters[key])]
                    y_1fit = popt[0] + self.fit_functions.implemented_functions[key](x, *params)
                    area[key].append(np.trapz(y_1fit, x))
                    self.ax.plot(x, y_1fit, label="{} (fit {} {})".format(label, key, j + 1))
                    for p in self.fit_functions.function_parameters[key].keys():
                        print_table.add_row([p, round(popt[a], 5), round(perr[a], 5)])
                        a += 1
                    print_table.add_rows([["area under curve", round(area[key][-1], 5), ""], ["", "", ""]])

            # create output list
            output = []
            idx = 0
            for p in parameter:
                d = {"function": p["name"]}
                for key in p["parameter"].keys():
                    d[key] = popt[idx]
                    idx += 1
                if p["name"] != '':
                    d["area"] = area[p["name"]].pop(0)
                output.append(d)

            # save results
            result_text += "R^2 = {}\n".format(r_squared)
            result_text += "{}\n".format(print_table)

            # set number of fit functions to 0 again
            self.fit_functions.n_fit_fct = dict.fromkeys(self.fit_functions.n_fit_fct, 0)
            y = y_fit_total
        else:
            y = None
            output = None

        return x, y, result_text, output

    def hydrogen_estimation(self):
        """
        determine the slope of PL background in carbon spectra in order to estimate the hydrogen content compare with:
        C. Casiraghi, A. C. Ferrari, J. Robertson, Physical Review B 2005, 72, 8 085401.
        """

        self.select_data_set()
        x_min_1 = 600
        x_max_1 = 900
        x_min_2 = 1900
        x_max_2 = 2300
        for n in self.selectedDatasetNumber:
            x = self.data[n]["line"].get_xdata()
            y = self.data[n]["line"].get_ydata()

            x1 = x[np.where((x > x_min_1) & (x < x_max_1))]
            y1 = y[np.where((x > x_min_1) & (x < x_max_1))]
            x2 = x[np.where((x > x_min_2) & (x < x_max_2))]
            y2 = y[np.where((x > x_min_2) & (x < x_max_2))]
            x = np.concatenate((x1, x2))
            y = np.concatenate((y1, y2))

            popt, pcov = curve_fit(self.fit_functions.LinearFct, x, y)

            # Plot determined linear function
            x_plot = np.linspace(min(x), max(x), 1000)
            self.ax.plot(x_plot, self.fit_functions.LinearFct(x_plot, *popt), '-r')
            self.canvas.draw()

            # get index of G peak
            idx_G = np.argmax(y)

            # calculate m/I(G):
            mIG = popt[0] / y[idx_G]

            print(self.data[n]["line"].get_label())
            if mIG > 0:
                hydrogen_content = 21.7 + 16.6 * math.log10(mIG * 10 ** 4)
                print("Slope: {}\nhydrogen content: {}".format(mIG, hydrogen_content))
            else:
                print('negative slope')

    def fit_D_G(self):
        """
        fit routine for D and G bands in spectra of carbon compounds
        with 5 peaks:
            Lorentz for D peak
            3x Gaussian for peaks origin from poly acetylen
            Breit-Wigner Fano for G Peak
        """
        # Select which data set will be fitted
        self.select_data_set()

        # fit process
        # D-Band: Lorentz
        # G-Band: BreitWignerFano
        self.fit_functions.n_fit_fct['Lorentz'] = 1  # number of Lorentzian
        self.fit_functions.n_fit_fct['Gauss'] = 3  # number of Gaussian
        self.fit_functions.n_fit_fct['Breit-Wigner-Fano'] = 1  # number of Breit-Wigner-Fano
        aL = self.fit_functions.n_fit_fct['Lorentz']
        aG = self.fit_functions.n_fit_fct['Gauss']
        aB = self.fit_functions.n_fit_fct['Breit-Wigner-Fano']
        aLG = self.fit_functions.n_fit_fct['Lorentz'] + self.fit_functions.n_fit_fct['Gauss']

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

            x = self.data[n]["line"].get_xdata()
            y = self.data[n]["line"].get_ydata()

            # baseline correction
            # Asymmetric least‐squares baseline algorithm with peak screening
            # for automatic processing of the Raman spectra
            yb, zb = self.blc.derpsALS(x, y, 1000000, 0.01)  # (lambda, p) parameter for baseline correction
            self.ax.plot(x, zb, 'c--', label='baseline ({})'.format(self.data[n]["line"].get_label()))
            self.ax.plot(x, yb, 'c-', label='baseline-corrected ({})'.format(self.data[n]["line"].get_label()))
            self.canvas.draw()

            # Limits for FitProcess
            # define fit region
            x_min_fit = 945
            x_max_fit = 1830

            # limit data to fit region
            working_y = yb[np.where((x > x_min_fit) & (x < x_max_fit))]
            working_x = x[np.where((x > x_min_fit) & (x < x_max_fit))]

            try:
                popt, pcov = curve_fit(self.fit_functions.FctSumme, working_x, working_y, p0=p_start, bounds=p_bounds,
                                       absolute_sigma=False)
            except RuntimeError as e:
                self.mw.show_statusbar_message(str(e), 4000)
                continue

            # Plot the Fit Data
            x1 = np.linspace(min(working_x), max(working_x), 3000)
            y_L = []
            for j in range(aL):
                y_L.append(np.array(
                    popt[0] + self.fit_functions.LorentzFct(x1, popt[1 + 3 * j], popt[2 + 3 * j], popt[3 + 3 * j])))
            y_G = []
            for j in range(aG):
                y_G.append(np.array(
                    popt[0] + self.fit_functions.GaussianFct(x1, popt[1 + 3 * aL + 3 * j], popt[2 + 3 * aL + 3 * j],
                                                             popt[3 + 3 * aL + 3 * j])))
            y_BWF = []
            for j in range(aB):
                y_BWF.append(np.array(
                    popt[0] + self.fit_functions.BreitWignerFct(x1, popt[4 * j + 3 * aLG + 1],
                                                                popt[4 * j + 3 * aLG + 2],
                                                                popt[4 * j + 3 * aLG + 3], popt[4 * j + 3 * aLG + 4])))
            y_Ges = np.array(self.fit_functions.FctSumme(x1, *popt))
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

            residuals = working_y - self.fit_functions.FctSumme(working_x, *popt)
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((working_y - np.mean(working_y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)

            # Peak Area
            area_Lorentz = []
            area_Lorentz_err = []
            for j in range(aL):
                area_Lorentz.append(np.trapz(y_L[j], x1))
                area_Lorentz_err.append(None)  # add error later

            area_Gauss = []
            area_Gauss_err = []
            for j in range(aG):
                area_Gauss.append(np.trapz(y_G[j], x1))
                area_Gauss_err.append(None)

            area_BWF = []
            area_BWF_err = []
            for j in range(aB):
                area_BWF.append(np.trapz(y_BWF[j], x1))
                area_BWF_err.append(None)

            # get data into printable form
            print_table = [['Background', popt[0], perr[0]], ['', '', '']]
            for j in range(aL):
                print_table.append(['Lorentz %i' % (j + 1), "", ""])
                print_table.append(['Raman Shift in cm-1', popt[j * 3 + 1], perr[j * 3 + 1]])
                print_table.append(['Peak height in cps', popt[j * 3 + 2], perr[j * 3 + 2]])
                I_D = popt[j * 3 + 2]
                print_table.append(['FWHM in cm-1', popt[j * 3 + 3], perr[j * 3 + 3]])
                print_table.append(['Peak area in cps*cm-1', area_Lorentz[j], area_Lorentz_err[j]])
                print_table.append(['', '', ''])
            for j in range(aG):
                print_table.append(['Gauss %i' % (j + 1), "", ""])
                print_table.append(['Raman Shift in cm-1', popt[j * 3 + 3 * aL + 1], perr[j * 3 + 3 * aL + 1]])
                print_table.append(['Peak height in cps', popt[j * 3 + 3 * aL + 2], perr[j * 3 + 3 * aL + 2]])
                print_table.append(['FWHM in cm-1', popt[j * 3 + 3 * aL + 3], perr[j * 3 + 3 * aL + 3]])
                print_table.append(['Peak area in cps*cm-1', area_Gauss[j], area_Gauss_err[j]])
                print_table.append(['', '', ''])
            for j in range(aB):
                print_table.append(['BWF %i' % (j + 1), "", ""])
                print_table.append(['Raman Shift in cm-1', popt[j * 3 + 3 * aLG + 1], perr[j * 3 + 3 * aLG + 1]])
                print_table.append(['Peak height in cps', popt[j * 3 + 3 * aLG + 2], perr[j * 3 + 3 * aLG + 2]])
                I_G = popt[j * 3 + 3 * aLG + 2]
                print_table.append(['FWHM in cm-1', popt[j * 3 + 3 * aLG + 3], perr[j * 3 + 3 * aLG + 3]])
                print_table.append(['BWF Coupling Coefficient', popt[j * 3 + 3 * aLG + 4], perr[j * 3 + 3 * aLG + 4]])
                print_table.append(['Peak area in cps*cm-1', area_BWF[j], area_BWF_err[j]])
                print_table.append(['', '', ''])

            # Estimate Cluster size
            # ID/IG = C(lambda)/L_a
            # mit C(514.5 nm) = 4.4 nm
            ratio = I_D / I_G
            ratio_err = None  # add error later
            L_a = 4.4 / ratio  # in nm
            L_a_err = None

            print_table.append(['I_D/I_G', ratio, ratio_err])
            print_table.append(['Cluster Size in nm', L_a, L_a_err])

            save_data = prettytable.PrettyTable()
            save_data.field_names = ["Parameters", "Values", "Errors"]
            save_data.add_rows(print_table)
            save_data = "R^2={:.6f} \n Lorentz 1 = D-Bande, BWF (Breit-Wigner-Fano) 1 = G-Bande \n {}".format(r_squared, save_data)

            print('\n')
            print(self.data[n]["line"].get_label())
            print(save_data)

            # (fileBaseName, fileExtension) = os.path.splitext(self.data[n]["line"].get_label())
            # startFileDirName = os.path.dirname(self.selectedData[0]["filename"])
            # with open(startFileDirName + "/ID-IG.txt", "a") as file_cluster:
            #    file_cluster.write('\n' + str(fileBaseName) + '   %.4f' % ratio + '   %.4f' % ratio_err)

            # pos_G_max = pos_G + b_G / (2 * q_G)
            # with open(startFileDirName + "/G-Position.txt", "a") as file_GPosition:
            #    file_GPosition.write('\n{} {:.4f}  {:.4f}'.format(fileBaseName, pos_G_max, 0.0))

            # Save the fit parameter
            # startFileBaseName = startFileDirName + '/' + fileBaseName
            # startFileName = startFileBaseName + '_fitpara.txt'
            # self.save_to_file('Save fit parameter in file', startFileName, save_data)

            # Save the Fit data
            # startFileName = startFileBaseName + '_fitdata.txt'
            # save_data = [x1]
            # for j in y_L:
            #    save_data.append(j)
            # for j in y_G:
            #    save_data.append(j)
            # for j in y_BWF:
            #    save_data.append(j)
            # save_data.append(y_Ges)
            # save_data = np.transpose(save_data)
            # self.save_to_file('Save fit data in file', startFileName, save_data)

    def norm_to_water(self):
        """
        performs baseline correction on data with Doubly Reweighted Penalized Least Squares and lambda=9000000
        and then normalizes the spectra to the water peak
        """
        self.select_data_set()
        for n in self.selectedDatasetNumber:
            # get data
            spct = self.data[n]["line"]
            xs = spct.get_xdata()
            ys = spct.get_ydata()

            # background correction
            yb, baseline = self.blc.drPLS(xs, ys, lam=9000000, eta=0.5)

            # norm spectrum regarding water peak
            norm_factor = np.max(yb[np.argwhere((xs > 3000) & (xs < 3700))])
            yb = yb / norm_factor
            self.data[n]["y"] = yb
            self.data[n]["line"].set_data(xs, yb)
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
        self.select_data_set()

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
        peak_pos = [900, 982, 1030, 1045, 1190, 1256, 1291]
        peak_fwhm = [25, 30, 15, 15, 55, 55, 35]
        peak_pos.extend(pos_PS + pos_Caros)
        peak_fwhm.extend(fwhm_PS + fwhm_Caros)

        # sort list according to peak positions
        peak_pos = sorted(peak_pos)
        peak_fwhm = [f for _, f in sorted(zip(peak_pos, peak_fwhm))]

        # number of fit functions
        self.fit_functions.n_fit_fct['Lorentz'] = len(peak_pos)

        for n in self.selectedDatasetNumber:
            peak_areas = []

            # get data
            spct = self.data[n]["line"]
            xs = spct.get_xdata()
            ys = spct.get_ydata()

            # limit data
            y = ys[np.where((xs > x_min) & (xs < x_max))]
            x = xs[np.where((xs > x_min) & (xs < x_max))]

            # Fit parameter: initial guess and boundaries
            p_start = [0]
            p_bounds_low = [-0.001]
            p_bounds_up = [np.inf]
            for (start_pos, start_width) in zip(peak_pos, peak_fwhm):
                start_height = max(y[np.where((x > (start_pos - 3)) & (x < (start_pos + 3)))]) * 0.9
                if start_height < 0:
                    start_height = 0
                start_width = 15
                p_start.extend([start_pos, start_height, start_width])
                p_bounds_low.extend([start_pos - 10, 0, 0])
                p_bounds_up.extend([start_pos + 10, np.inf, np.inf])
            p_bounds = [p_bounds_low, p_bounds_up]

            try:
                popt, pcov = curve_fit(self.fit_functions.FctSumme, x, y, p0=p_start, bounds=p_bounds,
                                       absolute_sigma=False)
            except RuntimeError as e:
                self.mw.show_statusbar_message(str(e), 4000)
                continue

            # Plot the Fit Data
            x_fit = np.linspace(x_min, x_max, 3000)
            for j in range(self.fit_functions.n_fit_fct['Lorentz']):
                y_Lorentz = self.fit_functions.LorentzFct(x_fit, popt[1 + 3 * j], popt[2 + 3 * j], popt[3 + 3 * j])
                peak_areas.append(np.trapz(y_Lorentz))
                self.ax.plot(x_fit, popt[0] + y_Lorentz, '--g')
            self.ax.plot(x_fit, self.fit_functions.FctSumme(x_fit, *popt), '-r')
            self.canvas.draw()

            # Calculate Errors and R square
            perr = np.sqrt(np.diag(pcov))

            residuals = y - self.fit_functions.FctSumme(x, *popt)
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)

            # store fit parameter in list
            print_table = [['Background', popt[0], perr[0]], ['', '', '']]
            for j in range(self.fit_functions.n_fit_fct['Lorentz']):
                print_table.append(['Lorentz %i' % (j + 1), "", ""])
                print_table.append(['Raman Shift in cm-1', popt[j * 3 + 1], perr[j * 3 + 1]])
                print_table.append(['Peak height in cps', popt[j * 3 + 2], perr[j * 3 + 2]])
                print_table.append(['FWHM in cm-1', popt[j * 3 + 3], perr[j * 3 + 3]])
                print_table.append(['Peak area in cps*cm-1', peak_areas[j], ''])
                print_table.append(['', '', ''])

            # use prettytable to create printable table
            fit_parameter_table = prettytable.PrettyTable()
            fit_parameter_table.field_names = ["Parameters", "Values", "Errors"]
            fit_parameter_table.add_rows(print_table)

            # print fit parameter
            print('\n')
            print(self.data[n]["line"].get_label(), "R^2={}".format(r_squared))
            print(fit_parameter_table)

            # save the fit parameter
            directory_name, file_name_spectrum = os.path.split(self.data[n]["filename"])
            (fileBaseName, fileExtension) = os.path.splitext(file_name_spectrum)
            file_name_parameter = '{}/{}_fitparameter.txt'.format(directory_name, fileBaseName)
            self.save_to_file('Save fit parameter in file', file_name_parameter, fit_parameter_table)

            # get peak heights of persulfate and CarosAcid peaks
            name = self.data[n]["line"].get_label()
            idx_PS = [peak_pos.index(p) for p in pos_PS]
            idx_Caros = [peak_pos.index(p) for p in pos_Caros]
            for j in idx_PS:
                with open("{}/PS_intensity_PS{}cm-1.txt".format(directory_name, peak_pos[j]), "a") as f:
                    f.write('\n{} {:.4f}  {:.4f}'.format(name, popt[3 * j + 2], perr[3 * j + 2]))

            for j in idx_Caros:
                with open("{}/PS_intensity_Caros{}cm-1.txt".format(directory_name, peak_pos[j]), "a") as f:
                    f.write('\n{} {:.4f}  {:.4f}'.format(name, popt[3 * j + 2], perr[3 * j + 2]))

        self.fit_functions.n_fit_fct['Lorentz'] = 0

    def open_peakdatabase(self):
        peak_database_dialog = databaseSpectra.DatabasePeakPosition()
        peak_database_dialog.setMinimumWidth(600)
        peak_database_dialog.show()
        # wait until QMainWindow is closes
        loop = QtCore.QEventLoop()
        peak_database_dialog.closeSignal.connect(loop.quit)
        peak_database_dialog.plot_peak_position_signal.connect(self.draw_peak_positions)
        peak_database_dialog.remove_peak_position_signal.connect(self.remove_peak_positions)
        loop.exec_()

        # remove vertical lines (Line2D) in plot
        for pp in self.peak_positions.values():
            for v_line in pp:
                v_line.remove()
                del v_line
        self.peak_positions = {}
        self.canvas.draw()

    def draw_peak_positions(self, peak_positions, id, n_materials):
        colors = list(mcolors.TABLEAU_COLORS)
        pp_list = []
        for pp in peak_positions:
            v_line = self.ax.axvline(x=pp, color=colors[n_materials])
            pp_list.append(v_line)
        self.peak_positions[id] = pp_list
        self.canvas.draw()

    def remove_peak_positions(self, id):
        if id in self.peak_positions.keys():
            for v_line in self.peak_positions[id]:
                v_line.remove()
                del v_line
            del self.peak_positions[id]
        elif id == -1:
            for pp in self.peak_positions.values():
                for v_line in pp:
                    v_line.remove()
                    del v_line
            self.peak_positions = {}
        else:
            return
        self.canvas.draw()

    # Functions of toolbar
    def create_vertical_line(self):
        if self.vertical_line is not None:
            try:
                self.vertical_line.remove_line()
            except:
                pass

            self.vertical_line = None
        else:
            y_min, y_max = self.ax.get_ylim()
            x_min, x_max = self.ax.get_xlim()
            self.vertical_line = LineBuilder([(x_min + x_max) / 2, (x_min + x_max) / 2], [y_min, y_max], self.canvas,
                                             parent=self)

    def remove_vertical_line(self):
        self.VertLineAct.setChecked(False)
        self.vertical_line = None

    def scale_spectrum(self):
        self.select_data_set(True)
        for n in self.selectedDatasetNumber:
            try:
                ms = MoveSpectra(self.data[n]["line"], scaling=True)
            except RuntimeError as e:
                print(e)
                continue
            self.data[n]["line"] = ms.line
            self.data[n]["y"] = ms.y

    def shift_spectrum(self):
        self.select_data_set(True)
        for n in self.selectedDatasetNumber:
            try:
                ms = MoveSpectra(self.data[n]["line"])
            except RuntimeError as e:
                print(e)
                continue
            self.data[n]["line"] = ms.line
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
