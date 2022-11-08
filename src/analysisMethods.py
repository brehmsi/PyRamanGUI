import rampy as rp
import numpy as np
import pybaselines
import scipy
from PyQt5 import QtWidgets, QtCore
from pybaselines import whittaker


class BaselineCorrectionMethods:
    """Class containing all implemented methods of base line correction"""

    def __init__(self):
        # all implemented baseline correction methods
        self.method_groups = {
            "Whittaker":
                [
                    "Asymmetric Least Square",
                    "Improved Asymmetric Least Square",
                    "Adaptive Iteratively Reweighted Penalized Least Squares",
                    "Asymmetrically Reweighted Penalized Least Squares",
                    "Doubly Reweighted Penalized Least Squares",
                    "Derivative Peak-Screening Asymmetric Least Square"
                ],
            "Spline":
                ["Univariate Spline", "GCV Spline"],
            "Polynomial":
                ["Polynomial", "Polynomial (without regions)"],
            "Miscellaneous":
                ["Rubberband", "Rolling Ball"]
        }
        self.methods = {
            "Rubberband":
                {"function": self.rubberband, "parameter": {}},
            "Rolling Ball":
                {"function": self.rolling_ball, "parameter": {"half window": 5}},
            "Polynomial":
                {"function": self.polynomial, "parameter": {"order": 3, "roi": [[150, 160], [3800, 4000]]}},
            "Polynomial (without regions)":
                {"function": self.polynomial_02, "parameter": {"order": 3}},
            "Univariate Spline":
                {"function": self.unispline, "parameter": {"s": 1e0, "roi": [[150, 160], [3800, 4000]]}},
            "GCV Spline":
                {"function": self.gcvspline, "parameter": {"s": 0.1, "roi": [[150, 160], [3800, 4000]]}},
            "Asymmetric Least Square":
                {"function": self.ALS, "parameter": {"p": 0.001, "lambda": 10000000}},
            "Improved Asymmetric Least Square":
                {"function": self.imALS, "parameter": {"p": 0.001, "lambda": 100000}},
            "Adaptive Iteratively Reweighted Penalized Least Squares":
                {"function": self.airPLS, "parameter": {"lambda": 10000000}},
            "Asymmetrically Reweighted Penalized Least Squares":
                {"function": self.arPLS, "parameter": {"lambda": 10000000}},
            "Doubly Reweighted Penalized Least Squares":
                {"function": self.drPLS, "parameter": {"lambda": 1000000, "eta": 0.5}},
            "Derivative Peak-Screening Asymmetric Least Square":
                {"function": self.derpsALS, "parameter": {"lambda": 1000000, "p": 0.01}}
        }

        # contains current method, for baseline dialog; start method is ASL
        self.current_method = "Asymmetric Least Square"
        self.current_group = "Whittaker"

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

    def rolling_ball(self, x, y, half_window):
        baseline, _ = pybaselines.morphological.rolling_ball(y, half_window=int(half_window))
        y_corr = y - baseline
        return y_corr, baseline

    def polynomial(self, x, y, p_order, roi):
        y, z = rp.baseline(x, y, np.array(roi), "poly", polynomial_order=p_order)
        y = y.flatten()
        z = z.flatten()
        return y, z

    def polynomial_02(self, x, y, p_order):
        baseline, _ = pybaselines.polynomial.poly(y, x_data=x, poly_order=int(p_order))
        y_corr = y - baseline
        return y_corr, baseline

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
            y, z = rp.baseline(x, y, np.array(roi), "unispline", s=s)
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
        baseline, _ = whittaker.asls(y, lam=lam, p=p)
        y_corr = y - baseline
        return y_corr, baseline

    def airPLS(self, x, y, lam):
        """
        adaptive  iteratively  reweighted  penalized  least  squares
        based on: Zhi-Min  Zhang,  Shan  Chen,  and  Yi-Zeng Liang.
        Baseline correction using adaptive iteratively reweighted penalized least squares.
        Analyst, 135(5):1138–1146, 2010.
        """
        baseline, params = whittaker.airpls(y, lam=lam)
        y_corr = y - baseline
        return y_corr, baseline

    def arPLS(self, x, y, lam):
        """
        (automatic) Baseline correction using asymmetrically reweighted penalized least squares smoothing.
        Baek et al. 2015, Analyst 140: 250-257;
        """
        baseline, params = whittaker.arpls(y, lam=lam)
        y_corr = y - baseline
        return y_corr, baseline

    def drPLS(self, x, y, lam, eta):
        """(automatic) Baseline correction method based on doubly reweighted penalized least squares.
        Xu et al., Applied Optics 58(14):3913-3920."""
        baseline, params = whittaker.drpls(y, lam=lam, eta=eta)
        y_corr = y - baseline
        return y_corr, baseline

    def imALS(self, x, y, p, lam):
        """
        He, Shixuan, et al. "Baseline correction for Raman spectra using an improved asymmetric least squares method."
        Analytical Methods 6.12 (2014): 4402-4407.
        """
        baseline, params = whittaker.iasls(y, lam=lam, p=p)
        y_corr = y - baseline
        return y_corr, baseline

    def derpsALS(self, x, y, lam, p, k=None):
        """
        Korepanov, Vitaly I. "Asymmetric least‐squares baseline algorithm with peak screening for automatic processing
        of the Raman spectra." Journal of Raman Spectroscopy 51.10 (2020): 2061-2065.
        @param x:
        @param y:
        @param lam:
        @param p:
        @param k:
        @return:
        """
        baseline, params = whittaker.derpsalsa(y, lam=lam, p=p, k=k)
        y_corr = y - baseline
        return y_corr, baseline


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


class AnalysisDialog(QtWidgets.QMainWindow):
    """class to create dialog, parent for BaselineCorrectionDialog and SmoothingDialog"""
    def __init__(self, parent, method_class, add_apply_button=True, title="Dialog"):
        super(AnalysisDialog, self).__init__(parent=parent)
        # contains parent: class PlotWindow
        self.pw = parent
        self.title = title
        self.method_class = method_class
        self.methods = self.method_class.methods
        self.method_groups = self.method_class.method_groups

        # list containing vertical spans (matplotlib.patches.Polygon) to color regions of interests
        self.roi_spans = []
        self.parameter_editor = {}
        self.parameter_label = {}

        self.parameter_layout = None
        self.combo_widget_methods = None
        self.ok_button = None
        self.close_button = None

        self.create_dialog(add_apply_button)

    def create_dialog(self, add_apply_button):
        # layouts
        main_layout = QtWidgets.QVBoxLayout()
        mthd_prmtr_layout = QtWidgets.QHBoxLayout()
        self.parameter_layout = QtWidgets.QGridLayout()

        method_box = self.create_method_box()
        self.fill_parameter_layout()
        parameter_box = QtWidgets.QGroupBox("Parameter")
        button_layout = self.create_buttons(add_apply_button)

        # set layouts
        parameter_box.setLayout(self.parameter_layout)
        mthd_prmtr_layout.addWidget(method_box)
        mthd_prmtr_layout.addWidget(parameter_box)
        main_layout.addLayout(mthd_prmtr_layout)
        main_layout.addLayout(button_layout)
        widget = QtWidgets.QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)
        self.setWindowTitle(self.title)
        self.setWindowModality(QtCore.Qt.ApplicationModal)

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
        for me in self.method_groups[self.method_class.current_group]:
            self.combo_widget_methods.addItem(me)
        self.combo_widget_methods.currentTextChanged.connect(self.method_change)
        method_layout.addWidget(self.combo_widget_methods)

        method_box.setLayout(method_layout)

        return method_box

    def method_group_changed(self, text):
        self.method_class.current_group = text
        self.combo_widget_methods.clear()
        for me in self.method_groups[self.method_class.current_group]:
            self.combo_widget_methods.addItem(me)
        self.method_change(self.method_groups[self.method_class.current_group][0])

    def method_change(self, text):
        if text is not None and text != "":
            self.method_class.current_method = text
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
        for key, val in self.methods[self.method_class.current_method]["parameter"].items():
            if key == "roi":
                self.add_roi_editors(val, idx)
                continue
            self.parameter_label[key] = QtWidgets.QLabel(key)
            self.parameter_editor[key] = QtWidgets.QLineEdit()
            self.parameter_layout.addWidget(self.parameter_editor[key], idx, 0)
            self.parameter_layout.addWidget(self.parameter_label[key], idx, 1)
            self.parameter_editor[key].setText(str(val))
            self.methods[self.method_class.current_method]["parameter"][key] = float(self.parameter_editor[key].text())
            idx += 1

    def add_roi_editors(self, roi, idx):
        roi_editors = []
        roi_layout_v = QtWidgets.QVBoxLayout()
        button_layout_v = QtWidgets.QVBoxLayout()
        button_layout_h = QtWidgets.QHBoxLayout()
        self.parameter_label["roi"] = QtWidgets.QLabel("regions of interest")
        button_add = QtWidgets.QPushButton("+")
        button_remove = QtWidgets.QPushButton("-")
        button_layout_h.addWidget(button_add)
        button_layout_h.addWidget(button_remove)
        button_layout_v.addWidget(self.parameter_label["roi"])
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
            self.methods[self.method_class.current_method]["parameter"]["roi"][i] = [float(editor1.text()),
                                                                                     float(editor2.text())]
        self.parameter_layout.addLayout(roi_layout_v, idx, 0)
        self.parameter_editor["roi"] = roi_editors

    def add_roi(self):
        try:
            last_roi = self.methods[self.method_class.current_method]["parameter"]["roi"][-1][1]
        except IndexError:
            last_roi = 140
        self.methods[self.method_class.current_method]["parameter"]["roi"].append([last_roi + 10, last_roi + 40])
        self.method_change(None)

    def del_roi(self):
        try:
            del self.methods[self.method_class.current_method]["parameter"]["roi"][-1]
        except IndexError:
            pass
        self.method_change(None)

    def sort_roi(self, roi_list):
        return sorted(roi_list, key=lambda x: x[0])

    def create_buttons(self, add_apply_button):
        # buttons for ok, close and apply
        button_layout = QtWidgets.QHBoxLayout()

        self.ok_button = QtWidgets.QPushButton('Ok')
        self.ok_button.setCheckable(True)
        self.ok_button.setToolTip(
            'Are you happy with the start parameters?\n Close the dialog window and save the baseline!')
        self.ok_button.clicked.connect(self.finish_call)
        button_layout.addWidget(self.ok_button)

        self.close_button = QtWidgets.QPushButton('Close')
        self.close_button.setCheckable(True)
        self.close_button.setToolTip('Closes the dialog window and baseline is not saved.')
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        if add_apply_button:
            apply_button = QtWidgets.QPushButton('Apply')
            apply_button.setToolTip('Do you want to try the fit parameters? \n Lets do it!')
            apply_button.clicked.connect(self.apply_call)
            button_layout.addWidget(apply_button)

        return button_layout

    def clear_layout(self, layout):
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget is None:
                self.clear_layout(layout.itemAt(i))
            else:
                widget.setParent(None)

    def finish_call(self):
        return [
            {
                "name": self.method_class.current_method,
                "parameter": self.method_class.methods[self.method_class.current_method]["parameter"]
            }
        ]

    def apply_call(self):
        pass


class SmoothingDialog(AnalysisDialog):
    def __init__(self, parent, x, y, spectrum, smoothing_methods):
        super(SmoothingDialog, self).__init__(parent=parent, method_class=smoothing_methods, title="Smoothing")

        # get axis and figure of PlotWindow
        self.ax = self.pw.ax
        self.fig = self.pw.fig

        self.sm = smoothing_methods
        self.spectrum = spectrum
        self.x = x
        self.y = y

        self.smoothed_spectrum = None

        self.plot_smoothed_spectrum()
        self.apply_call()

    def plot_smoothed_spectrum(self):
        params = self.methods[self.sm.current_method]["parameter"].values()
        return_value = self.methods[self.sm.current_method]["function"](self.x, self.y, *params)
        if return_value is None:
            return
        else:
            y_smooth = return_value
        self.smoothed_spectrum, = self.ax.plot(self.x, y_smooth, "c-",
                                               label="smooth ({})".format(self.spectrum.get_label()))
        self.fig.canvas.draw()

    def clear_plot(self):
        try:
            self.smoothed_spectrum.remove()
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
        self.smoothed_spectrum, = self.ax.plot(self.x, y_smoothed, "c-", label="smoothed ({})".format(name))
        self.fig.canvas.draw()

    def closeEvent(self, event):
        self.clear_plot()
        event.accept()


class BaselineCorrectionDialog(AnalysisDialog):
    def __init__(self, parent, x, y, spectrum, baseline_correction_methods):
        super(BaselineCorrectionDialog, self).__init__(parent=parent, method_class=baseline_correction_methods,
                                                       title="Baseline Correction")

        self.blcm = baseline_correction_methods
        self.x = x
        self.y = y
        self.spectrum = spectrum

        # get axis and figure of PlotWindow
        self.ax = self.pw.ax
        self.fig = self.pw.fig

        self.base_line = None
        self.spectrum_corr = None

        self.plot_baseline()
        self.apply_call()

    def plot_baseline(self):
        params = self.methods[self.blcm.current_method]["parameter"].values()
        return_value = self.methods[self.blcm.current_method]["function"](self.x, self.y, *params)
        if return_value is None:
            return
        else:
            yb, zb = return_value
        self.base_line, = self.ax.plot(self.x, zb, "c--", label="baseline ({})".format(self.spectrum.get_label()))
        self.spectrum_corr, = self.ax.plot(self.x, yb, "c-",
                                           label="{} (baseline corrected)".format(self.spectrum.get_label()))
        self.fig.canvas.draw()

    def clear_plot(self):
        try:
            self.spectrum_corr.remove()
            self.base_line.remove()
        except ValueError as e:
            print(e)
            return

        for rs in self.roi_spans:
            rs.remove()
        self.roi_spans = []
        self.fig.canvas.draw()

    def finish_call(self):
        params = self.methods[self.blcm.current_method]["parameter"].values()
        name = self.spectrum.get_label()
        for key, val in self.parameter_editor.items():
            if key == "roi":
                for i, roi_pe in enumerate(val):
                    roi_start = float(roi_pe[0].text())
                    roi_end = float(roi_pe[1].text())
                    self.methods[self.blcm.current_method]["parameter"]["roi"][i] = [roi_start, roi_end]
                self.methods[self.blcm.current_method]["parameter"]["roi"] = self.sort_roi(
                    self.methods[self.blcm.current_method]["parameter"]["roi"])
                continue
            self.methods[self.blcm.current_method]["parameter"][key] = float(val.text())
        return_value = self.methods[self.blcm.current_method]["function"](self.x, self.y, *params)
        if return_value is None:
            self.close()
            return
        else:
            yb, zb = return_value

        # Plot
        label_spct = "{} (baseline-corrected)".format(name)
        spct_corr, = self.ax.plot(self.x, yb, "c-", label=label_spct)
        self.pw.data.append(self.pw.create_data(self.x, yb, line=spct_corr, label=label_spct, style="-"))
        baseline, = self.ax.plot(self.x, zb, "c--", label="baseline ({})".format(name))
        self.pw.data.append(self.pw.create_data(
            self.x, zb, line=baseline, label="baseline ({})".format(name), style="-"))
        self.fig.canvas.draw()
        self.close()

    def apply_call(self):
        params = self.methods[self.blcm.current_method]["parameter"].values()
        name = self.spectrum.get_label()
        if self.spectrum_corr and self.base_line:
            self.clear_plot()
        for key, val in self.parameter_editor.items():
            if key == "roi":
                for i, roi_pe in enumerate(val):
                    roi_start = float(roi_pe[0].text())
                    roi_end = float(roi_pe[1].text())
                    self.methods[self.blcm.current_method]["parameter"]["roi"][i] = [roi_start, roi_end]
                    self.roi_spans.append(self.ax.axvspan(roi_start, roi_end, alpha=0.5, color="yellow"))
                self.methods[self.blcm.current_method]["parameter"]["roi"] = self.sort_roi(
                    self.methods[self.blcm.current_method]["parameter"]["roi"])
                continue
            try:
                self.methods[self.blcm.current_method]["parameter"][key] = float(val.text())
            except ValueError as e:
                self.pw.mw.show_statusbar_message(e, 4000)
                return
        return_value = self.methods[self.blcm.current_method]["function"](self.x, self.y, *params)
        if return_value is None:
            self.close()
            return
        else:
            yb, zb = return_value
        self.base_line, = self.ax.plot(self.x, zb, "c--", label="baseline ({})".format(name))
        self.spectrum_corr, = self.ax.plot(self.x, yb, "c-", label="baseline-corrected ({})".format(name))
        self.fig.canvas.draw()

    def closeEvent(self, event):
        self.clear_plot()
        event.accept()
