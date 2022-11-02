from PyQt5 import QtWidgets, QtCore, QtGui


class DragFrame(QtWidgets.QFrame):
    def __init__(self, label, method_dialog, parent):
        super().__init__(parent)
        self.method_dialog = method_dialog
        self.setLineWidth(1)
        self.setFrameStyle(1)
        self.setLayout(QtWidgets.QVBoxLayout())

        # label
        label = QtWidgets.QLabel(label)
        my_font = QtGui.QFont()
        my_font.setBold(True)
        label.setFont(my_font)
        self.layout().addWidget(label)

        # Push button
        push_button = QtWidgets.QPushButton("Click to open Dialog")
        push_button.clicked.connect(self.push_button_clicked)
        self.layout().addWidget(push_button)

    def push_button_clicked(self):
        self.method_dialog.show()

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

    def dragEnterEvent(self, event):
        # keep the default behaviour
        super(DropGroupBox, self).dragEnterEvent(event)
        event.accept()

    def dropEvent(self, event):

        sender = event.source()

        # keep the default behaviour
        super(DropGroupBox, self).dropEvent(event)

        self.layout().addWidget(sender)

        event.accept()


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, parent, list_of_methods):
        super(MainWindow, self).__init__(parent=parent)
        self.drag_buttons = []

        widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QHBoxLayout()

        layout1 = QtWidgets.QVBoxLayout()
        group_box1 = DropGroupBox("Available Methods")
        for key, val in list_of_methods.items():
            button = DragFrame(key, val, group_box1)
            self.drag_buttons.append(button)
            layout1.addWidget(button)
        group_box1.setLayout(layout1)

        layout2 = QtWidgets.QVBoxLayout()
        group_box2 = DropGroupBox("Used Methods")
        group_box2.setLayout(layout2)

        main_layout.addWidget(group_box1)
        main_layout.addWidget(group_box2)

        widget.setLayout(main_layout)
        self.setCentralWidget(widget)
        self.setWindowModality(QtCore.Qt.ApplicationModal)