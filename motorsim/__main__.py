"""Ejecutar con python -m motorsim desde la raíz del repositorio."""

import sys

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication

from .window import MainWindow
from .runtime import APP_VERSION, build_info, unexpected_error


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MotorSim")
    app.setApplicationVersion(APP_VERSION)
    sys.excepthook=unexpected_error
    QLocale.setDefault(QLocale("es_UY"))
    translator = QTranslator(app)
    translator.load("qtbase_es", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    app.installTranslator(translator)
    try:
        build_info()
        window = MainWindow()
    except Exception:
        unexpected_error(*sys.exc_info())
        return 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
