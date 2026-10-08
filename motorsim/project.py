"""Datos del proyecto, independientes de la interfaz."""

from dataclasses import asdict, dataclass, field
from decimal import Decimal, localcontext
import math
import re


class ProjectError(ValueError):
    """Datos o archivo de proyecto que no se pueden utilizar."""


NUMERIC_FIELDS = {
    "cylinder_count": "Número de cilindros",
    "bore_mm": "Diámetro del cilindro",
    "stroke_mm": "Carrera",
    "rod_length_mm": "Longitud de biela entre centros",
    "compression_ratio": "Relación de compresión geométrica",
}


PORT_FIELDS = {"top_mm": "Distancia al borde superior", "height_mm": "Altura de ventana",
               "width_mm": "Ancho desarrollado"}
INTAKE_FIELDS = {**PORT_FIELDS, "skirt_mm": "Distancia al borde inferior de falda"}
INTAKE_REFERENCE = "straight-skirt-peripheral-tdc-developed-v1"
DUCT_FIELDS = {"length_mm": "Longitud axial", "start_diameter_mm": "Diámetro interior inicial",
               "end_diameter_mm": "Diámetro interior final"}
DUCT_REFERENCE = "ordered-circular-inner-axial-linear-2t-v1"
FOUR_DUCT_REFERENCE = "ordered-circular-inner-axial-linear-4t-v1"
VALVE_FIELDS = {"seat_mm": "Diámetro de asiento D", "throat_mm": "Diámetro de garganta d",
                "stem_mm": "Diámetro del vástago s", "lift_mm": "Alzada máxima H",
                "opening_deg": "Apertura", "duration_deg": "Duración"}
VALVE_REFERENCE = "sin-squared-cylindrical-curtain-annular-cap-720-v1"
NUMBER_LABELS = {**NUMERIC_FIELDS, **INTAKE_FIELDS, **DUCT_FIELDS, **VALVE_FIELDS,
                 "crankcase_volume_bdc_cm3": "Volumen libre del cárter en PMI"}
TWO_STROKE_REFERENCE = "rectangular-peripheral-tdc-developed-bdc-v1"


def validate_number(value: object, field: str) -> None:
    if value is None:
        return
    label = NUMBER_LABELS[field]
    if field == "cylinder_count":
        if type(value) is not int or value <= 0:
            raise ProjectError(f"{label}: debe ser un entero positivo.")
        return
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    minimum = 1 if field == "compression_ratio" else 0
    if field in ("stem_mm", "opening_deg"):
        if not valid or value < 0 or (field == "opening_deg" and value >= 720):
            raise ProjectError(f"{label}: valor finito >= 0" + (" y < 720." if field == "opening_deg" else "."))
        return
    if field == "duration_deg" and valid and value >= 720:
        raise ProjectError("Duración: debe ser menor que 720°.")
    if not valid or value <= minimum:
        raise ProjectError(f"{label}: debe ser un número finito mayor que {minimum}.")


def parse_number(text: str, field: str) -> int | float | None:
    """Vacío es ausencia; cualquier otro texto se valida sin corregirlo."""
    text = text.strip()
    if not text:
        return None
    pattern = (r"\+?[0-9]+" if field == "cylinder_count" else
               r"[+-]?(?:[0-9]+(?:[.,][0-9]*)?|[.,][0-9]+)(?:[eE][+-]?[0-9]+)?")
    if not re.fullmatch(pattern, text):
        raise ProjectError(f"{NUMBER_LABELS[field]}: número inválido; no uses separadores de miles.")
    try:
        value = int(text) if re.fullmatch(r"[+-]?[0-9]+", text) else float(text.replace(",", "."))
    except ValueError as exc:
        raise ProjectError(f"{NUMBER_LABELS[field]}: número fuera del rango admitido.") from exc
    validate_number(value, field)
    return value


def displacements(bore: object, stroke: object, cylinders: object) -> tuple[Decimal | None, Decimal | None]:
    """cm³; cada resultado depende solo de sus entradas. Sin desbordar float."""
    try:
        validate_number(bore, "bore_mm")
        validate_number(stroke, "stroke_mm")
    except ProjectError:
        return None, None
    if bore is None or stroke is None:
        return None, None
    with localcontext() as context:
        context.prec = 40
        per_cylinder = Decimal(str(math.pi)) * Decimal(str(bore)) ** 2 * Decimal(str(stroke)) / 4000
        try:
            validate_number(cylinders, "cylinder_count")
        except ProjectError:
            return per_cylinder, None
        total = per_cylinder * cylinders if cylinders is not None else None
    return per_cylinder, total


@dataclass(frozen=True)
class Port:
    name: str = ""
    function: str | None = None
    top_mm: float | None = None
    height_mm: float | None = None
    width_mm: float | None = None

    def validate(self):
        if not isinstance(self.name, str):
            raise ProjectError("El nombre de lumbrera debe ser texto.")
        if self.function is not None and self.function not in ("escape", "transfer"):
            raise ProjectError("Función de lumbrera inválida: Escape o Transferencia.")
        for field in PORT_FIELDS:
            validate_number(getattr(self, field), field)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or not cls.__dataclass_fields__.keys() <= data.keys():
            raise ProjectError("Faltan campos de la lumbrera.")
        port = cls(**{key: data[key] for key in cls.__dataclass_fields__})
        port.validate()
        return port


@dataclass(frozen=True)
class Intake:
    mode: str | None = None
    top_mm: float | None = None
    height_mm: float | None = None
    width_mm: float | None = None
    skirt_mm: float | None = None
    reference: str = INTAKE_REFERENCE

    def validate(self):
        if self.mode is not None and self.mode != "piston_port":
            raise ProjectError("Modalidad de admisión no admitida.")
        if self.reference != INTAKE_REFERENCE:
            raise ProjectError("Referencia de admisión no admitida.")
        for key in INTAKE_FIELDS:
            validate_number(getattr(self, key), key)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or not cls.__dataclass_fields__.keys() <= data.keys():
            raise ProjectError("Faltan campos de admisión.")
        intake = cls(**{key: data[key] for key in cls.__dataclass_fields__})
        intake.validate()
        return intake


@dataclass(frozen=True)
class DuctSegment:
    name: str = ""
    length_mm: float | None = None
    start_diameter_mm: float | None = None
    end_diameter_mm: float | None = None

    def validate(self):
        if not isinstance(self.name, str):
            raise ProjectError("El nombre de tramo debe ser texto.")
        for key in DUCT_FIELDS:
            validate_number(getattr(self, key), key)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or not cls.__dataclass_fields__.keys() <= data.keys():
            raise ProjectError("Faltan campos del tramo de conducto.")
        segment = cls(**{key: data[key] for key in cls.__dataclass_fields__})
        segment.validate()
        return segment


@dataclass(frozen=True)
class Ducts:
    intake: tuple[DuctSegment, ...] = ()
    exhaust: tuple[DuctSegment, ...] = ()
    reference: str = DUCT_REFERENCE

    def validate(self):
        if self.reference not in (DUCT_REFERENCE, FOUR_DUCT_REFERENCE):
            raise ProjectError("Referencia de conductos no admitida.")
        for route in (self.intake, self.exhaust):
            if not isinstance(route, tuple) or any(not isinstance(s, DuctSegment) for s in route):
                raise ProjectError("La colección de tramos es inválida.")
            for segment in route:
                segment.validate()

    def to_dict(self):
        return {"reference": self.reference,
                "intake": [asdict(s) for s in self.intake],
                "exhaust": [asdict(s) for s in self.exhaust]}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or not cls.__dataclass_fields__.keys() <= data.keys():
            raise ProjectError("Faltan campos de conductos.")
        if not all(isinstance(data[key], list) for key in ("intake", "exhaust")):
            raise ProjectError("Los recorridos deben ser listas.")
        ducts = cls(tuple(DuctSegment.from_dict(s) for s in data["intake"]),
                    tuple(DuctSegment.from_dict(s) for s in data["exhaust"]), data["reference"])
        ducts.validate()
        return ducts


@dataclass(frozen=True)
class Valve:
    seat_mm: float | None = None
    throat_mm: float | None = None
    stem_mm: float | None = None
    lift_mm: float | None = None
    opening_deg: float | None = None
    duration_deg: float | None = None

    def validate(self):
        for key in VALVE_FIELDS:
            validate_number(getattr(self, key), key)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) != set(VALVE_FIELDS):
            raise ProjectError("Campos de válvula inválidos.")
        result = cls(**data)
        result.validate()
        return result


@dataclass(frozen=True)
class FourStroke:
    intake: Valve = field(default_factory=Valve)
    exhaust: Valve = field(default_factory=Valve)
    ducts: Ducts = field(default_factory=lambda: Ducts(reference=FOUR_DUCT_REFERENCE))
    reference: str = VALVE_REFERENCE

    def validate(self):
        if self.reference != VALVE_REFERENCE:
            raise ProjectError("Referencia de válvulas no admitida.")
        if not isinstance(self.intake, Valve) or not isinstance(self.exhaust, Valve) or not isinstance(self.ducts, Ducts):
            raise ProjectError("Configuración 4T inválida.")
        if self.ducts.reference != FOUR_DUCT_REFERENCE:
            raise ProjectError("Los conductos 4T requieren su referencia independiente.")
        self.intake.validate(); self.exhaust.validate(); self.ducts.validate()

    def to_dict(self):
        return {**asdict(self), "ducts": self.ducts.to_dict()}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) != set(cls.__dataclass_fields__):
            raise ProjectError("Campos de configuración 4T inválidos.")
        result = cls(Valve.from_dict(data['intake']), Valve.from_dict(data['exhaust']),
                     Ducts.from_dict(data['ducts']), data['reference'])
        result.validate()
        return result


@dataclass(frozen=True)
class Project:
    name: str = "Sin título"
    cycle: str = "2T"
    manufacturer: str = ""
    model: str = ""
    cylinder_count: int | None = None
    bore_mm: float | None = None
    stroke_mm: float | None = None
    rod_length_mm: float | None = None
    compression_ratio: float | None = None
    notes: str = ""
    ports: tuple[Port, ...] = ()
    crankcase_volume_bdc_cm3: float | None = None
    intake: Intake = field(default_factory=Intake)
    ducts: Ducts = field(default_factory=Ducts)

    four_stroke: FourStroke = field(default_factory=FourStroke)

    def validate(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ProjectError("El nombre debe ser texto y no puede estar vacío ni contener solo espacios.")
        if not isinstance(self.cycle, str) or self.cycle not in ("2T", "4T"):
            raise ProjectError("El tipo de motor debe ser 2T o 4T.")
        for field in ("manufacturer", "model", "notes"):
            if not isinstance(getattr(self, field), str):
                raise ProjectError(f"{field}: debe ser texto, aunque esté vacío.")
        for field in NUMERIC_FIELDS:
            validate_number(getattr(self, field), field)

        validate_number(self.crankcase_volume_bdc_cm3, "crankcase_volume_bdc_cm3")
        if not isinstance(self.ports, tuple) or any(not isinstance(port, Port) for port in self.ports):
            raise ProjectError("La colección de lumbreras es inválida.")
        for port in self.ports:
            port.validate()
        if not isinstance(self.intake, Intake):
            raise ProjectError("Datos de admisión inválidos.")
        self.intake.validate()
        if not isinstance(self.ducts, Ducts):
            raise ProjectError("Datos de conductos inválidos.")
        self.ducts.validate()
        if self.ducts.reference != DUCT_REFERENCE:
            raise ProjectError("Los conductos históricos requieren referencia 2T.")
        if not isinstance(self.four_stroke, FourStroke):
            raise ProjectError("Configuración 4T inválida.")
        self.four_stroke.validate()

    def to_dict(self) -> dict:
        self.validate()
        return {"format_version": 6, **asdict(self), "four_stroke": self.four_stroke.to_dict(), "ducts": self.ducts.to_dict(), "ports": [asdict(port) for port in self.ports],
                "two_stroke_reference": TWO_STROKE_REFERENCE}

    @classmethod
    def from_dict(cls, data: object) -> "Project":
        if not isinstance(data, dict):
            raise ProjectError("El archivo debe contener un objeto JSON.")
        if not {"format_version", "name", "cycle"} <= data.keys():
            raise ProjectError("Faltan campos obligatorios: format_version, name o cycle.")
        version = data["format_version"]
        if type(version) is not int or version not in (1, 2, 3, 4, 5, 6):
            raise ProjectError("La versión del archivo debe ser el entero 1, 2, 3, 4, 5 o 6.")
        if version == 1:
            project = cls(data["name"], data["cycle"])
        else:
            fields = set(cls.__dataclass_fields__)
            if version < 6:
                fields -= {"four_stroke"}
            if version < 5:
                fields -= {"ducts"}
            if version < 4:
                fields -= {"intake"}
            if version == 2:
                fields -= {"ports", "crankcase_volume_bdc_cm3"}
            if not fields <= data.keys():
                raise ProjectError(f"Faltan campos obligatorios de la ficha versión {version}.")
            values = {field: data[field] for field in fields}
            if version >= 3:
                if data.get("two_stroke_reference") != TWO_STROKE_REFERENCE:
                    raise ProjectError("Referencia de geometría 2T no admitida.")
                if not isinstance(data["ports"], list):
                    raise ProjectError("Las lumbreras deben ser una lista.")
                values["ports"] = tuple(Port.from_dict(port) for port in data["ports"])
            if version >= 4:
                values["intake"] = Intake.from_dict(data["intake"])
            if version >= 6:
                values["four_stroke"] = FourStroke.from_dict(data["four_stroke"])
            if version >= 5:
                values["ducts"] = Ducts.from_dict(data["ducts"])
            project = cls(**values)
        project.validate()
        return project
