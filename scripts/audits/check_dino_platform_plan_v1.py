"""Check audit/plan dependencies, authority and nonactivation; no solver work."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def check(root: Path) -> dict:
    def read(path):
        return json.loads((root / path).read_text(encoding="utf-8"))

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root)

    plan = read("results/platform-scientific-reliability-v1/plan.json")
    status = read("results/2t-commercial-core-20261002/program-status.json")
    findings = read("results/platform-integration-audit-v1/findings.json")
    supersession = read("results/platform-scientific-reliability-v1/supersession.json")
    checks = []

    def require(condition, message):
        if not condition:
            raise AssertionError(message)
        checks.append(message)

    tasks = {t["id"]: t for t in plan["tasks"]}
    require(len(tasks) == len(plan["tasks"]), "unique prospective stage IDs")
    visited, active = set(), set()

    def visit(tid):
        require(tid in tasks, "dependency exists: " + tid)
        if tid in active:
            raise AssertionError("dependency cycle at " + tid)
        if tid in visited:
            return
        active.add(tid)
        for dep in tasks[tid]["dependencies"]:
            visit(dep)
        active.remove(tid)
        visited.add(tid)

    for tid in tasks:
        visit(tid)
    require(len(visited) == len(tasks), "prospective dependency graph is acyclic")
    covered = {fid for task in tasks.values() for fid in task["audit_findings"]}
    expected = {x["id"] for x in findings["findings"]}
    require(covered == expected, "all and only recorded findings have future acceptance owners")
    obligations = {x["id"] for x in findings["scientific_obligations"]}
    require(set(plan["scientific_obligation_coverage"]) == obligations,
            "all independent scientific obligations have stage coverage")
    require(all(x in tasks for v in plan["scientific_obligation_coverage"].values() for x in v),
            "scientific obligation references resolve")
    require(set(plan["maturity"]) == {"2T", "4T"}, "separate native-family maturity records")
    require(all(m["experimental_validation"] == "NOT_PERFORMED" and m["predictive"] == "NOT_CLAIMED"
                for m in plan["maturity"].values()), "no unearned measured or predictive claim")
    require(not plan["implementation_or_campaign_activation"] and all(
        t["execution_state"] == "NOT_ACTIVATED" and t["budget_authorization"] == "NONE_GRANTED_BY_THIS_PLAN"
        for t in tasks.values()), "plan grants no implementation or campaign budget")
    require(tasks["N2"]["dependencies"] == [] and tasks["N4R"]["dependencies"] == [],
            "independent evidence/reference preparation does not wait on Desktop integration")
    require(set(tasks["N4S"]["dependencies"]) == {"C01", "C03", "C04"},
            "study assurance depends on the relevant contracts")
    successor = status["next_objective"]
    require(successor["id"] == plan["id"] and not successor["owner_approved"]
            and not successor["execution_activated"] and successor["planning_authorized"],
            "authoritative successor is planning-only and cannot auto-run")
    require(status["roadmap_control"]["roadmap"] == successor["roadmap"]
            and set(status["roadmap_control"]["scope"]) == {"COMMON", "2T", "4T"},
            "authoritative roadmap has unified scope")
    old = status["roadmap_control_history"][-1]["previous"]
    old_sha = hashlib.sha256(json.dumps(old, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(old_sha == supersession["predecessor_control_canonical_sha256"],
            "previous scheduling authority archived without reinterpretation")
    freeze = plan["audit_freeze_commit"]
    require(subprocess.run(["git", "merge-base", "--is-ancestor", freeze, "HEAD"], cwd=root).returncode == 0,
            "committed audit freeze precedes planning source")
    audit_root = root / "results/platform-integration-audit-v1"
    manifest = read("results/platform-integration-audit-v1/audit-evidence-sha256.json")
    require(all(hashlib.sha256((audit_root / k).read_bytes()).hexdigest() == v
                for k, v in manifest["files"].items()), "all frozen audit bytes still match")
    require(not git("diff", "--name-only", "8b371e2", "--", "motorsim", "packaging", "configs", "examples", "tests").strip(),
            "audit/replan introduced no product, physics, config or test changes")
    p9 = "openspec/changes/p9-experimental-validation/specs/p9-experimental-validation/spec.md"
    require(hashlib.sha256(git("show", "HEAD:" + p9)).hexdigest() == plan["immutable_constraints"]["p9_canonical_sha256"],
            "frozen P9 canonical bytes preserved")
    require(git("rev-parse", "main").decode().strip() == "5e4ba4d27a8156d2cf3b07d633ae92c6dea213c5"
            and git("rev-parse", "work/dino4t-ab-engineering-v1").decode().strip() == "8b371e247498f94255e88ab8d35dbae7b7c2ba6b",
            "reviewed official and A/B refs unchanged")
    return {"schema": "DINO_PLATFORM_PLAN_CONSISTENCY_V1", "result": "PASS_PLANNING_ONLY",
            "audit_freeze_commit": freeze, "future_stage_count": len(tasks),
            "finding_coverage_count": len(covered), "checks": list(dict.fromkeys(checks)),
            "solver_runs": 0, "scientific_or_product_acceptance": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = check(args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("result", "future_stage_count", "finding_coverage_count", "solver_runs")}))
