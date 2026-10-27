import json
from pathlib import Path
import math
import pytest

ROOT=Path(__file__).resolve().parents[1]/'results/predictive-reliability-v1'


def test_actual_stage_fluxes_close_each_subsystem_with_reaction_sources():
    r=json.loads((ROOT/'exhaust-composition-plateau-v1/interface-audit.json').read_text())
    assert r['terminal_state_and_ledger_exact']
    assert set(r['balances'])=={'cylinder','crankcase','intake','primary','secondary','boost','exhaust'}
    for b in r['balances'].values():
        for a,z,t,s in zip(b['start'],b['end'],b['transport'],b['source']):
            assert z-a-t-s==pytest.approx(0.,abs=2e-17)
    source=r['balances']['cylinder']['source']
    assert source[0]<0 and source[1]<0 and source[2]==0 and source[3]>0
    assert math.fsum(source)==pytest.approx(0.,abs=2e-17)


def test_signed_and_gross_interface_species_transport_are_consistent():
    r=json.loads((ROOT/'exhaust-composition-plateau-v1/interface-audit.json').read_text())
    for ends in r['interfaces'].values():
        for t in ends.values():
            for net,pos,neg in zip(t['net'],t['positive'],t['negative']):
                assert pos>=0 and neg<=0
                assert net==pytest.approx(pos+neg,abs=2e-17)
            assert sum(t['net'])==pytest.approx(t['positive_mass']+t['negative_mass'],abs=2e-17)
    assert r['interfaces']['exhaust']['left']['negative_mass']<0
    assert r['exhaust_gross_in_kg']==0
