"""Proyecto 4T 0D de referencia para Dino, independiente del proyecto 2T V3."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
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


class FourStrokeProjectError(ValueError):
    """Proyecto 4T ilegible, incompleto para ejecutar o fuera de contrato."""


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
        return {
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

    @classmethod
    def from_dict(cls, data: object) -> "FourStrokeProject":
        if not isinstance(data, dict):
            raise FourStrokeProjectError("El archivo 4T debe contener un objeto JSON.")
        required = {"schema", "version", "name", "cycle", "geometry", "valves", "ducts",
                    "operating_point", "classification", "scientific_status", "provenance"}
        if set(data) != required:
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
