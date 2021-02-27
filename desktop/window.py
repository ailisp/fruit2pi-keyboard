from PySide6.QtCore import Slot, QSize, QThread, Signal
from PySide6.QtGui import QAction, QIcon, QStandardItemModel, QStandardItem, QBrush, QColor
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog,
                               QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QMenu, QMessageBox, QPushButton,
                               QSpinBox, QStyle, QSystemTrayIcon, QTextEdit,
                               QVBoxLayout, QTabWidget, QTextBrowser, QWidget,
                               QListView)
from bluetooth.bluez import BluetoothSocket
import rc_systray
from libmanager import APP_NAME, Config, connect_keyboard, find_keyboard, send_command

class ConnectKeyboard(QThread):
    found = Signal(str)
    connected = Signal(BluetoothSocket)
    def run(self):
        config = Config()
        keyboardAddr = config.get('addr') or find_keyboard()
        self.found.emit(keyboardAddr)
        sock = connect_keyboard(keyboardAddr)
        self.connected.emit(sock)

class ListProgram(QThread):
    listed = Signal(list, str)

    def __init__(self, sock):
        super(ListProgram, self).__init__()
        self.sock = sock
    
    def run(self):
        res = send_command(self.sock, ['list'])
        print(res)
        self.listed.emit(res['programs'], res['current_program'])

class DeleteProgram(QThread):
    deleted = Signal(str)

    def __init__(self, sock, name):
        super(DeleteProgram, self).__init__()
        self.sock = sock
        self.name = name
    
    def run(self):
        send_command(self.sock, ['delete', self.name])
        self.deleted.emit(self.name)

class SetProgram(QThread):
    setDone = Signal(str)

    def __init__(self, sock, name):
        super(SetProgram, self).__init__()
        self.sock = sock
        self.name = name
    
    def run(self):
        send_command(self.sock, ['set', self.name])
        self.setDone.emit(self.name)

class EditProgram(QThread):
    edited = Signal(str)

    def __init__(self, sock, name, program):
        super(EditProgram, self).__init__()
        self.sock = sock
        self.name = name
        self.program = program
    
    def run(self):
        send_command(self.sock, ['edit', self.name, self.program])
        self.edited.emit(self.name)

class LoadProgram(QThread):
    loaded = Signal(str, str)

    def __init__(self, sock, name):
        super(LoadProgram, self).__init__()
        self.sock = sock
        self.name = name
    
    def run(self):
        program = send_command(self.sock, ['load', self.name])['program']
        self.loaded.emit(self.name, program)

class Window(QDialog):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        self.iconGroupBox = QGroupBox()
        self.iconLabel = QLabel()
        self.iconComboBox = QComboBox()
        self.showIconCheckBox = QCheckBox()

        self.messageGroupBox = QGroupBox()
        self.typeLabel = QLabel()
        self.durationLabel = QLabel()
        self.durationWarningLabel = QLabel()
        self.titleLabel = QLabel()
        self.bodyLabel = QLabel()

        self.typeComboBox = QComboBox()
        self.durationSpinBox = QSpinBox()
        self.titleEdit = QLineEdit()
        self.bodyEdit = QTextEdit()
        self.showMessageButton = QPushButton()

        self.minimizeAction = QAction()
        self.maximizeAction = QAction()
        self.restoreAction = QAction()
        self.quitAction = QAction()

        self.trayIcon = QSystemTrayIcon()
        self.trayIconMenu = QMenu()

        self.createIconGroupBox()
        self.createMessageGroupBox()

        self.iconLabel.setMinimumWidth(self.durationLabel.sizeHint().width())

        self.createActions()
        self.createTrayIcon()

        self.showMessageButton.clicked.connect(self.showMessage)
        self.showIconCheckBox.toggled.connect(self.trayIcon.setVisible)
        self.iconComboBox.currentIndexChanged.connect(self.setIcon)
        self.trayIcon.messageClicked.connect(self.messageClicked)
        self.trayIcon.activated.connect(self.iconActivated)

        self.programsListModel = QStandardItemModel(0, 1, self)
        self.programsList = QListView()
        self.programsList.setModel(self.programsListModel)
        self.programsListPage = QWidget()
        self.programsListLayout = QVBoxLayout()
        self.programsListButtons = QHBoxLayout()
        self.programsListButtonNew = QPushButton("New")
        self.programsListButtonDelete = QPushButton("Delete")
        self.programsListButtonEdit = QPushButton("Edit")
        self.programsListButtonSet = QPushButton("Set")
        self.programsListButtons.addWidget(self.programsListButtonNew)
        self.programsListButtons.addWidget(self.programsListButtonSet)
        self.programsListButtons.addWidget(self.programsListButtonEdit)
        self.programsListButtons.addWidget(self.programsListButtonDelete)
        self.programsListLayout.addLayout(self.programsListButtons)
        self.programsListLayout.addWidget(self.programsList)
        self.programsListPage.setLayout(self.programsListLayout)
        self.programsListButtonNew.clicked.connect(self.newProgram)
        self.programsListButtonEdit.clicked.connect(self.editProgram)
        self.programsListButtonDelete.clicked.connect(self.deleteProgram)
        self.programsListButtonSet.clicked.connect(self.setProgram)

        self.setProgramPage = QWidget()

        self.codeEditPage = QWidget()
        self.codeEditLayout = QVBoxLayout()
        self.codeEditNameBox = QHBoxLayout()
        self.codeEditNameBoxNameLabel = QLabel("Name:")
        self.codeEditNameBoxNameInput = QLineEdit()
        self.codeEditNameBoxSaveButton = QPushButton("Save")
        self.codeEditNameBoxCancelButton = QPushButton("Cancel")
        self.codeEditNameBox.addWidget(self.codeEditNameBoxNameLabel)
        self.codeEditNameBox.addWidget(self.codeEditNameBoxNameInput)
        self.codeEditNameBox.addWidget(self.codeEditNameBoxSaveButton)
        self.codeEditNameBox.addWidget(self.codeEditNameBoxCancelButton)
        self.codeEdit = QTextEdit()
        self.codeEditLayout.addLayout(self.codeEditNameBox)
        self.codeEditLayout.addWidget(self.codeEdit)
        self.codeEditPage.setLayout(self.codeEditLayout)
        self.codeEditLastCode = ''
        self.codeEditNameBoxSaveButton.clicked.connect(self.saveEditProgram)
        self.codeEditNameBoxCancelButton.clicked.connect(self.cancelEditProgram)

        self.documentation = QTextBrowser()

        self.tabWidget = QTabWidget()
        self.tabWidget.setIconSize(QSize(64, 64))
        self.tabWidget.addTab(self.programsListPage, QIcon(":/images/Spell-Scroll-icon.png"), "Programs")
        self.tabWidget.addTab(self.setProgramPage, QIcon(":/images/Adventure-Map-icon.png"), "Set Program")
        self.tabWidget.addTab(self.codeEditPage, QIcon(":/images/Sword-icon.png"), "Program Editor")
        self.tabWidget.addTab(self.documentation, QIcon(":/images/Spell-Book-icon.png"), "Documentation")

        self.mainLayout = QVBoxLayout()
        self.mainLayout.addWidget(self.tabWidget)
        self.setLayout(self.mainLayout)

        self.iconComboBox.setCurrentIndex(1)
        self.trayIcon.show()

        self.setWindowTitle(APP_NAME)
        self.resize(800, 600)
        self.findKeyboard()

    @Slot()
    def newProgram(self):
        self.showNormal()
        self.tabWidget.setCurrentWidget(self.codeEditPage)
        self.codeEdit.setPlainText("")
        self.codeEditLastCode = ''
        self.codeEditNameBoxNameInput.setText("")
    
    @Slot()
    def editProgram(self):
        selected = self.programsList.selectedIndexes()
        if not selected:
            return
        selected = selected[0].data()
        loadProgram = LoadProgram(self.cmdSocket, selected)
        loadProgram.loaded.connect(self.programLoaded)
        loadProgram.start()
        self.waitDialog.exec_()
    
    @Slot()
    def saveEditProgram(self):
        name = self.codeEditNameBoxNameInput.text()
        program = self.codeEdit.toPlainText()
        if not name:
            return
        editProgramWorker = EditProgram(self.cmdSocket, name, program)
        editProgramWorker.edited.connect(self.programSaved)
        editProgramWorker.start()
        self.waitDialog.exec_()
    
    @Slot()
    def cancelEditProgram(self):
        self.codeEdit.setPlainText(self.codeEditLastCode)
    
    @Slot()
    def deleteProgram(self):
        selected = self.programsList.selectedIndexes()
        if not selected:
            return
        selected = selected[0].data()
        deleteWorker = DeleteProgram(self.cmdSocket, selected)
        deleteWorker.deleted.connect(self.programDeleted)
        deleteWorker.start()
        self.waitDialog.exec_()
    
    @Slot()
    def setProgram(self):
        selected = self.programsList.selectedIndexes()
        if not selected:
            return
        selected = selected[0].data()
        setWorker = SetProgram(self.cmdSocket, selected)
        setWorker.setDone.connect(self.programSet)
        setWorker.start()
        self.waitDialog.exec_()
    
    @Slot(str, str)
    def programLoaded(self, name, program):
        self.waitDialog.close()
        self.tabWidget.setCurrentWidget(self.codeEditPage)
        self.codeEdit.setPlainText(program)
        self.codeEditLastCode = program
        self.codeEditNameBoxNameInput.setText(name)

    @Slot(str)
    def programDeleted(self, name):
        self.updateProgramsList()
    
    @Slot(str)
    def programSet(self, name):
        self.updateProgramsList()
    
    @Slot(str)
    def programSaved(self, name):
        self.updateProgramsList()
        self.tabWidget.setCurrentWidget(self.programsListPage)
    
    def findKeyboard(self):
        self.waitDialog = QDialog()
        find = ConnectKeyboard()
        find.connected.connect(self.keyboardConnected)
        find.start()
        self.waitDialog.exec_()
    
    @Slot(BluetoothSocket)
    def keyboardConnected(self, socket):
        self.cmdSocket = socket
        self.updateProgramsList()
    
    def updateProgramsList(self):
        self.listProgram = ListProgram(self.cmdSocket)
        self.listProgram.listed.connect(self.programListUpdated)
        self.listProgram.start()
    
    @Slot(list, str)
    def programListUpdated(self, programs, current_program):
        print(programs)
        print(current_program)
        self.waitDialog.close()
        self.programsListModel.clear()
        for p in programs:
            item = QStandardItem(p)
            if p == current_program:
                item.setForeground(QBrush(QColor(0, 0, 255, 127)))
            self.programsListModel.appendRow(item)

    def setVisible(self, visible):
        self.minimizeAction.setEnabled(visible)
        self.maximizeAction.setEnabled(not self.isMaximized())
        self.restoreAction.setEnabled(self.isMaximized() or not visible)
        super().setVisible(visible)

    def closeEvent(self, event):
        if not event.spontaneous() or not self.isVisible():
            return
        if self.trayIcon.isVisible():
            QMessageBox.information(self, "Systray",
                                    "The program will keep running in the system tray. "
                                    "To terminate the program, choose <b>Quit</b> in the context "
                                    "menu of the system tray entry.")
            self.hide()
            event.ignore()

    @Slot(int)
    def setIcon(self, index):
        icon = QIcon(":/images/yammi-banana-icon.png")
        self.trayIcon.setIcon(icon)
        self.setWindowIcon(icon)
        self.trayIcon.setToolTip(self.iconComboBox.itemText(index))

    @Slot(str)
    def iconActivated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            pass
        if reason == QSystemTrayIcon.DoubleClick:
            self.iconComboBox.setCurrentIndex(
                (self.iconComboBox.currentIndex() + 1) % self.iconComboBox.count()
            )
        if reason == QSystemTrayIcon.MiddleClick:
            self.showMessage()

    @Slot()
    def showMessage(self):
        self.showIconCheckBox.setChecked(True)
        selectedIcon = self.typeComboBox.itemData(self.typeComboBox.currentIndex())
        msgIcon = QSystemTrayIcon.MessageIcon(selectedIcon)

        if selectedIcon == -1:  # custom icon
            icon = QIcon(self.iconComboBox.itemIcon(self.iconComboBox.currentIndex()))
            self.trayIcon.showMessage(
                self.titleEdit.text(),
                self.bodyEdit.toPlainText(),
                icon,
                self.durationSpinBox.value() * 1000,
            )
        else:
            self.trayIcon.showMessage(
                self.titleEdit.text(),
                self.bodyEdit.toPlainText(),
                msgIcon,
                self.durationSpinBox.value() * 1000,
            )

    @Slot()
    def messageClicked(self):
        QMessageBox.information(None, "Systray",
                                "Sorry, I already gave what help I could.\n"
                                "Maybe you should try asking a human?")

    def createIconGroupBox(self):
        self.iconGroupBox = QGroupBox("Tray Icon")

        self.iconLabel = QLabel("Icon:")

        self.iconComboBox = QComboBox()
        self.iconComboBox.addItem(QIcon(":/images/bad.png"), "Bad")
        self.iconComboBox.addItem(QIcon(":/images/heart.png"), "Heart")
        self.iconComboBox.addItem(QIcon(":/images/trash.png"), "Trash")

        self.showIconCheckBox = QCheckBox("Show icon")
        self.showIconCheckBox.setChecked(True)

        iconLayout = QHBoxLayout()
        iconLayout.addWidget(self.iconLabel)
        iconLayout.addWidget(self.iconComboBox)
        iconLayout.addStretch()
        iconLayout.addWidget(self.showIconCheckBox)
        self.iconGroupBox.setLayout(iconLayout)

    def createMessageGroupBox(self):
        self.messageGroupBox = QGroupBox("Balloon Message")

        self.typeLabel = QLabel("Type:")

        self.typeComboBox = QComboBox()
        self.typeComboBox.addItem("None", QSystemTrayIcon.NoIcon)
        self.typeComboBox.addItem(
            self.style().standardIcon(QStyle.SP_MessageBoxInformation),
            "Information",
            QSystemTrayIcon.Information,
        )
        self.typeComboBox.addItem(
            self.style().standardIcon(QStyle.SP_MessageBoxWarning),
            "Warning",
            QSystemTrayIcon.Warning,
        )
        self.typeComboBox.addItem(
            self.style().standardIcon(QStyle.SP_MessageBoxCritical),
            "Critical",
            QSystemTrayIcon.Critical,
        )
        self.typeComboBox.addItem(QIcon(), "Custom icon", -1)
        self.typeComboBox.setCurrentIndex(1)

        self.durationLabel = QLabel("Duration:")

        self.durationSpinBox = QSpinBox()
        self.durationSpinBox.setRange(5, 60)
        self.durationSpinBox.setSuffix(" s")
        self.durationSpinBox.setValue(15)

        self.durationWarningLabel = QLabel("(some systems might ignore this hint)")
        self.durationWarningLabel.setIndent(10)

        self.titleLabel = QLabel("Title:")
        self.titleEdit = QLineEdit("Cannot connect to network")
        self.bodyLabel = QLabel("Body:")

        self.bodyEdit = QTextEdit()
        self.bodyEdit.setPlainText("Don't believe me. Honestly, I don't have a clue."
                                   "\nClick this balloon for details.")

        self.showMessageButton = QPushButton("Show Message")
        self.showMessageButton.setDefault(True)

        messageLayout = QGridLayout()
        messageLayout.addWidget(self.typeLabel, 0, 0)
        messageLayout.addWidget(self.typeComboBox, 0, 1, 1, 2)
        messageLayout.addWidget(self.durationLabel, 1, 0)
        messageLayout.addWidget(self.durationSpinBox, 1, 1)
        messageLayout.addWidget(self.durationWarningLabel, 1, 2, 1, 3)
        messageLayout.addWidget(self.titleLabel, 2, 0)
        messageLayout.addWidget(self.titleEdit, 2, 1, 1, 4)
        messageLayout.addWidget(self.bodyLabel, 3, 0)
        messageLayout.addWidget(self.bodyEdit, 3, 1, 2, 4)
        messageLayout.addWidget(self.showMessageButton, 5, 4)
        messageLayout.setColumnStretch(3, 1)
        messageLayout.setRowStretch(4, 1)
        self.messageGroupBox.setLayout(messageLayout)

    @Slot()
    def showProgramsPage(self):
        self.showNormal()
        self.tabWidget.setCurrentWidget(self.programsListPage)

    @Slot()
    def showSetProgramPage(self):
        self.showNormal()
        self.tabWidget.setCurrentWidget(self.setProgramPage)
    
    @Slot()
    def showDocumentation(self):
        self.showNormal()
        self.tabWidget.setCurrentWidget(self.documentation)

    def createActions(self):
        self.showProgramsAction = QAction("Programs", self)
        self.showProgramsAction.triggered.connect(self.showProgramsPage)
        self.showSetProgramAction = QAction("Set Program", self)
        self.showSetProgramAction.triggered.connect(self.showSetProgramPage)
        self.showNewProgramAction = QAction("New Program", self)
        self.showNewProgramAction.triggered.connect(self.newProgram)
        self.showDocumentationAction = QAction("Documentation", self)
        self.showDocumentationAction.triggered.connect(self.showDocumentation)
        self.quitAction = QAction("Quit", self)
        self.quitAction.triggered.connect(qApp.quit)

    def createTrayIcon(self):
        self.trayIconMenu = QMenu(self)
        self.trayIconMenu.addAction(self.showProgramsAction)
        self.trayIconMenu.addAction(self.showSetProgramAction)
        self.trayIconMenu.addAction(self.showNewProgramAction)
        self.trayIconMenu.addAction(self.showDocumentationAction)

        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.quitAction)

        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.setContextMenu(self.trayIconMenu)
