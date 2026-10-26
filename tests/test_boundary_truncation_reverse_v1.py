import pytest

from motorsim.integrated_2t import IntegratedEngine2T
from scripts.diagnostics.boundary_truncation_reverse_v1 import diagnose,V1,V2


def test_right_reservoir_boundary_recovers_second_order_without_time_steps(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('no time integration allowed')
    monkeypatch.setattr(IntegratedEngine2T,'step',forbidden)
    a,b=diagnose(80,V2),diagnose(160,V2)
    assert a['exact_right_face_connection_error']<1e-10
    assert b['exact_right_face_connection_error']<1e-10
    for k in (0,2):assert a['normalized_L1'][k]/b['normalized_L1'][k]>2**1.8
    old=diagnose(160,V1)
    assert b['right_mass_flux_relative_error']<old['right_mass_flux_relative_error']
