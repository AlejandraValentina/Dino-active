import json
from pathlib import Path

RESULT = Path("results/p4-r11-20260922")
for N in [300,350,400]:
    p = RESULT / f"temporal_metrics_N{N}.json"
    data = json.loads(p.read_text())
    # Check types
    for c in data.get("temporal",[]):
        d2 = c.get("d2_passed")
        if isinstance(d2, str):
            print(f"N{N} cycle {c['cycle']} d2_passed is string {d2!r} bool({d2})={bool(d2)}")
        elif isinstance(d2, bool):
            pass
        else:
            print(f"N{N} cycle {c['cycle']} d2_passed type {type(d2)} value {d2}")

# Also check decision
dec = json.loads((RESULT/"decision.json").read_text())
print("decision first_3x", dec.get("first_3x"))
# Check parity
import json as js
for N in [350,400]:
    p = RESULT / f"temporal_metrics_N{N}.json"
    data = js.loads(p.read_text())
    # Recompute streaks with corrected bool
    def to_bool(v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower()=="true"
        return bool(v)
    # Global streak
    max_streak=0; cur=0; first=None
    for c in data["temporal"]:
        if to_bool(c["d2_passed"]):
            cur+=1
            if cur==3 and first is None:
                first=c["cycle"]-2
            max_streak=max(max_streak,cur)
        else:
            cur=0
    print(f"N{N} corrected global first_3x {first} max {max_streak}")
    # Even/odd
    for parity in ["even","odd"]:
        seq = [c for c in data["temporal"] if (c["cycle"]%2==0) == (parity=="even")]
        max_s=0; cur=0; first_p=None
        for c in seq:
            if to_bool(c["d2_passed"]):
                cur+=1
                if cur==3 and first_p is None:
                    first_p=c["cycle"]-4
                max_s=max(max_s,cur)
            else:
                cur=0
        print(f" N{N} {parity} max {max_s} first {first_p}")

# Check numpy bool serialization
import numpy as np
print("np.bool_(False) json default=str:", json.dumps({"a": np.bool_(False)}, default=str))
print("np.bool_(False) bool:", bool(np.bool_(False)), "converted:", bool(np.bool_(False))==False)
print("bool('False'):", bool("False"))
