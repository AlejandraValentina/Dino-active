from copy import deepcopy

import pytest

from motorsim.gas1d.eos import IdealGas
from scripts.diagnostics.compare_integrated_port_v2 import terminal_differences


def state():
    e=IdealGas()
    q=e.conservative((1.,0.,1e5,1.))
    return dict(chambers={'cylinder':[1.,2.,3.]},ducts={'pipe':[q]},
        species={'chambers':{'cylinder':[.5,.5,0.,0.]},
                 'ducts':{'pipe':[[.5,.5,0.,0.]]}})


def test_comparison_is_exact_at_equal_states_and_ignores_only_redundant_proxy():
    a=state();b=deepcopy(a)
    q=b['ducts']['pipe'][0]
    b['ducts']['pipe'][0]=(*q[:3],q[0]+1e-15)
    assert terminal_differences(a,b,IdealGas())[0][0]==0.


def test_comparison_detects_species_difference_without_changing_pressure():
    a=state();b=deepcopy(a)
    b['species']['ducts']['pipe'][0]=[.4,.6,0.,0.]
    errors=terminal_differences(a,b,IdealGas())
    assert errors[0][0]==pytest.approx(.1)
    assert 'fraction' in errors[0][1]
