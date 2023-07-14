from PyQt5 import QtGui, QtCore, QtWidgets


class ConvertUnitDialog(QtWidgets.QMainWindow):
    closeSignal = QtCore.pyqtSignal()

    def __init__(self, parent):
        """
        options dialog for spreadsheet data import

        Parameters
        ----------
        parent: spreadsheet window object
        """
        super(ConvertUnitDialog, self).__init__(parent=parent)
        self.parent = parent

        self.wavelength_box = None
        self.unit_box = None
        self.main_layout = None
        self.ok_button = None
        self.cancel_button = None
        self.wavelength = None
        self.unit = None

        self.create_dialog()

    def create_dialog(self):
        dialog_layout = QtWidgets.QGridLayout()

        unit_label = QtWidgets.QLabel("Unit")
        dialog_layout.addWidget(unit_label, 0, 0)
        self.unit_box = QtWidgets.QComboBox()
        self.unit_box.addItem("cm\u207B\u00B9 to nm")
        self.unit_box.addItem("nm to cm\u207B\u00B9")
        dialog_layout.addWidget(self.unit_box, 0, 1)

        wavelength_label = QtWidgets.QLabel("Excitation wavelength in nm")
        dialog_layout.addWidget(wavelength_label, 1, 0)
        self.wavelength_box = QtWidgets.QComboBox()
        self.wavelength_box.addItem("325")
        self.wavelength_box.addItem("442")
        self.wavelength_box.addItem("532")
        self.wavelength_box.addItem("633")
        self.wavelength_box.addItem("785")
        # setting line edit
        edit_line = QtWidgets.QLineEdit(self)
        validator = QtGui.QDoubleValidator()
        validator.setBottom(0)
        edit_line.setValidator(validator)
        self.wavelength_box.setLineEdit(edit_line)
        dialog_layout.addWidget(self.wavelength_box, 1, 1)

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

        self.setWindowTitle("Convert unit")
        self.setWindowModality(QtCore.Qt.ApplicationModal)

    def apply_cancel(self):
        self.closeSignal.emit()
        self.close()

    def apply_ok(self):
        """ ok was clicked"""
        try:
            self.wavelength = float(self.wavelength_box.currentText())
        except ValueError as e:
            print(e)
            self.wavelength = None
            return
        self.unit = str(self.unit_box.currentText())
        self.closeSignal.emit()
        self.close()
