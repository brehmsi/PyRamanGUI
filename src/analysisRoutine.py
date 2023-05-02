from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt
import json
import os


class DragFrame(QtWidgets.QFrame):
    def __init__(self, label, method_dialog, parent, deletable=True):
        super().__init__(parent)
        self.method_dialog = method_dialog
        self.deletable = deletable

        self.setLineWidth(1)
        self.setFrameStyle(1)
        self.setLayout(QtWidgets.QVBoxLayout())

        # style
        self.setStyleSheet("""background-color: rgb(255, 255, 153);""")
        self.setFrameStyle(QtWidgets.QFrame.WinPanel | QtWidgets.QFrame.Sunken)
        self.setLineWidth(3)
        self.setMidLineWidth(3)

        # labels
        my_font = QtGui.QFont()
        my_font.setBold(True)
        self.main_label = QtWidgets.QLabel(label)
        self.main_label.setFont(my_font)
        self.layout().addWidget(self.main_label)

        self.method_label = QtWidgets.QLabel("")
        self.layout().addWidget(self.method_label)

        # Push button
        push_button = QtWidgets.QPushButton("Click to open dialog")
        push_button.setStyleSheet("""background-color: white;""")
        push_button.clicked.connect(self.push_button_clicked)
        self.layout().addWidget(push_button)

        self.label_list = None

    def push_button_clicked(self):
        if isinstance(self.method_dialog, str):
            self.label_list = self.method_dialog
            self.method_label.setText(self.label_list)
        else:
            self.method_dialog.show()
            self.method_dialog.ok_button.clicked.connect(self.change_label)

    def change_label(self):
        self.label_list = self.method_dialog.finish_call()
        new_label = ""
        for ll in self.label_list:
            new_label += "{}\n".format(ll["name"])
            for key, val in ll["parameter"].items():
                new_label += "{}={}\n".format(key, val)
            new_label += "\n"

        self.method_label.setText(new_label)

    def mouseMoveEvent(self, event):
        """mouse move event with implemented drag functionality (https://doc.qt.io/qtforpython/overviews/dnd.html)"""
        if event.buttons() == Qt.LeftButton:
            drag = QtGui.QDrag(self)
            mime = QtCore.QMimeData()
            drag.setMimeData(mime)

            pixmap = QtGui.QPixmap(self.size())
            self.render(pixmap)
            drag.setPixmap(pixmap)
            drag.exec_(Qt.CopyAction)

            if drag.target() is None:
                if self.deletable:
                    self.parent().remove_frame(self)


class GroupBox(QtWidgets.QGroupBox):

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet('background-color: white')

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        # set minimum height of group boxes
        minimum_height = 210
        self.setMinimumHeight(minimum_height)


class DropGroupBox(GroupBox):

    def __init__(self, parent, accept_drops=True):
        super().__init__(parent)
        self.setAcceptDrops(accept_drops)
        self.frames = []

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        src = event.source()

        frame = DragFrame(src.main_label.text(), src.method_dialog, self)
        self.layout().insertWidget(len(self.frames), frame)
        self.frames.append(frame)
        event.acceptProposedAction()

    def remove_frame(self, frame):
        self.frames.remove(frame)
        self.layout().removeWidget(frame)
        frame.setParent(None)

    def get_frames(self):
        """get all DragFrames"""
        return self.frames


class OutputDialog(QtWidgets.QMainWindow):

    def __init__(self, parent, input_info):
        super(OutputDialog, self).__init__(parent=parent)

        self.input_info = input_info

        list_of_methods = {
            "Define data area": self.define_area,
            "Cosmic spike removal": self.spike_removal,
            "Smoothing": self.smoothing,
            "Baseline correction": self.baseline_correction,
            "Peak fitting": self.fit,
            "Other": self.other
        }

        self.output_info = []
        self.bold_font = QtGui.QFont()
        self.bold_font.setBold(True)

        # create widget with main layout
        widget = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QVBoxLayout()
        widget.setLayout(self.main_layout)
        self.setCentralWidget(widget)

        label = QtWidgets.QLabel("Which output do you want?")
        self.main_layout.addWidget(label)

        for i in self.input_info:
            self.output_info.append({"method": i["method"]})
            if i["info"] is None:
                self.output_info[-1]["info"] = None
            else:
                self.output_info[-1]["info"] = list_of_methods[i["method"]](i["info"])

        ok_button = QtWidgets.QPushButton("ok")
        ok_button.clicked.connect(self.ok_call)
        self.main_layout.addWidget(ok_button)

    def fit(self, parameter):
        fit_layout = QtWidgets.QVBoxLayout()

        label = QtWidgets.QLabel("Fit Parameter")
        label.setFont(self.bold_font)
        fit_layout.addWidget(label)
        output_fit_into = []
        for functions in parameter:
            label = QtWidgets.QLabel(functions["name"])
            fit_layout.addWidget(label)
            # dictionary with function type and fit parameter
            output_fit_into.append({
                "function": functions["name"],
                "parameter": QtWidgets.QListWidget()
            })
            output_fit_into[-1]["parameter"].setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
            for p in functions["parameter"].keys():
                output_fit_into[-1]["parameter"].addItem(p)
            fit_layout.addWidget(output_fit_into[-1]["parameter"])
        self.main_layout.addLayout(fit_layout)

        return output_fit_into

    def baseline_correction(self, parameter):
        label = QtWidgets.QLabel("Baseline correction")
        label.setFont(self.bold_font)
        self.main_layout.addWidget(label)

    def define_area(self, parameter):
        label = QtWidgets.QLabel("Define data area")
        label.setFont(self.bold_font)
        self.main_layout.addWidget(label)

    def spike_removal(self, parameter):
        label = QtWidgets.QLabel("Cosmic spike removal")
        label.setFont(self.bold_font)
        self.main_layout.addWidget(label)

    def smoothing(self, parameter):
        label = QtWidgets.QLabel("Smoothing")
        label.setFont(self.bold_font)
        self.main_layout.addWidget(label)

    def other(self, parameter):
        label = QtWidgets.QLabel("Other")
        label.setFont(self.bold_font)
        self.main_layout.addWidget(label)

    def get_output_info(self):
        for i in self.output_info:
            if i["method"] == "Peak fitting":
                if i["info"] is not None:
                    for j in i["info"]:
                        selected_items = j["parameter"].selectedItems()
                        j["parameter"] = [s.text() for s in selected_items]

        return self.output_info

    def ok_call(self):
        self.output_info = self.get_output_info()
        self.parent().output_box.layout().addWidget(QtWidgets.QLabel("{}".format(self.output_info)))
        self.close()


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, parent, list_of_methods):
        super(MainWindow, self).__init__(parent=parent)

        self.list_of_methods = list_of_methods
        self.output_dialog = None

        # create widget with main layout
        widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout()

        # input field routine name
        self.routine_name = QtWidgets.QLineEdit("Enter routine name")

        # upper group box with draggable frames
        self.group_box1 = DropGroupBox("Available Methods", accept_drops=False)
        for key, val in self.list_of_methods.items():
            frame = DragFrame(key, val, self.group_box1, deletable=False)
            self.group_box1.layout().addWidget(frame)
        self.group_box1.layout().addStretch()

        # lower group box
        self.group_box2 = DropGroupBox("Used Methods")
        self.group_box2.layout().addStretch()

        # box for output control
        self.output_box = GroupBox("Output")

        # layout for buttons
        button_layout = QtWidgets.QHBoxLayout()

        # ok button
        self.ok_button = QtWidgets.QPushButton("Ok")
        self.ok_button.clicked.connect(self.ok_call)
        button_layout.addWidget(self.ok_button)

        # output button
        self.output_button = QtWidgets.QPushButton("Output")
        self.output_button.clicked.connect(self.get_output)
        button_layout.addWidget(self.output_button)

        # cancel button
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_call)
        button_layout.addWidget(self.cancel_button)

        # put everything together
        main_layout.addWidget(self.routine_name)
        main_layout.addWidget(self.group_box1)
        main_layout.addWidget(self.group_box2)
        main_layout.addWidget(self.output_box)
        main_layout.addLayout(button_layout)
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)
        self.setWindowModality(QtCore.Qt.ApplicationModal)

    def get_input_list(self):
        """ get used methods and their content """
        frames = self.group_box2.get_frames()
        input_list = []
        for f in frames:
            input_list.append({
                "method": f.main_label.text(),
                "info": f.label_list
            })
            if input_list[-1]["method"] == "Peak fitting":
                for i in input_list[-1]["info"]:
                    if i["name"] != '':
                        i["parameter"]["area"] = [0.0, 0.0, 0.0]

        return input_list

    def ok_call(self):
        """finish routine creating"""
        # get name of routine
        name = self.routine_name.text()
        if name == "Enter routine name" or name == "":
            message_box = QtWidgets.QMessageBox()
            message_box.setText("Please enter routine name.")
            message_box.exec_()
            return

        input_list = self.get_input_list()
        output_list = self.get_output_list()

        save_dict = {"input": input_list, "output": output_list}

        # create directory
        try:
            os.makedirs("analysis_routines")
        except FileExistsError:
            # directory already exists
            pass

        # save in file
        with open("analysis_routines/{}.txt".format(name), "w", encoding="utf-8") as f:
            json.dump(save_dict, f, ensure_ascii=False)

        self.close()

    def get_output_list(self):
        if self.output_dialog is not None:
            output_list = self.output_dialog.output_info
        else:
            output_list = None
        return output_list

    def get_output(self):
        output = self.get_input_list()
        self.output_dialog = OutputDialog(self, output)
        self.output_dialog.show()

    def cancel_call(self):
        self.close()
