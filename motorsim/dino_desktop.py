"""Launch the separate native Dino 2T engineering desktop application."""
import sys
from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication
from .desktop.app import DinoDesktopWindow
from .runtime import unexpected_error

def main():
    app=QApplication(sys.argv);app.setApplicationName('Dino 2T');app.setApplicationVersion('1.0.0');app.setOrganizationName('Dino2T')
    QLocale.setDefault(QLocale('es_UY'));sys.excepthook=unexpected_error
    window=DinoDesktopWindow();window.show();return app.exec()

if __name__=='__main__':raise SystemExit(main())
