"""Launch the separate native Dino 2T engineering desktop application."""
import sys
from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication
from .desktop.app import DinoDesktopWindow
from .runtime import APP_VERSION, unexpected_error

def main():
    if "--verify-four-stroke-desktop" in sys.argv:
        index=sys.argv.index("--verify-four-stroke-desktop")
        from .desktop.acceptance_smoke_4t import main as smoke_main
        return smoke_main(sys.argv[index+1:])
    app=QApplication(sys.argv);app.setApplicationName('Dino 2T');app.setApplicationVersion(APP_VERSION);app.setOrganizationName('Dino2T')
    QLocale.setDefault(QLocale('es_UY'));sys.excepthook=unexpected_error
    window=DinoDesktopWindow();window.show();return app.exec()

if __name__=='__main__':raise SystemExit(main())
