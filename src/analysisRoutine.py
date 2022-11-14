from PyQt5 import QtWidgets, QtCore, QtGui
import json


class DragFrame(QtWidgets.QFrame):
    def __init__(self, label, method_dialog, parent):
        super().__init__(parent)
        self.method_dialog = method_dialog
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

    def mouseMoveEvent(self, e):

        if e.buttons() == QtCore.Qt.LeftButton:
            drag = QtGui.QDrag(self)
            mime = QtCore.QMimeData()
            drag.setMimeData(mime)

            pixmap = QtGui.QPixmap(self.size())
            self.render(pixmap)
            drag.setPixmap(pixmap)

            drag.exec_(QtCore.Qt.MoveAction)


class DropGroupBox(QtWidgets.QGroupBox):

    def __init__(self, parent):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet('background-color: white')

        self.stretchy = None

    def dragEnterEvent(self, event):
        # keep the default behaviour
        super(DropGroupBox, self).dragEnterEvent(event)
        event.accept()

    def dropEvent(self, event):

        sender = event.source()

        # keep the default behaviour
        super(DropGroupBox, self).dropEvent(event)

        self.layout().addWidget(sender)

        # work around to have stretch at end of groupbox
        if self.stretchy:
            self.layout().removeItem(self.stretchy)
        self.stretchy = QtWidgets.QSpacerItem(
            10, 10, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.layout().addItem(self.stretchy)

        event.accept()

    def getDragFrames(self):
        """get all DragFrames"""
        widget_list = []
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            # not spacers
            if not isinstance(item, QtWidgets.QSpacerItem):
                widget_list.append(item.widget())
        return widget_list


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, parent, list_of_methods):
        super(MainWindow, self).__init__(parent=parent)
        self.drag_buttons = []

        # create widget with main layout
        widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout()

        # input field routine name
        self.routine_name = QtWidgets.QLineEdit("Enter routine name")

        # upper group box with draggable frames
        self.group_box1 = DropGroupBox("Available Methods")
        layout1 = QtWidgets.QHBoxLayout()
        for key, val in list_of_methods.items():
            button = DragFrame(key, val, self.group_box1)
            self.drag_buttons.append(button)
            layout1.addWidget(button)
        self.group_box1.stretchy = QtWidgets.QSpacerItem(
            10, 10, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        layout1.addItem(self.group_box1.stretchy)
        self.group_box1.setLayout(layout1)

        # lower group box
        self.group_box2 = DropGroupBox("Used Methods")
        layout2 = QtWidgets.QHBoxLayout()
        self.group_box2.setLayout(layout2)

        # set minimum height of group boxes
        minimum_height = 210
        self.group_box1.setMinimumHeight(minimum_height)
        self.group_box2.setMinimumHeight(minimum_height)

        # cancel and ok button
        button_layout = QtWidgets.QHBoxLayout()

        self.ok_button = QtWidgets.QPushButton("Ok")
        self.ok_button.clicked.connect(self.ok_call)
        button_layout.addWidget(self.ok_button)

        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_call)
        button_layout.addWidget(self.cancel_button)

        # put everything together
        main_layout.addWidget(self.routine_name)
        main_layout.addWidget(self.group_box1)
        main_layout.addWidget(self.group_box2)
        main_layout.addLayout(button_layout)
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)
        self.setWindowModality(QtCore.Qt.ApplicationModal)

    def ok_call(self):
        # get name of routine
        name = self.routine_name.text()
        if name == "Enter routine name" or name == "":
            message_box = QtWidgets.QMessageBox()
            message_box.setText("Please enter routine name.")
            message_box.exec_()
            return

        # get content of routine
        frames = self.group_box2.getDragFrames()
        save_dict = {}
        for f in frames:
            save_dict[f.main_label.text()] = f.label_list

        # save in file
        with open("analysis_routines/{}.txt".format(name), "w", encoding="utf-8") as f:
            json.dump(save_dict, f, ensure_ascii=False)

        self.close()

    def cancel_call(self):
        self.close()
