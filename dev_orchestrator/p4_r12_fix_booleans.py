import json
from pathlib import Path

def fix_file(p):
    data=json.loads(p.read_text())
    # Fix temporal
    for c in data.get("temporal",[]):
        for k in ["d1_passed","d2_passed","admissibility","conservation_pass"]:
            v=c.get(k)
            if isinstance(v, str):
                if v.lower()=="true":
                    c[k]=True
                elif v.lower()=="false":
                    c[k]=False
                else:
                    c[k]=bool(v)
            elif isinstance(v, (int,float)) and v in (0,1):
                # Keep as bool if it's 0/1 from numpy?
                pass
            # Also handle numpy bool-like
            try:
                import numpy as np
                if isinstance(v, np.bool_):
                    c[k]=bool(v)
            except:
                pass
        # Also fix d2_details etc. not needed
    p.write_text(json.dumps(data, indent=2))
    print(f"Fixed {p}")

for N in [300,350,400]:
    p=Path(f"results/p4-r11-20260922/temporal_metrics_N{N}.json")
    if p.exists():
        fix_file(p)
    # Also fix campaign r11_result.json
    for stage in ["campaign_stageA"]:
        for job in [f"G1_N{N}_A"]:
            p2=Path(f"results/p4-r11-20260922/{stage}/jobs/{job}/r11_result.json")
            if p2.exists():
                fix_file(p2)

# Also fix decision
p=Path("results/p4-r11-20260922/decision.json")
if p.exists():
    data=json.loads(p.read_text())
    # decision has first_3x etc. not booleans, but check
    p.write_text(json.dumps(data, indent=2))
    print("checked decision")

print("Done")
