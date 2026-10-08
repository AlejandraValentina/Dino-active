"""P4 closure regression: frozen P0/P2/P3 evidence, no physical campaigns."""
import argparse,json
from pathlib import Path
from .p3_r1 import run as p3_regression
from .p2_campaign import ROOT,sha,write


def run(run_dir):
    art=Path(run_dir)/'artifacts';art.mkdir(parents=True,exist_ok=True)
    p3_regression(Path(run_dir)/'historical-regression')
    historical=json.loads((Path(run_dir)/'historical-regression/artifacts/r1.json').read_text(encoding='utf-8'))
    receipt=json.loads((ROOT/'docs/gasdynamic/p3_human_acceptance.json').read_text(encoding='utf-8'))
    p3base=ROOT/'results/p3-r1-20260918'
    inventory=json.loads((p3base/'inventory-all.json').read_text(encoding='utf-8'))
    frozen=all(sha(ROOT/p)==h for p,h in receipt['frozen_sha256'].items())
    intact=all(sha(p3base/p)==h for p,h in inventory.items()) and sha(p3base/'inventory-all.json')==receipt['evidence_inventory_sha256']
    b=json.loads((p3base/'p3b/artifacts/summary.json').read_text(encoding='utf-8'))
    c=json.loads((p3base/'p3c/artifacts/summary.json').read_text(encoding='utf-8'))
    checks=dict(historical=all(historical['checks'].values()),P3_frozen=frozen,P3_evidence=intact,P3B=b['passed'],P3C=c['passed'])
    write(art/'regression.json',dict(checks=checks,P3_accepted=receipt['state'],P3_evidence_files=len(inventory),new_finite_integrations=0))
    write(art/'result.json',dict(checks=[dict(id=k,passed=v,kind='numerical',reason='Frozen baseline offline regression') for k,v in checks.items()],metrics=dict(new_integrations=0),scientific_change_required=not all(checks.values())))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);run(p.parse_args().run_dir)
