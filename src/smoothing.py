import rampy as rp
from PyQt5 import QtWidgets, QtCore


class SmoothingMethods:
    """Class containing all implemented methods for smoothing"""

    def __init__(self):
        self.method_groups = {
            "Spline":
                ["Generalised Cross Validated Spline", "Degree of Freedom spline", "Mean Square Error spline"],
            "Whittaker":
                ["Whittaker"],
            "Window":
                ["Savitsky-Golay", "Flat window", "Hanning window", "Hamming window", "Bartlett window",
                 "Blackman window"]
        }

        # all implemented smoothing methods
        self.methods = {
            "Generalised Cross Validated Spline": {"function": self.gcvspline, "parameter": {}},
            "Degree of Freedom spline": {"function": self.dofspline, "parameter": {}},
            "Mean Square Error spline": {"function": self.msespline, "parameter": {}},
            "Savitsky-Golay": {"function": self.savgol, "parameter": {"window length": 5, "polynomial order": 2}},
            "Whittaker": {"function": self.whittaker, "parameter": {"lambda": 10 ** 0.5}},
            "Flat window": {"function": self.flat, "parameter": {"window length": 5}},
            "Hanning window": {"function": self.hanning, "parameter": {"window length": 5}},
            "Hamming window": {"function": self.hamming, "parameter": {"window length": 5}},
            "Bartlett window": {"function": self.bartlett, "parameter": {"window length": 5}},
            "Blackman window": {"function": self.blackman, "parameter": {"window length": 5}},
        }

        # contains current method, for smoothing dialog; start method is savitsky golay
        self.current_method = "Savitsky-Golay"
        self.current_group = "Window"

    def gcvspline(self, x, y):
        """
        @param x: x data
        @param y: y data
        @return: smoothed data
        """
        y_smooth = rp.smooth(x, y, method="GCVSmoothedNSpline")
        return y_smooth

    def dofspline(self, x, y):
        y_smooth = rp.smooth(x, y, method="DOFSmoothedNSpline")
        return y_smooth

    def msespline(self, x, y):
        y_smooth = rp.smooth(x, y, method="MSESmoothedNSpline")
        return y_smooth

    def whittaker(self, x, y, lam=10 ** 0.5):
        y_smooth = rp.smooth(x, y, method="whittaker", Lambda=lam)
        return y_smooth

    def savgol(self, x, y, window_length=5, polyorder=2):
        window_length = self.check_window_length(x, window_length)
        y_smooth = rp.smooth(x, y, method="savgol", window_length=window_length, polyorder=int(polyorder))
        return y_smooth

    def window_smoothing(self, x, y, window_length=5, method="flat"):
        window_length = self.check_window_length(x, window_length)
        y_smooth = rp.smooth(x, y, method=method, window_length=window_length)
        return y_smooth

    def flat(self, x, y, window_length=5):
        y_smooth = self.window_smoothing(x, y, window_length=window_length, method="flat")
        return y_smooth

    def hanning(self, x, y, window_length=5):
        y_smooth = self.window_smoothing(x, y, window_length=window_length, method="hanning")
        return y_smooth

    def hamming(self, x, y, window_length=5):
        y_smooth = self.window_smoothing(x, y, window_length=window_length, method="hamming")
        return y_smooth

    def bartlett(self, x, y, window_length=5):
        y_smooth = self.window_smoothing(x, y, window_length=window_length, method="bartlett")
        return y_smooth

    def blackman(self, x, y, window_length=5):
        y_smooth = self.window_smoothing(x, y, window_length=window_length, method="blackman")
        return y_smooth

    def check_window_length(self, x, window_length):

        # Input vector needs to be bigger than window size.
        if x.size < window_length:
            window_length = x.size - 1

        # window_length must be odd
        if (window_length % 2) == 0:
            window_length += 1
        return int(window_length)


class SmoothingDialog(QtWidgets.QMainWindow):
    def __init__(self, parent, smoothing_methods):
        super(SmoothingDialog, self).__init__(parent=parent)
        # contains parent: class PlotWindow
        self.pw = parent

        # get axis and figure of PlotWindow
        self.ax = self.pw.ax
        self.fig = self.pw.fig

        self.sm = smoothing_methods
        self.methods = self.sm.methods
        self.method_groups = self.sm.method_groups

        self.spectrum = None
        self.x = None
        self.y = None

        self.parameter_editor = {}
        self.parameter_label = {}

    def get_smoothed_spectrum(self, x, y, spectrum):
        self.x = x
        self.y = y
        self.spectrum = spectrum

        self.plot_smoothed_spectrum()
        self.create_dialog()
        self.apply_call()

    def create_dialog(self):
        # layouts
        main_layout = QtWidgets.QVBoxLayout()
        mthd_prmtr_layout = QtWidgets.QHBoxLayout()
        self.parameter_layout = QtWidgets.QGridLayout()

        method_box = self.create_method_box()
        self.fill_parameter_layout()
        parameter_box = QtWidgets.QGroupBox("Parameter")
        button_layout = self.create_buttons()

        # set layouts
        parameter_box.setLayout(self.parameter_layout)
        mthd_prmtr_layout.addWidget(method_box)
        mthd_prmtr_layout.addWidget(parameter_box)
        main_layout.addLayout(mthd_prmtr_layout)
        main_layout.addLayout(button_layout)
        widget = QtWidgets.QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)
        self.setWindowTitle("Smoothing")
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.show()

    def create_method_box(self):
        method_layout = QtWidgets.QVBoxLayout()
        method_box = QtWidgets.QGroupBox("Methods")

        # combo box for method category
        method_combo_widget = QtWidgets.QComboBox()
        for key in self.method_groups.keys():
            method_combo_widget.addItem(key)
        method_combo_widget.currentTextChanged.connect(self.method_group_changed)
        method_layout.addWidget(method_combo_widget)

        # combo box for method
        self.combo_widget_methods = QtWidgets.QComboBox()
        for me in self.method_groups[self.sm.current_group]:
            self.combo_widget_methods.addItem(me)
        self.combo_widget_methods.currentTextChanged.connect(self.method_change)
        method_layout.addWidget(self.combo_widget_methods)

        method_box.setLayout(method_layout)

        return method_box

    def method_group_changed(self, text):
        self.sm.current_group = text
        self.combo_widget_methods.clear()
        for me in self.method_groups[self.sm.current_group]:
            self.combo_widget_methods.addItem(me)
        self.method_change(self.method_groups[self.sm.current_group][0])

    def method_change(self, text):
        if text is not None and text != "":
            self.sm.current_method = text
        elif text == "":
            return

        # clear layout
        self.clear_layout(self.parameter_layout)

        self.parameter_editor = {}
        self.parameter_label = {}

        # create new layout
        self.fill_parameter_layout()
        self.update()

    def fill_parameter_layout(self):
        idx = 0
        for key, val in self.methods[self.sm.current_method]["parameter"].items():
            self.parameter_label[key] = QtWidgets.QLabel(key)
            self.parameter_editor[key] = QtWidgets.QLineEdit()
            self.parameter_layout.addWidget(self.parameter_editor[key], idx, 0)
            self.parameter_layout.addWidget(self.parameter_label[key], idx, 1)
            self.parameter_editor[key].setText(str(val))
            self.methods[self.sm.current_method]["parameter"][key] = float(self.parameter_editor[key].text())
            idx += 1

    def create_buttons(self):
        # buttons for ok, close and apply
        button_layout = QtWidgets.QHBoxLayout()

        self.finishbutton = QtWidgets.QPushButton('Ok')
        self.finishbutton.setCheckable(True)
        self.finishbutton.setToolTip('Are you happy with the start parameters? '
                                     '\n Close the dialog window and save the smoothed spectrum!')
        self.finishbutton.clicked.connect(self.finish_call)
        button_layout.addWidget(self.finishbutton)

        self.closebutton = QtWidgets.QPushButton('Close')
        self.closebutton.setCheckable(True)
        self.closebutton.setToolTip('Closes the dialog window and smoothed spectrum is not saved.')
        self.closebutton.clicked.connect(self.close)
        button_layout.addWidget(self.closebutton)

        applybutton = QtWidgets.QPushButton('Apply')
        applybutton.setToolTip('Do you want to try this smoothing setting? \n Lets do it!')
        applybutton.clicked.connect(self.apply_call)
        button_layout.addWidget(applybutton)

        return button_layout

    def plot_smoothed_spectrum(self):
        params = self.methods[self.sm.current_method]["parameter"].values()
        return_value = self.methods[self.sm.current_method]["function"](self.x, self.y, *params)
        if return_value is None:
            return
        else:
            y_smooth = return_value
        self.smoothed_spektrum, = self.ax.plot(self.x, y_smooth, "c-",
                                               label="smooth ({})".format(self.spectrum.get_label()))
        self.fig.canvas.draw()

    def clear_layout(self, layout):
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget is None:
                self.clear_layout(layout.itemAt(i))
            else:
                widget.setParent(None)

    def clear_plot(self):
        try:
            self.smoothed_spektrum.remove()
        except ValueError:
            return
        self.fig.canvas.draw()

    def finish_call(self):
        params = self.methods[self.sm.current_method]["parameter"].values()
        name = self.spectrum.get_label()
        for key, val in self.parameter_editor.items():
            self.methods[self.sm.current_method]["parameter"][key] = float(val.text())
        return_value = self.methods[self.sm.current_method]["function"](self.x, self.y, *params)
        if return_value is None:
            self.close()
            return
        else:
            y_smooth = return_value

        # Plot
        label_spct = "{} (smoothed)".format(name)
        spct_smooth, = self.ax.plot(self.x, y_smooth, "c-", label=label_spct)
        self.pw.data.append(self.pw.create_data(self.x, y_smooth, line=spct_smooth, label=label_spct, style="-"))
        self.fig.canvas.draw()
        self.close()

    def apply_call(self):
        params = self.methods[self.sm.current_method]["parameter"].values()
        name = self.spectrum.get_label()
        self.clear_plot()
        for key, val in self.parameter_editor.items():
            self.methods[self.sm.current_method]["parameter"][key] = float(val.text())
        return_value = self.methods[self.sm.current_method]["function"](self.x, self.y, *params)
        if return_value is None:
            self.close()
            return
        else:
            y_smoothed = return_value
        self.smoothed_spektrum, = self.ax.plot(self.x, y_smoothed, "c-", label="smoothed ({})".format(name))
        self.fig.canvas.draw()

    def closeEvent(self, event):
        self.clear_plot()
        event.accept()
