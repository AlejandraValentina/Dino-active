import gzip
import hashlib
import csv
import io
import json
import shutil
import hashlib as _hashlib
from pathlib import Path

import pytest

from motorsim.p9_pipeline import (
    _audit_uncertainty, _shape_gate, audit_dataset, geometry_volumes_m3,
    indicated_power_2t_w, integrate_indicated_work_j,
)
from motorsim.p9_synthetic import GEOMETRY, RPM_POINTS, generate_fixture


@pytest.fixture(scope="session")
def fixtures(tmp_path_factory):
    root = tmp_path_factory.mktemp("p9-synthetic")
    return {name: generate_fixture(root / name, name)
            for name in ("pass", "fail", "inconclusive")}


def _copy(source, tmp_path):
    target = tmp_path / "dataset"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    return target


def _manifest(folder):
    path = folder / "manifest.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    return path, value


def _save_manifest(path, value):
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def _rebind_file(folder, manifest, role, mutate):
    record = next(item for item in manifest["raw_files"] if item["role"] == role)
    path = folder / record["path"]
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        rows = stream.read().splitlines()
    rows = mutate(rows)
    with path.open("wb") as binary:
        with gzip.GzipFile(fileobj=binary, mode="wb", filename="", mtime=0) as zipped:
            zipped.write(("\n".join(rows) + "\n").encode("utf-8"))
    content = path.read_bytes()
    record["size_bytes"] = len(content)
    record["sha256"] = hashlib.sha256(content).hexdigest()


def test_synthetic_pass_runs_all_recomputed_gates_but_never_p9_pass(fixtures):
    result = audit_dataset(fixtures["pass"])
    assert result["status"] == "P9_PIPELINE_QUALIFIED_WITH_SYNTHETIC_DATA"
    assert result["dataset_kind"] == "SYNTHETIC"
    assert result["synthetic_label"] == "SYNTHETIC_PIPELINE_QUALIFICATION_ONLY"
    assert result["experimental_validation"] == "NOT_PERFORMED"
    assert result["summary"]["performance_gates_pass"] is True
    assert result["summary"]["point_count"] == 7
    assert "P9_PASS" not in result["status"]
    assert all(row["work_exp_j"] > 0 and row["work_sim_j"] > 0 for row in result["operating_points"])


def test_generator_is_byte_deterministic(tmp_path):
    first = generate_fixture(tmp_path / "a", "pass")
    second = generate_fixture(tmp_path / "b", "pass")
    hashes = lambda root: {path.name: _hashlib.sha256(path.read_bytes()).hexdigest()
                           for path in root.iterdir() if path.is_file()}
    assert hashes(first) == hashes(second)


def test_synthetic_fail_and_inconclusive_fixtures(fixtures):
    assert audit_dataset(fixtures["fail"])["status"] == "PIPELINE_EXPECTED_FAIL"
    assert audit_dataset(fixtures["inconclusive"])["status"] == "PIPELINE_EXPECTED_INCONCLUSIVE"


def test_unreadable_manifest_and_corrupt_gzip_return_inconclusive(fixtures, tmp_path):
    folder = _copy(fixtures["pass"], tmp_path)
    (folder / "manifest.json").write_text("not json", encoding="utf-8")
    assert audit_dataset(folder)["status"] == "P9_INCONCLUSIVE"

    folder = _copy(fixtures["pass"], tmp_path / "gzip")
    path, manifest = _manifest(folder)
    record = manifest["raw_files"][0]
    broken = b"not a gzip file"
    (folder / record["path"]).write_bytes(broken)
    record["size_bytes"] = len(broken)
    record["sha256"] = hashlib.sha256(broken).hexdigest()
    _save_manifest(path, manifest)
    result = audit_dataset(folder)
    assert result["status"] == "PIPELINE_EXPECTED_INCONCLUSIVE"
    assert "cannot read raw CSV" in result["issues"][0]


def test_period_two_keeps_branches_separate_and_compares_their_work_mean(fixtures, tmp_path):
    folder = _copy(fixtures["pass"], tmp_path)
    path, manifest = _manifest(folder)
    record = next(item for item in manifest["raw_files"] if item["role"] == "simulation_primary")
    sim_path = folder / record["path"]
    with gzip.open(sim_path, "rt", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    text = io.StringIO(newline="")
    writer = csv.writer(text, lineterminator="\n")
    writer.writerow(("rpm", "branch", "cycle", "angle_deg", "pressure_pa"))
    for row in rows:
        for branch, scale in (("A", 0.999), ("B", 1.001)):
            writer.writerow((row["rpm"], branch, row["cycle"], row["angle_deg"],
                             format(float(row["pressure_pa"]) * scale, ".12g")))
    raw_bytes = gzip.compress(text.getvalue().encode("utf-8"), mtime=0)
    sim_path.write_bytes(raw_bytes)
    record["size_bytes"] = len(raw_bytes)
    record["sha256"] = hashlib.sha256(raw_bytes).hexdigest()
    for point in manifest["operating_points"]:
        point["p9a"]["period"] = 2
        point["p9a"]["branches"] = {
            branch: {"branch_id": branch, "qualified": True,
                     "simulation_sha256": record["sha256"]}
            for branch in ("A", "B")}
    _save_manifest(path, manifest)
    result = audit_dataset(folder)
    assert result["status"] == "P9_PIPELINE_QUALIFIED_WITH_SYNTHETIC_DATA"
    assert all(row["period"] == 2 and set(row["simulation_branch_work_j"]) == {"A", "B"}
               for row in result["operating_points"])
    assert all(row["work_sim_j"] == pytest.approx(
        sum(row["simulation_branch_work_j"].values()) / 2)
        for row in result["operating_points"])


def test_explicit_synthetic_p9_pass_attempt_is_rejected(fixtures):
    result = audit_dataset(fixtures["pass"], requested_status="P9_PASS")
    assert result["status"] == "PIPELINE_EXPECTED_INCONCLUSIVE"
    assert "synthetic dataset is ineligible for P9_PASS" in result["issues"][0]


def test_geometry_slider_crank_and_closed_pv_work_sign():
    volume = geometry_volumes_m3(GEOMETRY, [0.0, 180.0, 360.0])
    assert volume[0] == volume[-1]
    assert volume[1] > volume[0]
    work = integrate_indicated_work_j(
        [2.0e6, 1.0e6, 0.5e6, 2.0e6], [1.0e-5, 1.0e-4, 1.0e-4, 1.0e-5])
    assert work > 0


def test_two_stroke_power_conversion_is_one_cycle_per_revolution():
    assert indicated_power_2t_w(120.0, 6000) == pytest.approx(12_000.0)
    assert indicated_power_2t_w(120.0, 6000, cylinders=2) == pytest.approx(24_000.0)
    assert indicated_power_2t_w(120.0, 6000) != pytest.approx(6_000.0)  # 4T half-rate trap


@pytest.mark.parametrize("bad", ["True", "nan", "inf", "-inf"])
def test_boolean_nan_and_infinite_pressure_are_rejected(fixtures, tmp_path, bad):
    folder = _copy(fixtures["pass"], tmp_path)
    path, manifest = _manifest(folder)
    def mutate(rows):
        fields = rows[1].split(",")
        fields[-1] = bad
        rows[1] = ",".join(fields)
        return rows
    _rebind_file(folder, manifest, "experiment_raw", mutate)
    _save_manifest(path, manifest)
    result = audit_dataset(folder)
    assert result["status"] == "PIPELINE_EXPECTED_INCONCLUSIVE"
    assert result["issues"]


def test_wrong_units_and_degrees_radians_mismatch_are_rejected(fixtures, tmp_path):
    folder = _copy(fixtures["pass"], tmp_path)
    path, manifest = _manifest(folder)
    manifest["raw_files"][0]["units"]["pressure"] = "bar"
    _save_manifest(path, manifest)
    assert "units" in audit_dataset(folder)["issues"][0]

    folder = _copy(fixtures["pass"], tmp_path / "second")
    path, manifest = _manifest(folder)
    manifest["raw_files"][0]["units"]["angle"] = "rad"
    _save_manifest(path, manifest)
    assert "units" in audit_dataset(folder)["issues"][0]


def test_rpm_text_duplicate_missing_and_duplicate_points_are_rejected(fixtures, tmp_path):
    folder = _copy(fixtures["pass"], tmp_path)
    path, manifest = _manifest(folder)
    _rebind_file(folder, manifest, "experiment_raw",
                 lambda rows: [rows[0], rows[1].replace("3000,", "rpm-text,", 1), *rows[2:]])
    _save_manifest(path, manifest)
    assert audit_dataset(folder)["status"] == "PIPELINE_EXPECTED_INCONCLUSIVE"

    folder = _copy(fixtures["pass"], tmp_path / "missing")
    path, manifest = _manifest(folder)
    _rebind_file(folder, manifest, "experiment_raw",
                 lambda rows: [rows[0], *[row for row in rows[1:] if not row.startswith("3000,")]])
    _save_manifest(path, manifest)
    assert "missing or unlisted operating points" in audit_dataset(folder)["issues"][0]

    folder = _copy(fixtures["pass"], tmp_path / "duplicate")
    path, manifest = _manifest(folder)
    manifest["operating_points"][1]["rpm"] = manifest["operating_points"][0]["rpm"]
    _save_manifest(path, manifest)
    assert "unique RPM" in audit_dataset(folder)["issues"][0]


def test_unlisted_raw_rpm_point_cannot_be_silently_omitted(fixtures, tmp_path):
    folder = _copy(fixtures["pass"], tmp_path)
    path, manifest = _manifest(folder)
    _rebind_file(folder, manifest, "experiment_raw",
                 lambda rows: [*rows, "13000,0,0,101325"])
    _save_manifest(path, manifest)
    result = audit_dataset(folder)
    assert "missing or unlisted operating points" in result["issues"][0]


def test_missing_geometry_and_fewer_than_five_points_are_inconclusive(fixtures, tmp_path):
    folder = _copy(fixtures["pass"], tmp_path)
    path, manifest = _manifest(folder)
    manifest["geometry"] = None
    _save_manifest(path, manifest)
    assert audit_dataset(folder)["status"] == "PIPELINE_EXPECTED_INCONCLUSIVE"

    folder = _copy(fixtures["pass"], tmp_path / "few")
    path, manifest = _manifest(folder)
    manifest["operating_points"] = manifest["operating_points"][:4]
    _save_manifest(path, manifest)
    assert "at least five" in audit_dataset(folder)["issues"][0]


def test_hash_mismatch_changed_raw_and_unsafe_path_are_inconclusive(fixtures, tmp_path):
    folder = _copy(fixtures["pass"], tmp_path)
    path, manifest = _manifest(folder)
    file = folder / manifest["raw_files"][0]["path"]
    file.write_bytes(file.read_bytes() + b"tamper")
    assert "size" in audit_dataset(folder)["issues"][0]

    folder = _copy(fixtures["pass"], tmp_path / "wrong-hash")
    path, manifest = _manifest(folder)
    manifest["raw_files"][0]["sha256"] = "0" * 64
    _save_manifest(path, manifest)
    assert "SHA-256" in audit_dataset(folder)["issues"][0]

    folder = _copy(fixtures["pass"], tmp_path / "unsafe")
    path, manifest = _manifest(folder)
    manifest["raw_files"][0]["path"] = "../outside.csv"
    _save_manifest(path, manifest)
    assert "safe relative" in audit_dataset(folder)["issues"][0]


def test_same_size_raw_pressure_change_without_manifest_rebind_is_rejected(fixtures, tmp_path):
    folder = _copy(fixtures["pass"], tmp_path)
    _, manifest = _manifest(folder)
    path = folder / manifest["raw_files"][0]["path"]
    content = bytearray(path.read_bytes())
    content[-16] = content[-16] ^ 1
    path.write_bytes(content)
    result = audit_dataset(folder)
    assert result["status"] == "PIPELINE_EXPECTED_INCONCLUSIVE"
    assert "SHA-256" in result["issues"][0]


def test_nonconsecutive_cycle_ids_are_rejected(fixtures, tmp_path):
    folder = _copy(fixtures["pass"], tmp_path)
    path, manifest = _manifest(folder)
    _rebind_file(folder, manifest, "experiment_raw", lambda rows: [
        rows[0], *[row.replace(",1,", ",100,", 1) if row.startswith("3000,1,") else row
                   for row in rows[1:]]])
    _save_manifest(path, manifest)
    result = audit_dataset(folder)
    assert "consecutive sequence" in result["issues"][0]


def test_synthetic_claim_cannot_be_hidden_by_experimental_dataset_kind(fixtures, tmp_path):
    folder = _copy(fixtures["pass"], tmp_path)
    path, manifest = _manifest(folder)
    manifest["dataset_kind"] = "EXPERIMENTAL"
    manifest["provenance"] = {"source_type": "EXPERIMENTAL_SOURCE", "authorized": True}
    _save_manifest(path, manifest)
    result = audit_dataset(folder)
    assert result["status"] == "PIPELINE_EXPECTED_INCONCLUSIVE"
    assert "synthetic classification markers" in result["issues"][0]


def test_altered_claimed_work_and_summary_are_never_authoritative(fixtures, tmp_path):
    baseline = audit_dataset(fixtures["pass"])
    folder = _copy(fixtures["pass"], tmp_path)
    path, manifest = _manifest(folder)
    manifest["untrusted_claimed_summary"] = {"mape": 999.0, "status": "P9_PASS"}
    for point in manifest["operating_points"]:
        point["claimed_work_exp_j"] = -1e99
        point["claimed_relative_error"] = 1e99
    _save_manifest(path, manifest)
    altered = audit_dataset(folder)
    assert altered["status"] == baseline["status"]
    assert altered["summary"] == baseline["summary"]
    assert [r["work_exp_j"] for r in altered["operating_points"]] == [
        r["work_exp_j"] for r in baseline["operating_points"]]


def test_uncertainty_cycle_count_mismatch_and_rpm_alignment_over_one_percent(fixtures, tmp_path):
    folder = _copy(fixtures["pass"], tmp_path)
    path, manifest = _manifest(folder)
    manifest["uncertainty"]["cycle_count"] = 49
    _save_manifest(path, manifest)
    assert "uncertainty cycle_count" in audit_dataset(folder)["issues"][0]

    folder = _copy(fixtures["pass"], tmp_path / "rpm-mismatch")
    path, manifest = _manifest(folder)
    manifest["operating_points"][0]["simulation_rpm"] = 1.02 * RPM_POINTS[0]
    _save_manifest(path, manifest)
    assert "exceeds 1%" in audit_dataset(folder)["issues"][0]


def test_contract_allows_experimental_uncertainty_to_be_explicitly_unknown():
    uncertainty = _audit_uncertainty(
        {"status": "EXPERIMENTAL_UNCERTAINTY_UNKNOWN", "cycle_count": 50,
         "note": "transducer uncertainty was not reported"},
        expected_cycles=50, synthetic=False)
    assert uncertainty["status"] == "EXPERIMENTAL_UNCERTAINTY_UNKNOWN"
    assert uncertainty["note"] == "transducer uncertainty was not reported"


def test_shape_gate_applies_only_to_a_unique_interior_experimental_peak():
    rows = [
        {"rpm_exp": 3000, "power_exp_w": 3, "power_sim_w": 3, "rpm_sim": 3000},
        {"rpm_exp": 6000, "power_exp_w": 8, "power_sim_w": 8, "rpm_sim": 6000},
        {"rpm_exp": 9000, "power_exp_w": 5, "power_sim_w": 5, "rpm_sim": 9000},
    ]
    assert _shape_gate(rows) == (True, True, 6000, 6000)
    rows[0]["power_exp_w"] = 10
    passed, applies, _, _ = _shape_gate(rows)
    assert passed and not applies
    rows[0]["power_exp_w"] = rows[1]["power_exp_w"] = 8
    passed, applies, _, _ = _shape_gate(rows)
    assert passed and not applies


def test_incomplete_periodic_qualification_is_not_a_p9_decision(fixtures, tmp_path):
    folder = _copy(fixtures["pass"], tmp_path)
    path, manifest = _manifest(folder)
    manifest["operating_points"][0]["p9a"]["gates"]["restart"] = False
    _save_manifest(path, manifest)
    assert "incomplete P9-A" in audit_dataset(folder)["issues"][0]


def test_period_two_without_two_hashed_branches_is_inconclusive(fixtures, tmp_path):
    folder = _copy(fixtures["pass"], tmp_path)
    path, manifest = _manifest(folder)
    manifest["operating_points"][0]["p9a"]["period"] = 2
    _save_manifest(path, manifest)
    result = audit_dataset(folder)
    assert result["status"] == "PIPELINE_EXPECTED_INCONCLUSIVE"
    assert "incomplete P9-A" in result["issues"][0]


def test_changed_summary_fields_do_not_change_manifest_or_raw_hashes(fixtures):
    result = audit_dataset(fixtures["pass"])
    assert set(result["raw_sha256"]) == {"experiment_raw", "simulation_primary"}
    assert result["summary"]["mape"] < .10
