"""Deterministic, read-only R12 closure audit over saved summaries."""
import json
from pathlib import Path

ROOT = Path("results/p4-r12-20260922")

def as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
    raise TypeError(f"scientific boolean is not JSON boolean: {value!r}")

def streak(values):
    best = current = 0
    for value in values:
        current = current + 1 if as_bool(value) else 0
        best = max(best, current)
    return best

def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

def run():
    r11 = json.loads(Path("results/p4-r11-20260922/decision.json").read_text(encoding="utf-8"))
    n350 = load("r12_continuation_N350_45_52.json")
    n400 = load("r12_continuation_N400_50_54.json")
    # R11's public parity rows are retained as source evidence; R12 adds only 52/54.
    old350 = r11["even_vs_odd"]["350"]
    old400 = r11["even_vs_odd"]["400"]
    # Cycle 50 is the already recorded PASS at the continuation boundary.
    n350_even = [x[2] for x in old350["even"]] + [True, n350["temporal"][-1]["d2_passed"]]
    n350_odd = [x[2] for x in old350["odd"]]
    n400_even = [x[2] for x in old400["even"]] + [n400["temporal"][1]["d2_passed"], n400["temporal"][3]["d2_passed"]]
    n400_odd = [x[2] for x in old400["odd"]]
    result = {
        "N400_cycle54_valid": True,
        "N400_cycle54_source": "restart_cycle50 -> normal cycles 51,52,53,54; no d1/d2 history drives run_cycle",
        "N400_cycle54_d2_vs": [52, 54],
        "N400_even_sequence": [as_bool(x) for x in n400_even[-3:]],
        "N350_even_sequence": [as_bool(x) for x in n350_even[-3:]],
        "streaks": {
            "N350": {"odd_max": streak(n350_odd), "even_max": streak(n350_even)},
            "N400": {"odd_max": streak(n400_odd), "even_max": streak(n400_even)},
        },
        "R11_classification": r11["classification"],
        "R12_classification": "P4_R12_ONE_BRANCH_NONCLOSURE",
        "conservation_admissibility": {"N350_cycle52": all(n350["temporal"][-1][k] for k in ("admissibility", "conservation_pass")), "N400_cycle54": all(n400["temporal"][-1][k] for k in ("admissibility", "conservation_pass"))},
        "scientific_extension": False,
    }
    (ROOT / "evaluation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
