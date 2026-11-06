"""Self-consistent synthetic presentation fixtures, never scientific evidence."""
from copy import deepcopy
import math
from pathlib import Path
import json
from motorsim.dino4t.config import canonical_hash
from motorsim.dino4t.artifacts import publish_primary
from motorsim.desktop.four_stroke_artifacts import publish_desktop_run, require_verified_run
from motorsim.source_provenance import capture_source_identity
from test_c01_c03_provenance_boundary import _committed_tree


def endpoint_factory(root):
    source = root/'synthetic-source'
    _committed_tree(source)
    identity = capture_source_identity(source)
    original = sorted(Path('results/dino4t-ab-engineering-v1/runs/runs').glob('*/artifacts/summary.json'))[0]
    seed = json.loads(original.read_text(encoding='utf-8'))
    cfg = json.loads(original.with_name('config_resolved.json').read_text(encoding='utf-8'))
    serial = 0
    def make(side, *, mutate=None, power=None):
        nonlocal serial
        serial += 1
        config = deepcopy(cfg); summary = deepcopy(seed)
        config['identifier'] = 'SYNTHETIC_PRESENTATION_'+side
        if side == 'B': config['intake_valve']['lift']['max_lift_mm'] = 8.0
        summary['config_sha256'] = canonical_hash(config)
        summary['source_identity'] = deepcopy(identity)
        summary['code_commit'] = identity['code_commit']; summary['code_dirty'] = False
        summary['runtime_environment'] = {k: 'SYNTHETIC_TEST_ENV' for k in ('python','implementation','platform','numpy','scipy')}
        g = config['geometry']; rpm = config['operating_point']['rpm']; f = summary['final_cycle']
        displacement = math.pi/4*(g['bore_mm']*.001)**2*g['stroke_mm']*.001
        watts = (25.0 if side == 'A' else 24.0)*1000 if power is None else power*1000
        f['brake_power_kW'] = watts/1000; f['brake_torque_Nm'] = watts/(2*math.pi*rpm/60)
        f['bmep_bar'] = watts/(displacement*rpm/120)/1e5
        f['imep_net_bar'] = f['bmep_bar'] + f['fmep_bar']; f['work_net_J'] = f['imep_net_bar']*1e5*displacement
        if mutate: mutate(summary,config)
        summary['config_sha256'] = canonical_hash(config)
        run = root/f'synthetic-{side}-{serial}'
        artifacts = publish_primary(run/'artifacts',summary,config,
            {'theta':[0.,360.,720.], 'p':[100000.,200000.,100000.],
             'p_intake_port':[100000.]*3,'p_exhaust_port':[100000.]*3},
            origin={'kind':'SYNTHETIC_PRESENTATION_FIXTURE','not_a_simulation':True})
        ref = publish_desktop_run(run,{'summary':summary,'artifacts':artifacts},'synthetic-test',
                                  'Lift 8 mm' if side=='B' else '',run_id=run.name)
        # Return originals even for deliberately invalid fixtures so the consumer
        # itself must reject them. Never bypass original-byte verification.
        assessment = require_verified_run(ref) if mutate is None else None
        return assessment.endpoint() if assessment else {'summary':summary,'config':config,'reference':ref,'meta':{}}
    return make
