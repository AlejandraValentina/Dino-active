"""Self-contained engineering reports from already imported Desktop results.

This module is presentation/export only. It never recomputes or changes results.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import html
import json
import math
from pathlib import Path

from .presentation import format_number, state_label


METRICS = (
    ("Potencia de freno", "brake_power", "kW"),
    ("Torque de freno", "brake_torque", "N·m"),
    ("BMEP", "BMEP", "kPa"),
)
PERIODIC = {"PERIOD_1", "PERIOD_2"}
COLORS = ("#167d9a", "#d16a32", "#6a8d3b", "#8856a7", "#c04468", "#586879")
CONDITION_FIELDS = (
    "fuel_id", "afr_kg_air_per_kg_fuel", "mesh_resolution",
    "total_finite_volume_cells", "cycles_requested", "solver_identity_sha256",
    "implementation_identity_sha256", "periodicity_contract",
)
_PAIRING_LABELS = {
    "EXACT_RPM_AND_OPERATING_CONTEXT": "RPM exacta y contexto operativo coincidente",
}
_PAIRING_CONTEXT_LABELS = {
    "fuel_id": "identificador de combustible",
    "afr_kg_air_per_kg_fuel": "relación aire/combustible por masa",
    "total_finite_volume_cells": "cantidad de celdas de volumen finito",
    "cycles_requested": "ciclos solicitados",
    "solver_identity_sha256": "identidad SHA-256 del solver",
    "implementation_identity_sha256": "identidad SHA-256 de la implementación",
}


def _safe_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _metric_value(row, metric):
    value = row.get(metric)
    if row.get(metric + "_status") != "DEFINED" or not _safe_number(value):
        return None
    return float(value)


def _reportable(row, metric):
    periodicity = row.get("periodicity")
    if periodicity is None and row.get("classification") in PERIODIC:
        periodicity = row.get("classification")
    return periodicity in PERIODIC and _metric_value(row, metric) is not None


def _condition_status(left, right):
    different = [key for key in CONDITION_FIELDS
                 if left.get(key) is not None and right.get(key) is not None
                 and left.get(key) != right.get(key)]
    missing = [key for key in CONDITION_FIELDS
               if left.get(key) is None or right.get(key) is None]
    if different:
        return "Campos distintos: " + ", ".join(different)
    if missing:
        return "No verificable; faltan: " + ", ".join(missing)
    return "Coinciden los campos de operación informados"


def _esc(value):
    if value is None:
        return "No informado"
    return html.escape(str(value), quote=True)


def _pairing_label(value):
    if isinstance(value, str) and value in _PAIRING_LABELS:
        return _PAIRING_LABELS[value]
    return state_label(value or "NOT_REPORTED")


def _pairing_reason_label(value):
    if value is None:
        return "Motivo no informado"
    text = str(value)
    for field, label in _PAIRING_CONTEXT_LABELS.items():
        text = text.replace(field, label)
    return text


def _chart_svg(rows, variants, label, metric, unit):
    eligible = [row for row in rows if _reportable(row, metric)]
    width, height = 760, 330
    left, top, right, bottom = 72, 34, 22, 58
    plot_w, plot_h = width - left - right, height - top - bottom
    if not eligible:
        return (f'<section><h3>{_esc(label)}</h3><p class="empty">'
                'No hay puntos clasificados PERIOD_1/PERIOD_2 con la métrica definida.</p></section>')
    rpms = [float(row["rpm"]) for row in eligible]
    vals = [_metric_value(row, metric) for row in eligible]
    xmin, xmax = min(rpms), max(rpms)
    ymin, ymax = min(vals), max(vals)
    if xmax == xmin:
        xmin -= 1; xmax += 1
    if ymax == ymin:
        pad = max(abs(ymax) * .05, 1e-9); ymin -= pad; ymax += pad
    else:
        pad = (ymax - ymin) * .08; ymin -= pad; ymax += pad
    x = lambda value: left + (float(value) - xmin) / (xmax - xmin) * plot_w
    y = lambda value: top + (ymax - float(value)) / (ymax - ymin) * plot_h
    parts = [f'<section><h3>{_esc(label)}</h3><svg role="img" aria-label="{_esc(label)} por RPM" '
             f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
             f'<rect width="{width}" height="{height}" fill="#fff"/>',
             f'<path d="M{left} {top}V{top+plot_h}H{left+plot_w}" fill="none" stroke="#526273"/>']
    for index in range(5):
        fy = top + plot_h * index / 4
        value = ymax - (ymax - ymin) * index / 4
        parts.append(f'<path d="M{left} {fy:.2f}H{left+plot_w}" stroke="#e1e7ec"/>')
        parts.append(f'<text x="{left-8}" y="{fy+4:.2f}" text-anchor="end">{_esc(format_number(value))}</text>')
        rpm = xmin + (xmax - xmin) * index / 4
        fx = left + plot_w * index / 4
        parts.append(f'<text x="{fx:.2f}" y="{top+plot_h+22}" text-anchor="middle">{_esc(format_number(rpm))}</text>')
    parts.append(f'<text x="{left+plot_w/2}" y="{height-10}" text-anchor="middle">RPM</text>')
    parts.append(f'<text transform="translate(17 {top+plot_h/2}) rotate(-90)" text-anchor="middle">{_esc(unit)}</text>')
    for index, variant in enumerate(variants):
        color = COLORS[index % len(COLORS)]
        points = [row for row in eligible if str(row.get("variant_id")) == variant]
        for row in points:
            cx, cy = x(row["rpm"]), y(_metric_value(row, metric))
            parts.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="5" fill="{color}"><title>'
                         f'{_esc(variant)} · {_esc(format_number(row["rpm"]))} RPM · '
                         f'{_esc(format_number(_metric_value(row, metric)))} {unit}</title></circle>')
        lx = left + index * min(190, plot_w / max(len(variants), 1))
        parts.append(f'<circle cx="{lx+5:.2f}" cy="{top-12}" r="5" fill="{color}"/>')
        parts.append(f'<text x="{lx+15:.2f}" y="{top-8}">{_esc(variant)}</text>')
    parts.append('</svg><p class="note">Marcadores = puntos disponibles. No hay interpolación. '
                 'La clasificación periódica observada no equivale a validación experimental.</p></section>')
    return "".join(parts)


def _study_response_plot_html(manifest, imported_points, *, manifest_bound=True):
    """Render scalar study response from unique, artifact-bound PERIOD_1 rows."""
    method = manifest.get("design_method")
    parameter = manifest.get("parameter") or {}
    if method == "RPM_ENVELOPE_V1":
        return ("<h3>Respuesta paramétrica</h3><p class=\"empty\">Estudio de envolvente RPM: "
                "los puntos se presentan en la tabla por diseño y RPM; no se mezclan regímenes en una respuesta 1D.</p>")
    if parameter.get("axes") or method == "FACTORIAL_2X2_V1":
        return ("<h3>Respuesta paramétrica</h3><p class=\"empty\">Estudio factorial: "
                "la matriz se conserva como tal y no se reduce a una respuesta unidimensional.</p>")
    if not manifest_bound:
        return ("<h3>Respuesta paramétrica</h3><p class=\"empty\">No se grafica: no se pudo verificar "
                "la procedencia actual del manifiesto del estudio.</p>")

    by_run = {}
    for row in imported_points if isinstance(imported_points, list) else []:
        if isinstance(row, dict) and row.get("run_id") is not None:
            by_run.setdefault(str(row["run_id"]), []).append(row)

    definitions = (
        ("Potencia de freno", "brake_power", "kW"),
        ("Torque de freno", "brake_torque", "N·m"),
        ("BMEP", "BMEP", "kPa"),
    )
    study_points = manifest.get("points") if isinstance(manifest.get("points"), list) else []
    plots = []
    width, height = 760, 330
    left, top, right, bottom = 72, 34, 22, 58
    plot_w, plot_h = width-left-right, height-top-bottom

    for label, metric, unit in definitions:
        eligible, excluded = [], []
        for index, point in enumerate(study_points):
            value_x = point.get("value")
            run_id = (point.get("source_run_id") or point.get("historical_source_run_id") or
                      point.get("run_id"))
            reason = None
            result_row = None
            if not _safe_number(value_x):
                reason = "El valor del parámetro no es numérico y finito."
            elif point.get("status") not in {"COMPLETE", "CACHED"}:
                shown_status = state_label(point.get("status") or "NOT_REPORTED")
                reason = f"Punto sin resultado terminal: {shown_status}."
            elif point.get("status") == "CACHED" and not point.get("reused_verified"):
                reason = "Resultado histórico reutilizado sin verificación declarada."
            elif not run_id:
                reason = "El manifiesto no conserva un run ID de origen."
            else:
                candidates = by_run.get(str(run_id), [])
                source_dir = point.get("run_directory")
                source_hash = point.get("result_artifact_sha256") or point.get("result_sha256")
                if not source_dir or not source_hash:
                    reason = "El manifiesto no conserva ruta y hash del artifact fuente."
                else:
                    try:
                        expected_dir = Path(source_dir).resolve()
                    except (OSError, TypeError, ValueError):
                        expected_dir = None
                    try:
                        candidates = [row for row in candidates
                            if expected_dir is not None and row.get("artifact_directory") and
                            Path(row["artifact_directory"]).resolve() == expected_dir and
                            row.get("result_sha256") == source_hash]
                    except (OSError, RuntimeError, TypeError, ValueError):
                        candidates = []
                    if len(candidates) != 1:
                        reason = ("La fuente importada no coincide de forma única con el run, ruta y hash del manifiesto."
                                  if candidates else "No se encontró el artifact importado que coincide con el manifiesto.")
                    else:
                        result_row = candidates[0]
                        try:
                            raw = (expected_dir / "result.json").read_bytes()
                            source_result = json.loads(raw.decode("utf-8"))
                            run_meta = json.loads((expected_dir / "run.json").read_text(encoding="utf-8"))
                            identity = point.get("identity_sha256") or point.get("engine_identity_sha256")
                            bindings = source_result.get("bindings") or {}
                            if (hashlib_sha256(raw) != source_hash or run_meta.get("result_sha256") != source_hash or
                                    (point.get("result_sha256") is not None and point.get("result_sha256") != source_hash) or
                                    source_result.get("status") != "COMPLETE" or
                                    source_result.get("schema") != "DINO_ENGINEERING_RUN_V1" or
                                    bindings.get("run_id") != run_id or
                                    (identity is not None and bindings.get("identity_sha256") != identity)):
                                reason = "El artifact fuente no supera la comprobación actual de hash e identidad."
                            else:
                                attempt = source_result.get("attempt")
                                expected_diagnostics_hash = source_result.get("diagnostic_manifest_sha256")
                                diagnostics_path = expected_dir / str(attempt) / "manifest.json" if attempt else None
                                if not diagnostics_path or not expected_diagnostics_hash:
                                    reason = "El resultado no conserva el hash de su manifiesto de diagnóstico."
                                elif hashlib.sha256(diagnostics_path.read_bytes()).hexdigest() != expected_diagnostics_hash:
                                    reason = "El manifiesto de diagnóstico cambió desde la importación del resultado."
                        except (OSError, RuntimeError, UnicodeDecodeError, ValueError, TypeError, json.JSONDecodeError):
                            reason = "No se pudo volver a verificar result.json/run.json del punto."
            if reason is None and result_row is not None:
                periodicity = result_row.get("periodicity") or result_row.get("classification")
                if periodicity != "PERIOD_1":
                    shown_periodicity = state_label(periodicity or "NOT_REPORTED")
                    reason = f"La fuente está clasificada {shown_periodicity}; se requiere PERIOD_1."
                elif ((point.get("periodicity") or point.get("classification")) not in (None, "PERIOD_1")):
                    reason = "La periodicidad del manifiesto no coincide con la fuente PERIOD_1."
                elif result_row.get(metric + "_status") != "DEFINED" or not _safe_number(result_row.get(metric)):
                    reason = "La métrica no está definida y finita en la fuente PERIOD_1."
                else:
                    expected_rpm = point.get("rpm", manifest.get("rpm"))
                    if (_safe_number(expected_rpm) and
                            (not _safe_number(result_row.get("rpm")) or
                             float(expected_rpm) != float(result_row["rpm"]))):
                        reason = "La RPM importada no coincide exactamente con el punto del manifiesto."
            if reason:
                excluded.append((index, point, run_id, reason))
            else:
                eligible.append({"x": float(value_x), "y": float(result_row[metric]),
                    "baseline": bool(point.get("baseline")), "run_id": str(run_id),
                    "hash": point.get("result_artifact_sha256") or point.get("result_sha256")})

        parts = [f'<section class="study-response"><h3>{_esc(label)} por parámetro</h3>',
            '<p>Marcadores observados de fuentes únicas con run ID, ruta y SHA-256 coincidentes; '
            'result.json, run.json y el hash del manifiesto de diagnóstico se comprueban otra vez al exportar. '
            'Sólo PERIOD_1 con métrica definida. '
            'No se conectan, interpolan ni ajustan puntos.</p>']
        if not eligible:
            parts.append('<p class="empty">No hay puntos PERIOD_1 con fuente y métrica verificadas para esta gráfica.</p>')
        else:
            xs = [row["x"] for row in eligible]; ys = [row["y"] for row in eligible]
            xmin, xmax = min(xs), max(xs); ymin, ymax = min(ys), max(ys)
            if xmin == xmax:
                delta = max(abs(xmin)*.05, 1.0); xmin -= delta; xmax += delta
            if ymin == ymax:
                delta = max(abs(ymin)*.05, 1.0); ymin -= delta; ymax += delta
            else:
                delta = (ymax-ymin)*.08; ymin -= delta; ymax += delta
            x = lambda value: left + (value-xmin)/(xmax-xmin)*plot_w
            y = lambda value: top + (ymax-value)/(ymax-ymin)*plot_h
            x_unit = parameter.get("unit") or ""
            x_label = parameter.get("label") or parameter.get("id") or "Parámetro"
            parts.append(f'<svg role="img" aria-label="{_esc(label)} por {_esc(x_label)}" '
                f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
                f'<rect width="{width}" height="{height}" fill="#fff"/>'
                f'<path d="M{left} {top}V{top+plot_h}H{left+plot_w}" fill="none" stroke="#526273"/>')
            for tick in range(5):
                fraction = tick/4
                yy = top + plot_h*fraction; y_value = ymax-(ymax-ymin)*fraction
                xx = left + plot_w*fraction; x_value = xmin+(xmax-xmin)*fraction
                parts.append(f'<path d="M{left} {yy:.2f}H{left+plot_w}" stroke="#e1e7ec"/>'
                    f'<text x="{left-8}" y="{yy+4:.2f}" text-anchor="end">{_esc(format_number(y_value))}</text>'
                    f'<text x="{xx:.2f}" y="{top+plot_h+22}" text-anchor="middle">{_esc(format_number(x_value))}</text>')
            parts.append(f'<text x="{left+plot_w/2}" y="{height-10}" text-anchor="middle">{_esc(x_label)} ({_esc(x_unit)})</text>'
                f'<text transform="translate(17 {top+plot_h/2}) rotate(-90)" text-anchor="middle">{_esc(unit)}</text>')
            legend = []
            for baseline, name, color in ((True, "Baseline", COLORS[0]), (False, "Diseños alternativos", COLORS[1])):
                markers = [row for row in eligible if row["baseline"] is baseline]
                if not markers:
                    continue
                legend.append(f'<span><i style="color:{color}">●</i> {_esc(name)} · {len(markers)} punto(s)</span>')
                for row in markers:
                    title = (f"{row['run_id']} · {format_number(row['x'])} {x_unit} · "
                             f"{format_number(row['y'])} {unit} · SHA-256 {row['hash']}")
                    parts.append(f'<circle class="observed-point" cx="{x(row["x"]):.2f}" '
                        f'cy="{y(row["y"]):.2f}" r="5" fill="{color}"><title>{_esc(title)}</title></circle>')
            parts.append('</svg><p class="legend">'+' · '.join(legend)+'</p>')
        if excluded:
            rows = []
            for index, point, run_id, reason in excluded:
                rows.append('<tr>'+''.join((f'<td>{index+1}</td>',f'<td>{_esc(run_id or "No informado")}</td>',
                    f'<td>{_esc(format_number(point.get("value")) if _safe_number(point.get("value")) else "No informado")} {_esc(point.get("unit") or parameter.get("unit") or "")}</td>',
                    f'<td>{_esc(state_label(point.get("classification") or point.get("status") or "NOT_REPORTED"))} / {_esc(state_label(point.get("periodicity") or "NOT_EVALUATED"))}</td>',
                    f'<td>{_esc(reason)}</td>'))+'</tr>')
            parts.append('<h4>Puntos excluidos de la respuesta · '+_esc(label)+'</h4>'
                '<table><thead><tr><th>Punto</th><th>Run fuente</th><th>Parámetro</th><th>Estado informado</th><th>Motivo</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table>')
        parts.append('</section>')
        plots.append(''.join(parts))
    return ''.join(plots)


def hashlib_sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def render_technical_report(dataset: dict, *, source_kind: str,
                            selected_variants=None, source_path=None,
                            active_project_id=None, generated_at=None,
                            design_study_manifest=None,
                            design_study_manifest_path=None,
                            design_study_manifest_sha256=None,
                            design_study_reference=None,
                            factorial_effects=None) -> str:
    """Render exact selected result records and an explicit evidence boundary."""
    points = dataset.get("points") if isinstance(dataset, dict) else None
    if not isinstance(points, list) or not points:
        raise ValueError("No hay puntos cargados para documentar.")
    variants = sorted({str(row.get("variant_id") or "Variante no informada") for row in points})
    selected = set(str(value) for value in (selected_variants or variants))
    variants = [name for name in variants if name in selected]
    rows = [row for row in points if str(row.get("variant_id") or "Variante no informada") in selected]
    if not rows:
        raise ValueError("La selección actual no contiene puntos para documentar.")

    kind_labels = {
        "HISTORICAL_IMPL2": "Datos históricos sintéticos; no son mediciones experimentales.",
        "LEGACY_HISTORICAL": "Resumen histórico heredado; conserva los campos presentes en el artefacto.",
        "EXPLORATORY": "Corridas exploratorias; los transitorios no se presentan como prestaciones definitivas.",
        "IMPORTED_EXTERNAL": "Resultados importados; su origen se limita a la procedencia declarada en el artefacto.",
    }
    origin = kind_labels.get(source_kind, "Origen no clasificado por la interfaz; consultar procedencia original.")
    validation = dataset.get("experimental_validation", "NOT_REPORTED")
    generated_at = generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    if source_path:
        source_path = Path(source_path)
        source_entries = [source_path]
        if source_path.suffix.lower() == ".csv" and source_path.with_suffix(".json").is_file():
            source_entries.append(source_path.with_suffix(".json"))
    else:
        source_entries = [Path(path) for path in dataset.get("source_paths", [])
                          if isinstance(path, str)]
    source_rows = []
    for path in source_entries:
        try:
            digest = __import__("hashlib").sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        except OSError:
            digest = None
        source_rows.append(f"<tr><td>{_esc(path)}</td><td>{digest or 'No disponible'}</td></tr>")
    if not source_rows:
        source_rows.append("<tr><td>Ruta de origen no conservada por el importador</td><td>No disponible</td></tr>")
    study_html = ""
    if design_study_manifest is not None:
        manifest = design_study_manifest
        if not isinstance(manifest, dict) or manifest.get("schema") != "DINO_PARAMETRIC_DESIGN_STUDY_V1":
            raise ValueError("El manifiesto de estudio no tiene un esquema reconocido.")
        is_rpm_envelope=manifest.get("design_method")=="RPM_ENVELOPE_V1"
        rpm_groups={group.get("index"):group for group in manifest.get("groups",[]) if isinstance(group,dict)}
        parameter = manifest.get("parameter") or {}
        study_rows = []
        for point in manifest.get("points", []):
            value = point.get("value")
            shown_value = format_number(value) if _safe_number(value) else "No informado"
            factors = point.get("factor_values")
            if isinstance(factors,list) and factors:
                shown_value = " · ".join(
                    f"{_esc(item.get('label') or item.get('parameter_id'))}="
                    f"{_esc(format_number(item.get('value')) if _safe_number(item.get('value')) else 'No informado')} "
                    f"{_esc(item.get('unit') or '')}" for item in factors if isinstance(item,dict))
            identity_sha = point.get("engine_identity_sha256") or "No disponible"
            source_run = point.get("source_run_id") or point.get("historical_source_run_id") or point.get("run_id")
            design_index=point.get("design_index")
            rpm_group=rpm_groups.get(design_index,{}) if is_rpm_envelope else {}
            sweep_path=point.get("sweep_manifest") or rpm_group.get("sweep_manifest")
            sweep_digest=point.get("sweep_manifest_sha256") or rpm_group.get("sweep_manifest_sha256")
            study_rows.append("<tr>" + "".join((
                f"<td>{_esc(point.get('index',design_index))}</td>",
                f"<td>{_esc(point.get('status') or 'No ejecutado')}</td>",
                f"<td>{_esc(format_number(point.get('rpm',manifest.get('rpm'))) if _safe_number(point.get('rpm',manifest.get('rpm'))) else 'No informada')}</td>",
                f"<td>{_esc(state_label(point.get('classification') or point.get('status') or 'NOT_REPORTED'))}</td>",
                f"<td>{_esc(state_label(point.get('periodicity') or 'NOT_EVALUATED'))}</td>",
                f"<td>{_esc(point.get('cycles_completed') if point.get('cycles_completed') is not None else '—')}</td>",
                f"<td>{shown_value if isinstance(factors,list) and factors else _esc(shown_value)+' '+_esc(point.get('unit') or parameter.get('unit') or '')}</td>",
                f"<td>{_esc(source_run or 'No informado')}</td>",
                f"<td>{_esc(point.get('historical_source_project_id') or 'No informado')}</td>",
                f"<td><code>{_esc(point.get('run_directory') or 'No informada')}</code></td>",
                f"<td><code>{_esc(point.get('result_sha256') or 'No disponible')}</code></td>",
                f"<td><code>{_esc(point.get('result_artifact_sha256') or 'No disponible')}</code></td>",
                f"<td><code>{_esc(sweep_path or 'No informada')}</code></td>",
                f"<td><code>{_esc(sweep_digest or 'No disponible')}</code></td>",
                f"<td>{'Sí' if point.get('reused_verified') else 'No'}</td>",
                f"<td><code>{_esc(identity_sha)}</code></td>")) + "</tr>")
        manifest_path = Path(design_study_manifest_path) if design_study_manifest_path else None
        manifest_digest = None
        if manifest_path:
            try:
                manifest_raw=manifest_path.read_bytes()
                manifest_digest=hashlib.sha256(manifest_raw).hexdigest()
                if (json.loads(manifest_raw.decode("utf-8")) != manifest or
                        (design_study_manifest_sha256 and manifest_digest != design_study_manifest_sha256)):
                    if is_rpm_envelope:
                        raise ValueError("El manifiesto RPM cambió desde que se abrió; vuelva a cargar el estudio antes de exportar.")
                    raise ValueError("El manifiesto cambió desde que se abrió; vuelva a cargar el estudio antes de exportar.")
                if design_study_reference is not None and (
                        design_study_reference.get("manifest_sha256") != manifest_digest or
                        design_study_reference.get("study_id") != manifest.get("study_id") or
                        design_study_reference.get("source_project_id") != manifest.get("project_id")):
                    raise ValueError("El manifiesto no coincide con la referencia verificada guardada en el proyecto.")
                if is_rpm_envelope:
                    for group in manifest.get("groups",[]):
                        sweep_path=group.get("sweep_manifest")
                        sweep_digest=group.get("sweep_manifest_sha256")
                        if group.get("status")=="COMPLETE" and (not sweep_path or not sweep_digest):
                            raise ValueError("Un diseño RPM terminado carece de ruta/hash de manifiesto de barrido.")
                        if sweep_path and sweep_digest:
                            sweep_raw=Path(sweep_path).read_bytes()
                            actual=__import__("hashlib").sha256(sweep_raw).hexdigest()
                            if actual!=sweep_digest:
                                raise ValueError("Cambió el hash del manifiesto de barrido; vuelva a cargar el estudio antes de exportar.")
            except OSError as exc:
                if is_rpm_envelope:raise ValueError(f"No se pudo verificar el manifiesto RPM: {exc}") from exc
        elif is_rpm_envelope:
            raise ValueError("El informe de envolvente RPM necesita la ruta del manifiesto de origen.")
        manifest_origin = (f"<p>Manifiesto: <code>{_esc(manifest_path)}</code> · SHA-256 actual: "
                           f"<code>{_esc(manifest_digest or 'No disponible')}</code></p>" if manifest_path else
                           "<p>Manifiesto adjuntado como objeto por la interfaz; ruta original no informada.</p>")
        study_raw = html.escape(json.dumps(manifest, ensure_ascii=False, allow_nan=False,
                                           sort_keys=True, indent=2), quote=False)
        envelope_summary=""
        if is_rpm_envelope:
            values=manifest.get("values",[]);rpms=manifest.get("rpms",[])
            envelope_summary=("<h3>Envolvente geometría × RPM · observaciones exactas</h3>"
                f"<p>Método <code>RPM_ENVELOPE_V1</code> · diseños guardados: {_esc(len(values))} · "
                f"RPM exactas: {_esc(', '.join(format_number(value) for value in rpms))} · "
                f"puntos guardados: {_esc(len(manifest.get('points',[])))}. "
                "Cada fila es una observación del manifiesto. No se interpolan puntos ni se calculan resúmenes de rendimiento desde el manifiesto; las métricas sólo aparecen en resultados importados individualmente y periódicos. "
                f"Validación científica: <strong>{_esc(state_label(manifest.get('scientific_validation','NOT_CLAIMED')))}</strong>.</p>")
        factorial_html=""
        if manifest.get("design_method")=="FACTORIAL_2X2_V1":
            if (not isinstance(factorial_effects,dict) or
                    factorial_effects.get("schema")!="DINO_PARAMETRIC_FACTORIAL_EFFECTS_V1" or
                    factorial_effects.get("study_id")!=manifest.get("study_id")):
                factorial_effects={"status":"UNAVAILABLE","reason":"No se proporcionó un contraste con fuentes verificadas.","metrics":[]}
            effect_rows=[]
            for metric in factorial_effects.get("metrics",[]):
                for effect in metric.get("effects",[]):
                    value=effect.get("value")
                    shown=(f"{format_number(value,signed=True)} {_esc(effect.get('unit') or metric.get('unit') or '')}"
                        if _safe_number(value) else "—")
                    effect_rows.append("<tr>"+"".join((f"<td>{_esc(metric.get('label'))}</td>",
                        f"<td>{_esc(effect.get('term'))}</td>",f"<td>{shown}</td>",
                        f"<td>{_esc(metric.get('reason') or factorial_effects.get('reason') or 'Descriptivo · no validado')}</td>",
                        f"<td><code>{_esc(effect.get('formula'))}</code></td>"))+"</tr>")
            if not effect_rows:
                effect_rows.append(f"<tr><td colspan=\"5\">{_esc(factorial_effects.get('reason') or 'Contrastes no disponibles.')}</td></tr>")
            factor_names=" × ".join(str(axis.get("label") or axis.get("id")) for axis in manifest.get("parameter",{}).get("axes",[]))
            effect_state=("Descriptivos disponibles · no validados" if factorial_effects.get("status")=="AVAILABLE"
                else "No disponibles")
            factorial_html=("<h3>Contrastes factoriales 2×2 · descriptivos</h3>"
                f"<p>Diseño { _esc(factor_names or 'dos factores') }. Los efectos principales usan la media de cada nivel frente al otro; "
                "la interacción es la diferencia de diferencias indicada en la fórmula. Sólo se calculan con cuatro artifacts verificados, "
                "condiciones compatibles, métricas definidas y periodicidad PERIOD_1. No implican causalidad ni validación predictiva. "
                f"Estado: <strong>{_esc(effect_state)}</strong> · "
                f"{_esc(factorial_effects.get('reason') or '')}</p>"
                "<table><thead><tr><th>Métrica</th><th>Contraste</th><th>Valor</th><th>Estado</th><th>Definición exacta</th></tr></thead>"
                f"<tbody>{''.join(effect_rows)}</tbody></table>")
        response_plot_html = _study_response_plot_html(
            manifest, points, manifest_bound=bool(manifest_path and manifest_digest))
        study_html = ("<h2>Estudio paramétrico asociado</h2>"
            f"<p>Estudio <code>{_esc(manifest.get('study_id'))}</code>; parámetro "
            f"<strong>{_esc(parameter.get('label') or parameter.get('id') or 'No informado')}</strong>; "
            f"estado {_esc(state_label(manifest.get('status')))}. Los puntos conservan su clasificación de ejecución; "
            "la finalización del estudio no implica periodicidad ni validación científica.</p>"
            f"{manifest_origin}{envelope_summary}{factorial_html}{response_plot_html}<table><thead><tr><th>Punto</th><th>Estado de ejecución</th>"
            "<th>RPM</th><th>Clasificación</th><th>Periodicidad</th><th>Ciclos</th><th>Valor(es)</th>"
            f"<th>Run de origen</th><th>Proyecto de origen</th><th>Ruta de resultado</th>"
            f"<th>Resultado SHA-256</th><th>Artefacto SHA-256</th><th>Manifiesto sweep</th>"
            f"<th>Manifiesto sweep SHA-256</th><th>Reuso verificado</th>"
            f"<th>Identidad de motor SHA-256</th></tr></thead><tbody>{''.join(study_rows)}</tbody></table>"
            f"<details><summary>Manifiesto paramétrico original adjunto (JSON)</summary><pre>{study_raw}</pre></details>")
    source_sha = dataset.get("source_sha256")
    source_hash_html = f"<p>Hash de origen registrado: <code>{_esc(source_sha)}</code></p>" if source_sha else ""

    body_rows = []
    identity_rows = []
    for row in sorted(rows, key=lambda item: (str(item.get("variant_id")),
                                               float(item.get("rpm") or 0), str(item.get("run_id") or ""))):
        metric_cells = []
        for _, metric, unit in METRICS:
            value = _metric_value(row, metric)
            metric_cells.append(f"<td>{_esc(format_number(value) if value is not None else state_label(row.get(metric+'_status') or 'UNDEFINED'))}{(' ' + unit) if value is not None else ''}</td>")
        periodicity = row.get("periodicity") or row.get("classification")
        transient = row.get("transient_estimates")
        transient_note = " · estimación transitoria disponible" if isinstance(transient, dict) and transient else ""
        body_rows.append("<tr>" + "".join([
            f"<td>{_esc(row.get('variant_id'))}</td>",
            f"<td>{_esc(format_number(row.get('rpm')))} RPM</td>",
            f"<td>{_esc(state_label(row.get('classification')))}</td>",
            f"<td>{_esc(state_label(periodicity))}{transient_note}</td>",
            f"<td>{_esc(state_label(row.get('audit_status') or 'NOT_REPORTED'))}</td>",
            f"<td>{_esc(row.get('cycles_completed') if row.get('cycles_completed') is not None else '—')}</td>",
            *metric_cells,
        ]) + "</tr>")
        identity_rows.append("<tr>" + "".join(f"<td>{_esc(row.get(key))}</td>" for key in (
            "variant_id", "rpm", "run_id", "point_id", "artifact_directory",
            "result_sha256", "primary_sha256", "point_configuration_sha256",
        )) + "</tr>")

    comparisons = []
    for left_index, left_name in enumerate(variants):
        for right_name in variants[left_index + 1:]:
            left_rows = {row.get("rpm"): row for row in rows if str(row.get("variant_id")) == left_name}
            right_rows = {row.get("rpm"): row for row in rows if str(row.get("variant_id")) == right_name}
            for rpm in sorted(left_rows.keys() & right_rows.keys(), key=float):
                left, right = left_rows[rpm], right_rows[rpm]
                for label, metric, unit in METRICS:
                    if _reportable(left, metric) and _reportable(right, metric):
                        delta = _metric_value(right, metric) - _metric_value(left, metric)
                        comparisons.append(f"<tr><td>{_esc(left_name)} → {_esc(right_name)}</td>"
                            f"<td>{_esc(format_number(rpm))} RPM</td><td>{_esc(label)}</td>"
                            f"<td>{_esc(format_number(delta, signed=True))} {unit}</td>"
                            f"<td>{_esc(_condition_status(left, right))}</td></tr>")
    comparison_html = "".join(comparisons) or '<tr><td colspan="5">No hay pares A/B con RPM exacta común y métricas definidas en puntos periódicos observados.</td></tr>'
    chart_html = "".join(_chart_svg(rows, variants, label, metric, unit)
                         for label, metric, unit in METRICS[:2])
    exact_records = json.dumps(rows, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2)
    raw_record_html = html.escape(exact_records, quote=False)
    active_project = f"<p>Proyecto abierto al exportar: <code>{_esc(active_project_id)}</code>. " \
                     "Este contexto no reasigna la procedencia de las corridas.</p>" if active_project_id else ""
    provenance = dataset.get("provenance", "No informada")
    schema = dataset.get("schema", "No informado")
    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Informe técnico Dino 2T</title><style>
body{{font:15px/1.5 "Segoe UI",Arial,sans-serif;color:#202b36;max-width:1180px;margin:24px auto;padding:0 20px}}
h1,h2,h3{{color:#173d57}}.boundary{{border-left:5px solid #c18420;background:#fff6df;padding:12px 16px}}
table{{border-collapse:collapse;width:100%;margin:14px 0 24px;font-size:13px}}th,td{{border:1px solid #ccd5dc;padding:7px;text-align:left;vertical-align:top}}
th{{background:#edf2f6}}code,pre{{font-family:Consolas,monospace}}pre{{overflow:auto;background:#f3f5f7;padding:12px;white-space:pre-wrap;word-break:break-word}}
svg{{width:100%;height:auto;border:1px solid #d4dbe1}}svg text{{font:12px Arial;fill:#273746}}.note,.muted{{color:#536273;font-size:13px}}.legend span{{margin-right:12px}}.legend i{{font-style:normal;font-size:18px}}.empty{{padding:24px;background:#f3f5f7}}
@media print{{body{{max-width:none;margin:0}}details{{break-before:page}}}}
</style></head><body>
<h1>Informe técnico de resultados · Dino 2T</h1>
<div class="boundary"><strong>Límite de evidencia.</strong> {_esc(origin)} Validación experimental: <strong>{_esc(state_label(validation))}</strong>. La observación de periodicidad no valida predicción física. Los marcadores de desempeño incluyen sólo filas PERIOD_1/PERIOD_2 con métrica definida; los transitorios permanecen identificados y fuera de esos gráficos.</div>
<p>Generado UTC: {_esc(generated_at)} · Formato de datos: <code>{_esc(schema)}</code> · Procedencia declarada: {_esc(provenance)}</p>
{active_project}{source_hash_html}<h2>Origen y reproducibilidad</h2><table><thead><tr><th>Archivo fuente</th><th>SHA-256 actual</th></tr></thead><tbody>{''.join(source_rows)}</tbody></table>
<p>Las filas completas seleccionadas se incluyen al final sin redondear. Las tablas y gráficos de este informe son una vista legible de esos datos; no recalculan el solver.</p>
{study_html}
<h2>Resultados por variante y RPM</h2><table><thead><tr><th>Variante</th><th>Condición</th><th>Estado</th><th>Periodicidad</th><th>Auditoría</th><th>Ciclos</th><th>Potencia</th><th>Torque</th><th>BMEP</th></tr></thead><tbody>{''.join(body_rows)}</tbody></table>
<h2>Identidad y procedencia por punto</h2><table><thead><tr><th>Variante</th><th>RPM</th><th>Run ID</th><th>Point ID</th><th>Carpeta de artifacts</th><th>Resultado SHA-256</th><th>Primario SHA-256</th><th>Configuración SHA-256</th></tr></thead><tbody>{''.join(identity_rows)}</tbody></table>
<h2>Comparación entre variantes</h2><p class="muted">Sólo RPM exactas comunes. Δ = segunda variante menos primera; es un contraste descriptivo, no una atribución causal. No se interpolan puntos. Las diferencias y ausencias en los campos de operación se indican por fila. Se incluyen métricas definidas únicamente en resultados periódicos observados.</p>
<table><thead><tr><th>Par</th><th>RPM</th><th>Métrica</th><th>Δ descriptivo</th><th>Consistencia de condiciones informadas</th></tr></thead><tbody>{comparison_html}</tbody></table>
<h2>Visualización de puntos periódicos observados</h2>{chart_html}
<details><summary>Registros originales exactos seleccionados (JSON)</summary><pre>{raw_record_html}</pre></details>
<footer class="muted">Dino 2T Desktop · documento local autosuficiente · no implica validación experimental ni recomendación comercial.</footer>
</body></html>'''


def write_technical_report(path, dataset: dict, **kwargs) -> Path:
    path = Path(path)
    document = render_technical_report(dataset, **kwargs)
    path.write_text(document, encoding="utf-8")
    return path


def render_four_stroke_report(project_id: str, records: list[dict]) -> str:
    """Render native DINO4T_API_V1 records without mapping them onto 2T fields."""
    rows=[]
    for item in records:
        summary=item["summary"];ref=item["reference"];final=summary.get("final_cycle") or {}
        periodicity=summary.get("periodicity",{}).get("status","NOT_REPORTED")
        state=("Periódico · simulación no validada" if periodicity=="PERIODIC_CONVERGED"
               else "No periódico · no usar como curva definitiva")
        run_status={"completed":"Ejecución terminada","incomplete":"Ejecución incompleta","failed_numerical":"Fallo numérico"}.get(summary.get("status"),"Estado no informado")
        claims=summary.get("claims",{})
        calibration={"NOT_PERFORMED":"No realizado"}.get(claims.get("calibration"),claims.get("calibration"))
        experimental={"NOT_PERFORMED":"No realizado"}.get(claims.get("experimental_validation"),claims.get("experimental_validation"))
        predictive={"NOT_CLAIMED":"No declarado"}.get(claims.get("predictive_capability"),claims.get("predictive_capability"))
        evidence={"L1_ENGINEERING_RUN":"Corrida de ingeniería L1"}.get(summary.get("evidence_level"),summary.get("evidence_level"))
        values=(ref.get("run_id"),summary.get("operating_point",{}).get("rpm"),run_status,state,
            final.get("brake_power_kW"),final.get("brake_torque_Nm"),final.get("bmep_bar"),evidence,
            calibration,experimental,predictive,summary.get("config_sha256"),ref.get("result_sha256"),
            summary.get("code_commit"),summary.get("code_dirty"))
        rows.append("<tr>"+"".join(f"<td>{html.escape(str(value if value is not None else 'No disponible'))}</td>" for value in values)+"</tr>")
    headings=("Run ID","RPM","Ejecución","Periodicidad","Potencia freno (kW)","Torque freno (N·m)","BMEP (bar)",
        "Evidencia","Calibración","Validación experimental","Predictividad","Config SHA-256","Resultado SHA-256","Commit","Árbol sucio")
    return ("<!doctype html><html lang='es'><meta charset='utf-8'><title>Informe Dino 4T</title><h1>Dino Desktop · motor 4T</h1>"
        f"<p>Proyecto: {html.escape(str(project_id))}</p><p>Resultados nativos DINO4T_API_V1. Periodicidad describe estabilidad numérica y no valida un motor real. "
        "Calibración y validación experimental no se infieren.</p><table border='1' cellspacing='0' cellpadding='5'><thead><tr>"
        +"".join(f"<th>{html.escape(title)}</th>" for title in headings)+"</tr></thead><tbody>"+"".join(rows)+"</tbody></table></html>")


def _cross_study_point_state_markup(point: dict) -> str:
    """Render stored execution and scientific state fields without conflating them."""
    return "<br>".join((
        f"<strong>Ejecución:</strong> {_esc(state_label(point.get('status') or 'NOT_REPORTED'))}",
        f"<strong>Clasificación:</strong> {_esc(state_label(point.get('classification') or 'NOT_REPORTED'))}",
        f"<strong>Periodicidad:</strong> {_esc(state_label(point.get('periodicity') or 'NOT_EVALUATED'))}",
    ))


def render_study_comparison_report(comparison: dict) -> str:
    """Render a hash-bound comparison of verified saved-study observations."""
    if (not isinstance(comparison,dict) or
            comparison.get("schema")!="DINO_PARAMETRIC_CROSS_STUDY_COMPARISON_V1" or
            not isinstance(comparison.get("studies"),list) or len(comparison["studies"])<2):
        raise ValueError("La comparación de estudios no tiene un esquema verificable.")
    studies=[]
    point_rows=[]
    for study in comparison["studies"]:
        if study.get("baseline_engine_identity_sha256")!=comparison.get("baseline_engine_identity_sha256"):
            raise ValueError("La comparación contiene baselines incompatibles.")
        manifest_path=str(study.get("manifest_path") or "No informada")
        manifest_name=Path(manifest_path.replace("\\","/")).name or manifest_path
        manifest_digest=str(study.get("manifest_sha256") or "No disponible")
        manifest_digest_summary=(f"SHA-256 · {manifest_digest[:12]}…" if len(manifest_digest)==64
            else f"SHA-256 · {manifest_digest}")
        manifest_provenance=(
            '<details class="manifest-provenance"><summary>Ruta y hash completos</summary>'
            '<dl class="manifest-detail">'
            f'<dt>Ruta del manifiesto</dt><dd><code>{_esc(manifest_path)}</code></dd>'
            f'<dt>SHA-256 del manifiesto</dt><dd><code>{_esc(manifest_digest)}</code></dd>'
            '</dl></details>')
        studies.append("<tr>"+"".join((f"<td>{_esc(study.get('study_id'))}</td>",
            f"<td>{_esc(study.get('source_project_id'))}</td>",
            f'<td class="manifest-summary"><strong>{_esc(manifest_name)}</strong>'
            f'<span class="manifest-digest-summary">{_esc(manifest_digest_summary)}</span>'
            f'{manifest_provenance}</td>'))+"</tr>")
        for point in study.get("points",[]):
            metrics=point.get("metrics",{})
            classification=point.get("classification") or "NOT_REPORTED"
            periodicity=point.get("periodicity") or "NOT_EVALUATED"
            classification_label=_esc(state_label(classification))
            periodicity_label=_esc(state_label(periodicity))
            state_summary=(classification_label if classification==periodicity else
                f"{classification_label}<br>{periodicity_label}")
            factor=point.get("factor_values") or []
            design=(" · ".join(f"{_esc(row.get('label') or row.get('parameter_id'))}="
                f"{_esc(format_number(row.get('value')) if _safe_number(row.get('value')) else 'No informado')} "
                f"{_esc(row.get('unit') or '')}" for row in factor if isinstance(row,dict))
                if factor else f"{_esc((study.get('parameter') or {}).get('label') or 'Diseño')}="
                f"{_esc(format_number(point.get('value')) if _safe_number(point.get('value')) else 'No informado')} "
                f"{_esc(point.get('unit') or (study.get('parameter') or {}).get('unit') or '')}")
            metrics_summary=[]
            for metric,(label,unit) in _STUDY_REPORT_METRICS.items():
                value=metrics.get(metric)
                shown=(f"{_esc(format_number(value))} {_esc(unit)}" if _safe_number(value) else "—")
                metrics_summary.append(f"<span><strong>{_esc(label)}:</strong> {shown}</span>")
            provenance_fields=(
                ("Run fuente",point.get("source_run_id")),
                ("Motor SHA-256",point.get("engine_identity_sha256")),
                ("Corrida SHA-256",point.get("identity_sha256")),
                ("Resultado SHA-256",point.get("result_sha256")),
                ("Artifact SHA-256",point.get("result_artifact_sha256")),
                ("Ruta de artifact",point.get("run_directory")),
                ("Fuente verificada al cargar","Sí" if point.get("source_verified") else "No"),
            )
            provenance_html="".join(f"<div><dt>{_esc(label)}</dt><dd><code>{_esc(value if value is not None else 'No informado')}</code></dd></div>"
                for label,value in provenance_fields)
            point_rows.append("<tr>"+"".join((
                f"<td>{_esc(study.get('study_id'))}</td>",f"<td>{design}</td>",
                f"<td>{_esc(format_number(point.get('rpm')) if _safe_number(point.get('rpm')) else 'No informada')}</td>",
                f"<td>{_esc(state_label(point.get('status') or 'NOT_REPORTED'))}</td>",
                f"<td>{state_summary}</td>",
                f"<td>{_esc(point.get('cycles_completed') if point.get('cycles_completed') is not None else 'No informado')}</td>",
                f"<td class=\"run-id\">{_esc(point.get('source_run_id') or 'No informado')}</td>",
                f"<td class=\"metric-summary\">{'<br>'.join(metrics_summary)}</td>",
                f"<td><details class=\"point-provenance\"><summary>Ver fuente y hashes</summary><dl class=\"provenance-grid\">{provenance_html}</dl></details></td>"))+"</tr>")
    pair_rows=[]
    for pair in comparison.get("pairs",[]):
        for metric,(label,unit) in _STUDY_REPORT_METRICS.items():
            detail=pair.get("metrics",{}).get(metric,{})
            delta=detail.get("delta")
            pair_rows.append("<tr>"+"".join((f"<td>{_esc(pair.get('study_a'))}</td>",
                f"<td>{_esc(pair.get('point_a',{}).get('run_id'))}</td>",
                f"<td>{_esc(pair.get('study_b'))}</td>",
                f"<td>{_esc(pair.get('point_b',{}).get('run_id'))}</td>",
                f"<td>{_esc(format_number(pair.get('rpm')))} RPM</td>",f"<td>{_esc(label)}</td>",
                f"<td>{_esc(format_number(delta,signed=True) if _safe_number(delta) else '—')}{(' '+_esc(unit)) if _safe_number(delta) else ''}</td>",
                f"<td>{_esc(_pairing_label(pair.get('pairing')))}</td>"))+"</tr>")
    unpaired_rows=[]
    for item in comparison.get("unpaired",[]):
        point=item.get("point",{})
        unpaired_rows.append("<tr>"+"".join((f"<td>{_esc(item.get('study_id'))}</td>",
            f"<td>{_esc(point.get('run_id'))}</td>",f"<td>{_esc(format_number(point.get('rpm')))} RPM</td>",
            f"<td>{_esc(state_label(point.get('status') or 'NOT_REPORTED'))}</td>",
            f"<td>{_esc(state_label(point.get('classification') or 'NOT_REPORTED'))}</td>",
            f"<td>{_esc(state_label(point.get('periodicity') or 'NOT_EVALUATED'))}</td>",
            f"<td>{_esc(point.get('engine_identity_sha256'))}</td>",
            f"<td>{_esc(_pairing_reason_label(item.get('reason')))}</td>"))+"</tr>")
    payload=html.escape(json.dumps(comparison,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False),quote=False)
    baseline_digest=comparison.get("baseline_engine_identity_sha256")
    baseline_digest_text=str(baseline_digest) if baseline_digest is not None else "No disponible"
    baseline_digest_summary=(f"SHA-256 · {baseline_digest_text[:12]}…" if len(baseline_digest_text)==64
                            else f"SHA-256 · {baseline_digest_text}")
    baseline_digest_html=(f'<details class="baseline-digest"><summary>{_esc(baseline_digest_summary)}</summary>'
                          f'<code>{_esc(baseline_digest_text)}</code></details>')
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Comparación paramétrica · Dino 2T</title>
<style>body{{font:15px Segoe UI,Arial,sans-serif;color:#172536;margin:28px;max-width:1500px}}h1,h2{{color:#173852}}.notice{{padding:14px;background:#fff3dc;border-left:5px solid #cc7b18}}table{{border-collapse:collapse;width:100%;margin:12px 0 24px;font-size:12px}}th,td{{border:1px solid #becbd7;padding:6px;text-align:left;vertical-align:top;overflow-wrap:anywhere}}th{{background:#e9f0f5}}code{{font-size:11px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6f8;padding:16px}}.legend span{{margin-right:12px}}.legend i{{font-style:normal;font-size:18px}}.empty{{padding:12px;background:#f3f6f8}}.manifest-table{{table-layout:fixed}}.manifest-table th:nth-child(1){{width:22%}}.manifest-table th:nth-child(2){{width:20%}}.manifest-summary{{min-width:0}}.manifest-summary strong,.manifest-digest-summary{{display:block;overflow-wrap:anywhere}}.manifest-digest-summary{{color:#40556a;font-size:11px;margin-top:3px}}.manifest-provenance{{margin-top:5px}}.manifest-provenance summary{{cursor:pointer;color:#155b78}}.manifest-detail{{display:grid;grid-template-columns:minmax(10em,20%) minmax(0,1fr);gap:4px 10px;margin:6px 0 0;padding:8px;background:#f3f6f8;border:1px solid #becbd7}}.manifest-detail dt{{font-weight:600;color:#40556a}}.manifest-detail dd{{min-width:0;margin:0;overflow-wrap:anywhere;word-break:break-word}}.manifest-detail code{{white-space:normal;overflow-wrap:anywhere;word-break:break-word}}.run-id{{min-width:9em}}.metric-summary span{{display:inline-block;margin:0 8px 3px 0;white-space:nowrap}}.baseline-digest{{display:inline-block;position:relative;vertical-align:baseline}}.baseline-digest summary{{cursor:pointer;display:inline;color:#155b78;font-size:12px}}.baseline-digest code{{position:absolute;z-index:6;left:0;top:1.5em;white-space:nowrap;padding:10px;background:#fff;border:1px solid #91a8ba;box-shadow:0 4px 16px #17253640}}.point-provenance{{position:relative}}.point-provenance summary{{cursor:pointer;min-width:9em;color:#155b78}}.provenance-grid{{position:absolute;z-index:5;right:0;top:1.5em;display:grid;grid-template-columns:repeat(auto-fit,minmax(17em,1fr));gap:6px 14px;margin:0;padding:12px;width:min(780px,70vw);max-width:calc(100vw - 48px);background:#fff;border:1px solid #91a8ba;box-shadow:0 4px 16px #17253640}}.provenance-grid div{{min-width:0}}.provenance-grid dt{{font-weight:600;color:#40556a}}.provenance-grid dd{{margin:2px 0 0;overflow-wrap:anywhere}}@media(max-width:900px){{body{{margin:16px}}table{{font-size:11px}}.metric-summary span{{white-space:normal}}.provenance-grid{{grid-template-columns:1fr;width:min(780px,70vw)}}.manifest-detail{{grid-template-columns:1fr}}}}footer{{color:#526477}}</style></head><body>
<h1>Comparación de estudios paramétricos · Dino 2T</h1>
<p class="notice"><strong>Límite de evidencia.</strong> { _esc(comparison.get('notice')) } La validación científica no está reclamada. Las diferencias son contrastes descriptivos entre puntos observados; no se interpolan, ajustan ni agregan.</p>
<p>Baseline común: {baseline_digest_html} · generación UTC: {_esc(datetime.now(timezone.utc).isoformat(timespec='seconds'))}</p>
<h2>Manifiestos seleccionados</h2><p>La vista compacta identifica cada manifiesto por nombre y hash abreviado. Abra «Ruta y hash completos» para consultar los valores exactos; el JSON reproducible conserva el objeto íntegro.</p><table class="manifest-table"><thead><tr><th>Estudio</th><th>Proyecto fuente</th><th>Manifiesto seleccionado</th></tr></thead><tbody>{''.join(studies)}</tbody></table>
<h2>Puntos y procedencia</h2><p>Resumen por punto; abra «Ver fuente y hashes» para la procedencia completa. Los registros originales exactos permanecen disponibles en el JSON del informe.</p><table class="points-table"><thead><tr><th>Estudio</th><th>Diseño</th><th>RPM</th><th>Estado</th><th>Clasificación / periodicidad</th><th>Ciclos</th><th>Run fuente</th><th>Métricas</th><th>Fuente</th></tr></thead><tbody>{''.join(point_rows)}</tbody></table>
<h2>Respuesta observada por RPM</h2>{_cross_study_response_plots(comparison)}
<h2>Contrastes exactos</h2><p>Los pares requieren RPM y todos los campos operativos informados compatibles. Δ = estudio B menos A. Un resultado queda vacío si falta o si no es periódico y definido.</p><table><thead><tr><th>Estudio A</th><th>Run A</th><th>Estudio B</th><th>Run B</th><th>RPM</th><th>Métrica</th><th>Δ</th><th>Regla de pareo</th></tr></thead><tbody>{''.join(pair_rows) or '<tr><td colspan="8">No hay pares compatibles exactos.</td></tr>'}</tbody></table>
<h2>Puntos sin contraparte</h2><table><thead><tr><th>Estudio</th><th>Run ID</th><th>RPM</th><th>Ejecución</th><th>Clasificación</th><th>Periodicidad</th><th>Motor SHA-256</th><th>Motivo</th></tr></thead><tbody>{''.join(unpaired_rows) or '<tr><td colspan="8">Todos los puntos aparecen en al menos un pareo.</td></tr>'}</tbody></table>
<h2>Datos reproducibles</h2><details><summary>Objeto completo de comparación, puntos y source manifests</summary><pre>{payload}</pre></details>
<footer>Dino Desktop · exportación descriptiva. Los resultados transitorios no representan prestaciones periódicas; la periodicidad tampoco constituye validación experimental.</footer></body></html>'''


_STUDY_REPORT_METRICS={"brake_power":("Potencia de freno","kW"),
    "brake_torque":("Torque de freno","N·m"),"BMEP":("BMEP","kPa")}


def _cross_study_response_plots(comparison):
    """Render exact observed PERIOD_1 pairs as unconnected markers only."""
    studies=comparison.get("studies",[])
    studies_by_id={str(study.get("study_id")):study for study in studies}
    study_ids=[str(study.get("study_id")) for study in studies]
    plots=[]
    width,height=820,360
    left,top,right,bottom=82,42,24,62
    plot_width,plot_height=width-left-right,height-top-bottom
    for metric,(label,unit) in _STUDY_REPORT_METRICS.items():
        observed={study_id:{} for study_id in study_ids};excluded=[]
        for pair_index,pair in enumerate(comparison.get("pairs",[])):
            study_a,study_b=pair.get("study_a"),pair.get("study_b")
            point_a=pair.get("point_a") if isinstance(pair.get("point_a"),dict) else {}
            point_b=pair.get("point_b") if isinstance(pair.get("point_b"),dict) else {}
            def source_endpoint(study_id,candidate):
                if candidate.get("periodicity") is not None and isinstance(candidate.get("metrics"),dict):
                    return candidate
                study=studies_by_id.get(str(study_id),{})
                for source_point in study.get("points",[]):
                    if ((candidate.get("index") is not None and source_point.get("index")==candidate.get("index")) or
                            (candidate.get("run_id") and candidate.get("run_id")==source_point.get("run_id")) or
                            (candidate.get("source_run_id") and candidate.get("source_run_id")==source_point.get("source_run_id"))):
                        return source_point
                return candidate
            point_a=source_endpoint(study_a,point_a);point_b=source_endpoint(study_b,point_b)
            reason=None
            if pair.get("pairing")!="EXACT_RPM_AND_OPERATING_CONTEXT":
                reason="El pareo no conserva RPM y contexto exactos."
            elif point_a.get("periodicity")!="PERIOD_1" or point_b.get("periodicity")!="PERIOD_1":
                reason="Uno o ambos extremos no tienen periodicidad observada de orden 1."
            elif study_a not in observed or study_b not in observed:
                reason="La identidad de un estudio no pertenece a los manifiestos seleccionados."
            else:
                value_a=(point_a.get("metrics") or {}).get(metric)
                value_b=(point_b.get("metrics") or {}).get(metric)
                if not _safe_number(value_a) or not _safe_number(value_b):
                    reason="La métrica no está definida y finita en ambos resultados periódicos de orden 1."
            if reason:
                excluded.append((pair_index,pair,point_a,point_b,reason));continue
            rpm=pair.get("rpm")
            if not _safe_number(rpm) or float(rpm)<=0:
                excluded.append((pair_index,pair,point_a,point_b,"RPM no válida para representar el punto."));continue
            for study_id,point,value in ((study_a,point_a,value_a),(study_b,point_b,value_b)):
                identity=(point.get("index"),point.get("source_run_id") or point.get("run_id"),float(rpm))
                record={"rpm":float(rpm),"value":float(value),"point":point}
                previous=observed[study_id].get(identity)
                if previous is not None and previous["value"]!=record["value"]:
                    raise ValueError(f"El mismo punto de {study_id} conserva valores distintos para {label}.")
                observed[study_id][identity]=record
        eligible=[record for points in observed.values() for record in points.values()]
        parts=[f'<section class="cross-study-response"><h3>{_esc(label)} por RPM exacta</h3>',
            '<p>Se muestran pares con RPM y contexto operativos exactos, periodicidad observada de orden 1 en ambos extremos, '
            'y una métrica definida y finita. '
            'Los marcadores no se conectan, interpolan ni ajustan.</p>']
        if not eligible:
            parts.append('<p class="empty">No hay observaciones pareadas elegibles para esta métrica.</p>')
        else:
            rpms=[row["rpm"] for row in eligible];values=[row["value"] for row in eligible]
            xmin,xmax=min(rpms),max(rpms);ymin,ymax=min(values),max(values)
            if xmin==xmax:xmin-=1;xmax+=1
            if ymin==ymax:
                pad=max(abs(ymin)*.05,1.0);ymin-=pad;ymax+=pad
            else:
                pad=(ymax-ymin)*.08;ymin-=pad;ymax+=pad
            x=lambda value:left+(float(value)-xmin)/(xmax-xmin)*plot_width
            y=lambda value:top+(ymax-float(value))/(ymax-ymin)*plot_height
            parts.append(f'<svg role="img" aria-label="{_esc(label)} por RPM exacta" viewBox="0 0 {width} {height}" '
                'xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;background:#fff">')
            parts.append(f'<path d="M{left} {top}V{top+plot_height}H{left+plot_width}" fill="none" stroke="#526273"/>')
            for tick_index in range(5):
                fraction=tick_index/4
                yy=top+plot_height*fraction;value=ymax-(ymax-ymin)*fraction
                xx=left+plot_width*fraction;rpm=xmin+(xmax-xmin)*fraction
                parts.append(f'<path d="M{left} {yy:.2f}H{left+plot_width}" stroke="#e1e7ec"/>')
                parts.append(f'<text x="{left-8}" y="{yy+4:.2f}" text-anchor="end">{_esc(format_number(value))}</text>')
                parts.append(f'<path d="M{xx:.2f} {top}V{top+plot_height}" stroke="#eef1f4"/>')
                parts.append(f'<text x="{xx:.2f}" y="{top+plot_height+20}" text-anchor="middle">{_esc(format_number(rpm))}</text>')
            parts.append(f'<text x="{left+plot_width/2}" y="{height-8}" text-anchor="middle">RPM</text>')
            parts.append(f'<text transform="translate(18 {top+plot_height/2}) rotate(-90)" text-anchor="middle">{_esc(unit)}</text>')
            legend=[]
            for study_index,study_id in enumerate(study_ids):
                color=COLORS[study_index%len(COLORS)]
                records=sorted(observed[study_id].values(),key=lambda item:item["rpm"])
                legend.append(f'<span><i style="color:{color}">●</i> {_esc(study_id)} · {len(records)} punto(s)</span>')
                for item in records:
                    point=item["point"]
                    title=(f"{study_id} · {point.get('source_run_id') or point.get('run_id') or 'run no informado'} · "
                        f"{format_number(item['rpm'])} RPM · {format_number(item['value'])} {unit}")
                    parts.append(f'<circle class="observed-point" cx="{x(item["rpm"]):.2f}" cy="{y(item["value"]):.2f}" r="5" '
                        f'fill="{color}"><title>{_esc(title)}</title></circle>')
            parts.append('</svg><p class="legend">'+' · '.join(legend)+'</p>')
        if excluded:
            rows=[]
            for pair_index,pair,point_a,point_b,reason in excluded:
                rows.append('<tr>'+''.join((
                    f'<td>{pair_index+1}</td>',f'<td>{_esc(pair.get("rpm"))}</td>',
                    f'<td>{_esc(pair.get("study_a"))} · {_esc(point_a.get("source_run_id") or point_a.get("run_id"))}</td>',
                f'<td>{_cross_study_point_state_markup(point_a)}</td>',
                    f'<td>{_esc(pair.get("study_b"))} · {_esc(point_b.get("source_run_id") or point_b.get("run_id"))}</td>',
                f'<td>{_cross_study_point_state_markup(point_b)}</td>',
                    f'<td>{_esc(reason)}</td>'))+'</tr>')
            parts.append('<h4>Pares excluidos de esta gráfica · '+_esc(label)+'</h4>'
                '<table><thead><tr><th>Fila</th><th>RPM</th><th>Estudio/run A</th><th>Estado del punto A</th>'
                '<th>Estudio/run B</th><th>Estado del punto B</th><th>Motivo</th></tr></thead><tbody>'+
                ''.join(rows)+'</tbody></table>')
        plots.append(''.join(parts)+'</section>')
    return ''.join(plots)


def write_study_comparison_report(path, comparison: dict) -> Path:
    path=Path(path)
    path.write_text(render_study_comparison_report(comparison),encoding="utf-8")
    return path


def render_four_stroke_ab_report(comparison: dict) -> str:
    """Render one exact, already-validated 4T A/B comparison; performs no calculations."""
    if comparison.get("schema") not in ("DINO4T_AB_COMPARISON_V1", "DINO4T_AB_COMPARISON_V2"):
        raise ValueError("unsupported Dino 4T comparison schema")
    endpoints=comparison.get("endpoints",[])
    if len(endpoints)!=2 or [item.get("side") for item in endpoints] != ["A","B"]:
        raise ValueError("A/B report requires exactly the ordered endpoints A and B")
    esc=lambda value: html.escape(str(value),quote=True)
    rows=[]
    for row in comparison.get("metrics",[]):
        av=row.get("a");bv=row.get("b");delta=row.get("delta_b_minus_a");relative=row.get("relative_percent_to_abs_a")
        rows.append("<tr>"+"".join((
            f"<td>{esc(row.get('label'))}</td>",f"<td>{esc(format_number(av))} {esc(row.get('unit'))}</td>",
            f"<td>{esc(format_number(bv))} {esc(row.get('unit'))}</td>",
            f"<td>{esc(format_number(delta))} {esc(row.get('unit'))}</td>",
            f"<td>{esc(format_number(relative)+'%' if relative is not None else 'No definido')}</td>"))+"</tr>")
    changes=[]
    for change in comparison.get("design_changes",[]):
        changes.append("<tr>"+"".join((f"<td>{esc(change.get('path'))}</td>",
            f"<td><code>{esc(json.dumps(change.get('a'),ensure_ascii=False))}</code></td>",
            f"<td><code>{esc(json.dumps(change.get('b'),ensure_ascii=False))}</code></td>"))+"</tr>")
    endpoint_rows=[]
    for item in endpoints:
        endpoint_rows.append("<tr>"+"".join((f"<th>{esc(item['side'])}</th>",
            f"<td>{esc(item.get('variant_id') or 'Motor base')} · {esc(item.get('run_id'))}</td>",
            f"<td>{esc(item.get('run_status'))} · {esc(item.get('periodicity',{}).get('status'))}</td>",
            f"<td>{esc(item.get('cycles_run'))}</td>",f"<td><code>{esc(item.get('code_commit'))}</code></td>",
            f"<td><code>{esc(item.get('config_sha256'))}</code></td>",
            f"<td><code>{esc(item.get('result_sha256'))}</code></td>"))+"</tr>")
    payload=esc(json.dumps(comparison,ensure_ascii=False,indent=2,allow_nan=False))
    rpm=comparison.get("operating_point",{}).get("rpm")
    legacy_notice = "Registro histórico V1: vínculo original completo de artefactos no acreditado por este formato." if comparison.get("schema")=="DINO4T_AB_COMPARISON_V1" else "Integridad de artefactos V2; procedencia del código: "+str(comparison.get("qualification",{}).get("source_provenance","no declarada"))
    return f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>Comparación Dino 4T A/B</title>
<style>body{{font:15px Segoe UI,Arial,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#1c2833}}table{{border-collapse:collapse;width:100%;margin:1rem 0}}th,td{{border:1px solid #ccd4dc;padding:.55rem;text-align:left;vertical-align:top}}th{{background:#edf2f6}}code,pre{{overflow-wrap:anywhere;white-space:pre-wrap}}.notice{{border-left:5px solid #ba7730;background:#fff7e8;padding:1rem}}</style>
<h1>Comparación de diseño 4T A/B</h1><p>Clasificación: <b>{esc(comparison.get('classification'))}</b> · {esc(rpm)} RPM · comparación ID <code>{esc(comparison.get('comparison_id'))}</code></p>
<p>{esc(legacy_notice)}</p>
<p class="notice">Diferencias calculadas por el modelo Dino 4T bajo entradas y contexto compatibles. No constituyen una mejora demostrada en un motor real. Calibración: no realizada. Validación experimental: no realizada. Capacidad predictiva: no declarada. La periodicidad es una condición numérica del modelo, no validación experimental.</p>
<h2>Diseños y procedencia</h2><table><thead><tr><th>Extremo</th><th>Variante / corrida</th><th>Estado</th><th>Ciclos</th><th>Commit</th><th>Config SHA-256</th><th>Resultado SHA-256</th></tr></thead><tbody>{''.join(endpoint_rows)}</tbody></table>
<p>Modelos 4T: <code>{esc(json.dumps(comparison.get('models'),ensure_ascii=False))}</code><br>Criterios de periodicidad: <code>{esc(json.dumps(comparison.get('periodicity_tolerances'),ensure_ascii=False))}</code></p>
<h2>Cambios explícitos entre A y B</h2><table><thead><tr><th>Parámetro</th><th>A</th><th>B</th></tr></thead><tbody>{''.join(changes)}</tbody></table>
<h2>Diferencias de último ciclo periódico</h2><p>Δ = B − A. El cambio relativo usa |A| como denominador y queda indefinido si A = 0.</p><table><thead><tr><th>Métrica</th><th>A</th><th>B</th><th>Δ absoluto</th><th>Δ relativo a A</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>Registro reproducible completo</h2><details><summary>Ver configuración resuelta, criterios, hashes y resultados fuente</summary><pre>{payload}</pre></details>
<footer><p>Dino Desktop · informe descriptivo de resultados calculados; no valida experimentalmente el motor real.</p></footer></html>'''


def write_four_stroke_ab_report(path, comparison: dict) -> Path:
    path=Path(path)
    path.write_text(render_four_stroke_ab_report(comparison),encoding="utf-8")
    return path
