"""Brief product onboarding, synthetic examples and first-run checks."""
from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
                               QPushButton, QTextBrowser, QVBoxLayout)

GUIDE_STEPS = (
    ("1. Crear o abrir un proyecto",
     "Use Archivo > Nuevo para crear un proyecto 2T o 4T, o abra un proyecto "
     "existente. Las plantillas iniciales son configuraciones sintéticas de ingeniería."),
    ("2. Elegir la familia correcta",
     "2T, 4T 0D de referencia y 4T nativo son flujos separados. No mezcle "
     "resultados ni compare diseños de familias distintas."),
    ("3. Editar el modelo",
     "Revise cilindro, admisión, escape, combustión y condiciones de operación. "
     "Cada dato conserva su clasificación de procedencia."),
    ("4. Ejecutar o cargar resultados",
     "Una corrida periódica no es validación experimental. Los estados parciales "
     "o no convergentes se muestran como tales y no se promocionan."),
    ("5. Exportar con procedencia",
     "Exporte HTML, PDF o CSV según el flujo. Los informes declaran calibración "
     "no realizada, validación experimental no realizada y predictiva no declarada."),
)
LIMITS = (
    "Dino Desktop es una herramienta de ingeniería. La funcionalidad comercial "
    "no equivale a calibración, validación experimental ni capacidad predictiva."
)


def guide_html() -> str:
    steps = "".join(f"<h3>{title}</h3><p>{body}</p>" for title, body in GUIDE_STEPS)
    return (f"<h2>Guía breve de inicio</h2><p>{LIMITS}</p>{steps}"
            "<p><b>Primeros pasos:</b> use los botones de ejemplo o verifique el "
            "estado del proyecto actual.</p>")


def first_steps_status(window) -> list[dict]:
    """Return presentation-only checks for the current desktop state."""
    context = getattr(window, "context", None)
    project = getattr(context, "project", {}) or {}
    active = window._active_context() if hasattr(window, "_active_context") else context
    if active is getattr(window, "four_stroke_context", None):
        family = "4T_0D"
        engine_ready = getattr(active, "project", None) is not None
    else:
        family = getattr(active, "engine_family", "2T")
        try:
            engine_ready = bool(active.engine())
        except (AttributeError, KeyError, TypeError):
            engine_ready = False
    result_ready = False
    dataset = getattr(getattr(window, "results", None), "dataset", None)
    if dataset:
        result_ready = True
    if getattr(getattr(window, "four_stroke_results", None), "result", None):
        result_ready = True
    native = getattr(window, "native_four_stroke", None)
    if native is not None and getattr(getattr(native, "results", None), "loaded", None):
        result_ready = True
    return [
        {"label": "Proyecto con identidad",
         "ok": bool(project.get("project_id") or getattr(active, "name", None)),
         "detail": str(project.get("project_id") or getattr(active, "name", "sin proyecto"))},
        {"label": "Familia y motor activos", "ok": engine_ready,
         "detail": family},
        {"label": "Resultado o ejecución disponibles", "ok": result_ready,
         "detail": "Cargue o ejecute un punto para exportar resultados." if not result_ready else "Listo para revisar resultados."},
    ]


def status_html(window) -> str:
    rows = "".join(
        f"<tr><td>{'OK' if item['ok'] else 'Pendiente'}</td>"
        f"<td>{item['label']}</td><td>{item['detail']}</td></tr>"
        for item in first_steps_status(window))
    return ("<h3>Verificación de primeros pasos</h3><table border='1' "
            "cellspacing='0' cellpadding='4'><tr><th>Estado</th><th>Paso</th>"
            f"<th>Detalle</th></tr>{rows}</table>")


class OnboardingDialog(QDialog):
    def __init__(self, window, parent=None):
        super().__init__(parent or window)
        self.window = window
        self.setWindowTitle("Guía de inicio y plantillas")
        self.resize(760, 560)
        layout = QVBoxLayout(self)
        title = QLabel("Dino Desktop — primeros pasos")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)
        self.browser = QTextBrowser()
        self.browser.setHtml(guide_html())
        layout.addWidget(self.browser, 2)
        self.status = QTextBrowser()
        self.status.setMaximumHeight(190)
        layout.addWidget(self.status, 1)
        examples = QHBoxLayout()
        for label, method in (
            ("Ejemplo 2T sintético", "new_example_2t"),
            ("Ejemplo 4T nativo sintético", "new_example_native_4t"),
            ("Ejemplo 4T 0D sintético", "new_example_4t_0d"),
        ):
            button = QPushButton(label)
            button.setObjectName(f"onboarding-{method}")
            button.clicked.connect(lambda *_, name=method: self._create_example(name))
            examples.addWidget(button)
        examples.addStretch(1)
        refresh = QPushButton("Verificar primeros pasos")
        refresh.clicked.connect(self.refresh)
        examples.addWidget(refresh)
        layout.addLayout(examples)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self.refresh()

    def _create_example(self, name):
        callback = getattr(self.window, name, None)
        if callback is not None:
            callback()
            self.refresh()

    def refresh(self):
        self.status.setHtml(status_html(self.window))
