import numpy as np
import math
from PyQt5 import QtWidgets, QtCore
from scipy import special
import os
import prettytable
from scipy.optimize import curve_fit


class FitFunctions:
    """
    Fit functions
    """

    def __init__(self):
        # number of fit functions
        self.n_fit_fct = {"Lorentz": 0,
                          "Gauss": 0,
                          "Breit-Wigner-Fano": 0,
                          "Pseudo Voigt": 0,
                          "Voigt": 0}

        self.function_parameters = {
            "Linear": {"slope": [1, -np.inf, np.inf],
                       "intercept": [0, -np.inf, np.inf]},
            "Lorentz": {"position": [520, 0, np.inf],
                        "intensity": [100, 0, np.inf],
                        "FWHM": [15, 0, np.inf]},
            "Gauss": {"position": [520, 0, np.inf],
                      "intensity": [100, 0, np.inf],
                      "FWHM": [15, 0, np.inf]},
            "Voigt": {"position": [520, 0, np.inf],
                      "intensity": [100, 0, np.inf],
                      "FWHM (Gauss)": [15, 0, np.inf],
                      "FWHM (Lorentz)": [15, 0, np.inf]},
            "Pseudo Voigt": {"position": [520, 0, np.inf],
                             "intensity": [100, 0, np.inf],
                             "FWHM (Gauss)": [15, 0, np.inf],
                             "FWHM (Lorentz)": [15, 0, np.inf],
                             "nu": [0.5, 0, 1]},
            "Breit-Wigner-Fano": {"position": [520, 0, np.inf],
                                  "intensity": [100, 0, np.inf],
                                  "FWHM": [15, 0, np.inf],
                                  "BWF coupling coefficient": [-10, -np.inf, np.inf]}
        }

        self.implemented_functions = {
            "Linear": self.LinearFct,
            "Lorentz": self.LorentzFct,
            "Gauss": self.GaussianFct,
            "Voigt": self.VoigtFct,
            "Pseudo Voigt": self.PseudoVoigt,
            "Breit-Wigner-Fano": self.BreitWignerFct,
        }

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

    def PseudoVoigt(self, x, xc, h, f_G, f_L, nu):
        """line profile pseudo function (linear combination of Lorentzian and Gaussian)"""
        return nu * self.LorentzFct(x, xc, h, f_L) + (1 - nu) * self.GaussianFct(x, xc, h, f_G)

    def VoigtFct(self, x, xc, h, f_G, f_L):
        sigma = 1 / np.sqrt(8 * np.log(2)) * f_G
        gamma = 1 / 2 * f_L
        norm_factor = 5.24334
        return norm_factor * h * sigma * special.voigt_profile(x - xc, sigma, gamma)

    def FctSumme(self, x, *p):
        """
        Summing up the fit functions
        @param x: x data
        @param p: fitparameter
        @return: fitted y data
        """
        y_sum = np.full(len(x), p[0])
        n_para = 1
        for key, val in self.n_fit_fct.items():
            for i in range(val):
                start = n_para
                end = start + len(self.function_parameters[key])
                params = p[start: end]
                y_fct = self.implemented_functions[key](x, *params)
                n_para = end
                y_sum += y_fct
        return y_sum


class Dialog(QtWidgets.QMainWindow):
    closeSignal = QtCore.pyqtSignal()  # Signal in case dialog is closed

    def __init__(self, parent, add_fit_button=False):
        """
        Options Dialog for fit process

        Parameters
        ----------
        parent: PlotWindow object
        """
        super(Dialog, self).__init__(parent=parent)
        self.parent = parent

        # list of vertical headers
        self.vertical_headers = ["0"]

        self.used_functions = []
        self.fit_functions = FitFunctions()

        self.main_layout = None
        self.table = None
        self.background = None
        self.ok_button = None
        self.cancel_button = None

        self.plotted_functions = []

        # create actual window
        self.create_dialog(add_fit_button)
        self.create_menu_bar()

    def create_dialog(self, add_fit_button):
        button_layout_01 = QtWidgets.QHBoxLayout()
        button_layout_02 = QtWidgets.QHBoxLayout()

        # Button to add Fit function
        add_button = QtWidgets.QPushButton("Add Function")
        add_button.clicked.connect(lambda: self.add_function("Lorentz", None))
        button_layout_01.addWidget(add_button)

        # Button to remove fit function
        remove_button = QtWidgets.QPushButton("Remove Function")
        remove_button.clicked.connect(self.remove_function)
        button_layout_01.addWidget(remove_button)

        if add_fit_button:
            # Fit Button => accept start values for fit
            fit_button = QtWidgets.QPushButton("Fit")
            fit_button.clicked.connect(self.fit)
            button_layout_02.addWidget(fit_button)

            # Apply
            apply_button = QtWidgets.QPushButton("Apply")
            apply_button.clicked.connect(self.apply)
            button_layout_02.addWidget(apply_button)

        # create table
        self.table = QtWidgets.QTableWidget(1, 5)
        self.table.itemChanged.connect(self.value_changed)

        # set items in each cell
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                cell = QtWidgets.QTableWidgetItem("")
                self.table.setItem(r, c, cell)

        # set headers
        self.table.setHorizontalHeaderLabels(["Fit Function", "Parameter", "Value", "Lower Bound", "Upper Bound"])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.table.setVerticalHeaderLabels(self.vertical_headers)

        # background
        self.table.item(0, 0).setFlags(QtCore.Qt.NoItemFlags)  # no interaction with this cell
        self.table.item(0, 1).setText("background")
        self.table.item(0, 1).setFlags(QtCore.Qt.NoItemFlags)
        self.background = self.table.item(0, 2)
        self.background.setText(str(0.0))

        # bounds
        self.table.item(0, 3).setText(str(-np.inf))
        self.table.item(0, 4).setText(str(np.inf))

        # cancel and ok button
        button_layout_03 = QtWidgets.QHBoxLayout()

        self.ok_button = QtWidgets.QPushButton("Ok")
        self.ok_button.clicked.connect(self.finish_call)
        button_layout_03.addWidget(self.ok_button)

        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.apply_cancel)
        button_layout_03.addWidget(self.cancel_button)

        # put main layout together
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.addLayout(button_layout_01)
        self.main_layout.addLayout(button_layout_02)
        self.main_layout.addWidget(self.table)
        self.main_layout.addLayout(button_layout_03)

        # create placeholder widget
        widget = QtWidgets.QWidget()
        widget.setLayout(self.main_layout)
        self.setCentralWidget(widget)

        self.setWindowTitle("Fit Functions")
        self.setWindowModality(QtCore.Qt.ApplicationModal)

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction("Save Fit Parameter", self.save_fit_parameter)
        file_menu.addAction("Load Fit Parameter", self.load_fit_parameter)

        edit_menu = menu_bar.addMenu("Edit")
        edit_menu.addAction("Clear table", self.clear_table)
        edit_menu.addAction("Sort fit functions by wavenumber", self.sort_fit_functions)

    def add_function(self, fct_name, fct_value):
        """
        add fit function to table
        """

        self.used_functions.append({})

        # get parameters of function
        if fct_value is None:
            parameters = self.fit_functions.function_parameters[fct_name]
        else:
            parameters = fct_value
        add_rows = len(parameters)

        self.table.setRowCount(self.table.rowCount() + add_rows)
        self.vertical_headers.extend([str(len(self.used_functions))] * add_rows)
        self.table.setVerticalHeaderLabels(self.vertical_headers)

        rows = self.table.rowCount()

        # set items in new cell
        for r in range(rows - add_rows, rows):
            for c in range(self.table.columnCount()):
                cell = QtWidgets.QTableWidgetItem('')
                self.table.setItem(r, c, cell)

        # add Combobox to select fit function
        combo_box = QtWidgets.QComboBox(self)
        for key in self.fit_functions.n_fit_fct.keys():
            combo_box.addItem(key)
        combo_box.setCurrentText(fct_name)
        n_fct = len(self.used_functions)
        combo_box.currentTextChanged.connect(lambda: self.fct_change(combo_box.currentText(), n_fct - 1))
        self.table.setCellWidget(rows - add_rows, 0, combo_box)
        self.used_functions[-1]["fct"] = combo_box

        # configure cells
        self.table.item(rows - 2, 0).setFlags(QtCore.Qt.NoItemFlags)  # no interaction with these cells
        self.table.item(rows - 1, 0).setFlags(QtCore.Qt.NoItemFlags)
        self.used_functions[-1]["parameter"] = {}
        for i, (key, val) in enumerate(parameters.items()):
            self.table.item(rows - add_rows + i, 1).setText(key)
            self.table.item(rows - add_rows + i, 1).setFlags(QtCore.Qt.NoItemFlags)
            self.table.item(rows - add_rows + i, 2).setText(str(val[0]))  # starting value
            self.table.item(rows - add_rows + i, 3).setText(str(val[1]))  # lower bound
            self.table.item(rows - add_rows + i, 4).setText(str(val[2]))  # upper bound
            self.used_functions[-1]["parameter"][key] = {
                "value": self.table.item(rows - add_rows + i, 2),
                "lower boundaries": self.table.item(rows - add_rows + i, 3),
                "upper boundaries": self.table.item(rows - add_rows + i, 4),
            }

    def remove_function(self):
        last_key = len(self.used_functions)
        row_indices = [i for i, x in enumerate(self.vertical_headers) if x == str(last_key)]
        if last_key != 0:
            for j in reversed(row_indices):
                del self.vertical_headers[j]
                self.table.removeRow(j)
            del self.used_functions[last_key - 1]

    def fct_change(self, fct_name, n):
        old_parameters = self.used_functions[n]["parameter"].keys()
        new_parameters = self.fit_functions.function_parameters[fct_name].keys()

        for del_para in list(set(old_parameters) - set(new_parameters)):
            # get index of row
            row_index = self.vertical_headers.index(str(n + 1)) + len(new_parameters)
            for item in self.table.findItems(del_para, QtCore.Qt.MatchExactly):
                try:
                    end = self.vertical_headers.index(str(n + 2))
                except ValueError:
                    end = len(self.vertical_headers) + 1
                if self.vertical_headers.index(str(n + 1)) <= self.table.row(item) < end:
                    row_index = self.table.row(item)
                else:
                    continue
            # delete row and dictionary entry
            del self.vertical_headers[row_index]
            self.table.removeRow(row_index)
            del self.used_functions[n]["parameter"][del_para]

        row_index = self.vertical_headers.index(str(n + 1)) + len(old_parameters)
        for new_para in [element for element in new_parameters if element not in old_parameters]:
            self.table.insertRow(row_index)
            self.vertical_headers.insert(row_index, str(n + 1))
            self.table.setVerticalHeaderLabels(self.vertical_headers)

            # set items in new cell
            for c in range(self.table.columnCount()):
                cell = QtWidgets.QTableWidgetItem("")
                self.table.setItem(row_index, c, cell)
            self.table.item(row_index, 1).setText(new_para)
            self.table.item(row_index, 1).setFlags(QtCore.Qt.NoItemFlags)
            self.table.item(row_index, 2).setText(str(self.fit_functions.function_parameters[fct_name][new_para][0]))

            # boundaries
            self.table.item(row_index, 3).setText(str(self.fit_functions.function_parameters[fct_name][new_para][1]))
            self.table.item(row_index, 4).setText(str(self.fit_functions.function_parameters[fct_name][new_para][2]))

            # update dictionary
            self.used_functions[n]["parameter"][new_para] = {
                "value": self.table.item(row_index, 2),
                "lower boundaries": self.table.item(row_index, 3),
                "upper boundaries": self.table.item(row_index, 4)
            }
            row_index += 1

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

    def save_fit_parameter(self, file_name=None):
        """Save fit parameter in txt file"""

        # Get fit_parameter in printable form
        print_table, r_squared = self.print_fitparameter()
        save_data = print_table.get_string()

        # Get file name
        if file_name is None:
            file_name = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save fit parameter in file", os.path.dirname(self.parent.mw.pHomeRmn),
                "All Files (*);;Text Files (*.txt)")
            if file_name[0] != '':
                file_name = file_name[0]
                if file_name[-4:] == ".txt":
                    pass
                else:
                    file_name = str(file_name) + ".txt"
            else:
                return

        file = open(file_name, "w+")
        file.write(save_data)
        file.close()

    def load_fit_parameter(self, file_name=None):
        if file_name is None:
            load_filename = QtWidgets.QFileDialog.getOpenFileName(self, "Load fit parameter")
            if load_filename[0] != '':
                file_name = load_filename[0]
            else:
                return

        try:
            table_content = np.genfromtxt(file_name, dtype="str", delimiter="|", skip_header=3, skip_footer=1,
                                          usecols=(1, 2, 3), autostrip=True)
        except ValueError as e:
            print("File not readable")
            print(e)
            return

        # set Background
        if table_content[0][0] == "background":
            self.table.item(0, 2).setText(str(table_content[0][1]))  # starting parameter
        else:
            print("File not readable")
            return

        # delete background from table content
        table_content = np.delete(table_content, 0, axis=0)

        fct_value = {}
        row = 0
        fct_name = None
        while row < len(table_content):
            if all(tr == "" for tr in table_content[row]):
                if fct_value:
                    self.add_function(fct_name, fct_value)
                if row == len(table_content) - 1:
                    break
                fct_name = table_content[row + 1][0][:-2]
                row += 2
                fct_value = {}
            else:
                if table_content[row][0] == "area under curve":
                    pass
                else:
                    if table_content[row][0] == "BWF coupling coefficient":
                        lower_boundary = -np.inf
                    else:
                        lower_boundary = 0
                    upper_boundary = np.inf
                    fct_value[table_content[row][0]] = [table_content[row][1], lower_boundary, upper_boundary]
                row += 1

    def get_parameter_dict(self):
        parameter = []
        for u in self.used_functions:
            name_fct = u["fct"].currentText()
            parameter.append({
                "fct": name_fct,
                "parameter": {}
            })
            for key, val in u["parameter"].items():
                parameter[-1]["parameter"][key] = [float(val["value"].text()),
                                                   float(val["lower boundaries"].text()),
                                                   float(val["upper boundaries"].text())]
        return parameter

    def sort_fit_functions(self):
        parameter = self.get_parameter_dict()
        parameter.sort(key=self.take_position_value)
        self.clear_table()
        for p in parameter:
            self.add_function(p["fct"], p["parameter"])

    @staticmethod
    def take_position_value(element):
        """function for sorting purposes"""
        return element["parameter"]["position"][0]

    def clear_table(self):
        while len(self.vertical_headers) > 1:
            self.remove_function()
        self.reset_n_fit_fct()

    def clear_plot(self):
        pass

    def apply(self):
        pass

    def fit(self):
        pass

    def reset_n_fit_fct(self):
        self.fit_functions.n_fit_fct = dict.fromkeys(self.fit_functions.n_fit_fct, 0)

    def finish_call(self):
        parameter = [
            {
                "fct": "",
                "parameter": {"background": [float(self.background.text()),
                                             self.table.item(0, 3).text(),
                                             self.table.item(0, 4).text()]}
            }
        ]
        parameter += self.get_parameter_dict()
        for p in parameter:
            p["name"] = p.pop("fct")
        self.close(clear_plot=False)

        return parameter

    def apply_cancel(self):
        self.close()

    def close(self, clear_plot=True):
        if clear_plot:
            self.clear_plot()
        else:
            for line in self.plotted_functions:
                self.parent.data.append(self.parent.create_data(
                    line.get_xdata(), line.get_ydata(), line=line, label=line.get_label(), style="-"))
        # keep the default behaviour
        super(Dialog, self).close()

    def closeEvent(self, event):
        self.reset_n_fit_fct()
        self.closeSignal.emit()
        event.accept()


class FitOptionsDialog(Dialog):
    closeSignal = QtCore.pyqtSignal()  # Signal in case dialog is closed

    def __init__(self, parent, x, y, spectrum):
        """
        Options Dialog for fit process

        Parameters
        ----------
        x: x data / Raman shift
        y: y data / Raman intensity
        spectrum: Line2D
        """
        super(FitOptionsDialog, self).__init__(parent=parent, add_fit_button=True)
        self.x = x
        self.y = y
        self.spectrum = spectrum

        # get canvas, axes and figure object of parent
        self.canvas = self.parent.canvas
        self.ax = self.parent.ax
        self.fig = self.parent.fig

        # plotted function
        self.plotted_functions = []

    def apply(self):
        self.clear_plot()
        p_start, boundaries = self.get_fit_parameter()
        self.plot_functions(p_start)

    def fit(self):
        self.reset_n_fit_fct()
        self.clear_plot()
        p_start, boundaries = self.get_fit_parameter()
        try:
            popt, pcov = curve_fit(self.fit_functions.FctSumme, self.x, self.y, p0=p_start, bounds=boundaries)
        except RuntimeError as e:
            self.parent.mw.show_statusbar_message(str(e), 4000)
            return
        except ValueError as e:
            self.parent.mw.show_statusbar_message(str(e), 4000)
            return

        self.plot_functions(popt, store_line=True)
        self.set_fit_parameter(popt)
        print_table, r_squared = self.print_fitparameter(popt=popt, pcov=pcov)
        print('\n {}'.format(self.spectrum.get_label()))
        print(r'R^2={:.4f}'.format(r_squared))
        print(print_table)

    def set_fit_parameter(self, parameter):
        self.background.setText(str(parameter[0]))

        for i in range(1, len(parameter)):
            self.table.item(i, 2).setText(str(parameter[i]))

    def get_fit_parameter(self):
        self.reset_n_fit_fct()

        # Background
        p_start = [float(self.background.text())]
        bg_low = self.table.item(0, 3).text()
        bg_up = self.table.item(0, 4).text()
        if bg_low == "":
            bg_low = -np.inf
        else:
            bg_low = float(bg_low)
        if bg_up == "":
            bg_up = np.inf
        else:
            bg_up = float(bg_up)
        boundaries = [[bg_low], [bg_up]]

        parameter = {_key: [] for _key in self.fit_functions.n_fit_fct.keys()}

        lower_boundaries = {_key: [] for _key in self.fit_functions.n_fit_fct.keys()}
        upper_boundaries = {_key: [] for _key in self.fit_functions.n_fit_fct.keys()}

        for ufct in self.used_functions:
            name_fct = ufct["fct"].currentText()
            for key, val in ufct["parameter"].items():
                parameter[name_fct].append(float(val["value"].text()))  # Parameter
                if val["lower boundaries"].text() == '':
                    lower_boundaries[name_fct].append(-np.inf)
                else:
                    lower_boundaries[name_fct].append(float(val["lower boundaries"].text()))
                if val["upper boundaries"].text() == '':
                    upper_boundaries[name_fct].append(np.inf)
                else:
                    upper_boundaries[name_fct].append(float(val["upper boundaries"].text()))

            self.fit_functions.n_fit_fct[name_fct] += 1

        for p in parameter.values():
            p_start.extend(p)

        for lb, ub in zip(lower_boundaries.values(), upper_boundaries.values()):
            boundaries[0].extend(lb)
            boundaries[1].extend(ub)

        return p_start, boundaries

    def plot_functions(self, param, store_line=False):
        x1 = np.linspace(min(self.x), max(self.x), int((max(self.x) - min(self.x)) * 5))
        y_fit = self.fit_functions.FctSumme(x1, *param)
        line, = self.ax.plot(x1, y_fit, "-r")
        self.plotted_functions.append(line)
        if store_line is True:
            label = "{} (fit)".format(self.spectrum.get_label())
            line.set_label(label)
        n_param = 1
        for key in self.fit_functions.n_fit_fct.keys():
            for i in range(self.fit_functions.n_fit_fct[key]):
                start = n_param
                end = start + len(self.fit_functions.function_parameters[key])
                params = param[start: end]
                y_fit = self.fit_functions.implemented_functions[key](x1, *params)
                line, = self.ax.plot(x1, y_fit, "--g")
                self.plotted_functions.append(line)
                n_param = end
                if store_line is True:
                    label = "{} {}".format(key, i)
                    line.set_label(label)

        self.canvas.draw()

    def clear_plot(self):
        for pf in self.plotted_functions:
            try:
                pf.remove()
            except ValueError as e:
                print("Line couldn't be removed: {}".format(e))
                continue
        self.plotted_functions = []
        self.canvas.draw()

    def print_fitparameter(self, popt=None, pcov=None):
        """bring fit parameter in printable form"""

        # Get data from table
        if popt is None:
            popt = []
            for r in range(self.table.rowCount()):
                popt.append(float(self.table.item(r, 2).text()))

        # Calculate Errors and R square
        if pcov is not None:
            perr = np.sqrt(np.diag(pcov))
            residuals = self.y - self.fit_functions.FctSumme(self.x, *popt)
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((self.y - np.mean(self.y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)
        else:
            r_squared = None
            perr = [""] * len(popt)

        print_table = prettytable.PrettyTable()
        print_table.field_names = ["Parameters", "Values", "Errors"]
        print_table.add_rows([["background", popt[0], perr[0]], ["", "", ""]])
        a = 1
        for key in self.fit_functions.n_fit_fct.keys():  # iterate over Lorentz, Gauss, BWF
            for j in range(self.fit_functions.n_fit_fct[key]):  # iterate over used fit functions per L, G or BWF
                print_table.add_row(["{} {}".format(key, j + 1), "", ""])
                params = popt[a: a + len(self.fit_functions.function_parameters[key])]
                area = np.trapz(self.fit_functions.implemented_functions[key](self.x, *params), self.x)
                for parameter in self.fit_functions.function_parameters[key].keys():
                    print_table.add_row([parameter, popt[a], perr[a]])
                    a += 1
                print_table.add_rows([["area under curve", area, ""], ["", "", ""]])

        return print_table, r_squared

    def reset_n_fit_fct(self):
        self.fit_functions.n_fit_fct = dict.fromkeys(self.fit_functions.n_fit_fct, 0)

    def closeEvent(self, event):
        self.save_fit_parameter("fit_parameter_cache.txt")
        # keep the default behaviour
        super(FitOptionsDialog, self).closeEvent(event)
