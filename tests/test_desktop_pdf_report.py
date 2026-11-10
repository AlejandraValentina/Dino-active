"""CP1 PDF export of existing technical reports."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from motorsim.desktop.pdf_report import pdf_safe_html, write_html_pdf
from motorsim.desktop.technical_report import write_technical_report_pdf

APP = QApplication.instance() or QApplication([])


def test_pdf_safe_html_removes_interactive_charts_and_raw_details():
    document = ('<h1>Informe</h1><svg role="img"><text>gráfico</text></svg>'
                '<details><summary>Registro</summary>{"raw": true}</details>'
                '<p>Contenido verificable</p>')
    text = pdf_safe_html(document)
    assert "Informe" in text and "Contenido verificable" in text
    assert "Gráfico interactivo" in text
    assert "<svg" not in text and "<details" not in text
    assert '"raw": true' not in text


def test_write_html_pdf_produces_a_nonempty_document(tmp_path):
    target = tmp_path / "informe.pdf"
    write_html_pdf(target, "<h1>Informe técnico</h1><table><tr><td>A</td></tr></table>")
    data = target.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 1000


def test_technical_report_pdf_wrapper_keeps_report_content(tmp_path):
    dataset = {"points": [{
        "variant_id": "A", "rpm": 3000.0, "status": "COMPLETE",
        "classification": "PERIOD_1", "periodicity": "PERIOD_1",
        "cycles_completed": 10, "brake_power": 10.0,
        "brake_power_status": "DEFINED", "brake_torque": 30.0,
        "brake_torque_status": "DEFINED", "BMEP": 200.0,
        "BMEP_status": "DEFINED", "engine_identity_sha256": "a" * 64,
        "identity_sha256": "b" * 64, "result_sha256": "c" * 64,
        "result_artifact_sha256": "d" * 64, "run_id": "run-a",
        "run_directory": "SYNTHETIC/run-a",
    }], "experimental_validation": "NOT_PERFORMED"}
    target = tmp_path / "technical-report.pdf"
    write_technical_report_pdf(target, dataset, source_kind="EXPLORATORY",
                               generated_at="fixed")
    data = target.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 1000
