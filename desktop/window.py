from PySide6.QtCore import Slot, QSize, QThread, Signal, Qt
from PySide6.QtGui import QAction, QIcon, QStandardItemModel, QStandardItem, QBrush, QColor, QCloseEvent
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog,
                               QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QMenu, QMessageBox, QPushButton,
                               QSpinBox, QStyle, QSystemTrayIcon, QTextEdit,
                               QVBoxLayout, QTabWidget, QTextBrowser, QWidget,
                               QListView)
from bluetooth.bluez import BluetoothSocket
import rc_systray
from libmanager import APP_NAME, Config, connect_keyboard, find_keyboard, send_command
import time

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
        self.createTrayIcon()
        self.createProgramsList()
        self.createCodeEditPage()
        self.logsPage = QTextBrowser()
        self.documentation = QTextBrowser()

        self.tabWidget = QTabWidget()
        self.tabWidget.setIconSize(QSize(64, 64))
        self.tabWidget.addTab(self.programsListPage, QIcon(":/images/Adventure-Map-icon.png"), "Programs")
        self.tabWidget.addTab(self.codeEditPage, QIcon(":/images/Sword-icon.png"), "Edit Program")
        self.tabWidget.addTab(self.logsPage, QIcon(":/images/Spell-Scroll-icon.png"), "Logs")
        self.tabWidget.addTab(self.documentation, QIcon(":/images/Spell-Book-icon.png"), "Documentation")

        self.mainLayout = QVBoxLayout()
        self.mainLayout.addWidget(self.tabWidget)
        self.setLayout(self.mainLayout)

        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.resize(800, 600)

        self.systrayHintMsgShowed = False
        self.firstShow = True
        self.fromQuit = False

    def createProgramsList(self):
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

    def createCodeEditPage(self):
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

    def showEvent(self, event):
        super().showEvent(event)
        if self.firstShow:
            self.firstShow = False
            self.createWaitDialog()
            self.findKeyboard()

    def closeWaitDialog(self):
        time.sleep(1)
        self.waitDialog.close()

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
        self.showWaitDialog("Loading program ...")

    @Slot()
    def saveEditProgram(self):
        name = self.codeEditNameBoxNameInput.text()
        program = self.codeEdit.toPlainText()
        if not name:
            return
        editProgramWorker = EditProgram(self.cmdSocket, name, program)
        editProgramWorker.edited.connect(self.programSaved)
        editProgramWorker.start()
        self.showWaitDialog("Saving program ...")

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
        self.showWaitDialog("Deleting program ...")

    @Slot()
    def setProgram(self):
        selected = self.programsList.selectedIndexes()
        if not selected:
            return
        selected = selected[0].data()
        setWorker = SetProgram(self.cmdSocket, selected)
        setWorker.setDone.connect(self.programSet)
        setWorker.start()
        self.showWaitDialog("Setting program ...")

    @Slot(str, str)
    def programLoaded(self, name, program):
        self.closeWaitDialog()
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

    def createWaitDialog(self):
        self.waitDialog = QDialog(self)
        self.waitDialogLayout = QHBoxLayout()
        self.waitDialogLabel = QLabel()
        self.waitDialogLayout.addWidget(self.waitDialogLabel)
        self.waitDialog.setLayout(self.waitDialogLayout)
        self.waitDialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

    def showWaitDialog(self, text='Please wait...'):
        self.waitDialogLabel.setText(text)
        self.waitDialog.exec_()

    def findKeyboard(self):
        find = ConnectKeyboard()
        find.connected.connect(self.keyboardConnected)
        find.start()
        self.showWaitDialog('Finding and connecting Fruit2Pi Keyboard ...')

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
        self.closeWaitDialog()
        self.programsListModel.clear()
        for p in programs:
            item = QStandardItem(p)
            if p == current_program:
                item.setForeground(QBrush(QColor(0, 0, 255, 127)))
            self.programsListModel.appendRow(item)

    def setVisible(self, visible):
        super().setVisible(visible)

    def closeEvent(self, event):
        if self.fromQuit:
            return
        if not event.spontaneous() or not self.isVisible():
            return
        if not self.systrayHintMsgShowed:
            self.systrayHintMsgShowed = True
            icon = QIcon(":/images/yammi-banana-icon.png")
            self.trayIcon.showMessage(APP_NAME,
                                      "Running on background"
                                      "To quit, choose <b>Quit</b> in the icon menu",
                                      icon,
                                      5000
                                      )
        self.hide()
        event.ignore()

    @Slot(str)
    def iconActivated(self, reason):
        print(reason)
        if reason == QSystemTrayIcon.Trigger:
            self.showNormal()
        if reason == QSystemTrayIcon.DoubleClick:
            self.showNormal()

    @Slot()
    def showProgramsPage(self):
        self.showNormal()
        self.tabWidget.setCurrentWidget(self.programsListPage)

    @Slot()
    def showLogsPage(self):
        self.showNormal()
        self.tabWidget.setCurrentWidget(self.logsPage)
    
    @Slot()
    def showDocumentation(self):
        self.showNormal()
        self.tabWidget.setCurrentWidget(self.documentation)

    @Slot()
    def quit(self):
        self.fromQuit = True
        qApp.quit()

    def createTrayIcon(self):
        self.showProgramsAction = QAction("Programs", self)
        self.showProgramsAction.triggered.connect(self.showProgramsPage)
        self.showNewProgramAction = QAction("New Program", self)
        self.showNewProgramAction.triggered.connect(self.newProgram)
        self.showSetProgramAction = QAction("Logs", self)
        self.showSetProgramAction.triggered.connect(self.showLogsPage)
        self.showDocumentationAction = QAction("Documentation", self)
        self.showDocumentationAction.triggered.connect(self.showDocumentation)
        self.quitAction = QAction("Quit", self)
        self.quitAction.triggered.connect(self.quit)

        self.trayIconMenu = QMenu(self)
        self.trayIconMenu.addAction(self.showProgramsAction)
        self.trayIconMenu.addAction(self.showSetProgramAction)
        self.trayIconMenu.addAction(self.showNewProgramAction)
        self.trayIconMenu.addAction(self.showDocumentationAction)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.quitAction)
        self.trayIcon = QSystemTrayIcon(self)

        self.trayIcon.setContextMenu(self.trayIconMenu)
        self.trayIcon.activated.connect(self.iconActivated)
        self.trayIcon.setIcon(QIcon(":/images/yammi-banana-icon.png"))
        self.trayIcon.show()
