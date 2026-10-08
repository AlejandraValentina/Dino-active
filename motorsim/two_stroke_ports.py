"""Versioned, reusable 2T port geometry and bound effective-area profiles.

This module is intentionally separate from Project v6 and from the historical
P5/P6/P7 campaign contracts. Its profiles are geometric/configuration outputs;
they are not flow, scavenging, or performance predictions.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any

from .intake import intake_results
from .kinematics import piston_position
from .ports import crossing_angle, uncovered_area
from .project import Intake, ProjectError

SCHEMA = "GENERIC_2T_PORTS_V1"
SCHEMA_ONE_TRANSFER = "GENERIC_2T_PORTS_V2"
PROVENANCE = {"DOCUMENTED", "DERIVED_FROM_DOCUMENTED",
              "SYNTHETIC_ASSUMPTION", "UNKNOWN"}
DUCT_ROLES = {"intake", "transfer", "exhaust"}
PORT_ROLES = {"intake", "transfer", "exhaust"}
FEATURES = {
    "intake": {"piston_port"},
    "transfer": {"primary", "secondary", "boost"},
    "exhaust": {"main", "auxiliary", "bridged_segment"},
}


def _finite(value: Any, label: str) -> float:
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ProjectError(f"{label}: se requiere un número finito.")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ProjectError(f"{label}: fuera de rango numérico.") from exc
    if not math.isfinite(result):
        raise ProjectError(f"{label}: fuera de rango numérico.")
    return result


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class DuctBinding:
    id: str
    role: str

    def validate(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ProjectError("Cada conducto requiere un id de texto no vacío.")
        if not isinstance(self.role, str) or self.role not in DUCT_ROLES:
            raise ProjectError(f"Rol de conducto inválido: {self.role!r}.")

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "role": self.role}

    @classmethod
    def from_dict(cls, value: Any) -> "DuctBinding":
        if not isinstance(value, dict) or set(value) != {"id", "role"}:
            raise ProjectError("Objeto de asociación de conducto inválido.")
        result = cls(value["id"], value["role"])
        result.validate()
        return result


@dataclass(frozen=True)
class AreaKnot:
    angle_deg: float
    area_mm2: float

    def to_dict(self) -> dict[str, float]:
        return {"angle_deg": self.angle_deg, "area_mm2": self.area_mm2}

    @classmethod
    def from_dict(cls, value: Any) -> "AreaKnot":
        if not isinstance(value, dict) or set(value) != {"angle_deg", "area_mm2"}:
            raise ProjectError("Punto de perfil de área inválido.")
        return cls(value["angle_deg"], value["area_mm2"])


@dataclass(frozen=True)
class PortDefinition:
    id: str
    name: str
    role: str
    feature: str
    duct_id: str
    family: str
    discharge_coefficient: float
    provenance: str
    top_mm: float | None = None
    height_mm: float | None = None
    width_mm: float | None = None
    skirt_mm: float | None = None
    roof_travel_mm: float = 0.0
    roof_position: float = 0.0
    group_id: str | None = None
    area_profile: tuple[AreaKnot, ...] = ()

    def validate(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ProjectError("Cada lumbrera requiere un id no vacío.")
        if not isinstance(self.name, str):
            raise ProjectError(f"{self.id}: name debe ser texto.")
        if (not isinstance(self.role, str) or not isinstance(self.feature, str) or
                self.role not in PORT_ROLES or
                self.feature not in FEATURES.get(self.role, set())):
            raise ProjectError(f"{self.id}: combinación de rol/función inválida.")
        if not isinstance(self.duct_id, str) or not self.duct_id.strip():
            raise ProjectError(f"{self.id}: falta la asociación de conducto.")
        if not isinstance(self.family, str) or self.family not in {
                "rectangular_window", "piston_port", "effective_profile"}:
            raise ProjectError(f"{self.id}: familia geométrica inválida.")
        cd = _finite(self.discharge_coefficient, f"{self.id}.discharge_coefficient")
        if cd <= 0.0:
            raise ProjectError(f"{self.id}: el coeficiente de descarga debe ser positivo.")
        if not isinstance(self.provenance, str) or self.provenance not in PROVENANCE:
            raise ProjectError(f"{self.id}: provenance inválida.")

        travel = _finite(self.roof_travel_mm, f"{self.id}.roof_travel_mm")
        position = _finite(self.roof_position, f"{self.id}.roof_position")
        if travel < 0.0 or not 0.0 <= position <= 1.0:
            raise ProjectError(f"{self.id}: roof travel/position fuera de dominio.")
        if self.role != "exhaust" and (travel != 0.0 or position != 0.0):
            raise ProjectError("El desplazamiento de techo powervalve solo aplica a escape.")
        if self.feature == "bridged_segment":
            if not isinstance(self.group_id, str) or not self.group_id.strip():
                raise ProjectError(f"{self.id}: un segmento bridged requiere group_id.")
        elif self.group_id is not None:
            raise ProjectError(f"{self.id}: group_id solo aplica a bridged_segment.")

        geometry_fields = (self.top_mm, self.height_mm, self.width_mm)
        if self.family == "effective_profile":
            if travel != 0.0 or position != 0.0:
                raise ProjectError(f"{self.id}: perfiles explícitos no admiten roof_travel.")
            if self.role != "exhaust":
                raise ProjectError(f"{self.id}: perfiles explícitos se reservan a aperturas de escape.")
            if any(value is not None for value in (*geometry_fields, self.skirt_mm)):
                raise ProjectError(f"{self.id}: perfil explícito no admite dimensiones de ventana.")
            if len(self.area_profile) < 2:
                raise ProjectError(f"{self.id}: el perfil requiere knots en 0° y 360°.")
            previous = -math.inf
            for knot in self.area_profile:
                angle = _finite(knot.angle_deg, f"{self.id}.angle_deg")
                area = _finite(knot.area_mm2, f"{self.id}.area_mm2")
                if not 0.0 <= angle <= 360.0 or angle <= previous or area < 0.0:
                    raise ProjectError(f"{self.id}: knots deben crecer en 0–360° y tener área >= 0.")
                previous = angle
            if (self.area_profile[0].angle_deg != 0.0 or
                    self.area_profile[-1].angle_deg != 360.0 or
                    self.area_profile[0].area_mm2 != self.area_profile[-1].area_mm2):
                raise ProjectError(f"{self.id}: el perfil debe ser periódico entre 0° y 360°.")
            return

        if self.area_profile:
            raise ProjectError(f"{self.id}: ventana geométrica no admite area_profile explícito.")
        top, height, width = geometry_fields
        for key, value in (("top_mm", top), ("height_mm", height), ("width_mm", width)):
            number = _finite(value, f"{self.id}.{key}")
            if number <= 0.0:
                raise ProjectError(f"{self.id}.{key}: debe ser positivo.")
        if self.family == "piston_port":
            if self.role != "intake" or self.skirt_mm is None:
                raise ProjectError("piston_port requiere rol intake y skirt_mm.")
            if _finite(self.skirt_mm, f"{self.id}.skirt_mm") <= 0.0:
                raise ProjectError(f"{self.id}.skirt_mm: debe ser positivo.")
        elif self.skirt_mm is not None:
            raise ProjectError(f"{self.id}: skirt_mm solo aplica a piston_port.")
        if self.role == "intake" and self.family != "piston_port":
            raise ProjectError("La admisión de esta versión requiere geometría piston_port.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "role": self.role,
            "feature": self.feature, "duct_id": self.duct_id,
            "family": self.family,
            "discharge_coefficient": self.discharge_coefficient,
            "provenance": self.provenance, "top_mm": self.top_mm,
            "height_mm": self.height_mm, "width_mm": self.width_mm,
            "skirt_mm": self.skirt_mm, "roof_travel_mm": self.roof_travel_mm,
            "roof_position": self.roof_position, "group_id": self.group_id,
            "area_profile": [point.to_dict() for point in self.area_profile],
        }

    @classmethod
    def from_dict(cls, value: Any) -> "PortDefinition":
        fields = {"id", "name", "role", "feature", "duct_id", "family",
                  "discharge_coefficient", "provenance", "top_mm", "height_mm",
                  "width_mm", "skirt_mm", "roof_travel_mm", "roof_position",
                  "group_id", "area_profile"}
        if not isinstance(value, dict) or set(value) != fields:
            raise ProjectError("Campos de definición de lumbrera faltantes o inesperados.")
        if not isinstance(value["area_profile"], list):
            raise ProjectError("area_profile debe ser una lista.")
        result = cls(**{**value, "area_profile": tuple(
            AreaKnot.from_dict(point) for point in value["area_profile"])})
        result.validate()
        return result


def _base_dict(stroke_mm: float, rod_length_mm: float,
               ducts: tuple[DuctBinding, ...], ports: tuple[PortDefinition, ...],
               schema: str = SCHEMA) -> dict:
    return {"schema": schema, "stroke_mm": stroke_mm,
            "rod_length_mm": rod_length_mm,
            "ducts": [duct.to_dict() for duct in ducts],
            "ports": [port.to_dict() for port in ports]}


@dataclass(frozen=True)
class CompiledPortProfile:
    port_id: str
    duct_id: str
    role: str
    angles_deg: tuple[float, ...]
    effective_area_mm2: tuple[float, ...]
    event_angles_deg: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"port_id": self.port_id, "duct_id": self.duct_id,
                "role": self.role, "angles_deg": list(self.angles_deg),
                "effective_area_mm2": list(self.effective_area_mm2),
                "event_angles_deg": list(self.event_angles_deg)}


@dataclass(frozen=True)
class CompiledDuctProfile:
    duct_id: str
    role: str
    angles_deg: tuple[float, ...]
    effective_area_mm2: tuple[float, ...]
    event_angles_deg: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"duct_id": self.duct_id, "role": self.role,
                "angles_deg": list(self.angles_deg),
                "effective_area_mm2": list(self.effective_area_mm2),
                "event_angles_deg": list(self.event_angles_deg)}


@dataclass(frozen=True)
class TwoStrokePortSet:
    stroke_mm: float
    rod_length_mm: float
    ducts: tuple[DuctBinding, ...]
    ports: tuple[PortDefinition, ...]

    def validate(self) -> None:
        stroke = _finite(self.stroke_mm, "stroke_mm")
        rod = _finite(self.rod_length_mm, "rod_length_mm")
        if stroke <= 0.0 or rod <= stroke / 2.0:
            raise ProjectError("Se requiere carrera positiva y biela mayor que media carrera.")
        # Domain validation, shared with the existing kinematic model.
        piston_position(stroke, rod, 90.0)
        if not isinstance(self.ducts, tuple) or not self.ducts:
            raise ProjectError("Se requiere una colección de conductos.")
        if not isinstance(self.ports, tuple) or not self.ports:
            raise ProjectError("Se requiere una colección de lumbreras.")
        for duct in self.ducts:
            duct.validate()
        duct_ids = [duct.id for duct in self.ducts]
        if len(set(duct_ids)) != len(duct_ids):
            raise ProjectError("Los ids de conducto deben ser únicos.")
        duct_roles = {duct.id: duct.role for duct in self.ducts}
        ids = [port.id for port in self.ports]
        if len(set(ids)) != len(ids):
            raise ProjectError("Los ids de lumbrera deben ser únicos.")
        for port in self.ports:
            port.validate()
            if port.duct_id not in duct_roles:
                raise ProjectError(f"{port.id}: duct_id no existe.")
            if duct_roles[port.duct_id] != port.role:
                raise ProjectError(f"{port.id}: el rol no coincide con el conducto asociado.")
            if port.family == "rectangular_window":
                top = port.top_mm + port.roof_travel_mm * port.roof_position
                for distance in (top, top + port.height_mm):
                    if 0.0 < distance < stroke:
                        crossing_angle(stroke, rod, distance)
            elif port.family == "piston_port":
                # Reuse the established intake-domain checks and geometry.
                intake = Intake("piston_port", port.top_mm, port.height_mm,
                                port.width_mm, port.skirt_mm)
                result = intake_results(intake, stroke, rod)
                if result.event_error or result.area_error:
                    raise ProjectError(f"{port.id}: {result.event_error or result.area_error}")

        bridge_groups: dict[str, int] = {}
        for port in self.ports:
            if port.feature == "bridged_segment":
                bridge_groups[port.group_id] = bridge_groups.get(port.group_id, 0) + 1
        if any(count < 2 for count in bridge_groups.values()):
            raise ProjectError("Cada grupo bridged requiere al menos dos aperturas.")

        counts = {role: sum(port.role == role for port in self.ports)
                  for role in PORT_ROLES}
        if counts["intake"] < 1 or counts["transfer"] < 1 or counts["exhaust"] < 1:
            raise ProjectError("Se requiere intake piston-port, al menos una transferencia y un escape.")

    def _schema(self) -> str:
        transfer_count = sum(port.role == "transfer" for port in self.ports)
        return SCHEMA_ONE_TRANSFER if transfer_count == 1 else SCHEMA

    def area_at(self, port: PortDefinition, angle_deg: float) -> float:
        """Return geometric effective area in mm²; direction belongs to the flow solver."""
        port.validate()
        angle = _finite(angle_deg, "angle_deg")
        wrapped = angle % 360.0
        if angle != 0.0 and wrapped == 0.0:
            wrapped = 360.0
        if port.family == "effective_profile":
            knots = port.area_profile
            for left, right in zip(knots, knots[1:]):
                if left.angle_deg <= wrapped <= right.angle_deg:
                    fraction = ((wrapped - left.angle_deg) /
                                (right.angle_deg - left.angle_deg))
                    value = left.area_mm2 + fraction * (right.area_mm2 - left.area_mm2)
                    return port.discharge_coefficient * value
            raise ProjectError(f"{port.id}: ángulo fuera del perfil periódico.")

        x = piston_position(self.stroke_mm, self.rod_length_mm, wrapped)
        if port.family == "piston_port":
            distance = port.top_mm + port.height_mm - port.skirt_mm
            geometric = uncovered_area(port.width_mm, port.height_mm, distance - x)
        else:
            top = port.top_mm + port.roof_travel_mm * port.roof_position
            geometric = uncovered_area(port.width_mm, port.height_mm, x - top)
        result = port.discharge_coefficient * geometric
        if not math.isfinite(result):
            raise ProjectError(f"{port.id}: área efectiva fuera de rango numérico.")
        return result

    def event_angles(self, port: PortDefinition) -> tuple[float, ...]:
        port.validate()
        if port.family == "effective_profile":
            return tuple(knot.angle_deg for knot in port.area_profile)
        if port.family == "piston_port":
            distance = port.top_mm + port.height_mm - port.skirt_mm
            thresholds = (distance, distance - port.height_mm)
        else:
            top = port.top_mm + port.roof_travel_mm * port.roof_position
            thresholds = (top, top + port.height_mm)
        events = {0.0, 180.0, 360.0}
        for distance in thresholds:
            if 0.0 < distance < self.stroke_mm:
                opening = crossing_angle(self.stroke_mm, self.rod_length_mm, distance)
                events.update((opening, 360.0 - opening))
        return tuple(sorted(events))

    def duct_closing_angles(self, duct_id: str) -> tuple[float, ...]:
        """Return exact angular boundaries where a duct's aggregate area closes.

        The area is classified on each open interval between analytic window
        events/profile knots. A boundary is a closure only when the aggregate
        area is positive immediately before it and zero immediately after it.
        Isolated zero-area points do not count as closure when the path remains
        open on both sides.
        """
        if duct_id not in {duct.id for duct in self.ducts}:
            raise ProjectError(f"Conducto desconocido: {duct_id}.")
        apertures = tuple(port for port in self.ports if port.duct_id == duct_id)
        boundaries = sorted({0.0, 360.0, *(event for port in apertures
                                           for event in self.event_angles(port))})
        if len(boundaries) < 2:
            return ()
        intervals = []
        for left, right in zip(boundaries, boundaries[1:]):
            midpoint = left + (right - left) * 0.5
            intervals.append(self.duct_area_at(duct_id, midpoint) > 0.0)
        result = []
        count = len(intervals)
        # boundaries[:-1] represents each periodic boundary exactly once;
        # the 360-degree endpoint and zero-degree origin are the same event.
        for index, boundary in enumerate(boundaries[:-1]):
            left_open = intervals[index - 1]
            right_open = intervals[index]
            if left_open and not right_open:
                result.append(boundary)
        return tuple(result)

    def compile_profiles(self) -> tuple[CompiledPortProfile, ...]:
        self.validate()
        angles = tuple(float(degree) for degree in range(361))
        return tuple(CompiledPortProfile(
            port.id, port.duct_id, port.role, angles,
            tuple(self.area_at(port, angle) for angle in angles),
            self.event_angles(port)) for port in self.ports)

    def compile_duct_profiles(self) -> tuple[CompiledDuctProfile, ...]:
        self.validate()
        angles = tuple(float(degree) for degree in range(361))
        result = []
        for duct in self.ducts:
            apertures = tuple(port for port in self.ports if port.duct_id == duct.id)
            values = []
            for angle in angles:
                try:
                    area = math.fsum(self.area_at(port, angle) for port in apertures)
                except OverflowError as exc:
                    raise ProjectError(f"{duct.id}: área agregada fuera de rango numérico.") from exc
                if not math.isfinite(area):
                    raise ProjectError(f"{duct.id}: área agregada fuera de rango numérico.")
                values.append(area)
            events = tuple(sorted({event for port in apertures
                                   for event in self.event_angles(port)}))
            result.append(CompiledDuctProfile(duct.id, duct.role, angles,
                                               tuple(values), events))
        return tuple(result)

    def duct_area_at(self, duct_id: str, angle_deg: float) -> float:
        if duct_id not in {duct.id for duct in self.ducts}:
            raise ProjectError(f"Conducto desconocido: {duct_id}.")
        try:
            result = math.fsum(self.area_at(port, angle_deg)
                               for port in self.ports if port.duct_id == duct_id)
        except OverflowError as exc:
            raise ProjectError(f"{duct_id}: área agregada fuera de rango numérico.") from exc
        if not math.isfinite(result):
            raise ProjectError(f"{duct_id}: área agregada fuera de rango numérico.")
        return result

    def _derived(self) -> dict[str, Any]:
        profiles = {"ports": [profile.to_dict() for profile in self.compile_profiles()],
                    "ducts": [profile.to_dict() for profile in self.compile_duct_profiles()]}
        return {"input_sha256": _hash(_base_dict(self.stroke_mm, self.rod_length_mm,
                                                   self.ducts, self.ports,
                                                   schema=self._schema())),
                "profile_sha256": _hash(profiles), "profiles": profiles}

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {**_base_dict(self.stroke_mm, self.rod_length_mm,
                             self.ducts, self.ports, schema=self._schema()),
                "derived_profiles": self._derived()}

    @classmethod
    def from_dict(cls, value: Any) -> "TwoStrokePortSet":
        fields = {"schema", "stroke_mm", "rod_length_mm", "ducts", "ports",
                  "derived_profiles"}
        if (not isinstance(value, dict) or set(value) != fields or
                value["schema"] not in {SCHEMA, SCHEMA_ONE_TRANSFER}):
            raise ProjectError("Esquema GENERIC_2T_PORTS inválido.")
        if not isinstance(value["ducts"], list) or not isinstance(value["ports"], list):
            raise ProjectError("ducts y ports deben ser listas.")
        result = cls(value["stroke_mm"], value["rod_length_mm"],
                     tuple(DuctBinding.from_dict(item) for item in value["ducts"]),
                     tuple(PortDefinition.from_dict(item) for item in value["ports"]))
        result.validate()
        if value["schema"] != result._schema():
            raise ProjectError("El esquema GENERIC_2T_PORTS no coincide con la topología.")
        if value["derived_profiles"] != result._derived():
            raise ProjectError("Perfiles derivados desactualizados o con binding inválido.")
        return result

    def dumps(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2,
                          allow_nan=False) + "\n"

    @classmethod
    def loads(cls, text: str) -> "TwoStrokePortSet":
        try:
            value = json.loads(text, parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"JSON no finito: {token}")))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProjectError(f"JSON de puertos inválido: {exc}") from exc
        return cls.from_dict(value)
