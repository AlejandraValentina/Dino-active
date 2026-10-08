"""Opt-in mapping from generic port geometry to the frozen two-transfer P5-C.

This adapter changes only resolved geometric face areas. It does not extend
the historical P5 topology: one intake path, two transfer paths, and one
exhaust path are required. Multiple apertures may share any mapped path.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Callable

from .project import ProjectError
from .two_stroke_ports import TwoStrokePortSet


@dataclass(frozen=True)
class P5CPathBinding:
    intake_duct: str
    transfer_ducts: tuple[str, str]
    exhaust_duct: str

    def validate(self, ports: TwoStrokePortSet) -> None:
        if not isinstance(self.intake_duct, str) or not self.intake_duct:
            raise ProjectError("P5-C necesita un conducto de admisión asociado.")
        if (not isinstance(self.transfer_ducts, tuple) or len(self.transfer_ducts) != 2 or
                any(not isinstance(value, str) or not value for value in self.transfer_ducts)):
            raise ProjectError("P5-C admite exactamente dos conductos de transferencia.")
        if not isinstance(self.exhaust_duct, str) or not self.exhaust_duct:
            raise ProjectError("P5-C necesita un conducto de escape asociado.")
        path_ids = (self.intake_duct, *self.transfer_ducts, self.exhaust_duct)
        if len(set(path_ids)) != 4:
            raise ProjectError("Cada interfaz P5-C debe asociarse a un conducto distinto.")
        roles = {duct.id: duct.role for duct in ports.ducts}
        expected = ((self.intake_duct, "intake"),
                    (self.transfer_ducts[0], "transfer"),
                    (self.transfer_ducts[1], "transfer"),
                    (self.exhaust_duct, "exhaust"))
        for duct_id, role in expected:
            if roles.get(duct_id) != role:
                raise ProjectError(f"Conducto {duct_id!r} no existe con rol {role!r}.")
        unmapped = set(roles) - set(path_ids)
        if unmapped:
            raise ProjectError(
                "El P5-C de dos transferencias no puede resolver conductos adicionales: "
                + ", ".join(sorted(unmapped)))


class P5CGenericPortGeometry:
    """Resolve per-aperture GENERIC_2T_PORTS_V1 areas into P5-C face areas."""

    def __init__(self, ports: TwoStrokePortSet, bindings: P5CPathBinding,
                 chamber_geometry: Callable[[float], Any]):
        ports.validate()
        bindings.validate(ports)
        if not callable(chamber_geometry):
            raise ProjectError("chamber_geometry debe ser una función angular.")
        self.ports = ports
        self.bindings = bindings
        self.chamber_geometry = chamber_geometry

    def __call__(self, angle_deg: float) -> dict[str, Any]:
        base = self.chamber_geometry(angle_deg)
        if isinstance(base, dict):
            try:
                volumes = tuple(base["volumes"])
                rates = tuple(base["volume_rates"])
            except (KeyError, TypeError) as exc:
                raise ProjectError("La geometría base requiere volumes y volume_rates.") from exc
        elif isinstance(base, (tuple, list)) and len(base) >= 2:
            volumes, rates = tuple(base[0]), tuple(base[1])
        else:
            raise ProjectError("La geometría base debe devolver volúmenes y tasas.")
        if len(volumes) < 3 or len(rates) != 2:
            raise ProjectError("La geometría base debe contener I/K/C y dos tasas de volumen.")
        checked = []
        for label, values in (("volumes", volumes), ("volume_rates", rates)):
            row = []
            for value in values:
                if type(value) not in (int, float) or not isfinite(value):
                    raise ProjectError(f"{label} contiene un valor no finito.")
                row.append(float(value))
            checked.append(tuple(row))
        volumes, rates = checked
        if any(value <= 0.0 for value in volumes[:3]):
            raise ProjectError("Los volúmenes I/K/C deben ser positivos.")
        areas_mm2 = (
            self.ports.duct_area_at(self.bindings.intake_duct, angle_deg),
            self.ports.duct_area_at(self.bindings.transfer_ducts[0], angle_deg),
            self.ports.duct_area_at(self.bindings.transfer_ducts[1], angle_deg),
            self.ports.duct_area_at(self.bindings.exhaust_duct, angle_deg),
        )
        areas_m2 = tuple(area * 1e-6 for area in areas_mm2)
        if any(not isfinite(value) or value < 0.0 for value in areas_m2):
            raise ProjectError("Las áreas P5-C deben ser finitas y no negativas.")
        return {"volumes": volumes, "volume_rates": rates, "areas": areas_m2}
