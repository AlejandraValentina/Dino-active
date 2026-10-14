import copy
import json
from pathlib import Path

import pytest

from motorsim.engine_configuration import (create, identity, validate, sha256,
                                            resolve_for_operating_point)
from motorsim.engine_variants import (compare_configurations, escape_sections,
                                      replace_escape_sections, variant)
from motorsim.engine_project import (create_project, duplicate_project, load_project,
                                     save_project, compare_project_engines)
from motorsim.engine_results import import_report, compare

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "results/2t-commercial-core-20261002/fixtures/v1-prime-mesh/fixture_a_prime-mesh-0.json"


def configured(name="base"):
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return create(native_configuration=fixture["engine_configuration"],
                  mechanical_loss_model=fixture["mechanical_loss_model"],
                  operating_conditions={"reference_rpm": 3000, "load": 1.0,
                                        "fuel_id": "fixture-synthetic-fuel", "afr": 49.0},
                  provenance={"configuration_source": {"path": str(FIXTURE.relative_to(ROOT)),
                                                         "classification": fixture["classification"]},
                              "fuel": fixture["fuel_surrogate_snapshot"]},
                  display_name=name)


def test_fixture_adapter_hash_and_display_name():
    a, b = configured("A"), configured("B")
    assert validate(a).configuration_identity == validate(b).configuration_identity
    assert identity(a) == identity(b)
    assert a["native_configuration_sha256"] == sha256(a["native_configuration"])


def test_operating_point_adapter_binds_effective_rpm_and_solver_sources_without_mutating_project(tmp_path,monkeypatch):
    import sys
    from motorsim.engine_configuration import implementation_source_hashes
    doc=configured()
    effective=resolve_for_operating_point(doc,rpm=1000.0)
    assert effective["native_configuration"]["reference_rpm"]==1000.0
    assert effective["operating_conditions"]["reference_rpm"]==1000.0
    assert effective["native_configuration_sha256"]==sha256(effective["native_configuration"])
    assert effective["identity_sha256"]==sha256({k:v for k,v in effective.items() if k!="identity_sha256"})
    assert {"motorsim.integrated_2t","motorsim.mechanical","motorsim.powervalve",
            "motorsim.engine_configuration","motorsim.engineering_outputs",
            "motorsim.exploratory_workflow"}.issubset(effective["source_hashes"])
    assert len(effective["source_hashes"]) >= 24
    assert doc["native_configuration"]["reference_rpm"]==3000.0
    with pytest.raises(ValueError,match="positive finite"):
        resolve_for_operating_point(doc,rpm=float("inf"))
    source_hashes=implementation_source_hashes()
    package_root=tmp_path/"motorsim";package_root.mkdir()
    (package_root/"build.json").write_text(json.dumps({"workflow_source_hashes":source_hashes}),encoding="utf-8")
    monkeypatch.setattr(sys,"frozen",True,raising=False)
    monkeypatch.setattr(sys,"_MEIPASS",str(tmp_path),raising=False)
    packaged=implementation_source_hashes()
    assert packaged["dino.package_build_manifest"]
    assert {k:v for k,v in packaged.items() if k!="dino.package_build_manifest"}==source_hashes


def test_invalid_implicit_loss_and_mutated_native_rejected():
    doc = configured()
    missing = copy.deepcopy(doc); missing["mechanical_loss_model"] = None
    with pytest.raises((ValueError, TypeError)): validate(missing)
    bad = copy.deepcopy(doc); bad["native_configuration"]["max_cfl"] = float("nan")
    with pytest.raises(ValueError): validate(bad)
    bad = copy.deepcopy(doc); bad["native_configuration"]["max_cfl"] *= 0.5
    with pytest.raises(ValueError, match="hash mismatch"): validate(bad)
    bad = copy.deepcopy(doc); bad["native_configuration"]["unimplemented_component"] = {"kind": "invented"}
    bad["native_configuration_sha256"] = sha256(bad["native_configuration"])
    with pytest.raises(ValueError): validate(bad)


def test_exhaust_variant_builds_exact_frustum_mesh_without_solver_step():
    base = configured()
    sections = escape_sections(base)
    sections[1]["length_mm"] += 10
    changed = replace_escape_sections(base, sections, display_name="longer diffuser")
    base_solver=validate(base);changed_solver=validate(changed)
    base_exhaust=next(duct for duct in base_solver.ducts if duct.id=="exhaust")
    changed_exhaust=next(duct for duct in changed_solver.ducts if duct.id=="exhaust")
    assert len(changed_exhaust.mesh.volumes) == 5
    assert changed_exhaust.mesh.volumes != base_exhaust.mesh.volumes
    assert changed_solver.configuration_identity["configuration_sha256"] != base_solver.configuration_identity["configuration_sha256"]
    assert identity(changed) != identity(base)
    deltas = compare_project_engines(create_project("p", base, variants={"longer": changed}), "longer")
    assert any("geometry_identity/chamber/sections/1/length_mm" in item["path"] for item in deltas)
    with pytest.raises(ValueError, match="discontinuous"):
        broken = copy.deepcopy(sections); broken[1]["inlet_diameter_mm"] += 1
        replace_escape_sections(base, broken)
    tuned = variant(base, display_name="higher reference speed",
                    operating_conditions_patch={"reference_rpm": 3200})
    assert tuned["operating_conditions"]["reference_rpm"] == 3200
    assert tuned["native_configuration"] == base["native_configuration"]


def test_packaged_exhaust_sensitivity_fixture_changes_only_diffuser_geometry_and_derived_mesh():
    path=ROOT/"examples/projects/dino-2t-exhaust-comparison.dino2t.json"
    project=load_project(path)
    base=project["variants"]["Escape original"]
    changed=project["variants"]["Escape modified +20 mm"]
    assert base["operating_conditions"]==changed["operating_conditions"]
    assert base["mechanical_loss_model"]==changed["mechanical_loss_model"]
    for key in ("fuel_coupled_combustion","fuel_combustion_events","fuel_combustion_event",
                "thermal_system","thermal_load","port_binding","slider_crank",
                "external_boundary_model","initial_chambers"):
        assert base["native_configuration"].get(key)==changed["native_configuration"].get(key),key
    differences=compare_configurations(base,changed)
    paths={item["path"] for item in differences}
    assert "/native_configuration/geometry_identity/chamber/sections/1/length_mm" in paths
    assert len(paths)==11
    assert all(path.startswith(("/native_configuration/geometry_identity/chamber/sections/1/length_mm",
                               "/native_configuration/ducts/",
                               "/native_configuration/duct_species/exhaust/")) for path in paths)
    assert (escape_sections(base)[1]["length_mm"],escape_sections(changed)[1]["length_mm"])==(180.0,200.0)
    a,b=validate(base),validate(changed)
    assert a.exhaust.mesh.n==b.exhaust.mesh.n==5
    assert a.exhaust.mesh.volumes!=b.exhaust.mesh.volumes
    assert a.exhaust.mesh.faces!=b.exhaust.mesh.faces


def test_project_roundtrip_duplicate_and_external_reference(tmp_path):
    base = configured()
    project = create_project("demo", base, result_references=[{
        "path": "external/report.json", "identity_sha256": "a"*64,
        "artifact_sha256": "b"*64, "classification": "SYNTHETIC"}])
    path = tmp_path / "project.json"
    digest = save_project(path, project)
    assert len(digest) == 64 and load_project(path) == project
    duplicate = duplicate_project(project, project_id="copy", display_name="renamed")
    assert duplicate["base_identity_sha256"] == project["base_identity_sha256"]


def test_curve_comparison_preserves_invalid_gaps_and_hard_gates(tmp_path):
    def report(prefix, classification="PERIOD_1"):
        rows = []
        for rpm, cls, status, val in [(1000, "NUMERICAL_INVALID", "NOT_VALID_FOR_NONCONVERGED_POINT", None),
                                      (2000, classification, "DEFINED", 12.0)]:
            row = {"point_id": f"{prefix}@{rpm}", "variant_id": prefix, "rpm": rpm,
                   "classification": cls, "result_sha256": "a"*64,
                   "point_configuration_sha256": "b"*64, "hard_gates": {"all_passed": True}}
            for field in ("brake_power", "brake_torque", "IMEP", "FMEP", "BMEP", "ISFC", "BSFC"):
                row[field] = val if status == "DEFINED" else None
                row[field+"_status"] = status
                row[field+"_reason"] = "synthetic test gap" if val is None else None
            rows.append(row)
        return {"schema": "FULL_RPM_SWEEP_V1_IMPL2_AGGREGATE_REPORT_V1",
                "experimental_validation": "NOT_PERFORMED", "implementation_identity_sha256": "c"*64,
                "preregistration_sha256": "d"*64, "producer_sha256": "e"*64,
                "units": {"brake_power":"kW", "brake_torque":"N·m", "IMEP":"kPa", "FMEP":"kPa", "BMEP":"kPa", "ISFC":"g/kWh", "BSFC":"g/kWh"}, "points": rows}
    files=[]
    for idx, prefix in enumerate(("A", "B")):
        path=tmp_path/f"{idx}.json"; path.write_text(json.dumps(report(prefix)),encoding="utf-8"); files.append(path)
    result = compare({"A": import_report(files[0]), "B": import_report(files[1])}, ("power",))
    series=result["metrics"]["power"]["curves"]["A"]
    assert series[0]["value"] is None and series[0]["classification"] == "NUMERICAL_INVALID"
    assert series[1]["value"] == 12.0 and series[1]["hard_gates"] == {"all_passed": True}
    assert result["interpolation"] == "NONE"


def test_csv_requires_matching_metadata_and_checks_rows(tmp_path):
    payload = {"schema": "FULL_RPM_SWEEP_V1_IMPL2_AGGREGATE_REPORT_V1",
               "experimental_validation": "NOT_PERFORMED", "implementation_identity_sha256": "c"*64,
               "preregistration_sha256": "d"*64, "producer_sha256": "e"*64,
               "csv": "curves.csv", "units": {"brake_power":"kW", "brake_torque":"N*m", "IMEP":"kPa", "FMEP":"kPa", "BMEP":"kPa", "ISFC":"g/kWh", "BSFC":"g/kWh"},
               "points": []}
    for variant_id in ("A", "B"):
        row = {"point_id": variant_id+"@1000", "variant_id": variant_id, "rpm": 1000,
               "classification":"PERIOD_1", "result_sha256":"a"*64,
               "point_configuration_sha256":"b"*64, "hard_gates": {}}
        for field in ("brake_power", "brake_torque", "IMEP", "FMEP", "BMEP", "ISFC", "BSFC"):
            row[field]=1.0; row[field+"_status"]="DEFINED"; row[field+"_reason"]=None
        payload["points"].append(row)
    meta=tmp_path/"report.json"; meta.write_text(json.dumps(payload),encoding="utf-8")
    cols=["point_id","variant_id","classification","result_sha256","point_configuration_sha256"]
    for field in ("brake_power", "brake_torque", "IMEP", "FMEP", "BMEP", "ISFC", "BSFC"):
        cols.extend([field,field+"_status"])
    import csv
    csv_path=tmp_path/"curves.csv"
    with csv_path.open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=cols);writer.writeheader()
        for row in payload["points"]:
            writer.writerow({k: row[k] for k in cols})
    assert len(import_report(csv_path,metadata_path=meta)["points"]) == 2
    with pytest.raises(ValueError,match="requires its companion"):
        import_report(csv_path)
