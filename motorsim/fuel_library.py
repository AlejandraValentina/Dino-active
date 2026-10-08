"""Versioned fuel definitions and immutable simulation snapshots.

This library stores fuel properties and their provenance.  It deliberately
does not configure injection, combustion, lubricant, or a solver EOS.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from types import MappingProxyType
from typing import Any, Mapping


SCHEMA = "FUEL_LIBRARY_V1"
DEFINITION_SCHEMA = "FUEL_DEFINITION_V1"
SNAPSHOT_SCHEMA = "FUEL_SIMULATION_SNAPSHOT_V1"
PROVENANCE = {"DOCUMENTED", "DERIVED_FROM_DOCUMENTED", "MODELED_SURROGATE",
              "USER_DEFINED_UNVERIFIED", "UNKNOWN"}
ELEMENTS = ("C", "H", "O", "N", "S")
# Atomic/molecular weights (kg/kmol) and dry-air oxygen mass fraction used by
# the explicitly versioned elemental stoichiometry calculation below.
ATOMIC_WEIGHT_KG_KMOL = {"C": 12.011, "H": 1.008, "O": 15.999,
                         "N": 14.007, "S": 32.06}
O2_MOLAR_MASS_KG_KMOL = 31.998
DRY_AIR_OXYGEN_MASS_FRACTION = 0.232
STOICHIOMETRY_METHOD = "ELEMENTAL_MASS_BALANCE_DRY_AIR_V1"


def _finite_optional(value: Any, label: str, *, positive: bool = False) -> float | None:
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label} must be finite numeric data or null")
    result = float(value)
    if positive and result <= 0.0:
        raise ValueError(f"{label} must be positive")
    return result


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


@dataclass(frozen=True)
class FuelSource:
    title: str
    uri: str
    accessed_date: str
    claim: str

    def validate(self) -> None:
        for field in ("title", "uri", "accessed_date", "claim"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"fuel source {field} must be nonempty text")
        if not self.uri.startswith(("https://", "http://")):
            raise ValueError("fuel source uri must be an http(s) URL")

    def to_dict(self) -> dict[str, str]:
        self.validate()
        return {"title": self.title, "uri": self.uri,
                "accessed_date": self.accessed_date, "claim": self.claim}

    @classmethod
    def from_dict(cls, value: Any) -> "FuelSource":
        if not isinstance(value, dict) or set(value) != {
                "title", "uri", "accessed_date", "claim"}:
            raise ValueError("fuel source schema mismatch")
        result = cls(**value)
        result.validate()
        return result


@dataclass(frozen=True)
class FuelDefinition:
    id: str
    version: str
    display_name: str
    family_category: str
    provenance: str
    builtin: bool = False
    enabled: bool = True
    ron: float | None = None
    density_kg_m3: float | None = None
    lower_heating_value_j_kg: float | None = None
    stoichiometric_afr: float | None = None
    stoichiometry_method_version: str = STOICHIOMETRY_METHOD
    elemental_mass_fractions: Mapping[str, float] | None = None
    oxygen_fraction: float | None = None
    oxygen_fraction_basis: str | None = None
    ethanol_fraction: float | None = None
    ethanol_fraction_basis: str | None = None
    reference_temperature_K: float | None = None
    sources: tuple[FuelSource, ...] = ()
    note: str = ""

    def __post_init__(self) -> None:
        # frozen=True is shallow. Detach the caller's mapping and make the
        # record's nested composition immutable as well, so library contents
        # cannot change without an explicit versioned edit.
        if self.elemental_mass_fractions is not None:
            object.__setattr__(
                self, "elemental_mass_fractions",
                MappingProxyType(dict(self.elemental_mass_fractions)))

    def validate(self) -> None:
        for name in ("id", "version", "display_name", "family_category"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"fuel {name} must be nonempty text")
        if not isinstance(self.builtin, bool) or not isinstance(self.enabled, bool):
            raise ValueError("fuel builtin/enabled flags must be boolean")
        if self.provenance not in PROVENANCE:
            raise ValueError("fuel provenance is invalid")
        if self.stoichiometry_method_version not in {
                "EXPLICIT_STOICHIOMETRIC_AFR_V1", STOICHIOMETRY_METHOD}:
            raise ValueError("fuel stoichiometry method version is unsupported")
        if (self.stoichiometric_afr is not None and
                self.stoichiometry_method_version != "EXPLICIT_STOICHIOMETRIC_AFR_V1"):
            raise ValueError("explicit AFR must use EXPLICIT_STOICHIOMETRIC_AFR_V1")
        if (self.stoichiometric_afr is None and
                self.stoichiometry_method_version == "EXPLICIT_STOICHIOMETRIC_AFR_V1"):
            raise ValueError("explicit AFR method requires a stoichiometric AFR value")
        for name, positive in (("ron", True), ("density_kg_m3", True),
                               ("lower_heating_value_j_kg", True),
                               ("stoichiometric_afr", True),
                               ("reference_temperature_K", True)):
            _finite_optional(getattr(self, name), name, positive=positive)
        for name in ("oxygen_fraction", "ethanol_fraction"):
            value = _finite_optional(getattr(self, name), name)
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be a fraction in [0,1]")
        if self.oxygen_fraction is None and self.oxygen_fraction_basis is not None:
            raise ValueError("oxygen fraction basis requires a known fraction")
        if self.oxygen_fraction is not None and self.oxygen_fraction_basis not in {
                "MASS_FRACTION", "VOLUME_FRACTION"}:
            raise ValueError("oxygen fraction basis must be MASS_FRACTION or VOLUME_FRACTION")
        if self.ethanol_fraction is None and self.ethanol_fraction_basis is not None:
            raise ValueError("ethanol fraction basis requires a known fraction")
        if self.ethanol_fraction is not None and self.ethanol_fraction_basis not in {
                "MASS_FRACTION", "VOLUME_FRACTION"}:
            raise ValueError("ethanol fraction basis must be MASS_FRACTION or VOLUME_FRACTION")
        if self.density_kg_m3 is not None and self.reference_temperature_K is None:
            raise ValueError("density requires its reference temperature")
        if self.elemental_mass_fractions is not None:
            if not isinstance(self.elemental_mass_fractions, Mapping):
                raise ValueError("elemental composition must be a mapping")
            if set(self.elemental_mass_fractions) - set(ELEMENTS):
                raise ValueError("elemental composition contains unsupported elements")
            values = {key: _finite_optional(value, f"elemental.{key}")
                      for key, value in self.elemental_mass_fractions.items()}
            if not values or any(value is None or value < 0.0 for value in values.values()):
                raise ValueError("elemental composition fractions must be nonnegative numbers")
            if not math.isclose(math.fsum(values.values()), 1.0,
                                rel_tol=0.0, abs_tol=1e-9):
                raise ValueError("elemental composition must be complete and sum to one")
        if not isinstance(self.sources, tuple) or any(
                not isinstance(source, FuelSource) for source in self.sources):
            raise ValueError("fuel sources must be a tuple of FuelSource")
        for source in self.sources:
            source.validate()
        if not isinstance(self.note, str):
            raise ValueError("fuel note must be text")

    @property
    def effective_stoichiometric_afr(self) -> float | None:
        """Return explicit AFR or calculate it from complete elemental mass fractions."""
        self.validate()
        if self.stoichiometric_afr is not None:
            return float(self.stoichiometric_afr)
        composition = self.elemental_mass_fractions
        if composition is None:
            return None
        c = float(composition.get("C", 0.0)) / ATOMIC_WEIGHT_KG_KMOL["C"]
        h = float(composition.get("H", 0.0)) / ATOMIC_WEIGHT_KG_KMOL["H"]
        o = float(composition.get("O", 0.0)) / ATOMIC_WEIGHT_KG_KMOL["O"]
        s = float(composition.get("S", 0.0)) / ATOMIC_WEIGHT_KG_KMOL["S"]
        required_o2_kmol_per_kg = c + h / 4.0 + s - o / 2.0
        if required_o2_kmol_per_kg <= 0.0:
            raise ValueError("elemental composition does not require positive external oxygen")
        afr = (required_o2_kmol_per_kg * O2_MOLAR_MASS_KG_KMOL /
               DRY_AIR_OXYGEN_MASS_FRACTION)
        if not math.isfinite(afr) or afr <= 0.0:
            raise ValueError("derived stoichiometric AFR is outside supported range")
        return afr

    def missing_combustion_properties(self) -> tuple[str, ...]:
        missing = []
        if self.effective_stoichiometric_afr is None:
            missing.append("stoichiometric_afr_or_complete_elemental_composition")
        if self.lower_heating_value_j_kg is None:
            missing.append("lower_heating_value_j_kg")
        return tuple(missing)

    def snapshot(self) -> dict[str, Any]:
        """Return the complete identity/version/hash snapshot used by V2."""
        return FuelSimulationSnapshot.freeze(self).to_dict()

    @property
    def sha256(self) -> str:
        return FuelSimulationSnapshot.freeze(self).content_hash

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"schema": DEFINITION_SCHEMA, "id": self.id,
                "version": self.version, "display_name": self.display_name,
                "family_category": self.family_category,
                "provenance": self.provenance, "builtin": self.builtin,
                "enabled": self.enabled, "ron": self.ron,
                "density_kg_m3": self.density_kg_m3,
                "lower_heating_value_j_kg": self.lower_heating_value_j_kg,
                "stoichiometric_afr": self.stoichiometric_afr,
                "stoichiometry_method_version": self.stoichiometry_method_version,
                "elemental_mass_fractions": (None if self.elemental_mass_fractions is None
                                               else dict(self.elemental_mass_fractions)),
                "oxygen_fraction": self.oxygen_fraction,
                "oxygen_fraction_basis": self.oxygen_fraction_basis,
                "ethanol_fraction": self.ethanol_fraction,
                "ethanol_fraction_basis": self.ethanol_fraction_basis,
                "reference_temperature_K": self.reference_temperature_K,
                "sources": [source.to_dict() for source in self.sources],
                "note": self.note}

    @classmethod
    def from_dict(cls, value: Any) -> "FuelDefinition":
        fields = {"schema", "id", "version", "display_name", "family_category",
                  "provenance", "builtin", "enabled", "ron", "density_kg_m3",
                  "lower_heating_value_j_kg", "stoichiometric_afr",
                  "stoichiometry_method_version", "elemental_mass_fractions",
                  "oxygen_fraction", "ethanol_fraction",
                  "oxygen_fraction_basis", "ethanol_fraction_basis",
                  "reference_temperature_K", "sources", "note"}
        if not isinstance(value, dict) or set(value) != fields or value["schema"] != DEFINITION_SCHEMA:
            raise ValueError("fuel definition schema mismatch")
        data = dict(value)
        data.pop("schema")
        data["sources"] = tuple(FuelSource.from_dict(source) for source in data["sources"])
        result = cls(**data)
        result.validate()
        return result


@dataclass(frozen=True)
class FuelSimulationSnapshot:
    fuel_id: str
    version: str
    content_hash: str
    full_definition: str

    @classmethod
    def freeze(cls, definition: FuelDefinition) -> "FuelSimulationSnapshot":
        definition.validate()
        encoded = _canonical(definition.to_dict()).decode("utf-8")
        return cls(definition.id, definition.version,
                   hashlib.sha256(encoded.encode("utf-8")).hexdigest(), encoded)

    def validate(self) -> FuelDefinition:
        raw = self.full_definition.encode("utf-8")
        if hashlib.sha256(raw).hexdigest() != self.content_hash:
            raise ValueError("frozen fuel snapshot hash mismatch")
        definition = FuelDefinition.from_dict(json.loads(self.full_definition))
        if (definition.id, definition.version) != (self.fuel_id, self.version):
            raise ValueError("frozen fuel snapshot identity mismatch")
        return definition

    def to_dict(self) -> dict[str, str]:
        self.validate()
        return {"schema": SNAPSHOT_SCHEMA, "fuel_id": self.fuel_id,
                "version": self.version, "content_hash": self.content_hash,
                "full_definition": self.full_definition}

    @classmethod
    def from_dict(cls, value: Any) -> "FuelSimulationSnapshot":
        if not isinstance(value, dict) or set(value) != {
                "schema", "fuel_id", "version", "content_hash", "full_definition"} or \
                value["schema"] != SNAPSHOT_SCHEMA:
            raise ValueError("frozen fuel snapshot schema mismatch")
        result = cls(value["fuel_id"], value["version"], value["content_hash"],
                     value["full_definition"])
        result.validate()
        return result


def builtin_defaults() -> tuple[FuelDefinition, ...]:
    """Identified Uruguay profiles; unknown physical chemistry stays null."""
    return (
        FuelDefinition(
            id="ANCAP_SUPER_95", version="2024-06", display_name="ANCAP Súper 95",
            family_category="AUTOMOTIVE_GASOLINE", provenance="DOCUMENTED", builtin=True,
            ron=95.0,
            sources=(
                FuelSource("ANCAP Súper 95 product page", "https://www.ancap.com.uy/1636/5/super-95.html",
                           "2026-10-06", "Product is RON 95; may contain up to 10% v/v anhydrous ethanol."),
                FuelSource("ANCAP Super 95 technical sheet", "https://exploracionyproduccion.ancap.com.uy/innovaportal/file/1636/1/gasolina-super-95--2024-06-24.pdf",
                           "2026-10-06", "RON specification 95.0; ethanol maximum 10% v/v; oxygen is specified as a maximum, not a measured batch value."),
            ),
            note="Identified product profile only. Density, batch ethanol fraction, elemental composition, stoichiometric AFR and LHV are not supplied as point values; chemical outputs remain unavailable.",
        ),
        FuelDefinition(
            id="ANCAP_PREMIUM_97", version="2024-06", display_name="ANCAP Premium 97",
            family_category="AUTOMOTIVE_GASOLINE", provenance="DOCUMENTED", builtin=True,
            ron=97.0,
            sources=(
                FuelSource("ANCAP Premium 97 product page", "https://www.ancap.com.uy/1637/6/premium-97.html",
                           "2026-10-06", "Product is RON 97; may contain up to 10% v/v anhydrous ethanol."),
                FuelSource("ANCAP Premium 97 technical sheet", "https://www.ancap.com.uy/innovaportal/file/1637/1/gasolina-premium-97-euro-5-2024-06-24.pdf",
                           "2026-10-06", "RON specification 97.0; ethanol maximum 10% v/v; oxygen is specified as a maximum, not a measured batch value."),
            ),
            note="Identified product profile only. Density, batch ethanol fraction, elemental composition, stoichiometric AFR and LHV are not supplied as point values; chemical outputs remain unavailable.",
        ),
        FuelDefinition(
            id="MOTORSIM_ISOOCTANE_SURROGATE_V1", version="1.0.0",
            display_name="MotorSim pure iso-octane surrogate",
            family_category="PURE_HYDROCARBON_SURROGATE",
            provenance="MODELED_SURROGATE", builtin=True,
            density_kg_m3=691.853,
            lower_heating_value_j_kg=44_343_551.390414825,
            stoichiometry_method_version=STOICHIOMETRY_METHOD,
            elemental_mass_fractions={
                "C": (8 * 12.011) / (8 * 12.011 + 18 * 1.008),
                "H": (18 * 1.008) / (8 * 12.011 + 18 * 1.008),
            },
            oxygen_fraction=0.0, oxygen_fraction_basis="MASS_FRACTION",
            ethanol_fraction=0.0, ethanol_fraction_basis="VOLUME_FRACTION",
            reference_temperature_K=293.15,
            sources=(
                FuelSource(
                    "NIST Chemistry WebBook, 2,2,4-trimethylpentane",
                    "https://webbook.nist.gov/cgi/cbook.cgi?ID=C540841&Mask=187&Units=CAL",
                    "2026-10-06",
                    "Chemical identity C8H18; liquid standard combustion enthalpy -1305.29 kcal/mol. LHV is derived by subtracting 9 mol water vaporization at 298.15 K and dividing by NIST molecular weight 114.2285 g/mol."),
                FuelSource(
                    "NIST SP 260-186, SRM 2214 density",
                    "https://doi.org/10.6028/NIST.SP.260-186",
                    "2026-10-06",
                    "Certified iso-octane SRM density 691.853 kg/m3 at 20 C and 0.1 MPa."),
            ),
            note=("Explicit pure-compound surrogate for synthetic capability tests; "
                  "not ANCAP Super 95/Premium 97, not a commercial gasoline blend, "
                  "and not an engine calibration. RON is intentionally unknown in "
                  "this record. LHV provenance is a derived thermochemical value."),
        ),
    )


class FuelLibrary:
    """In-memory library with explicit built-in/user lifecycle operations."""

    def __init__(self, definitions: tuple[FuelDefinition, ...] | None = None):
        self._defaults = {item.id: item for item in builtin_defaults()}
        supplied = builtin_defaults() if definitions is None else definitions
        self._definitions: dict[str, FuelDefinition] = {}
        for definition in supplied:
            definition.validate()
            if definition.id in self._definitions:
                raise ValueError("duplicate fuel id")
            if definition.id in self._defaults:
                baseline = self._defaults[definition.id].to_dict()
                candidate = definition.to_dict()
                baseline.pop("enabled")
                candidate.pop("enabled")
                if candidate != baseline:
                    raise ValueError("built-in fuel defaults are immutable; use enabled state only")
            self._definitions[definition.id] = definition
        for key, value in self._defaults.items():
            if key not in self._definitions:
                self._definitions[key] = value

    def list(self, *, enabled_only: bool = False) -> tuple[FuelDefinition, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions)
                     if not enabled_only or self._definitions[key].enabled)

    def get(self, fuel_id: str) -> FuelDefinition:
        try:
            return self._definitions[fuel_id]
        except KeyError as error:
            raise KeyError(f"unknown fuel id: {fuel_id}") from error

    def create(self, definition: FuelDefinition) -> FuelDefinition:
        definition.validate()
        if definition.builtin:
            raise ValueError("user create cannot insert a built-in fuel")
        if definition.id in self._definitions:
            raise ValueError("fuel id already exists")
        self._definitions[definition.id] = definition
        return definition

    def duplicate(self, fuel_id: str, *, new_id: str, new_version: str,
                  display_name: str | None = None) -> FuelDefinition:
        source = self.get(fuel_id)
        duplicate = FuelDefinition.from_dict(source.to_dict() | {
            "id": new_id, "version": new_version,
            "display_name": display_name or f"{source.display_name} copy",
            "builtin": False, "enabled": True,
            "provenance": "USER_DEFINED_UNVERIFIED", "schema": DEFINITION_SCHEMA,
            "note": (source.note + " Duplicated from " + source.id + "@" + source.version).strip(),
        })
        return self.create(duplicate)

    def edit_user(self, definition: FuelDefinition) -> FuelDefinition:
        definition.validate()
        current = self.get(definition.id)
        if current.builtin:
            raise ValueError("built-in fuel definitions are immutable")
        if definition.builtin or definition.version == current.version:
            raise ValueError("edited fuel must remain user-defined and increment its version")
        self._definitions[definition.id] = definition
        return definition

    def set_enabled(self, fuel_id: str, enabled: bool) -> FuelDefinition:
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be boolean")
        current = self.get(fuel_id)
        updated = FuelDefinition.from_dict(current.to_dict() | {"enabled": enabled})
        self._definitions[fuel_id] = updated
        return updated

    def delete_user(self, fuel_id: str) -> None:
        current = self.get(fuel_id)
        if current.builtin:
            raise ValueError("built-in fuel cannot be physically deleted")
        del self._definitions[fuel_id]

    def restore_defaults(self) -> None:
        users = {key: value for key, value in self._definitions.items() if not value.builtin}
        self._definitions = dict(self._defaults) | users

    def freeze(self, fuel_id: str) -> FuelSimulationSnapshot:
        definition = self.get(fuel_id)
        if not definition.enabled:
            raise ValueError("disabled fuel cannot be selected for a simulation")
        return FuelSimulationSnapshot.freeze(definition)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA,
                "definitions": [item.to_dict() for item in self.list()]}

    @classmethod
    def from_dict(cls, value: Any) -> "FuelLibrary":
        if not isinstance(value, dict) or set(value) != {"schema", "definitions"} or \
                value["schema"] != SCHEMA or not isinstance(value["definitions"], list):
            raise ValueError("fuel library schema mismatch")
        return cls(tuple(FuelDefinition.from_dict(item) for item in value["definitions"]))

    def save(self, path: str | Path) -> None:
        """Write atomically; callers choose a user-data path, never the package."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = _canonical(self.to_dict())
        fd, temporary = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp",
                                         dir=str(target.parent))
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @classmethod
    def load(cls, path: str | Path) -> "FuelLibrary":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def export_user_fuel(self, fuel_id: str) -> bytes:
        definition = self.get(fuel_id)
        if definition.builtin:
            raise ValueError("only user-defined fuels can be exported as editable profiles")
        return _canonical({"schema": "FUEL_DEFINITION_EXPORT_V1",
                           "definition": definition.to_dict()})

    def import_user_fuel(self, payload: bytes | str) -> FuelDefinition:
        value = json.loads(payload)
        if not isinstance(value, dict) or set(value) != {"schema", "definition"} or \
                value["schema"] != "FUEL_DEFINITION_EXPORT_V1":
            raise ValueError("fuel import schema mismatch")
        definition = FuelDefinition.from_dict(value["definition"])
        if definition.builtin:
            raise ValueError("import cannot create or overwrite a built-in fuel")
        return self.create(definition)


def future_lubricant_interface() -> dict[str, str]:
    """Typed extension seam; deliberately not a fuel or combustion model."""
    return {"schema": "LUBRICANT_DEFINITION_INTERFACE_V1",
            "definition_ref": "separate versioned lubricant identity",
            "premix_ratio_ref": "separate explicit ratio; not part of FuelDefinition"}
