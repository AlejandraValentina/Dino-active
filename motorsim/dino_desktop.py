"""Launch the separate native Dino 2T engineering desktop application."""
import sys
from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication
from .desktop.app import DinoDesktopWindow
from .runtime import APP_VERSION, unexpected_error

def main():
    if '--verify-frontend-f23' in sys.argv:
        index=sys.argv.index('--verify-frontend-f23')
        from .desktop.acceptance_frontend_f23 import main as acceptance_main
        return acceptance_main(sys.argv[index+1:])
    if '--verify-frontend-commercial' in sys.argv:
        index=sys.argv.index('--verify-frontend-commercial')
        from .desktop.acceptance_frontend_commercial import main as acceptance_main
        return acceptance_main(sys.argv[index+1:])
    if "--verify-cp2-acceptance" in sys.argv:
        index=sys.argv.index("--verify-cp2-acceptance")
        from .desktop.acceptance_cp2 import main as acceptance_main
        return acceptance_main(sys.argv[index+1:])
    if "--verify-cp1-acceptance" in sys.argv:
        index=sys.argv.index("--verify-cp1-acceptance")
        from .desktop.acceptance_cp1 import main as acceptance_main
        return acceptance_main(sys.argv[index+1:])
    if "--verify-four-stroke-desktop" in sys.argv:
        index=sys.argv.index("--verify-four-stroke-desktop")
        from .desktop.acceptance_smoke_4t import main as smoke_main
        return smoke_main(sys.argv[index+1:])
    app=QApplication(sys.argv);app.setApplicationName('Dino 2T');app.setApplicationVersion(APP_VERSION);app.setOrganizationName('Dino2T')
    QLocale.setDefault(QLocale('es_UY'));sys.excepthook=unexpected_error
    window=DinoDesktopWindow();window.show();return app.exec()

if __name__=='__main__':raise SystemExit(main())
