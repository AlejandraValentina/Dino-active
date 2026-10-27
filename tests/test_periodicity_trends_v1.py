from scripts.diagnostics.periodicity_trends_v1 import analyze


def test_threshold_ratios_and_recent_trends_do_not_confuse_counts_with_progress():
    cycles=[]
    for i in range(4):
        metrics={'ducts.exhaust[0].pressure':{'value':8-i,'threshold':2.,'passed':False},
                 'global_species.residual':{'value':1+i,'threshold':1.,'passed':i==0}}
        cycles.append(dict(cycle=i+1,cylinder_work_J=1.,comparison={'metrics':metrics},detector_outcome={'outcomes':{}}))
    r=analyze(cycles)
    by={x['observable']:x for x in r['observables']}
    assert by['ducts.exhaust[0].pressure']['trend']=='improving'
    assert by['global_species.residual']['trend']=='worsening'
    assert by['ducts.exhaust[0].pressure']['last_ratio']==2.5
    assert r['cycles'][-1]['lags']['lag1']['all']['failed']==2


def test_zero_error_is_stable_and_finite():
    c=dict(cycle=1,cylinder_work_J=0.,comparison={'metrics':{'work':{'value':0.,'threshold':.005,'passed':True}}},detector_outcome={'outcomes':{}})
    # At least two distinct cycles are required for a slope fit.
    r=analyze([c,c|{'cycle':2}]);assert r['observables'][0]['trend']=='stable'
