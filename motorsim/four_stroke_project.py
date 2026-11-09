"""Proyecto 4T 0D de referencia para Dino, independiente del proyecto 2T V3."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile

from .four_stroke import execution_errors as four_stroke_execution_errors
from .four_stroke import geometry as synthetic_geometry
from .project import (FOUR_DUCT_REFERENCE, DuctSegment, Ducts, FourStroke,
                      Project, ProjectError, VALVE_REFERENCE, Valve,
                      validate_number)
from .reference_results import FOUR_MODEL_VERSION
from .rpm_domain import validate_rpm

SCHEMA = "MOTORSIM_4T_REFERENCE_PROJECT_V1"
VERSION = 1
CLASSIFICATION = "SYNTHETIC_REFERENCE_0D"
SCIENTIFIC_STATUS = "NOT_VALIDATED"
DEFAULT_RPM = 3000

PROVENANCE_FIELDS = {"origin", "created_at", "model_version", "classification",
                     "scientific_status"}
CURVE_REFERENCE_FIELDS = {"schema", "series_path", "series_sha256", "series_id",
                          "project_sha256", "status", "model_version", "created_at", "rpms"}
CURVE_REFERENCE_SCHEMA = "MOTORSIM_4T_REFERENCE_CURVE_V1"
CURVE_REFERENCE_STATUSES = {"converged", "cancelled", "stopped"}
CURVE_ASSESSMENT_STATES = {"FRESH_COMPLETE", "FRESH_PARTIAL", "STALE_PROJECT",
                           "STALE_IN_PROGRESS", "UNAVAILABLE", "CORRUPT",
                           "UNBOUND_PROJECT"}


class FourStrokeProjectError(ValueError):
    """Proyecto 4T ilegible, incompleto para ejecutar o fuera de contrato."""


def _hex_digest(value, key: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise FourStrokeProjectError(f"Hash de referencia de curva 4T inválido: {key}.")
    return value


def _curve_path(value) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise FourStrokeProjectError("Ruta de serie 4T inválida: debe ser relativa POSIX.")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.name != "series.json":
        raise FourStrokeProjectError("Ruta de serie 4T inválida: sólo series.json relativo al proyecto.")
    return path


def validate_curve_reference(reference) -> None:
    if not isinstance(reference, dict) or set(reference) != CURVE_REFERENCE_FIELDS:
        raise FourStrokeProjectError("Referencia de curva 4T incompleta.")
    if reference["schema"] != CURVE_REFERENCE_SCHEMA:
        raise FourStrokeProjectError("Schema de referencia de curva 4T no admitido.")
    _curve_path(reference["series_path"])
    series_id = reference["series_id"]
    if (not isinstance(series_id, str) or len(series_id) != 32
            or any(c not in "0123456789abcdef" for c in series_id)):
        raise FourStrokeProjectError("Identidad de la serie 4T inválida.")
    _hex_digest(reference["series_sha256"], "series_sha256")
    _hex_digest(reference["project_sha256"], "project_sha256")
    if reference["status"] not in CURVE_REFERENCE_STATUSES:
        raise FourStrokeProjectError("Estado de referencia de curva 4T inválido.")
    if reference["model_version"] != FOUR_MODEL_VERSION:
        raise FourStrokeProjectError("Modelo de referencia de curva 4T inválido.")
    if not isinstance(reference["created_at"], str) or not reference["created_at"].strip():
        raise FourStrokeProjectError("Fecha de referencia de curva 4T inválida.")
    rpms = reference["rpms"]
    if (not isinstance(rpms, list) or not 2 <= len(rpms) <= 5
            or any(type(x) is not int for x in rpms)):
        raise FourStrokeProjectError("RPM de referencia de curva 4T inválidos.")
    step = rpms[1] - rpms[0]
    if step <= 0 or any(b - a != step for a, b in zip(rpms, rpms[1:])):
        raise FourStrokeProjectError("RPM de referencia de curva 4T no ascendentes o irregulares.")
    for rpm in rpms:
        try:
            validate_rpm(rpm, "4T")
        except ProjectError as exc:
            raise FourStrokeProjectError(str(exc)) from exc


def project_identity(project: "FourStrokeProject") -> str:
    data = project.to_dict()
    data.pop("curve_references", None)
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def with_curve_reference(project: "FourStrokeProject", reference,
                         *, max_references: int = 8) -> "FourStrokeProject":
    """Return a project with the reference linked; same series_id is replaced, not duplicated."""
    validate_curve_reference(reference)
    current = [dict(item) for item in project.curve_references
               if item.get("series_id") != reference["series_id"]]
    current.append(dict(reference))
    return replace(project, curve_references=tuple(current[-max_references:]))


def assess_curve_reference(project: "FourStrokeProject", reference, *,
                           base_dir=None) -> dict:
    """Classify a curve reference without modifying the project or the series.

    ``base_dir`` is the directory containing the saved project. A reference is
    only portable and checkable when the project has been saved next to its
    ``curves/<series_id>/series.json`` directory.
    """
    result = {"state": "CORRUPT", "issues": [], "reference": dict(reference),
              "path": None, "series": None}
    try:
        validate_curve_reference(reference)
    except FourStrokeProjectError as exc:
        result["issues"] = [str(exc)]
        return result
    if base_dir is None:
        result.update(state="UNBOUND_PROJECT",
                      issues=["El proyecto no está guardado; no se puede resolver la serie 4T."])
        return result
    try:
        identity = project_identity(project)
    except FourStrokeProjectError as exc:
        result["issues"] = [str(exc)]
        return result
    if reference["project_sha256"] != identity:
        result.update(state="STALE_PROJECT",
                      issues=["La referencia corresponde a otra configuración del proyecto."])
        return result
    try:
        base = Path(base_dir).resolve()
        target = (base / Path(reference["series_path"])).resolve()
        if not target.is_relative_to(base):
            result.update(state="CORRUPT", issues=["La referencia escapa del directorio del proyecto."])
            return result
        result["path"] = target
        if not target.is_file():
            result.update(state="UNAVAILABLE", issues=["No se encontró series.json."])
            return result
        raw = target.read_bytes()
        if hashlib.sha256(raw).hexdigest() != reference["series_sha256"]:
            result.update(state="CORRUPT", issues=["El hash de series.json no coincide."])
            return result
        from .sweep import load_sweep
        loaded = load_sweep(target)
    except FourStrokeProjectError as exc:
        result["issues"] = [str(exc)]
        return result
    except Exception as exc:  # ResultError/OSError/ValueError from strict readers
        result.update(state="CORRUPT", issues=[f"{type(exc).__name__}: {exc}"])
        return result
    index = loaded["index"]
    if (index["series_id"] != reference["series_id"]
            or index["rpms"] != reference["rpms"]):
        result.update(state="CORRUPT",
                      issues=["La serie no coincide con la identidad o los RPM registrados."])
        return result
    if index["state"] == "running":
        result.update(state="STALE_IN_PROGRESS",
                      issues=["La serie quedó en ejecución y no es un resultado terminal."])
        return result
    if index["state"] != reference["status"]:
        result.update(state="CORRUPT",
                      issues=["El estado de la serie no coincide con la referencia."])
        return result
    for point in loaded["results"]:
        if point is None:
            continue
        manifest = point.get("manifest") or {}
        if manifest.get("model_version") != FOUR_MODEL_VERSION:
            result.update(state="CORRUPT",
                          issues=["Un punto de la serie declara otro modelo 4T."])
            return result
    if index["state"] == "converged":
        state = "FRESH_COMPLETE"
    elif index["state"] in CURVE_REFERENCE_STATUSES:
        state = "FRESH_PARTIAL"
    else:
        result.update(state="STALE_IN_PROGRESS",
                      issues=["La serie quedó en ejecución y no es un resultado terminal."])
        return result
    result.update(state=state, series=loaded,
                  issues=[] if state == "FRESH_COMPLETE" else ["Serie parcial: no todos los puntos convergieron."])
    return result


def default_provenance(origin: str = "new") -> dict:
    return {
        "origin": origin,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_version": FOUR_MODEL_VERSION,
        "classification": CLASSIFICATION,
        "scientific_status": SCIENTIFIC_STATUS,
    }


@dataclass(frozen=True)
class FourStrokeProject:
    name: str = "4T 0D — EJEMPLO SINTÉTICO"
    cylinder_count: int = 1
    bore_mm: float | None = None
    stroke_mm: float | None = None
    rod_length_mm: float | None = None
    compression_ratio: float | None = None
    notes: str = ""
    intake: Valve = field(default_factory=Valve)
    exhaust: Valve = field(default_factory=Valve)
    ducts: Ducts = field(default_factory=lambda: Ducts(reference=FOUR_DUCT_REFERENCE))
    rpm: int | None = None
    provenance: dict = field(default_factory=default_provenance)
    curve_references: tuple[dict, ...] = ()

    def validate(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise FourStrokeProjectError("El nombre del proyecto 4T no puede estar vacío.")
        if type(self.cylinder_count) is not int or self.cylinder_count != 1:
            raise FourStrokeProjectError("El modelo 4T requiere exactamente un cilindro.")
        for key in ("bore_mm", "stroke_mm", "rod_length_mm", "compression_ratio"):
            try:
                validate_number(getattr(self, key), key)
            except ProjectError as exc:
                raise FourStrokeProjectError(str(exc)) from exc
        if (self.stroke_mm is not None and self.rod_length_mm is not None
                and self.rod_length_mm <= self.stroke_mm / 2):
            raise FourStrokeProjectError("Biela incompatible: debe superar media carrera.")
        if not isinstance(self.notes, str):
            raise FourStrokeProjectError("Las notas deben ser texto.")
        if not isinstance(self.intake, Valve) or not isinstance(self.exhaust, Valve):
            raise FourStrokeProjectError("Configuración de válvulas 4T inválida.")
        self.intake.validate()
        self.exhaust.validate()
        if not isinstance(self.ducts, Ducts):
            raise FourStrokeProjectError("Configuración de conductos 4T inválida.")
        self.ducts.validate()
        if self.ducts.reference != FOUR_DUCT_REFERENCE:
            raise FourStrokeProjectError("Los conductos 4T requieren su referencia independiente.")
        if self.rpm is not None:
            try:
                validate_rpm(self.rpm, "4T")
            except ProjectError as exc:
                raise FourStrokeProjectError(str(exc)) from exc
        if not isinstance(self.provenance, dict) or set(self.provenance) != PROVENANCE_FIELDS:
            raise FourStrokeProjectError("Procedencia 4T incompleta.")
        if (not isinstance(self.provenance["origin"], str) or not self.provenance["origin"].strip()
                or not isinstance(self.provenance["created_at"], str)
                or not self.provenance["created_at"].strip()
                or self.provenance["model_version"] != FOUR_MODEL_VERSION
                or self.provenance["classification"] != CLASSIFICATION
                or self.provenance["scientific_status"] != SCIENTIFIC_STATUS):
            raise FourStrokeProjectError("Procedencia 4T inválida.")
        if not isinstance(self.curve_references, tuple):
            raise FourStrokeProjectError("Referencias de curva 4T inválidas.")
        for reference in self.curve_references:
            validate_curve_reference(reference)

    def execution_errors(self) -> list[str]:
        try:
            self.validate()
        except (FourStrokeProjectError, ProjectError) as exc:
            return [str(exc)]
        messages = list(four_stroke_execution_errors(self.to_project()))
        if self.rpm is None:
            messages.append("RPM requerido para ejecutar (entero 2500–3500).")
        else:
            try:
                validate_rpm(self.rpm, "4T")
            except ProjectError as exc:
                messages.append(str(exc))
        return messages

    def validate_for_execution(self) -> None:
        messages = self.execution_errors()
        if messages:
            raise FourStrokeProjectError("\n".join(messages))

    def to_project(self) -> Project:
        self.validate()
        four = FourStroke(
            intake=self.intake,
            exhaust=self.exhaust,
            ducts=self.ducts,
            reference=VALVE_REFERENCE,
        )
        return Project(
            name=self.name,
            cycle="4T",
            cylinder_count=self.cylinder_count,
            bore_mm=self.bore_mm,
            stroke_mm=self.stroke_mm,
            rod_length_mm=self.rod_length_mm,
            compression_ratio=self.compression_ratio,
            notes=self.notes,
            four_stroke=four,
        )

    @classmethod
    def from_project(cls, project: Project) -> "FourStrokeProject":
        if not isinstance(project, Project) or project.cycle != "4T":
            raise FourStrokeProjectError("Se esperaba un Project 4T.")
        project.validate()
        return cls(
            name=project.name,
            cylinder_count=project.cylinder_count or 1,
            bore_mm=project.bore_mm,
            stroke_mm=project.stroke_mm,
            rod_length_mm=project.rod_length_mm,
            compression_ratio=project.compression_ratio,
            notes=project.notes,
            intake=project.four_stroke.intake,
            exhaust=project.four_stroke.exhaust,
            ducts=project.four_stroke.ducts,
            rpm=None,
            provenance=default_provenance("import"),
        )

    def to_dict(self) -> dict:
        self.validate()
        data = {
            "schema": SCHEMA,
            "version": VERSION,
            "name": self.name,
            "cycle": "4T",
            "geometry": {
                "cylinder_count": self.cylinder_count,
                "bore_mm": self.bore_mm,
                "stroke_mm": self.stroke_mm,
                "rod_length_mm": self.rod_length_mm,
                "compression_ratio": self.compression_ratio,
                "notes": self.notes,
            },
            "valves": {
                "intake": asdict(self.intake),
                "exhaust": asdict(self.exhaust),
            },
            "ducts": self.ducts.to_dict(),
            "operating_point": {"rpm": self.rpm},
            "classification": CLASSIFICATION,
            "scientific_status": SCIENTIFIC_STATUS,
            "provenance": dict(self.provenance),
        }
        if self.curve_references:
            data["curve_references"] = [dict(item) for item in self.curve_references]
        return data

    @classmethod
    def from_dict(cls, data: object) -> "FourStrokeProject":
        if not isinstance(data, dict):
            raise FourStrokeProjectError("El archivo 4T debe contener un objeto JSON.")
        required = {"schema", "version", "name", "cycle", "geometry", "valves", "ducts",
                    "operating_point", "classification", "scientific_status", "provenance"}
        if set(data) not in (required, required | {"curve_references"}):
            raise FourStrokeProjectError("Campos del proyecto 4T inválidos.")
        if data["schema"] != SCHEMA or data["version"] != VERSION:
            raise FourStrokeProjectError("Schema o versión del proyecto 4T no admitidos.")
        if data["cycle"] != "4T":
            raise FourStrokeProjectError("El proyecto debe declarar ciclo 4T.")
        if data["classification"] != CLASSIFICATION or data["scientific_status"] != SCIENTIFIC_STATUS:
            raise FourStrokeProjectError("Clasificación o estado científico 4T inválido.")
        geometry = data["geometry"]
        if not isinstance(geometry, dict) or set(geometry) != {
                "cylinder_count", "bore_mm", "stroke_mm", "rod_length_mm",
                "compression_ratio", "notes"}:
            raise FourStrokeProjectError("Geometría 4T inválida.")
        valves = data["valves"]
        if not isinstance(valves, dict) or set(valves) != {"intake", "exhaust"}:
            raise FourStrokeProjectError("Válvulas 4T inválidas.")
        operating = data["operating_point"]
        if not isinstance(operating, dict) or set(operating) != {"rpm"}:
            raise FourStrokeProjectError("Punto operativo 4T inválido.")
        provenance = data["provenance"]
        if not isinstance(provenance, dict) or set(provenance) != PROVENANCE_FIELDS:
            raise FourStrokeProjectError("Procedencia 4T inválida.")
        references = data.get("curve_references", [])
        if not isinstance(references, list):
            raise FourStrokeProjectError("Referencias de curva 4T inválidas.")
        try:
            project = cls(
                name=data["name"],
                cylinder_count=geometry["cylinder_count"],
                bore_mm=geometry["bore_mm"],
                stroke_mm=geometry["stroke_mm"],
                rod_length_mm=geometry["rod_length_mm"],
                compression_ratio=geometry["compression_ratio"],
                notes=geometry["notes"],
                intake=Valve.from_dict(valves["intake"]),
                exhaust=Valve.from_dict(valves["exhaust"]),
                ducts=Ducts.from_dict(data["ducts"]),
                rpm=operating["rpm"],
                provenance=dict(provenance),
                curve_references=tuple(references),
            )
        except ProjectError as exc:
            raise FourStrokeProjectError(str(exc)) from exc
        project.validate()
        return project


def starter_project(name: str | None = None, *, rpm: int | None = DEFAULT_RPM,
                    origin: str = "template") -> FourStrokeProject:
    """Caso sintético documentado; no es una medición ni una aceptación."""
    source = synthetic_geometry()
    project = FourStrokeProject.from_project(source)
    return replace(
        project,
        name=name or "4T 0D — EJEMPLO SINTÉTICO",
        rpm=rpm,
        provenance=default_provenance(origin),
    )


def save_project(path: str | Path, project: FourStrokeProject) -> str:
    project.validate()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(project.to_dict(), sort_keys=True, indent=2,
                          ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_name, target)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
    return hashlib.sha256(payload).hexdigest()


def load_project(path: str | Path) -> FourStrokeProject:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return FourStrokeProject.from_dict(data)
