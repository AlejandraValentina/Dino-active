"""Build one normalized, explicit-null P9 dataset candidate matrix."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results" / "p9-dataset-search-20261001"
FIELDS = [
    "candidate_id", "engine", "architecture", "displacement", "source", "DOI",
    "publication", "institution", "year", "RPM_count", "RPM_range",
    "cylinder_pressure", "crank_angle", "raw_numeric_data", "file_formats",
    "cycles_per_point", "bore", "stroke", "rod_length", "compression_ratio",
    "port_data", "exhaust_data", "ignition_data", "AFR_or_mixture", "load",
    "atmospheric_conditions", "TDC_method", "pressure_calibration", "uncertainty",
    "dyno_data", "access", "license", "provenance_quality", "P9_compatibility",
    "P9_classification", "blocking_reason", "next_action",
]
CLASSIFICATIONS = {
    "C01": "DATA_REQUEST_REQUIRED", "C02": "DATA_REQUEST_REQUIRED",
    "C03": "INSUFFICIENT_RPM_POINTS", "C04": "DATA_REQUEST_REQUIRED",
    "C05": "INSUFFICIENT_RPM_POINTS", "C06": "DATA_REQUEST_REQUIRED",
    "C07": "INSUFFICIENT_RPM_POINTS", "C08": "DATA_REQUEST_REQUIRED",
    "C09": "DATA_REQUEST_REQUIRED", "C10": "INCOMPATIBLE_ARCHITECTURE",
}


def _load(name: str) -> dict:
    return json.loads((SOURCE / name).read_text(encoding="utf-8"))


def main() -> int:
    old = _load("search.json")
    expansion = _load("search-expansion.json")
    candidates = []
    for row in old["candidates"]:
        normalized = {
            "candidate_id": row.get("candidate_id"), "engine": row.get("engine"),
            "architecture": row.get("2T configuration"), "source": row.get("source"),
            "DOI": row.get("doi"), "publication": row.get("publication"),
            "institution": row.get("institution"), "year": row.get("year"),
            "RPM_count": row.get("number_of_RPM_points"), "RPM_range": row.get("RPM_range"),
            "cylinder_pressure": row.get("cylinder_pressure"),
            "crank_angle": row.get("crank_angle"), "raw_numeric_data": row.get("raw_numeric_data"),
            "cycles_per_point": row.get("cycles_per_point"), "dyno_data": row.get("brake_power"),
            "access": row.get("license/access"), "P9_compatibility": row.get("P9_compatible"),
            "blocking_reason": row.get("blocking_reason"),
            "next_action": row.get("recommended_action"),
            "provenance_quality": "Evidence and unknowns are summarized in the original search record; no raw file was ingested.",
            "P9_classification": CLASSIFICATIONS[row["candidate_id"]],
        }
        candidates.append({field: normalized.get(field) for field in FIELDS})
    for row in expansion["candidates"]:
        candidates.append({field: row.get(field) for field in FIELDS})
    if len(candidates) != 27 or len({row["candidate_id"] for row in candidates}) != 27:
        raise SystemExit("expected exactly 27 unique candidate rows")
    if any(row["P9_classification"] not in expansion["classification_values"] for row in candidates):
        raise SystemExit("candidate has an invalid P9 classification")
    matrix = {
        "schema": "motorsim-p9-normalized-public-search-matrix-v1",
        "search_date": "2026-10-01", "candidate_count": len(candidates),
        "columns": FIELDS,
        "unknown_semantics": "null means that the inspected public source did not establish this field; it is not an inferred or fabricated value.",
        "classification_values": expansion["classification_values"],
        "search_sources": ["search.json (original 10-row record)", "search-expansion.json (17-row expansion)"],
        "candidates": candidates,
    }
    (SOURCE / "matrix.json").write_text(
        json.dumps(matrix, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(candidates)} normalized candidate rows to {SOURCE / 'matrix.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
