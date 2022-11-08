from PyQt5 import QtWidgets, QtCore, QtGui


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
        main_label = QtWidgets.QLabel(label)
        main_label.setFont(my_font)
        self.layout().addWidget(main_label)

        self.method_label = QtWidgets.QLabel("")
        self.layout().addWidget(self.method_label)

        # Push button
        push_button = QtWidgets.QPushButton("Click to open dialog")
        push_button.setStyleSheet("""background-color: white;""")
        push_button.clicked.connect(self.push_button_clicked)
        self.layout().addWidget(push_button)

    def push_button_clicked(self):
        self.method_dialog.show()
        self.method_dialog.ok_button.clicked.connect(self.change_label)

    def change_label(self):
        label_list = self.method_dialog.finish_call()
        new_label = ""
        for ll in label_list:
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


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, parent, list_of_methods):
        super(MainWindow, self).__init__(parent=parent)
        self.drag_buttons = []

        widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout()

        layout1 = QtWidgets.QHBoxLayout()
        group_box1 = DropGroupBox("Available Methods")

        for key, val in list_of_methods.items():
            button = DragFrame(key, val, group_box1)
            self.drag_buttons.append(button)
            layout1.addWidget(button)
        group_box1.stretchy = QtWidgets.QSpacerItem(
            10, 10, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        layout1.addItem(group_box1.stretchy)
        group_box1.setLayout(layout1)

        layout2 = QtWidgets.QHBoxLayout()
        group_box2 = DropGroupBox("Used Methods")

        group_box2.setLayout(layout2)

        # set minimum height of group boxes
        minimum_height = 210
        group_box1.setMinimumHeight(minimum_height)
        group_box2.setMinimumHeight(minimum_height)

        main_layout.addWidget(group_box1)
        main_layout.addWidget(group_box2)

        widget.setLayout(main_layout)
        self.setCentralWidget(widget)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
