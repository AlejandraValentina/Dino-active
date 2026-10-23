"""Offline reduction checks; these tests do not advance the physical solver."""
import hashlib
import json

import pytest

from scripts.diagnostics.analyze_periodicity_blocker_v1 import analyze, reduce_cycle


def sample_cycle():
    return dict(cycle=1, cylinder_work_J=34., mechanical_estimate=None,
        closure_snapshots={'exhaust': {'cylinder_species_kg': [3e-5, 3e-6, 0., 4e-5]}},
        observables=dict(ducts={'exhaust': [dict(mass_kg=.002, total_energy_J=1000.,
            pressure_Pa=101325., temperature_K=600., species_mass_fractions=[.1,.01,.7,.19])]},
            global_species_kg=[.0002,.00002,.0014,.00038]),
        periodicity_streak=0, wall_s=7., conservation={'relative': {'mass': 1e-15}},
        comparison=None)


def test_reduction_separates_inventory_from_fraction():
    c=sample_cycle()
    c['comparison']={'metrics': {'ducts.exhaust[0].species.residual':
        {'passed': False, 'value': .028, 'threshold': .002}}}
    r=reduce_cycle(c)
    assert r['exhaust_species_kg'][2] == pytest.approx(.0014)
    assert r['failed_groups'] == {'species.residual': 1}
    assert r['worst_threshold_ratio'] == 14.


def test_analysis_rejects_tampered_diagnostic(tmp_path):
    c=sample_cycle()
    data=json.dumps({'samples': [{'angle_deg': i/2} for i in range(720)]}).encode()
    (tmp_path/'cycle-001-diagnostics.json').write_bytes(data)
    c['diagnostic_artifact_sha256']=hashlib.sha256(data).hexdigest()
    bindings={'configuration_canonical_sha256': 'fixture'}
    cp=json.dumps({'next_cycle': 2, 'bindings': bindings, 'periodicity_history': [{}]}).encode()
    (tmp_path/'checkpoint.json').write_bytes(cp)
    manifest=dict(cycles=[c], bindings=bindings, checkpoint_artifact='checkpoint.json',
        checkpoint_sha256=hashlib.sha256(cp).hexdigest(), status='MAX_CYCLES_NONCONVERGED',
        periodicity='NOT_EVALUATED', continuation=None, wall_s=7.,solver_step_wall_s=6.,
        processing_wall_s=1.,peak_rss_mib=100.,rejected_trials={})
    path=tmp_path/'manifest.json';path.write_text(json.dumps(manifest))
    assert analyze(path)['next_cycle'] == 2
    (tmp_path/'cycle-001-diagnostics.json').write_bytes(data+b' ')
    with pytest.raises(AssertionError):
        analyze(path)
