#https://github.com/matplotlib/matplotlib/blob/ede8e566e5c7e7a12fdd66231ba02f363aab8913/lib/matplotlib/backends/backend_qt5.py#L644

import functools
import importlib
import os
import re
import signal
import sys
import traceback

import matplotlib

from matplotlib import backend_tools, cbook
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import (
    _Backend, FigureCanvasBase, FigureManagerBase, NavigationToolbar2,
    TimerBase, cursors, ToolContainerBase, StatusbarBase, MouseButton)
import matplotlib.backends.qt_editor.figureoptions as figureoptions
from matplotlib.backends.qt_editor.formsubplottool import UiSubplotTool
from matplotlib.backends import qt_compat
from matplotlib.backends.qt_compat import (
     QtCore, QtGui, QtWidgets, __version__, QT_API)

def edit_parameters(self):
    axes = self.canvas.figure.get_axes()
    if not axes:
        QtWidgets.QMessageBox.warning(
            self.canvas.parent(), "Error", "There are no axes to edit.")
        return
    # elif len(axes) == 1:
    #     ax, = axes
    # else:
    #     titles = [
    #         ax.get_label() or
    #         ax.get_title() or
    #         " - ".join(filter(None, [ax.get_xlabel(), ax.get_ylabel()])) or
    #         f"<anonymous {type(ax).__name__}>"
    #         for ax in axes]
    #     duplicate_titles = [
    #         title for title in titles if titles.count(title) > 1]
    #     for i, ax in enumerate(axes):
    #         if titles[i] in duplicate_titles:
    #             titles[i] += f" (id: {id(ax):#x})"  # Deduplicate titles.
    #     item, ok = QtWidgets.QInputDialog.getItem(
    #         self.canvas.parent(),
    #         'Customize', 'Select axes:', titles, 0, False)
    #     if not ok:
    #         return
    #     ax = axes[titles.index(item)]
    # figureoptions.figure_edit(ax, self)
    figureoptions.figure_edit(axes, self)


# Monkey-patch original NavigationToolbar2QT
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
NavigationToolbar2QT.edit_parameters = edit_parameters