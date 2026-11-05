"""Read-only, revision-bound artifact/history audit. Never executes a solver."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import zipfile

MAIN = "5e4ba4d27a8156d2cf3b07d633ae92c6dea213c5"
AB = "8b371e247498f94255e88ab8d35dbae7b7c2ba6b"
BUILD = "07849322b8ad0115defb28de2ad5f23b8bfacd55"
P9 = "openspec/changes/p9-experimental-validation/specs/p9-experimental-validation/spec.md"
P9_SHA = "79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def audit(root: Path) -> dict:
    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", *args], cwd=root)

    windows = root / "results/dino4t-ab-engineering-v1/windows"
    candidate = json.loads((windows / "candidate-acceptance.json").read_text(encoding="utf-8"))
    build = json.loads((windows / "build.json").read_text(encoding="utf-8"))
    manifest_checks = []
    for line in (windows / "evidence-sha256.txt").read_text(encoding="ascii").splitlines():
        expected, name = line.split("  ", 1)
        p = windows / name
        rel = p.relative_to(root).as_posix()
        manifest_checks.append({"file": name, "expected": expected,
            "worktree_sha256": digest(p.read_bytes()), "git_blob_sha256": digest(git("show", f"{AB}:{rel}"))})

    artifact_checks = []
    pair_root = root / "results/dino4t-ab-engineering-v1/runs"
    comparison = json.loads((pair_root / "comparison.json").read_text(encoding="utf-8"))
    for endpoint in comparison["endpoints"]:
        local = pair_root / "runs" / endpoint["run_id"] / "artifacts"
        checks = {}
        for name, field in (("summary.json", "result_sha256"), ("config_resolved.json", "config_sha256"),
                            ("trace_last_cycle.csv", "trace_sha256")):
            p = local / name
            raw = p.read_bytes() if p.is_file() else None
            # The public config identity hashes canonical parsed JSON; summary
            # and trace identities bind raw artifact bytes. Never confuse them.
            identity = (digest(json.dumps(json.loads(raw), sort_keys=True,
                        separators=(",", ":")).encode())
                        if raw is not None and name == "config_resolved.json"
                        else digest(raw) if raw is not None else None)
            checks[name] = {"exists": p.is_file(), "expected": endpoint[field],
                "actual": identity, "raw_sha256": digest(raw) if raw is not None else None,
                "identity_mode": "canonical_json" if name == "config_resolved.json" else "raw_bytes"}
        artifact_checks.append({"run_id": endpoint["run_id"], "checks": checks,
            "summary_path_absolute": Path(endpoint["summary_path"]).is_absolute(),
            "periodicity": endpoint["periodicity"]["status"], "code_commit": endpoint["code_commit"]})

    archive = Path(candidate["candidate"]["zip_path"])
    exe = Path(candidate["candidate"]["exe_path"])
    archive_result = {"available": archive.is_file(), "expected_sha256": candidate["candidate"]["zip_sha256"]}
    if archive.is_file():
        archive_result["actual_sha256"] = digest(archive.read_bytes())
        with zipfile.ZipFile(archive) as z:
            archive_result["crc_failure"] = z.testzip()
            example = next(n for n in z.namelist() if n.endswith("configs/dino4t/example_single_cylinder_500cc.json"))
            actual = z.read(example)
            original = git("show", f"{BUILD}:configs/dino4t/example_single_cylinder_500cc.json")
            archive_result["example"] = {"member": example, "raw_sha256": digest(actual),
                "git_blob_sha256": digest(original), "semantic_equal_to_source": json.loads(actual) == json.loads(original)}
    spec = importlib.util.spec_from_file_location("audit_build_provenance", root / "packaging/build_provenance.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    current_manifest = module.input_manifest(root)
    current_by_path = {item["path"]: item for item in current_manifest["files"]}
    differing = [x["path"] for x in build["packaged_inputs"]
                 if current_by_path.get(x["path"]) != x]
    example_path = "configs/dino4t/example_single_cylinder_500cc.json"
    p9 = {rev: digest(git("show", f"{rev}:{P9}")) for rev in (MAIN, AB)}
    return {"schema": "DINO_PLATFORM_READ_ONLY_AUDIT_V1", "solver_runs": 0,
        "revisions": {"main": MAIN, "ab": AB, "package_source": BUILD,
            "main_is_ancestor_of_ab": subprocess.run(["git", "merge-base", "--is-ancestor", MAIN, AB], cwd=root).returncode == 0,
            "ab_commits_not_in_main": git("rev-list", "--count", f"{MAIN}..{AB}").decode().strip(),
            "product_delta_main_to_ab": git("diff", "--name-only", MAIN, AB, "--", "motorsim", "packaging").decode().splitlines()},
        "p9": {"expected_canonical_sha256": P9_SHA, "git_blobs": p9, "all_match": all(x == P9_SHA for x in p9.values())},
        "windows_evidence": {"files": manifest_checks,
            "raw_worktree_matches": sum(x["expected"] == x["worktree_sha256"] for x in manifest_checks),
            "git_blob_matches": sum(x["expected"] == x["git_blob_sha256"] for x in manifest_checks)},
        "actual_ab_artifacts": artifact_checks,
        "comparison": {"id": comparison["comparison_id"], "classification": comparison["classification"],
            "design_changes": comparison["design_changes"]},
        "archive": archive_result,
        "exe": {"available": exe.is_file(), "expected_sha256": candidate["candidate"]["exe_sha256"],
            "actual_sha256": digest(exe.read_bytes()) if exe.is_file() else None},
        "package_manifest": {"recorded_count": build["packaged_input_count"],
            "recorded_sha256": build["packaged_input_manifest_sha256"], "current_raw_sha256": current_manifest["sha256"],
            "raw_input_paths_differing_from_built_tree": differing,
            "example_in_recorded_manifest": any(x["path"] == example_path for x in build["packaged_inputs"]),
            "example_in_current_manifest": any(x["path"] == example_path for x in current_manifest["files"]),
            "note": "An exact manifest is provenance for included inputs only; false/partial coverage is a separate finding."}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "solver_runs": 0, "p9_match": result["p9"]["all_match"],
        "raw_evidence_matches": result["windows_evidence"]["raw_worktree_matches"],
        "git_evidence_matches": result["windows_evidence"]["git_blob_matches"],
        "package_example_is_covered": result["package_manifest"]["example_in_current_manifest"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
