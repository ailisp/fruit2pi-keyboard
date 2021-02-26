import sys

from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from window import Window
from libmanager import APP_NAME

if __name__ == "__main__":
    app = QApplication()

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, APP_NAME, "Cannot detect any system tray on system")
        sys.exit(1)

    QApplication.setQuitOnLastWindowClosed(False)

    window = Window()
    window.show()
    sys.exit(app.exec_())